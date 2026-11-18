"""Aba: gerar dataset sintético."""

import tkinter as tk
from tkinter import ttk

from gerador import CENARIOS, S_FATORES, carrega_referencia, escreve, gera_dataset
from ui_desktop import widgets
from ui_desktop.runner import executar


def construir(parent, root):
    v_n = tk.IntVar(value=30)
    v_semente = tk.IntVar(value=42)
    v_fatores = tk.IntVar(value=S_FATORES)
    v_cenario = tk.StringVar(value="normal")
    v_saida = tk.StringVar(value=widgets.caminho("resultados"))

    frm = ttk.LabelFrame(parent, text="Parâmetros", padding=8)
    frm.pack(fill="x")

    widgets.campo(frm, "Usuários", v_n).pack(fill="x", pady=2)
    widgets.campo(frm, "Semente", v_semente).pack(fill="x", pady=2)
    widgets.campo(frm, "Fatores (S)", v_fatores).pack(fill="x", pady=2)

    f = ttk.Frame(frm)
    ttk.Label(f, text="Cenário", width=22).pack(side="left")
    ttk.Combobox(f, textvariable=v_cenario, values=list(CENARIOS),
                 state="readonly", width=20).pack(side="left")
    f.pack(fill="x", pady=2)

    widgets.campo_com_botao(
        frm, "Saída", v_saida,
        lambda: widgets.seletor_pasta(v_saida, root),
    ).pack(fill="x", pady=2)

    barra = widgets.BarraProgresso(parent)
    log = widgets.PainelLog(parent, altura=10)
    log.pack(fill="both", expand=True, pady=(8, 0))

    def tarefa():
        gd, tr, cenas_ref = carrega_referencia(widgets.caminho("dados"))
        linhas, K, hist, cenas, config = gera_dataset(
            gd, tr, cenas_ref, v_n.get(), v_semente.get(),
            v_fatores.get(), v_cenario.get())
        caminhos = escreve(v_saida.get(), linhas, K, hist, cenas, config)
        return {"linhas": linhas, "config": config, "caminhos": caminhos}

    def terminou(status, resultado):
        if status != "ok":
            return
        c = resultado["config"]
        log.escreve(
            f"\nGerado: {len(resultado['linhas'])} registros | "
            f"variância nos fatores {100 * c['variancia_nos_fatores']:.1f}% | "
            f"amplitude do perfil a = {c.get('amplitude_perfil', 1.0):.3f}\n",
            "ok")
        for c in resultado["caminhos"]:
            log.escreve(f"  {c}\n")

    def clicar():
        log.limpa()
        executar(root, barra, log, tarefa, ao_terminar=terminou)

    ttk.Button(parent, text="Gerar", command=clicar).pack(anchor="w", pady=6)
