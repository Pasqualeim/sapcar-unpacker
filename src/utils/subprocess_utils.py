import subprocess
from typing import List, Callable

def run_cmd(cwd: str, cmd: List[str], log_callback: Callable[[str], None]) -> int:
    """
    Esegue un comando e invia l'output alla callback di log.
    
    Args:
        cwd: Directory di lavoro
        cmd: Lista di argomenti del comando
        log_callback: Funzione per loggare l'output
        
    Returns:
        int: Codice di uscita del processo
    """
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        # Stream dell'output
        for line in process.stdout:
            log_callback(line.rstrip("\n"))
            
        return process.wait()
        
    except FileNotFoundError as e:
        log_callback(f"[ERRORE] File non trovato: {e}")
        return 127
        
    except Exception as e:
        log_callback(f"[ERRORE] {e}")
        return 1