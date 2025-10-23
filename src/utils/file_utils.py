import os
import shutil
import ctypes
from typing import Optional

def to_short_path(path: str) -> str:
    """Converte un percorso Windows in formato DOS 8.3 (short path)"""
    try:
        if not os.path.exists(path):
            return path
            
        _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
        _GetShortPathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
        
        buf_len = 4096
        buf = ctypes.create_unicode_buffer(buf_len)
        res = _GetShortPathNameW(path, buf, buf_len)
        
        return buf.value if res and buf.value else path
    except Exception:
        return path

def get_powershell_exe() -> str:
    """Trova l'eseguibile di PowerShell disponibile"""
    candidates = [
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe"
    ]
    
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path
            
    return "powershell"  # Fallback default

def find_dispwork(base_dir: str) -> Optional[str]:
    """
    Cerca ricorsivamente disp+work in una directory.
    Preferisce percorsi contenenti 'ntamd64' o 'exe'.
    """
    base_dir = os.path.abspath(base_dir)
    candidates = []
    
    for root, _, files in os.walk(base_dir):
        for name in files:
            if name.lower() in ("disp+work", "disp+work.exe"):
                full_path = os.path.join(root, name)
                try:
                    mtime = os.path.getmtime(full_path)
                except Exception:
                    mtime = 0.0
                    
                # Calcola priorità
                prio = 0
                lower_path = full_path.lower()
                if "ntamd64" in lower_path:
                    prio += 3
                if any(x in lower_path for x in (f"{os.sep}exe{os.sep}", f"{os.sep}exe", f"{os.sep}uc{os.sep}")):
                    prio += 2
                    
                candidates.append((prio, mtime, -len(full_path), full_path))
                
    if not candidates:
        # Cerca nella root
        for name in ("disp+work.exe", "disp+work"):
            path = os.path.join(base_dir, name)
            if os.path.isfile(path):
                return path
        return None
        
    # Ordina per priorità (decrescente)
    candidates.sort(reverse=True)
    return candidates[0][3]