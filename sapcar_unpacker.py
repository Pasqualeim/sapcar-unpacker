#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAPCAR Unpacker (Windows, Thonny)
- Scegli SAPCAR.exe
- Seleziona uno o più .SAR (file singoli o intera cartella)
- Scegli la cartella di destinazione
- Estrae con: "./SAPCAR.exe -xvf <pkg> -R <dest>" via PowerShell (così `./` funziona)
- Converte i percorsi con spazi in short path (8.3) per evitare errori di SAPCAR
- Pulsante "Testa kernel (disp+work -v)" che cerca disp+work ed esegue la versione
- Mostra solo la sezione principale dell'output di disp+work
- NOVITÀ:
  * Estrae prima i pacchetti che iniziano con "SAPEXE*" (es. SAPEXE_, SAPEXEDB_) e poi gli altri
  * Pulsante "Crea .tar della destinazione" per generare un archivio TAR della cartella estratta
"""

import os
import sys
import shutil
import subprocess
import threading
import tarfile
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext


# ---------- Utilità percorso ----------
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

    for i, raw, low in norm[start_idx + 1 :]:
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
        self.geometry("980x620")
        self.resizable(True, True)

        self.sapcar_path = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.sar_files = []

        # Row 0: SAPCAR
        frm0 = tk.Frame(self)
        frm0.pack(fill="x", padx=10, pady=6)
        tk.Label(frm0, text="SAPCAR.exe:").pack(side="left")
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

        # Row 3: Actions
        frm3 = tk.Frame(self)
        frm3.pack(fill="x", padx=10, pady=6)
        self.run_btn = tk.Button(frm3, text="Esegui Estrazione", command=self.run_extraction)
        self.run_btn.pack(side="left")
        tk.Button(frm3, text="Esporta script PowerShell", command=self.export_batch).pack(side="left", padx=8)
        tk.Button(frm3, text="Testa kernel (disp+work -v)", command=self.test_kernel).pack(side="left", padx=8)
        tk.Button(frm3, text="Crea .tar della destinazione", command=self.create_tar_of_destination).pack(side="left", padx=8)

        # Row 4: Log
        self.log = scrolledtext.ScrolledText(self, height=20, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=10)

    # ----- UI helpers -----
    def log_line(self, line: str):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def choose_sapcar(self):
        path = filedialog.askopenfilename(
            title="Seleziona SAPCAR.exe",
            filetypes=[("SAPCAR", "SAPCAR.exe"), ("Exe", "*.exe"), ("Tutti i file", "*.*")]
        )
        if path:
            self.sapcar_path.set(path)

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
            messagebox.showerror("Errore", "Seleziona un file SAPCAR.exe valido.")
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

    # ----- Estrazione pacchetti -----
    def run_extraction(self):
        if not self.validate_inputs():
            return

        sapcar = os.path.abspath(self.sapcar_path.get().strip('" '))
        sapcar_dir = os.path.dirname(sapcar)
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

                ps_cmd = f'& ./SAPCAR.exe --% -xvf {sar_arg} -R {dest_arg}'
                cmd = [ps_exe, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]

                self.log_line(f"Comando PowerShell: {ps_cmd} (cwd={sapcar_dir})")
                rc = run_cmd(sapcar_dir, cmd, self.log_line)

                if rc == 0:
                    self.log_line(f"[OK] Estratto: {os.path.basename(sar_norm)}")
                else:
                    overall_rc = rc or overall_rc
                    self.log_line(f"[ERRORE] RC={rc} su: {os.path.basename(sar_norm)}")

            if overall_rc == 0:
                self.log_line("\n== Completato senza errori ==")
                messagebox.showinfo("Fatto", "Estrazione completata senza errori.")
            else:
                self.log_line("\n== Completato con errori ==")
                messagebox.showwarning("Completato con errori", "Alcune estrazioni non sono andate a buon fine. Controlla il log.")
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
            messagebox.showerror("disp+work non trovato", "Non è stato trovato 'disp+work' nella cartella di destinazione.\n"
                                 "Controlla di aver estratto SAPEXE / SAPEXEDB correttamente.")
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
            lines.append(f'& ./SAPCAR.exe --% -xvf {sar_arg} -R {dest_arg}')

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
                # Evita di includere il tar se l'utente lo salva dentro la stessa cartella
                save_abs = os.path.abspath(save_to)
                base = os.path.basename(dest_dir.rstrip("\\/"))
                base_parent = os.path.dirname(dest_dir)

                with tarfile.open(save_abs, "w") as tar:
                    # Aggiunge i file ricorsivamente preservando il nome root 'base'
                    for root, dirs, files in os.walk(dest_dir):
                        for name in files:
                            full = os.path.join(root, name)
                            if os.path.abspath(full) == save_abs:
                                # skip il file .tar stesso
                                continue
                            rel = os.path.relpath(full, start=os.path.dirname(dest_dir))
                            arcname = os.path.join(base, os.path.relpath(full, start=dest_dir))
                            self.log_line(f"Aggiungo: {arcname}")
                            tar.add(full, arcname=arcname, recursive=False)
                        # aggiungi directory vuote (tar su Linux le vede)
                        for d in dirs:
                            dir_full = os.path.join(root, d)
                            rel_arc = os.path.join(base, os.path.relpath(dir_full, start=dest_dir))
                            ti = tarfile.TarInfo(rel_arc.replace("\\", "/"))
                            ti.type = tarfile.DIRTYPE
                            ti.mtime = int(os.path.getmtime(dir_full))
                            tar.addfile(ti)

                self.log_line("[OK] Archivio TAR creato.")
                messagebox.showinfo("TAR creato", f"Archivio creato:\n{save_to}")
            except Exception as e:
                self.log_line(f"[ERRORE] Creazione TAR fallita: {e}")
                messagebox.showerror("Errore", f"Creazione TAR fallita:\n{e}")

        threading.Thread(target=worker, daemon=True).start()


def main():
    try:
        root = App()
        root.mainloop()
    except Exception as e:
        sys.stderr.write(f"Errore di esecuzione: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
