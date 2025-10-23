import os
import json
from typing import List, Optional

class SapcarModel:
    def __init__(self):
        self.sapcar_path: str = ""
        self.sar_files: List[str] = []
        self.dest_dir: str = ""
        
    def add_sar_file(self, file_path: str) -> None:
        """Aggiunge un file SAR alla lista"""
        if file_path and file_path not in self.sar_files:
            self.sar_files.append(file_path)
            
    def add_sar_files(self, file_paths: List[str]) -> None:
        """Aggiunge più file SAR alla lista"""
        for path in file_paths:
            self.add_sar_file(path)
            
    def clear_sar_files(self) -> None:
        """Rimuove tutti i file SAR dalla lista"""
        self.sar_files.clear()
        
    def set_sapcar_path(self, path: str) -> bool:
        """Imposta il percorso dell'eseguibile SAPCAR"""
        if not path or not os.path.isfile(path):
            return False
        if not os.path.basename(path).upper().startswith("SAPCAR"):
            return False
        self.sapcar_path = path
        return True
        
    def set_dest_dir(self, path: str) -> bool:
        """Imposta la directory di destinazione"""
        try:
            os.makedirs(path, exist_ok=True)
            self.dest_dir = path
            return True
        except Exception:
            return False
            
    def get_sar_files_sorted(self) -> List[str]:
        """Restituisce i file SAR ordinati (SAPEXE* prima)"""
        return sorted(
            self.sar_files,
            key=lambda p: (
                0 if os.path.basename(p).upper().startswith("SAPEXE") else 1,
                os.path.basename(p).upper()
            )
        )
        
    def to_dict(self) -> dict:
        """Converte il modello in dizionario per il salvataggio"""
        return {
            "sapcar_path": self.sapcar_path,
            "dest_dir": self.dest_dir
        }
        
    def from_dict(self, data: dict) -> None:
        """Carica il modello da un dizionario"""
        if "sapcar_path" in data and os.path.isfile(data["sapcar_path"]):
            self.sapcar_path = data["sapcar_path"]
        if "dest_dir" in data:
            self.dest_dir = data["dest_dir"]