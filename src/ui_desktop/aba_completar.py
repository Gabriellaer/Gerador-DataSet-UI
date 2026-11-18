"""Aba: completar matriz de atenção esparsa."""

import tkinter as tk
from tkinter import ttk

import numpy as np

from predicao import completa
from ui_desktop import widgets
from ui_desktop.runner import executar


def construir(parent, root):
    v_metodo = tk.StringVar(value="anls")
    v_frac = tk.DoubleVar(value=0.4)
    v_s = tk.IntVar(value=4)
    v_lam = tk.DoubleVar(value=0.1)

    frm = ttk.LabelFrame(parent, text="Entrada", padding=8)
    frm.pack(fill="x")

    f = ttk.Frame(frm)
    ttk.Label(f, text="Método", width=22).pack(side="left")
    ttk.Combobox(f, textvariable=v_metodo, values=["als", "anls"],
                 state="readonly", width=10).pack(side="left")
    f.pack(fill="x", pady=2)

    widgets.campo(frm, "Fração mascarada", v_frac).pack(fill="x", pady=2)
    widgets.campo(frm, "Fatores (S)", v_s).pack(fill="x", pady=2)
    widgets.campo(frm, "Lambda", v_lam).pack(fill="x", pady=2)

    barra = widgets.BarraProgresso(parent)
    log = widgets.PainelLog(parent, altura=14)
    log.pack(fill="both", expand=True, pady=(8, 0))

    def tarefa():
        from gerador import carrega_referencia
        gd, _, _ = carrega_referencia(widgets.caminho("dados"))
        rng = np.random.default_rng(0)
        mask = rng.random(gd.shape) >= v_frac.get()
        K, info = completa(gd, mask, metodo=v_metodo.get(),
                           S=v_s.get(), lam=v_lam.get())
        verdade = gd[~mask]
        predito = K[~mask]
        erro = predito - verdade
        return {"K": K, "info": info,
                "rmse": float(np.sqrt((erro ** 2).mean())),
                "mae": float(np.abs(erro).mean()),
                "n": int((~mask).sum())}

    def terminou(status, r):
        if status != "ok":
            return
        i = r["info"]
        log.escreve(f"\nMétodo {i['metodo']} | {i['iteracoes']} iterações | "
                    f"objetivo {i['objetivo']:.4f} | delta {i['delta_relativo']:.2e} | "
                    f"{'convergiu' if i['convergiu'] else 'TETO ATINGIDO'}\n", "ok")
        log.escreve(f"RMSE (mascaradas) = {r['rmse']:.4f} | "
                    f"MAE = {r['mae']:.4f} | n = {r['n']}\n")
        log.escreve(f"min(K) = {r['K'].min():.4f} (deve ser > 0)\n")

    def clicar():
        log.limpa()
        executar(root, barra, log, tarefa, ao_terminar=terminou)

    ttk.Button(parent, text="Completar", command=clicar).pack(anchor="w", pady=6)
