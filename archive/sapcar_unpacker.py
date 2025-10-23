#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAPCAR Unpacker (Windows, Thonny)
- Scegli un eseguibile che INIZI con "SAPCAR" (es. SAPCAR.exe, SAPCAR_721-80000935.exe, ...)
- Seleziona uno o più .SAR (file singoli o intera cartella)
- Scegli la cartella di destinazione
- Estrae con: "./<NOME_SAPCAR> -xvf <pkg> -R <dest>" via PowerShell (così `./` funziona)
- Converte i percorsi con spazi in short path (8.3) per evitare errori di SAPCAR
- Pulsante "Testa kernel (disp+work -v)" che cerca disp+work ed esegue la versione
- Mostra solo la sezione principale dell'output di disp+work

NOVITÀ:
  * Estrae prima i pacchetti che iniziano con "SAPEXE*" (es. SAPEXE_, SAPEXEDB_) e poi gli altri
  * Barra di avanzamento + ETA
  * Pulsante "Crea .tar della destinazione" per generare un archivio TAR della cartella estratta
  * Pulsante "Apri cartella destinazione" (apre Esplora File sulla cartella di output)
  * Controllo aggiornamenti da GitHub Releases
  * Salvataggio/ricarica dell’ultimo SAPCAR scelto
  * ✅ Supporto a nomi di SAPCAR che iniziano con "SAPCAR" (non per forza "SAPCAR.exe")
"""

import os
import sys
import shutil
import subprocess
import threading
import tarfile
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import time
from tkinter import ttk

__version__ = "1.1.4"  # <--- aggiorna ad ogni release
GITHUB_USER = "Pasqualeim"   # <-- metti il tuo username GitHub
GITHUB_REPO = "sapcar-unpacker"          # <-- metti il nome del repo

import json
import webbrowser
import urllib.request
import urllib.error


# ---------- Update checker (GitHub Releases) ----------
def _parse_ver(v: str):
    v = v.strip().lstrip("vV")
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts)

def get_latest_release():
    """Ottiene (tag, url) dalla Release più recente del repo GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": f"{GITHUB_REPO}/{__version__}"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    tag = data.get("tag_name") or data.get("name") or ""
    html_url = data.get("html_url") or f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases"
    return tag, html_url

def _notify_update(parent, latest_tag, rel_url):
    if messagebox.askyesno(
        "Aggiornamento disponibile",
        f"È disponibile la versione {latest_tag} (tu hai {__version__}).\nAprire la pagina Releases su GitHub?"
    ):
        webbrowser.open(rel_url)

def check_updates_async(parent):
    def worker():
        try:
            latest_tag, rel_url = get_latest_release()
            if latest_tag and _parse_ver(latest_tag) > _parse_ver(__version__):
                parent.after(0, lambda: _notify_update(parent, latest_tag, rel_url))
        except Exception:
            pass
    threading.Thread(target=worker, daemon=True).start()


# ---------- Impostazioni: salva/leggi SOLO l'ultimo SAPCAR scelto ----------
def _settings_file() -> str:
    base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SapcarUnpacker")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base, "settings.json")


# ---------- Utilità percorso / esecuzione ----------
def to_short_path(path: str) -> str:
    """Converte un percorso Windows in DOS 8.3 (short path). Se fallisce, restituisce l'originale."""
    try:
        import ctypes
        _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
        _GetShortPathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        buf_len = 4096
        buf = ctypes.create_unicode_buffer(buf_len)
        res = _GetShortPathNameW(path, buf, buf_len)
        if res and buf.value:
            return buf.value
        return path
    except Exception:
        return path

def get_powershell_exe() -> str:
    """Trova PowerShell (Windows PowerShell o PowerShell 7)."""
    for candidate in ("powershell", "powershell.exe", "pwsh", "pwsh.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    return "powershell"

def run_cmd(cwd, cmd, log_callback):
    """Esegue un comando (lista argomenti) e streamma stdout/stderr nel log."""
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in proc.stdout:
            log_callback(line.rstrip("\n"))
        return proc.wait()
    except FileNotFoundError as e:
        log_callback(f"[ERRORE] File non trovato: {e}")
        return 127
    except Exception as e:
        log_callback(f"[ERRORE] {e}")
        return 1


# ---------- Ricerca & filtro disp+work ----------
def find_dispwork(base_dir: str):
    """
    Cerca disp+work/disp+work.exe ricorsivamente in base_dir.
    Preferisce path che contengono 'ntamd64' o 'exe'.
    """
    base_dir = os.path.abspath(base_dir)
    candidates = []

    for root, dirs, files in os.walk(base_dir):
        for name in files:
            low = name.lower()
            if low in ("disp+work", "disp+work.exe"):
                full = os.path.join(root, name)
                try:
                    st = os.stat(full)
                    mtime = st.st_mtime
                except Exception:
                    mtime = 0.0
                prio = 0
                lower_path = full.lower()
                if "ntamd64" in lower_path:
                    prio += 3
                if f"{os.sep}exe{os.sep}" in lower_path or lower_path.endswith(f"{os.sep}exe") or f"{os.sep}uc{os.sep}" in lower_path:
                    prio += 2
                candidates.append((prio, mtime, -len(full), full))

    if not candidates:
        for cand in ("disp+work.exe", "disp+work"):
            p = os.path.join(base_dir, cand)
            if os.path.isfile(p):
                return p
        return None

    candidates.sort(reverse=True)
    return candidates[0][3]

def extract_dispwork_main_section(lines):
    """
    Estrae solo la parte principale dell'output di 'disp+work -v':
    - dalla riga "disp+work information" inclusa (compresi i separatori)
    - fino alla riga prima di "disp+work patch information" (esclusa).
    Se i marker non si trovano, restituisce l'output originale.
    """
    norm = [(i, (line or ""), (line or "").strip().lower()) for i, line in enumerate(lines)]
    start_idx = None
    end_idx = None

    for i, raw, low in norm:
        if low == "disp+work information":
            start_idx = i
            if i > 0 and set(norm[i - 1][1].strip()) <= set("-"):
                start_idx = i - 1
            break

    if start_idx is None:
        return lines

    for i, raw, low in norm[start_idx + 1:]:
        if low == "disp+work patch information":
            end_idx = i
            if i > 0 and set(norm[i - 1][1].strip()) <= set("-"):
                end_idx = i - 1
            break

    if end_idx is None:
        end_idx = len(lines)

    return lines[start_idx:end_idx]


# ---------- App GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SAPCAR Unpacker")
        self.geometry("980x660")
        self.resizable(True, True)

        self.sapcar_path = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.sar_files = []

        # Row 0: SAPCAR (può chiamarsi SAPCAR*, non per forza SAPCAR.exe)
        frm0 = tk.Frame(self)
        frm0.pack(fill="x", padx=10, pady=6)
        tk.Label(frm0, text="Eseguibile SAPCAR*:").pack(side="left")
        tk.Entry(frm0, textvariable=self.sapcar_path).pack(side="left", fill="x", expand=True, padx=8)
        tk.Button(frm0, text="Scegli...", command=self.choose_sapcar).pack(side="left")

        # Row 1: SAR files
        frm1 = tk.Frame(self)
        frm1.pack(fill="x", padx=10, pady=6)
        tk.Label(frm1, text="Pacchetti .SAR:").pack(side="left")
        self.sar_count_lbl = tk.Label(frm1, text="0 selezionati")
        self.sar_count_lbl.pack(side="left", padx=8)
        tk.Button(frm1, text="Aggiungi .SAR...", command=self.choose_sar_files).pack(side="left")
        tk.Button(frm1, text="Aggiungi cartella .SAR...", command=self.choose_sar_folder).pack(side="left", padx=6)
        tk.Button(frm1, text="Svuota lista", command=self.clear_sar_files).pack(side="left", padx=6)

        # Row 2: Dest dir
        frm2 = tk.Frame(self)
        frm2.pack(fill="x", padx=10, pady=6)
        tk.Label(frm2, text="Cartella di estrazione:").pack(side="left")
        tk.Entry(frm2, textvariable=self.dest_dir).pack(side="left", fill="x", expand=True, padx=8)
        tk.Button(frm2, text="Scegli cartella...", command=self.choose_dest_dir).pack(side="left")

        # Row 3: Actions (griglia su 2 righe)
        frm3 = tk.LabelFrame(self, text="Azioni")
        frm3.pack(fill="x", padx=10, pady=6)
        for i in range(3):
            frm3.grid_columnconfigure(i, weight=1, uniform="act")

        self.run_btn   = tk.Button(frm3, text="Esegui Estrazione", command=self.run_extraction)
        self.test_btn  = tk.Button(frm3, text="Testa kernel (disp+work -v)", command=self.test_kernel)
        self.export_btn= tk.Button(frm3, text="Esporta script PowerShell", command=self.export_batch)
        self.tar_btn   = tk.Button(frm3, text="Crea .tar della destinazione", command=self.create_tar_of_destination)
        self.open_btn  = tk.Button(frm3, text="Apri cartella destinazione", command=self.open_destination)

        self.run_btn.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=6, pady=(4, 6))
        self.test_btn.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        self.export_btn.grid(row=1, column=1, sticky="nsew", padx=6, pady=4)
        self.tar_btn.grid(row=1, column=2, sticky="nsew", padx=6, pady=4)
        self.open_btn.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=6, pady=(4, 2))

        # Row 3.5: Progress
        frmP = tk.Frame(self)
        frmP.pack(fill="x", padx=10, pady=(0, 6))
        self.progress_var = tk.DoubleVar(value=0.0)  # percentuale 0..100
        self.progress_bar = ttk.Progressbar(frmP, maximum=100.0, variable=self.progress_var)
        self.progress_bar.pack(fill="x", side="left", expand=True)
        self.progress_lbl = tk.Label(frmP, text="Pronto")
        self.progress_lbl.pack(side="left", padx=10)

        # Row 4: Log
        self.log = scrolledtext.ScrolledText(self, height=20, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=10)

        # Carica ultimo SAPCAR salvato e hook di chiusura
        self.load_last_sapcar()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Avvia controllo aggiornamenti 1.5s dopo l’apertura, senza bloccare la GUI
        self.after(1500, lambda: check_updates_async(self))

    # ----- UI helpers -----
    def log_line(self, line: str):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def choose_sapcar(self):
        path = filedialog.askopenfilename(
            title="Seleziona eseguibile SAPCAR*",
            filetypes=[
                ("SAPCAR*", "SAPCAR*.*"),
                ("Eseguibili", "*.exe"),
                ("Tutti i file", "*.*"),
            ]
        )
        if path:
            name = os.path.basename(path)
            if not name.upper().startswith("SAPCAR"):
                messagebox.showerror(
                    "File non valido",
                    "L'eseguibile deve iniziare con 'SAPCAR' (es. SAPCAR.exe, SAPCAR_721-8000xxxx.exe)."
                )
                return
            self.sapcar_path.set(path)
            self.save_last_sapcar()

    def choose_sar_files(self):
        files = filedialog.askopenfilenames(
            title="Seleziona uno o più file .SAR",
            filetypes=[("SAP Archives", "*.SAR;*.sar"), ("Tutti i file", "*.*")]
        )
        if files:
            self._append_sar_files(files)

    def choose_sar_folder(self):
        """Seleziona una cartella e aggiunge tutti i .SAR in essa (non ricorsivo)."""
        folder = filedialog.askdirectory(title="Seleziona cartella contenente file .SAR")
        if not folder:
            return
        found = []
        try:
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if os.path.isfile(path) and name.lower().endswith(".sar"):
                    found.append(path)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile leggere la cartella:\n{e}")
            return
        if not found:
            messagebox.showinfo("Nessun file", "Nella cartella selezionata non ci sono file .SAR.")
            return
        self._append_sar_files(found)

    def _append_sar_files(self, new_files):
        """Aggiunge file alla lista, de-duplicando e preservando l'ordine."""
        self.sar_files.extend(list(new_files))
        seen = set()
        uniq = []
        for f in self.sar_files:
            if f not in seen:
                uniq.append(f)
                seen.add(f)
        self.sar_files = uniq
        self.sar_count_lbl.config(text=f"{len(self.sar_files)} selezionati")
        self.log_line(f"Aggiunti {len(new_files)} file .SAR (totale: {len(self.sar_files)})")

    def clear_sar_files(self):
        self.sar_files = []
        self.sar_count_lbl.config(text="0 selezionati")
        self.log_line("Lista .SAR svuotata.")

    def choose_dest_dir(self):
        d = filedialog.askdirectory(title="Scegli la cartella di destinazione")
        if d:
            self.dest_dir.set(d)

    def validate_inputs(self):
        sapcar = self.sapcar_path.get().strip('" ')
        if not sapcar or not os.path.isfile(sapcar):
            messagebox.showerror("Errore", "Seleziona un eseguibile SAPCAR* valido.")
            return False
        # Enforce: deve iniziare con SAPCAR
        if not os.path.basename(sapcar).upper().startswith("SAPCAR"):
            messagebox.showerror("Errore", "L'eseguibile deve iniziare con 'SAPCAR'.")
            return False
        if not self.sar_files:
            messagebox.showerror("Errore", "Aggiungi almeno un file .SAR (singolo o da cartella).")
            return False
        dest = self.dest_dir.get().strip('" ')
        if not dest:
            messagebox.showerror("Errore", "Seleziona una cartella di destinazione.")
            return False
        try:
            os.makedirs(dest, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile creare/accedere alla cartella di destinazione:\n{e}")
            return False
        return True

    # ----- Progress bar helpers -----
    def _fmt_time(self, sec: float) -> str:
        if sec is None or sec <= 0 or sec == float("inf"):
            return "--:--"
        m, s = divmod(int(sec), 60)
        if m >= 100:
            return f"{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def init_progress(self, total: int):
        """Inizializza stato avanzamento & ETA."""
        self._total_pkgs = max(0, int(total))
        self._done_pkgs = 0
        self._start_ts = time.time()
        self._durations = []
        self._ma_window = 6
        self.progress_var.set(0.0)
        self.progress_lbl.config(text="Pronto")
        self.update_idletasks()

    def tick_progress(self, last_duration: float | None):
        """Aggiorna stato dopo un pacchetto estratto (OK o errore) e stima ETA."""
        self._done_pkgs = min(self._done_pkgs + 1, self._total_pkgs)
        if last_duration and last_duration > 0:
            self._durations.append(last_duration)
            if len(self._durations) > self._ma_window:
                self._durations = self._durations[-self._ma_window:]
        perc = 0.0 if self._total_pkgs == 0 else (self._done_pkgs / self._total_pkgs) * 100.0
        eta_sec = None
        if self._durations and self._total_pkgs > self._done_pkgs:
            avg = sum(self._durations) / len(self._durations)
            remaining = self._total_pkgs - self._done_pkgs
            eta_sec = avg * remaining

        def _apply():
            self.progress_var.set(perc)
            self.progress_lbl.config(text=f"{self._done_pkgs}/{self._total_pkgs} • {int(perc)}% • ETA {self._fmt_time(eta_sec)}")
        self.after(0, _apply)

    def finish_progress(self):
        """Imposta al 100% e stato finale."""
        def _apply():
            self.progress_var.set(100.0)
            elapsed = time.time() - (self._start_ts or time.time())
            self.progress_lbl.config(text=f"Completato • {self._fmt_time(elapsed)}")
        self.after(0, _apply)

    # ----- Estrazione pacchetti -----
    def run_extraction(self):
        if not self.validate_inputs():
            return

        sapcar = os.path.abspath(self.sapcar_path.get().strip('" '))
        sapcar_dir = os.path.dirname(sapcar)
        sapcar_name = os.path.basename(sapcar)  # <-- usa il nome reale scelto (SAPCAR*)
        dest_long = self.dest_dir.get().strip('" ')
        sar_list = list(self.sar_files)

        # Ordina: prima file che iniziano con "SAPEXE*" (case-insensitive), poi gli altri
        def sort_key(p):
            base = os.path.basename(p).upper()
            return (0 if base.startswith("SAPEXE") else 1, base)

        sar_list_sorted = sorted(sar_list, key=sort_key)
        first_count = sum(1 for p in sar_list_sorted if os.path.basename(p).upper().startswith("SAPEXE"))

        self.run_btn.config(state="disabled")
        self.log_line("== Inizio estrazione ==")
        self.log_line(f"SAPCAR: {sapcar}")
        self.log_line(f"Working dir: {sapcar_dir}")
        self.log_line(f"Destinazione: {dest_long}")
        self.log_line(f"Pacchetti: {len(sar_list_sorted)} (priorità SAPEXE*: {first_count})")

        ps_exe = get_powershell_exe()

        def worker():
            overall_rc = 0
            dest_norm = os.path.normpath(dest_long)
            dest_short = to_short_path(dest_norm)

            # Inizializza progress bar totale
            self.init_progress(len(sar_list_sorted))

            for idx, sar in enumerate(sar_list_sorted, start=1):
                self.log_line(f"\n[{idx}/{len(sar_list_sorted)}] Estrazione di: {sar}")
                sar_norm = os.path.normpath(sar)
                sar_short = to_short_path(sar_norm)

                if sar_short == sar_norm:
                    self.log_line("(info) ShortPath non disponibile per l'archivio: uso percorso lungo tra virgolette.")
                if dest_short == dest_norm:
                    self.log_line("(info) ShortPath non disponibile per la destinazione: uso percorso lungo tra virgolette.")

                sar_arg = sar_short if (sar_short == to_short_path(sar_short) and " " not in sar_short) else f'"{sar_norm}"'
                dest_arg = dest_short if (dest_short == to_short_path(dest_short) and " " not in dest_short) else f'"{dest_norm}"'

                # PowerShell: --% = pass-through | usa il NOME REALE di SAPCAR
                ps_cmd = f'& ./"{sapcar_name}" --% -xvf {sar_arg} -R {dest_arg}'
                cmd = [ps_exe, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]

                self.log_line(f"Comando PowerShell: {ps_cmd} (cwd={sapcar_dir})")

                t0 = time.time()
                rc = run_cmd(sapcar_dir, cmd, self.log_line)
                elapsed = time.time() - t0

                if rc == 0:
                    self.log_line(f"[OK] Estratto: {os.path.basename(sar_norm)}")
                else:
                    overall_rc = rc or overall_rc
                    self.log_line(f"[ERRORE] RC={rc} su: {os.path.basename(sar_norm)}")

                # Aggiorna progress bar / ETA
                self.tick_progress(elapsed)

            if overall_rc == 0:
                self.log_line("\n== Completato senza errori ==")
                messagebox.showinfo("Fatto", "Estrazione completata senza errori.")
            else:
                self.log_line("\n== Completato con errori ==")
                messagebox.showwarning("Completato con errori", "Alcune estrazioni non sono andate a buon fine. Controlla il log.")

            # Chiudi progress
            self.finish_progress()
            self.run_btn.config(state="normal")

        threading.Thread(target=worker, daemon=True).start()

    # ----- Test kernel (disp+work -v) -----
    def test_kernel(self):
        dest = self.dest_dir.get().strip('" ')
        if not dest:
            messagebox.showerror("Errore", "Seleziona prima la cartella di estrazione.")
            return

        disp = find_dispwork(dest)
        if not disp:
            messagebox.showerror(
                "disp+work non trovato",
                "Non è stato trovato 'disp+work' nella cartella di destinazione.\n"
                "Controlla di aver estratto SAPEXE / SAPEXEDB correttamente."
            )
            return

        disp_dir = os.path.dirname(disp)
        disp_name = os.path.basename(disp)
        ps_exe = get_powershell_exe()

        self.log_line(f"\n== Test kernel: eseguo {disp} -v ==")

        def worker():
            buf = []

            def collect_only(line: str):
                buf.append(line)

            rc = None
            for flag in ("-v", "-V"):
                ps_cmd = f'& ./"{disp_name}" {flag}'
                cmd = [ps_exe, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
                self.log_line(f"Comando PowerShell: {ps_cmd} (cwd={disp_dir})")
                rc = run_cmd(disp_dir, cmd, collect_only)
                if rc == 0:
                    break
                else:
                    self.log_line(f"(info) disp+work ha restituito RC={rc} con {flag}. Provo alternativa...")

            # Mostra solo la sezione principale
            lines = extract_dispwork_main_section(buf)
            self.log_line("\n== Sezione principale (filtrata) ==")
            for ln in lines:
                self.log_line(ln)

            if rc == 0:
                messagebox.showinfo("Test kernel", "disp+work ha risposto correttamente.")
            else:
                messagebox.showwarning("Test kernel", "disp+work non ha restituito 0. Verifica dipendenze/variabili d'ambiente.")

        threading.Thread(target=worker, daemon=True).start()

    # ----- Export script PS -----
    def export_batch(self):
        if not self.validate_inputs():
            return
        sapcar = os.path.abspath(self.sapcar_path.get().strip('" '))
        sapcar_dir = os.path.dirname(sapcar)
        sapcar_name = os.path.basename(sapcar)  # <-- usa il nome reale scelto (SAPCAR*)
        dest_norm = os.path.normpath(self.dest_dir.get().strip('" '))
        dest_short = to_short_path(dest_norm)

        lines = [f'Set-Location -Path "{sapcar_dir}"', ""]
        # Stesso ordinamento: prima SAPEXE*, poi resto
        def sort_key(p):
            base = os.path.basename(p).upper()
            return (0 if base.startswith("SAPEXE") else 1, base)

        for sar in sorted(self.sar_files, key=sort_key):
            sar_norm = os.path.normpath(sar)
            sar_short = to_short_path(sar_norm)
            sar_arg = sar_short if (sar_short == to_short_path(sar_short) and " " not in sar_short) else f'"{sar_norm}"'
            dest_arg = dest_short if (dest_short == to_short_path(dest_short) and " " not in dest_short) else f'"{dest_norm}"'
            # Usa il nome reale dell'eseguibile
            lines.append(f'& ./"{sapcar_name}" --% -xvf {sar_arg} -R {dest_arg}')

        save_to = filedialog.asksaveasfilename(
            title="Salva script PowerShell",
            defaultextension=".ps1",
            filetypes=[("PowerShell script", "*.ps1")]
        )
        if save_to:
            try:
                with open(save_to, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                messagebox.showinfo("Esportato", f"Script PowerShell salvato in:\n{save_to}")
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare il file:\n{e}")

    # ----- Crea archivio .tar della destinazione -----
    def create_tar_of_destination(self):
        """Crea un .tar della cartella di destinazione (leggibile anche su Linux)."""
        dest_dir = self.dest_dir.get().strip('" ')
        if not dest_dir:
            messagebox.showerror("Errore", "Seleziona la cartella di destinazione prima di creare il .tar.")
            return
        dest_dir = os.path.normpath(dest_dir)
        if not os.path.isdir(dest_dir):
            messagebox.showerror("Errore", f"La cartella di destinazione non esiste:\n{dest_dir}")
            return

        default_name = os.path.basename(dest_dir.rstrip("\\/")) or "estrazione"
        save_to = filedialog.asksaveasfilename(
            title="Salva archivio TAR",
            initialfile=f"{default_name}.tar",
            defaultextension=".tar",
            filetypes=[("TAR archive", "*.tar")]
        )
        if not save_to:
            return

        self.log_line(f"\n== Creazione archivio TAR ==")
        self.log_line(f"Sorgente: {dest_dir}")
        self.log_line(f"Archivio: {save_to}")

        def worker():
            try:
                save_abs = os.path.abspath(save_to)
                base = os.path.basename(dest_dir.rstrip("\\/"))

                with tarfile.open(save_abs, "w") as tar:
                    for root, dirs, files in os.walk(dest_dir):
                        for name in files:
                            full = os.path.join(root, name)
                            if os.path.abspath(full) == save_abs:
                                continue
                            arcname = os.path.join(base, os.path.relpath(full, start=dest_dir)).replace("\\", "/")
                            self.log_line(f"Aggiungo: {arcname}")
                            tar.add(full, arcname=arcname, recursive=False)
                        for d in dirs:
                            dir_full = os.path.join(root, d)
                            rel_arc = os.path.join(base, os.path.relpath(dir_full, start=dest_dir)).replace("\\", "/")
                            ti = tarfile.TarInfo(rel_arc)
                            ti.type = tarfile.DIRTYPE
                            try:
                                ti.mtime = int(os.path.getmtime(dir_full))
                            except Exception:
                                ti.mtime = int(time.time())
                            tar.addfile(ti)

                self.log_line("[OK] Archivio TAR creato.")
                messagebox.showinfo("TAR creato", f"Archivio creato:\n{save_to}")
            except Exception as e:
                self.log_line(f"[ERRORE] Creazione TAR fallita: {e}")
                messagebox.showerror("Errore", f"Creazione TAR fallita:\n{e}")

        threading.Thread(target=worker, daemon=True).start()

    # ----- Apri cartella destinazione -----
    def open_destination(self):
        """Apre Esplora File sulla cartella di destinazione."""
        d = self.dest_dir.get().strip('" ')
        if not d or not os.path.isdir(d):
            messagebox.showerror("Errore", "Seleziona una cartella di destinazione valida.")
            return
        try:
            os.startfile(d)  # Windows
        except Exception as e:
            try:
                subprocess.Popen(["explorer", d])
            except Exception:
                messagebox.showerror("Errore", f"Impossibile aprire la cartella:\n{e}")

    # ----- Settings: salva/leggi ultimo SAPCAR scelto -----
    def load_last_sapcar(self):
        """Carica l'ultimo SAPCAR scelto da %AppData%\\SapcarUnpacker\\settings.json (se esiste)."""
        try:
            with open(_settings_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
            last = data.get("sapcar_path")
            if last and os.path.isfile(last):
                self.sapcar_path.set(last)
                self.log_line(f"(impostazioni) Caricato ultimo SAPCAR: {last}")
        except FileNotFoundError:
            pass
        except Exception as e:
            self.log_line(f"(impostazioni) Errore lettura impostazioni: {e}")

    def save_last_sapcar(self):
        """Salva SOLO il percorso corrente di SAPCAR nel file impostazioni."""
        try:
            val = self.sapcar_path.get().strip('" ')
            data = {"sapcar_path": val} if val else {}
            with open(_settings_file(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_line(f"(impostazioni) Errore salvataggio impostazioni: {e}")

    def on_close(self):
        """Salva l'ultimo SAPCAR e chiude l'app."""
        try:
            self.save_last_sapcar()
        finally:
            self.destroy()


def main():
    try:
        root = App()
        root.mainloop()
    except Exception as e:
        sys.stderr.write(f"Errore di esecuzione: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
