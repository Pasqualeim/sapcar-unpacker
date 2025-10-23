import os
import json
from typing import Optional

class SettingsManager:
    def __init__(self):
        self.settings_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "SapcarUnpacker"
        )
        self.settings_file = os.path.join(self.settings_dir, "settings.json")
        
    def _ensure_dir(self) -> None:
        """Assicura che la directory delle impostazioni esista"""
        try:
            os.makedirs(self.settings_dir, exist_ok=True)
        except Exception:
            pass
            
    def load_last_sapcar(self) -> Optional[str]:
        """Carica l'ultimo percorso SAPCAR usato"""
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                last = data.get("sapcar_path")
                if last and os.path.isfile(last):
                    return last
        except FileNotFoundError:
            pass
        except Exception:
            pass
        return None
        
    def save_last_sapcar(self, path: str) -> None:
        """Salva l'ultimo percorso SAPCAR usato"""
        try:
            self._ensure_dir()
            data = {"sapcar_path": path.strip('" ')} if path else {}
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass