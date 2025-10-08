# SAPCAR Unpacker (GUI)

Strumento Windows per:

* selezionare `SAPCAR.exe` *(accetta anche eseguibili il cui nome **inizia con `SAPCAR`**, es. `SAPCAR_7xx-....exe`)*
* scegliere uno o più pacchetti `.SAR` **o** caricare un’intera cartella
* impostare la cartella di destinazione
* estrarre con `./SAPCAR.exe --% -xvf <pkg> -R <dest>` (via PowerShell con gestione spazi/caratteri speciali)
* **testare il kernel** con `disp+work -v` e mostrare solo le info principali
* comprimere la cartella creata con i file scompattati in `.tar` (compatibile Linux/Unix)

## Download

### Opzione A — Eseguibile pronto (consigliato)

Vai su **Releases** e scarica `sapcar_unpacker.exe`.

> Se SmartScreen avvisa, clicca *More info* → *Run anyway*.

### Opzione B — Da sorgente (serve Python)

* Windows 10/11
* Python 3.10+ (installer python.org) con **tcl/tk**
* Esegui: `python sapcar_unpacker.py`

## Uso

1. **SAPCAR.exe → Scegli…** *(il nome può anche essere `SAPCAR_<versione>.exe`, l’importante è che inizi con `SAPCAR`)*
2. **Aggiungi .SAR…** o **Aggiungi cartella .SAR…** (carica tutti i `.sar` nella cartella)
3. **Scegli cartella…** (destinazione)
4. **Esegui Estrazione**

   * estrae **prima** i pacchetti che iniziano con `SAPEXE` e poi gli altri
   * log in tempo reale + **progress bar** con **ETA**
5. **Testa kernel (disp+work -v)** → mostra versione/patch/compatibilità principali
6. **Comprimi cartella in .tar** → crea un archivio `.tar` della destinazione (preserva struttura e cartelle vuote, esclude il `.tar` stesso)
7. *(Opz.)* **Apri cartella destinazione** / **Esporta script PowerShell (.ps1)**

## Aggiornamenti

All’avvio il tool controlla se è disponibile una release più recente e mostra un link alla pagina **Releases**.

## FAQ

* Percorsi con spazi (OneDrive, “- Azienda”)? → Gestiti con short-path (8.3) e pass-through `--%`. Se persiste l’errore, prova con percorsi semplici (es. `C:\temp\sap\`).
* Perché PowerShell e non CMD? → `./` funziona nativamente e `--%` evita problemi di parsing degli argomenti.
* `disp+work non trovato`? → Assicurati di aver estratto i pacchetti **`SAPEXE*`**.
* Il mio eseguibile non si chiama `SAPCAR.exe` → va bene se **inizia con `SAPCAR`** (es. `SAPCAR_7xx-....exe`).
* Lo script `.ps1` non parte? → apri PowerShell e usa `Set-ExecutionPolicy -Scope Process Bypass` **oppure** clic destro → *Esegui con PowerShell*.
* Il `.tar` non si apre su Windows? → usa 7-Zip/WinRAR o aprilo su Linux/WSL; Windows 11 supporta nativamente `.tar`.
* Antivirus/SmartScreen segnala l’EXE? → possibili falsi positivi con PyInstaller: aggiungi l’EXE alle eccezioni.

## Licenza

MIT


