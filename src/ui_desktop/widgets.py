"""Widgets reutilizáveis: campo rotulado, seletor de pasta, painel de log."""

import os
import tkinter as tk
from tkinter import filedialog, ttk

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def caminho(*partes):
    return os.path.join(RAIZ, *partes)


def campo(parent, rotulo, variavel, largura=12, dica=None):
    f = ttk.Frame(parent)
    ttk.Label(f, text=rotulo, width=22).pack(side="left")
    ttk.Entry(f, textvariable=variavel, width=largura).pack(side="left")
    if dica:
        ttk.Label(f, text=dica, foreground="gray").pack(side="left", padx=(6, 0))
    return f


def campo_com_botao(parent, rotulo, variavel, comando, texto_botao="Procurar…"):
    f = ttk.Frame(parent)
    ttk.Label(f, text=rotulo, width=22).pack(side="left")
    ttk.Entry(f, textvariable=variavel, width=40).pack(side="left")
    ttk.Button(f, text=texto_botao, command=comando).pack(side="left", padx=(6, 0))
    return f


def seletor_pasta(variavel, parent=None):
    p = filedialog.askdirectory(parent=parent, initialdir=caminho("dados"))
    if p:
        variavel.set(p)


class PainelLog(ttk.Frame):
    def __init__(self, parent, altura=14):
        super().__init__(parent)
        self.texto = tk.Text(self, height=altura, wrap="word",
                             font=("TkFixedFont", 9), state="disabled")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.texto.yview)
        self.texto.configure(yscrollcommand=sb.set)
        self.texto.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.texto.tag_configure("ok", foreground="#2e7d32")
        self.texto.tag_configure("aviso", foreground="#b26a00")
        self.texto.tag_configure("erro", foreground="#b00020")

    def escreve(self, msg, tag=None):
        self.texto.configure(state="normal")
        self.texto.insert("end", msg, tag)
        self.texto.see("end")
        self.texto.configure(state="disabled")

    def limpa(self):
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.configure(state="disabled")


class BarraProgresso(ttk.Progressbar):
    def __init__(self, parent):
        super().__init__(parent, mode="indeterminate")

    def iniciar(self):
        if not self.winfo_ismapped():
            self.pack(fill="x", pady=(4, 0))
        self.start(12)

    def parar(self):
        self.stop()
        self.pack_forget()
