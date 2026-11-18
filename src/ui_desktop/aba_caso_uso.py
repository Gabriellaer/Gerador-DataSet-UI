"""Aba: rodar caso_uso.py (roteiro turístico em Pirenópolis) via subprocess."""

import os
import subprocess
import tkinter as tk
from tkinter import ttk

from ui_desktop import widgets
from ui_desktop.runner import executar


def construir(parent, root):
    v_modo = tk.StringVar(value="pe")
    v_tempo = tk.StringVar(value="")           # vazio = default do modo
    v_perm = tk.DoubleVar(value=15.0)
    v_perfis = tk.IntVar(value=300)
    v_rep = tk.IntVar(value=30)
    v_semente = tk.IntVar(value=42)
    v_sem_osm = tk.BooleanVar(value=False)
    v_excluir = tk.BooleanVar(value=False)

    frm = ttk.LabelFrame(parent, text="Parâmetros", padding=8)
    frm.pack(fill="x")

    f = ttk.Frame(frm)
    ttk.Label(f, text="Modo", width=22).pack(side="left")
    ttk.Combobox(f, textvariable=v_modo, values=["pe", "carro"],
                 state="readonly", width=10).pack(side="left")
    f.pack(fill="x", pady=2)

    widgets.campo(frm, "Tempo disponível (min)", v_tempo,
                  dica="vazio = default do modo (90 pe / 240 carro)").pack(fill="x", pady=2)
    widgets.campo(frm, "Permanência por ponto (min)", v_perm).pack(fill="x", pady=2)
    widgets.campo(frm, "Perfis (visitantes)", v_perfis).pack(fill="x", pady=2)
    widgets.campo(frm, "Réplicas da rede", v_rep).pack(fill="x", pady=2)
    widgets.campo(frm, "Semente", v_semente).pack(fill="x", pady=2)

    chk = ttk.Frame(frm)
    chk.pack(fill="x", pady=(4, 0))
    ttk.Checkbutton(chk, text="Sem OpenStreetMap (malha sintética, não usa internet)",
                    variable=v_sem_osm).pack(anchor="w")
    ttk.Checkbutton(chk, text="Excluir pontos sem avaliação (análise de sensibilidade)",
                    variable=v_excluir).pack(anchor="w")

    # aviso sobre o arquivo de entrada
    pois = widgets.caminho("dados", "pois_pirenopolis.csv")
    if not os.path.exists(pois):
        aviso = ttk.Label(
            parent,
            text=f"AVISO: {pois} não existe. O caso de uso precisa desse arquivo "
                 f"(nome;categoria;avaliacoes;lat;lon;nota, com '#' para comentários).",
            foreground="#b00020", wraplength=900, justify="left")
        aviso.pack(fill="x", pady=(4, 0))

    barra = widgets.BarraProgresso(parent)
    log = widgets.PainelLog(parent, altura=18)
    log.pack(fill="both", expand=True, pady=(8, 0))

    botoes = ttk.Frame(parent)
    botoes.pack(fill="x", pady=6)
    btn_rodar = ttk.Button(botoes, text="Rodar caso de uso")
    btn_rodar.pack(side="left")

    def tarefa():
        args = [
            "python3", "src/caso_uso.py",
            "--modo", v_modo.get(),
            "--permanencia", str(v_perm.get()),
            "--perfis", str(v_perfis.get()),
            "--replicas", str(v_rep.get()),
            "--semente", str(v_semente.get()),
        ]
        if v_tempo.get().strip():
            args += ["--tempo", v_tempo.get().strip()]
        if v_sem_osm.get():
            args.append("--sem-osm")
        if v_excluir.get():
            args.append("--excluir-sem-avaliacao")
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
                f"  {widgets.caminho('resultados')}\n"
                f"  {widgets.caminho('figuras')}\n", "ok")
        else:
            log.escreve(f"\nSaiu com código {proc.returncode}\n", "erro")

    def clicar():
        log.limpa()
        executar(root, barra, log, tarefa, ao_terminar=terminou)

    btn_rodar.configure(command=clicar)
