# SAPCAR Unpacker (GUI)

Strumento Windows per:
- selezionare `SAPCAR.exe`
- scegliere uno o più pacchetti `.SAR` **o** caricare un’intera cartella
- impostare la cartella di destinazione
- estrarre con `./SAPCAR.exe -xvf <pkg> -R <dest>` (via PowerShell con gestione spazi)
- **testare il kernel** con `disp+work -v` e mostrare solo le info principali
- comprimere la cartella creata con i file scompattati in .tar
- **avviso automatico** quando esce una nuova versione su GitHub

## Download

### Opzione A — Eseguibile pronto (consigliato)
Vai su **Releases** e scarica `sapcar_unpacker.exe`.  
> Se SmartScreen avvisa, clicca *More info* → *Run anyway*.

### Opzione B — Da sorgente (serve Python)
- Windows 10/11
- Python 3.10+ (installer python.org) con **tcl/tk**
- Esegui: `python sapcar_unpacker.py`

## Uso
1. **SAPCAR.exe → Scegli…**  
2. **Aggiungi .SAR…** o **Aggiungi cartella .SAR…**  
3. **Scegli cartella…** (destinazione)  
4. **Esegui Estrazione**  
5. **Testa kernel (disp+work -v)** → mostra versione/patch/compatibilità
6. **Compirmi cartella in .tar** (facilitȧ il passaggio sulle macchien del cliente

## Aggiornamenti
All’avvio il tool controlla se è disponibile una release più recente e mostra un link alla pagina **Releases**.

## FAQ
- Percorsi con spazi (OneDrive, “- Azienda”)? → Gestiti con short-path + pass-through `--%`.
- Perché PowerShell e non CMD? → `./` funziona nativamente e il pass-through è più affidabile.
- Niente dipendenze extra: usa solo librerie standard.

## Licenza
MIT
