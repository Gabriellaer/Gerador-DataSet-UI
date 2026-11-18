"""Entrada da UI. Executar da raiz:

    python3 run_ui.py
    # ou
    python3 -m src.ui_desktop.app
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from ui_desktop import (aba_alocar, aba_caso_uso, aba_completar, aba_gerar,
                        aba_validar)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de datasets sintéticos de QoE")
        self.geometry("1150x800")
        self.minsize(900, 600)

        estilo = ttk.Style(self)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        for nome, modulo in (
            ("Gerar dataset", aba_gerar),
            ("Alocar recursos", aba_alocar),
            ("Completar atenção", aba_completar),
            ("Validar", aba_validar),
            ("Caso de uso", aba_caso_uso),
        ):
            frame = ttk.Frame(nb, padding=8)
            nb.add(frame, text=nome)
            modulo.construir(frame, self)


if __name__ == "__main__":
    App().mainloop()
