#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAPCAR Unpacker - Main Application Entry
"""

import sys
from views.main_window import MainWindow
from controllers.app_controller import AppController

def main():
    try:
        app = MainWindow()
        controller = AppController(app)
        app.mainloop()
    except Exception as e:
        sys.stderr.write(f"Errore di esecuzione: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()