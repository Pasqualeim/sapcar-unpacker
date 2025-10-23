import os
import threading
import time
from tkinter import messagebox, filedialog
from models.sapcar_model import SapcarModel
from utils.file_utils import to_short_path, get_powershell_exe, find_dispwork
from utils.subprocess_utils import run_cmd
from utils.settings_manager import SettingsManager
import tarfile
import subprocess
import time
import webbrowser
import json

class AppController:
    def __init__(self, view):
        self.view = view
        self.model = SapcarModel()
        self.settings = SettingsManager()
        
        self._bind_events()
        self._load_settings()
        
    def _bind_events(self):
        """Collega gli eventi dell'interfaccia ai metodi del controller"""
        # File menu
        self.view.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Buttons
        self.view.run_btn.configure(command=self.run_extraction)
        # browse/selectors
        self.view.sapcar_browse_btn.configure(command=self.choose_sapcar)
        self.view.add_sar_btn.configure(command=self.choose_sar_files)
        self.view.add_sar_folder_btn.configure(command=self.choose_sar_folder)
        self.view.clear_sar_btn.configure(command=self.clear_sar_files)
        self.view.dest_browse_btn.configure(command=self.choose_dest_dir)
        # secondary actions
        self.view.test_btn.configure(command=self.test_kernel)
        self.view.export_btn.configure(command=self.export_batch)
        self.view.tar_btn.configure(command=self.create_tar_of_destination)
        self.view.open_btn.configure(command=self.open_destination)
        
    def _load_settings(self):
        """Carica le impostazioni salvate"""
        last_sapcar = self.settings.load_last_sapcar()
        if last_sapcar and os.path.isfile(last_sapcar):
            self.view.sapcar_path.set(last_sapcar)
            self.view.log.insert("end", f"Caricato ultimo SAPCAR: {last_sapcar}\n")
            
    def _validate_inputs(self):
        """Valida gli input prima dell'estrazione"""
        sapcar = self.view.sapcar_path.get().strip('" ')
        if not sapcar or not os.path.isfile(sapcar):
            messagebox.showerror("Errore", "Seleziona un eseguibile SAPCAR* valido.")
            return False
            
        if not os.path.basename(sapcar).upper().startswith("SAPCAR"):
            messagebox.showerror("Errore", "L'eseguibile deve iniziare con 'SAPCAR'.")
            return False
            
        if not self.view.sar_files:
            messagebox.showerror("Errore", "Aggiungi almeno un file .SAR.")
            return False
            
        dest = self.view.dest_dir.get().strip('" ')
        if not dest:
            messagebox.showerror("Errore", "Seleziona una cartella di destinazione.")
            return False
            
        try:
            os.makedirs(dest, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile creare/accedere alla cartella di destinazione:\n{e}")
            return False
            
        return True

    # ---- UI handlers wired to view ----
    def choose_sapcar(self):
        path = filedialog.askopenfilename(title="Seleziona eseguibile SAPCAR*", filetypes=[("Eseguibili", "*.exe"), ("Tutti i file", "*.*")])
        if path:
            if not os.path.basename(path).upper().startswith("SAPCAR"):
                messagebox.showerror("File non valido", "L'eseguibile deve iniziare con 'SAPCAR'.")
                return
            self.view.sapcar_path.set(path)

    def choose_sar_files(self):
        files = filedialog.askopenfilenames(title="Seleziona uno o più file .SAR", filetypes=[("SAP Archives", "*.SAR;*.sar"), ("Tutti i file", "*.*")])
        if files:
            self._append_sar_files(list(files))

    def choose_sar_folder(self):
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
        if found:
            self._append_sar_files(found)

    def _append_sar_files(self, new_files):
        self.view.sar_files.extend(new_files)
        # de-dup
        seen = set()
        uniq = []
        for f in self.view.sar_files:
            if f not in seen:
                uniq.append(f)
                seen.add(f)
        self.view.sar_files = uniq
        self.view.sar_count_lbl.config(text=f"{len(self.view.sar_files)} selezionati")
        self._log(f"Aggiunti {len(new_files)} file .SAR (totale: {len(self.view.sar_files)})")

    def clear_sar_files(self):
        self.view.sar_files = []
        self.view.sar_count_lbl.config(text="0 selezionati")
        self._log("Lista .SAR svuotata.")

    def choose_dest_dir(self):
        d = filedialog.askdirectory(title="Scegli la cartella di destinazione")
        if d:
            self.view.dest_dir.set(d)
        
    def run_extraction(self):
        """Esegue l'estrazione dei file SAR"""
        if not self._validate_inputs():
            return
            
        sapcar = os.path.abspath(self.view.sapcar_path.get().strip('" '))
        sapcar_dir = os.path.dirname(sapcar)
        sapcar_name = os.path.basename(sapcar)
        
        # Ordina i file SAR (SAPEXE* prima)
        sar_files = sorted(
            self.view.sar_files,
            key=lambda p: (0 if os.path.basename(p).upper().startswith("SAPEXE") else 1, os.path.basename(p).upper())
        )
        
        self.view.run_btn.configure(state="disabled")
        self._log("\n== Inizio estrazione ==")
        self._log(f"SAPCAR: {sapcar}")
        self._log(f"Working dir: {sapcar_dir}")
        
        def worker():
            try:
                self._execute_extraction(sapcar_dir, sapcar_name, sar_files)
            finally:
                self.view.run_btn.configure(state="normal")
                
        threading.Thread(target=worker, daemon=True).start()
        
    def _execute_extraction(self, sapcar_dir, sapcar_name, sar_files):
        """Esegue l'estrazione effettiva dei file"""
        dest_dir = os.path.normpath(self.view.dest_dir.get().strip('" '))
        ps_exe = get_powershell_exe()
        
        overall_rc = 0
        self._init_progress(len(sar_files))
        
        for idx, sar in enumerate(sar_files, start=1):
            sar_norm = os.path.normpath(sar)
            self._log(f"\n[{idx}/{len(sar_files)}] Estrazione di: {sar_norm}")

            # Ottieni short paths quando possibile per evitare problemi con gli spazi
            sar_short = to_short_path(sar_norm)
            dest_short = to_short_path(dest_dir)

            # Scegli argomento per SAPCAR: preferisci short path se non contiene spazi
            if sar_short and os.path.exists(sar_short) and " " not in sar_short:
                sar_arg = sar_short
                sar_used = "short"
            else:
                sar_arg = f'"{sar_norm}"'
                sar_used = "quoted"

            if dest_short and os.path.exists(dest_short) and " " not in dest_short:
                dest_arg = dest_short
                dest_used = "short"
            else:
                dest_arg = f'"{dest_dir}"'
                dest_used = "quoted"

            self._log(f"(info) sar arg: {sar_arg} ({sar_used}), dest arg: {dest_arg} ({dest_used})")

            # PowerShell: --% passa i parametri così com'è
            ps_cmd = f'& ./"{sapcar_name}" --% -xvf {sar_arg} -R {dest_arg}'
            cmd = [ps_exe, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]

            self._log(f"Comando: {ps_cmd}")
            
            t0 = time.time()
            rc = run_cmd(sapcar_dir, cmd, self._log)
            elapsed = time.time() - t0
            
            if rc == 0:
                self._log(f"[OK] Estratto: {os.path.basename(sar)}")
            else:
                overall_rc = rc
                self._log(f"[ERRORE] RC={rc} su: {os.path.basename(sar)}")
                
            self._tick_progress(elapsed)
            
        if overall_rc == 0:
            self._log("\n== Completato senza errori ==")
            messagebox.showinfo("Fatto", "Estrazione completata senza errori.")
        else:
            self._log("\n== Completato con errori ==")
            messagebox.showwarning("Errore", "Alcune estrazioni non sono andate a buon fine.")
            
        self._finish_progress()
        
    def _init_progress(self, total):
        """Inizializza la barra di progresso"""
        self._total_pkgs = max(0, total)
        self._done_pkgs = 0
        self._start_ts = time.time()
        self.view.progress_var.set(0.0)
        
    def _tick_progress(self, duration):
        """Aggiorna la barra di progresso"""
        self._done_pkgs = min(self._done_pkgs + 1, self._total_pkgs)
        perc = (self._done_pkgs / self._total_pkgs * 100) if self._total_pkgs > 0 else 0
        
        def update():
            self.view.progress_var.set(perc)
            self.view.progress_lbl.configure(
                text=f"{self._done_pkgs}/{self._total_pkgs} • {int(perc)}%"
            )
        self.view.after(0, update)
        
    def _finish_progress(self):
        """Completa la barra di progresso"""
        def update():
            self.view.progress_var.set(100.0)
            elapsed = time.time() - self._start_ts
            m, s = divmod(int(elapsed), 60)
            self.view.progress_lbl.configure(text=f"Completato • {m:02d}:{s:02d}")
        self.view.after(0, update)
        
    def _log(self, message):
        """Aggiunge una riga al log"""
        self.view.log.configure(state="normal")
        self.view.log.insert("end", message + "\n")
        self.view.log.see("end")
        self.view.log.configure(state="disabled")
        self.view.update_idletasks()
        
    def _on_close(self):
        """Gestisce la chiusura dell'applicazione"""
        try:
            self.settings.save_last_sapcar(self.view.sapcar_path.get().strip('" '))
        finally:
            self.view.destroy()

    # ---- Extra actions (export, tar, open, test kernel) ----
    def export_batch(self):
        if not self._validate_inputs():
            return
        sapcar = os.path.abspath(self.view.sapcar_path.get().strip('" '))
        sapcar_dir = os.path.dirname(sapcar)
        sapcar_name = os.path.basename(sapcar)
        dest_norm = os.path.normpath(self.view.dest_dir.get().strip('" '))
        dest_short = to_short_path(dest_norm)

        lines = [f'Set-Location -Path "{sapcar_dir}"', ""]
        for sar in sorted(self.view.sar_files, key=lambda p: (0 if os.path.basename(p).upper().startswith("SAPEXE") else 1, os.path.basename(p).upper())):
            sar_norm = os.path.normpath(sar)
            sar_short = to_short_path(sar_norm)
            sar_arg = sar_short if (sar_short == to_short_path(sar_short) and " " not in sar_short) else f'"{sar_norm}"'
            dest_arg = dest_short if (dest_short == to_short_path(dest_short) and " " not in dest_short) else f'"{dest_norm}"'
            lines.append(f'& ./"{sapcar_name}" --% -xvf {sar_arg} -R {dest_arg}')

        save_to = filedialog.asksaveasfilename(title="Salva script PowerShell", defaultextension=".ps1", filetypes=[("PowerShell script", "*.ps1")])
        if save_to:
            try:
                with open(save_to, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                messagebox.showinfo("Esportato", f"Script PowerShell salvato in:\n{save_to}")
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare il file:\n{e}")

    def create_tar_of_destination(self):
        dest_dir = self.view.dest_dir.get().strip('" ')
        if not dest_dir:
            messagebox.showerror("Errore", "Seleziona la cartella di destinazione prima di creare il .tar.")
            return
        dest_dir = os.path.normpath(dest_dir)
        if not os.path.isdir(dest_dir):
            messagebox.showerror("Errore", f"La cartella di destinazione non esiste:\n{dest_dir}")
            return

        default_name = os.path.basename(dest_dir.rstrip("\\/")) or "estrazione"
        save_to = filedialog.asksaveasfilename(title="Salva archivio TAR", initialfile=f"{default_name}.tar", defaultextension=".tar", filetypes=[("TAR archive", "*.tar")])
        if not save_to:
            return

        self._log(f"\n== Creazione archivio TAR ==")
        self._log(f"Sorgente: {dest_dir}")
        self._log(f"Archivio: {save_to}")

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
                            self._log(f"Aggiungo: {arcname}")
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

                self._log("[OK] Archivio TAR creato.")
                messagebox.showinfo("TAR creato", f"Archivio creato:\n{save_to}")
            except Exception as e:
                self._log(f"[ERRORE] Creazione TAR fallita: {e}")
                messagebox.showerror("Errore", f"Creazione TAR fallita:\n{e}")

        threading.Thread(target=worker, daemon=True).start()

    def open_destination(self):
        d = self.view.dest_dir.get().strip('" ')
        if not d or not os.path.isdir(d):
            messagebox.showerror("Errore", "Seleziona una cartella di destinazione valida.")
            return
        try:
            os.startfile(d)
        except Exception as e:
            try:
                subprocess.Popen(["explorer", d])
            except Exception:
                messagebox.showerror("Errore", f"Impossibile aprire la cartella:\n{e}")

    def extract_dispwork_main_section(self, lines):
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

    def test_kernel(self):
        dest = self.view.dest_dir.get().strip('" ')
        if not dest:
            messagebox.showerror("Errore", "Seleziona prima la cartella di estrazione.")
            return

        disp = find_dispwork(dest)
        if not disp:
            messagebox.showerror("disp+work non trovato", "Non è stato trovato 'disp+work' nella cartella di destinazione.\nControlla di aver estratto SAPEXE / SAPEXEDB correttamente.")
            return

        disp_dir = os.path.dirname(disp)
        disp_name = os.path.basename(disp)
        ps_exe = get_powershell_exe()

        self._log(f"\n== Test kernel: eseguo {disp} -v ==")

        def worker():
            buf = []

            def collect_only(line: str):
                buf.append(line)

            rc = None
            for flag in ("-v", "-V"):
                ps_cmd = f'& ./"{disp_name}" {flag}'
                cmd = [ps_exe, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd]
                self._log(f"Comando PowerShell: {ps_cmd} (cwd={disp_dir})")
                rc = run_cmd(disp_dir, cmd, collect_only)
                if rc == 0:
                    break
                else:
                    self._log(f"(info) disp+work ha restituito RC={rc} con {flag}. Provo alternativa...")

            lines = self.extract_dispwork_main_section(buf)
            self._log("\n== Sezione principale (filtrata) ==")
            for ln in lines:
                self._log(ln)

            if rc == 0:
                messagebox.showinfo("Test kernel", "disp+work ha risposto correttamente.")
            else:
                messagebox.showwarning("Test kernel", "disp+work non ha restituito 0. Verifica dipendenze/variabili d'ambiente.")

        threading.Thread(target=worker, daemon=True).start()