import os
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("SAPCAR Unpacker")
        self.geometry("1024x768")
        self.configure(bg="#FFFFFF")  # EY White background
        
        # Variabili
        self.sapcar_path = tk.StringVar()
        self.dest_dir = tk.StringVar()
        self.sar_files = []
        
        # EY Style
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#FFFFFF")
        self.style.configure("TLabelframe", background="#FFFFFF")
        self.style.configure("TLabelframe.Label", background="#FFFFFF", foreground="#000000")
        self.style.configure("TButton", background="#FFE600", foreground="#000000")  # EY Yellow button
        self.style.configure("TLabel", background="#FFFFFF", foreground="#000000")
        self.style.configure("TEntry", fieldbackground="#FFFFFF", foreground="#000000")
        self.style.configure("Horizontal.TProgressbar", 
                           troughcolor="#FFFFFF",
                           background="#FFE600")  # EY Yellow for progress
        
        self._create_gui()
        self._setup_menu()
        
    def _create_gui(self):
        # Frame principale con margini
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Sezione SAPCAR
        sapcar_frame = self._create_section(main_frame, "Eseguibile SAPCAR", 0)
        ttk.Entry(sapcar_frame, textvariable=self.sapcar_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.sapcar_browse_btn = ttk.Button(sapcar_frame, text="Sfoglia", style="Accent.TButton")
        self.sapcar_browse_btn.pack(side="right")
        
        # Sezione Files SAR
        sar_frame = self._create_section(main_frame, "File SAR", 1)
        self.sar_count_lbl = ttk.Label(sar_frame, text="0 selezionati")
        self.sar_count_lbl.pack(side="left", padx=(0, 10))
        self.add_sar_btn = ttk.Button(sar_frame, text="Aggiungi File")
        self.add_sar_btn.pack(side="left", padx=2)
        self.add_sar_folder_btn = ttk.Button(sar_frame, text="Aggiungi Cartella")
        self.add_sar_folder_btn.pack(side="left", padx=2)
        self.clear_sar_btn = ttk.Button(sar_frame, text="Svuota Lista")
        self.clear_sar_btn.pack(side="left", padx=2)
        
        # Sezione Destinazione
        dest_frame = self._create_section(main_frame, "Cartella Destinazione", 2)
        ttk.Entry(dest_frame, textvariable=self.dest_dir).pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.dest_browse_btn = ttk.Button(dest_frame, text="Sfoglia")
        self.dest_browse_btn.pack(side="right")
        
        # Sezione Azioni
        actions_frame = ttk.LabelFrame(main_frame, text="Azioni", padding="10")
        actions_frame.pack(fill="x", pady=10)
        
        # Griglia azioni
        for i in range(3):
            actions_frame.columnconfigure(i, weight=1, uniform="actions")
            
        self.run_btn = ctk.CTkButton(
            actions_frame, 
            text="Esegui Estrazione",
            fg_color="#FFE600",     # EY Yellow
            hover_color="#FFD700",   # Slightly darker yellow on hover
            text_color="#000000",    # Black text
            height=40,              # Slightly taller main button
            border_width=0         # Remove border
        )
        self.run_btn.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 5))
        
        # Bottoni azioni secondarie
        secondary_btns = [
            ("Testa Kernel", 1, 0),
            ("Esporta Script", 1, 1),
            ("Crea TAR", 1, 2),
            ("Apri Destinazione", 2, 0, 3)
        ]
        
        # create references for secondary buttons so controller can bind actions
        self.test_btn = ctk.CTkButton(
            actions_frame, 
            text="Testa Kernel",
            fg_color="#FFE600",     # EY Yellow
            hover_color="#FFD700",   # Slightly darker yellow on hover
            text_color="#000000",    # Black text
            height=32,
            border_width=0         # Remove border
        )
        self.test_btn.grid(row=1, column=0, sticky="ew", padx=2, pady=2)

        self.export_btn = ctk.CTkButton(
            actions_frame, 
            text="Esporta Script",
            fg_color="#FFE600",     # EY Yellow
            hover_color="#FFD700",   # Slightly darker yellow on hover
            text_color="#000000",    # Black text
            height=32,
            border_width=0         # Remove border
        )
        self.export_btn.grid(row=1, column=1, sticky="ew", padx=2, pady=2)

        self.tar_btn = ctk.CTkButton(
            actions_frame, 
            text="Crea TAR",
            fg_color="#FFE600",     # EY Yellow
            hover_color="#FFD700",   # Slightly darker yellow on hover
            text_color="#000000",    # Black text
            height=32,
            border_width=0         # Remove border
        )
        self.tar_btn.grid(row=1, column=2, sticky="ew", padx=2, pady=2)

        self.open_btn = ctk.CTkButton(
            actions_frame, 
            text="Apri Destinazione",
            fg_color="#FFE600",     # EY Yellow
            hover_color="#FFD700",   # Slightly darker yellow on hover
            text_color="#000000",    # Black text
            height=32,
            border_width=0         # Remove border
        )
        self.open_btn.grid(row=2, column=0, columnspan=3, sticky="ew", padx=2, pady=2)
            
        # Progress bar
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=5)
        
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            variable=self.progress_var
        )
        self.progress_bar.pack(side="left", fill="x", expand=True)
        
        self.progress_lbl = ttk.Label(progress_frame, text="Pronto")
        self.progress_lbl.pack(side="left", padx=10)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        self.log = tk.Text(
            log_frame,
            height=10,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#ffffff",
            fg="#000000"
        )
        self.log.pack(fill="both", expand=True)
        
        # Scrollbar per il log
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scrollbar.set)
        
    def _create_section(self, parent, text, row):
        """Crea una sezione standard dell'interfaccia"""
        frame = ttk.LabelFrame(parent, text=text, padding="5")
        frame.pack(fill="x", pady=5)
        return frame
        
    def _setup_menu(self):
        """Configura la barra dei menu"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Apri SAPCAR...")
        file_menu.add_command(label="Aggiungi SAR...")
        file_menu.add_separator()
        file_menu.add_command(label="Esci")
        
        # Menu Strumenti
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Strumenti", menu=tools_menu)
        tools_menu.add_command(label="Test Kernel")
        tools_menu.add_command(label="Crea TAR...")
        
        # Menu Aiuto
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aiuto", menu=help_menu)
        help_menu.add_command(label="Guida")
        help_menu.add_command(label="Controlla Aggiornamenti")
        help_menu.add_separator()
        help_menu.add_command(label="Info")