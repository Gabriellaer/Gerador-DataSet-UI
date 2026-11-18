"""Aba: rodar os ensaios de validacao.py via subprocess."""

import subprocess
import tkinter as tk
from tkinter import ttk

from ui_desktop import widgets
from ui_desktop.runner import executar


def construir(parent, root):
    v_n = tk.IntVar(value=60)
    v_rep = tk.IntVar(value=3)
    v_fat = tk.IntVar(value=4)

    frm = ttk.LabelFrame(parent, text="Parâmetros", padding=8)
    frm.pack(fill="x")
    widgets.campo(frm, "Usuários (corpus sint.)", v_n).pack(fill="x", pady=2)
    widgets.campo(frm, "Repetições", v_rep).pack(fill="x", pady=2)
    widgets.campo(frm, "Fatores (S)", v_fat).pack(fill="x", pady=2)

    barra = widgets.BarraProgresso(parent)
    log = widgets.PainelLog(parent, altura=18)
    log.pack(fill="both", expand=True, pady=(8, 0))

    botoes = ttk.Frame(parent)
    botoes.pack(fill="x", pady=6)
    btn_rodar = ttk.Button(botoes, text="Rodar ensaios")
    btn_rodar.pack(side="left")

    def tarefa():
        args = [
            "python3", "src/validacao.py",
            "--usuarios", str(v_n.get()),
            "--repeticoes", str(v_rep.get()),
            "--fatores", str(v_fat.get()),
        ]
        proc = subprocess.run(args, cwd=widgets.RAIZ, capture_output=True, text=True)
        return proc

    def terminou(status, proc):
        if status != "ok":
            return
        log.escreve(proc.stdout)
        if proc.stderr:
            log.escreve(proc.stderr, "erro")
        if proc.returncode == 0:
            log.escreve(
                f"\nConcluído. Resultados em:\n"
                f"  {widgets.caminho('resultados', 'validacao.csv')}\n"
                f"  {widgets.caminho('resultados', 'relatorio_validacao.txt')}\n"
                f"  {widgets.caminho('figuras')}\n", "ok")
        else:
            log.escreve(f"\nSaiu com código {proc.returncode}\n", "erro")

    def clicar():
        log.limpa()
        executar(root, barra, log, tarefa, ao_terminar=terminou)

    btn_rodar.configure(command=clicar)
