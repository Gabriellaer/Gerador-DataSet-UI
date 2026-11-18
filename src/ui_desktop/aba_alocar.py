"""Aba: alocação ótima de recursos para um usuário."""

import tkinter as tk
from tkinter import ttk

import numpy as np

from metricas import (
    CAP_POR_OBJETO, aloca, aloca_uniforme, meta_imersao, qoe_cac,
    verifica_viabilidade,
)
from ui_desktop import widgets
from ui_desktop.runner import executar


def construir(parent, root):
    v_K = tk.StringVar(value="5, 1, 1, 1, 1, 1")
    v_orc = tk.DoubleVar(value=CAP_POR_OBJETO * 6)
    v_down = tk.DoubleVar(value=50.0)
    v_bep = tk.StringVar(value="1e-5")
    v_lat = tk.DoubleVar(value=12.0)
    v_ajustar = tk.BooleanVar(value=True)

    frm = ttk.LabelFrame(parent, text="Entrada", padding=8)
    frm.pack(fill="x")
    widgets.campo(frm, "Atenção K (vírgula)", v_K, largura=40).pack(fill="x", pady=2)
    widgets.campo(frm, "Orçamento total (K)", v_orc).pack(fill="x", pady=2)
    widgets.campo(frm, "Downlink (Mbit/s)", v_down).pack(fill="x", pady=2)
    widgets.campo(frm, "BEP uplink", v_bep).pack(fill="x", pady=2)
    widgets.campo(frm, "Latência MTP (ms)", v_lat).pack(fill="x", pady=2)
    ttk.Checkbutton(frm, text="Ajustar orçamento se inviável",
                    variable=v_ajustar).pack(anchor="w", pady=2)

    saida = ttk.LabelFrame(parent, text="Resultado", padding=8)
    saida.pack(fill="both", expand=True, pady=(8, 0))
    txt = tk.Text(saida, height=12, wrap="word", font=("TkFixedFont", 9))
    txt.pack(fill="both", expand=True)

    barra = widgets.BarraProgresso(parent)
    log = widgets.PainelLog(parent, altura=6)
    log.pack(fill="x", pady=(8, 0))

    def tarefa():
        K = np.array([float(x) for x in v_K.get().replace(",", " ").split()])
        orc = float(v_orc.get())
        bep = float(v_bep.get())
        diag = verifica_viabilidade(len(K), orc)

        P_ot = aloca(K, orc, ajustar_se_inviavel=v_ajustar.get())
        P_un = aloca_uniforme(len(K), orc) if diag["viavel"] else None

        mi_ot = meta_imersao(K, P_ot, v_down.get(), bep)
        qc_ot = qoe_cac(K, P_ot, v_down.get(), bep, v_lat.get())
        mi_un = meta_imersao(K, P_un, v_down.get(), bep) if P_un is not None else None
        qc_un = qoe_cac(K, P_un, v_down.get(), bep, v_lat.get()) if P_un is not None else None

        return {"K": K, "P_ot": P_ot, "P_un": P_un, "diag": diag,
                "mi_ot": mi_ot, "qc_ot": qc_ot, "mi_un": mi_un, "qc_un": qc_un}

    def terminou(status, r):
        txt.delete("1.0", "end")
        if status != "ok":
            txt.insert("end", "Falha — veja o log abaixo.\n")
            return
        d = r["diag"]
        txt.insert("end", f"Viável: {'sim' if d['viavel'] else 'NÃO'} | "
                          f"mínimo {d['minimo']:.2f} | folga {d['folga']:.2f}\n\n")
        txt.insert("end", f"K          = {np.round(r['K'], 3).tolist()}\n")
        txt.insert("end", f"P ótima    = {np.round(r['P_ot'], 3).tolist()}\n")
        if r["P_un"] is not None:
            txt.insert("end", f"P uniforme = {np.round(r['P_un'], 3).tolist()}\n")
        txt.insert("end", "\n")
        txt.insert("end", f"Meta-Imersão ótima    = {r['mi_ot']:.4f}\n")
        txt.insert("end", f"QoE-CAC ótima         = {r['qc_ot']:.4f}\n")
        if r["mi_un"] is not None:
            txt.insert("end", f"Meta-Imersão uniforme = {r['mi_un']:.4f}  "
                              f"(ganho {100 * (r['mi_ot'] / r['mi_un'] - 1):+.2f}%)\n")
            txt.insert("end", f"QoE-CAC uniforme      = {r['qc_un']:.4f}  "
                              f"(ganho {100 * (r['qc_ot'] / r['qc_un'] - 1):+.2f}%)\n")

    def clicar():
        log.limpa()
        executar(root, barra, log, tarefa, ao_terminar=terminou)

    ttk.Button(parent, text="Calcular alocação", command=clicar).pack(anchor="w", pady=6)
