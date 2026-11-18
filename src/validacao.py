"""
Validacao do dataset sintetico.

Quatro ensaios, correspondendo as melhorias previstas:

    A. ENSAIO INTERNO (Melhoria I)
       Mascara parte das atencoes observadas, preve com ALS e ANLS, mede RMSE
       contra os valores retidos. Nao depende de coleta adicional. Roda no real
       e no sintetico: se o sintetico for mais facil de prever que o real, o
       gerador esta simplificando o fenomeno.

    B. TRANSFERENCIA (Melhoria IV)
       Uma politica de alocacao derivada INTEIRAMENTE do sintetico, aplicada aos
       usuarios reais, perde quanto em relacao a politica derivada do real?

           perda = 1 - M(politica do sintetico) / M(politica do real)

       Ambas avaliadas nos usuarios REAIS, com a atencao verdadeira. Nao e
       comparacao distribucional nem validacao de metrica: e teste de utilidade
       para decisao.

    C. ROBUSTEZ NUMERICA (Melhoria III)
       Verifica que atencao nao positiva e recusada, que inviabilidade de
       orcamento e detectada, que o ajuste e iterativo e que a alocacao respeita
       o piso.

    D. REGIME DE RECURSO (Melhoria II)
       Ganho da alocacao otima sobre a uniforme, e estabilidade da transferencia,
       ao longo da faixa de orcamento.

POR QUE A TRANSFERENCIA E NAO OUTRO CRITERIO
--------------------------------------------
Criterios testados e descartados:

  - Acuracia de predicao da atencao: um preditor trivial de posto 1 acerta MAIS
    celulas (66,4% contra 63,5%) e aloca PIOR (17,2% contra 20,1% de ganho). A
    metrica pondera por atencao; a acuracia trata toda celula como igual. Por
    isso o ensaio A e diagnostico, nao criterio de aceite.
  - Estatisticas estruturais (posto efetivo, Spearman, marginais): um gerador
    que acertava as quatro simultaneamente ainda produzia decisoes 6 pontos
    percentuais fora. Fidelidade distribucional nao implica consistencia de
    decisao.

CLASSES DE DECISAO
------------------
    P1  perfil global medio       nao personalizada
    P2  colaborativa item-item    usa correlacao entre objetos
    P3  ALS / ANLS                completa a matriz e aloca sobre a predicao
    P4  top-30%                   decisao discreta, nao linear

USO
---
    python3 src/validacao.py
    python3 src/validacao.py --usuarios 300 --repeticoes 12
"""

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from gerador import S_FATORES, ajusta_atencao, carrega_referencia, gera_atencao
from metricas import (
    CAP_POR_OBJETO,
    LIM_DOWNLINK,
    P_TH,
    InviavelError,
    aloca,
    aloca_uniforme,
    meta_imersao,
    qoe_cac,
    verifica_viabilidade,
)
from predicao import completa, rmse_mascarado

plt.rcParams.update({
    "font.size": 9, "axes.grid": True, "grid.alpha": 0.3,
    "figure.constrained_layout.use": True, "pdf.fonttype": 42,
})
AZUL, LARANJA, VERDE = "#3b6ea5", "#c2703d", "#4c8055"


# --------------------------------------------------------------------------- #
# Politicas
# --------------------------------------------------------------------------- #
def p1_global(corpus):
    perfil = corpus.mean(0)
    return lambda hist, objs: perfil[objs]


def p2_item_item(corpus, k_viz=20):
    C = corpus - corpus.mean(0)
    dp = np.where(C.std(0) < 1e-9, 1e-9, C.std(0))
    W = (C / dp).T @ (C / dp) / corpus.shape[0]
    np.fill_diagonal(W, 0.0)
    perfil = corpus.mean(0)

    def prever(hist, objs):
        vistos = np.nonzero(hist >= 0)[0]
        if len(vistos) == 0:
            return perfil[objs]
        desvio = hist[vistos] - perfil[vistos]
        out = np.empty(len(objs))
        for i, n in enumerate(objs):
            w = W[n, vistos]
            top = np.argsort(np.abs(w))[-k_viz:]
            den = np.abs(w[top]).sum()
            out[i] = perfil[n] + (w[top] @ desvio[top] / den if den > 1e-9 else 0.0)
        return np.clip(out, 0.5, 5.5)

    return prever


def p3_fatoracao(corpus, metodo="anls", S=S_FATORES):
    """Completa a matriz do corpus por fatoracao e usa o perfil resultante.

    O corpus e denso, entao a fatoracao aqui extrai a estrutura latente; o
    historico do usuario real projeta sobre ela.
    """
    mask = np.ones(corpus.shape, bool)
    K, _ = completa(corpus.astype(float), mask, metodo=metodo, S=S)
    perfil = K.mean(0)
    C = K - perfil
    dp = np.where(C.std(0) < 1e-9, 1e-9, C.std(0))
    W = (C / dp).T @ (C / dp) / K.shape[0]
    np.fill_diagonal(W, 0.0)

    def prever(hist, objs):
        vistos = np.nonzero(hist >= 0)[0]
        if len(vistos) == 0:
            return perfil[objs]
        desvio = hist[vistos] - perfil[vistos]
        out = np.array([
            perfil[n] + (W[n, vistos] @ desvio / max(np.abs(W[n, vistos]).sum(), 1e-9))
            for n in objs
        ])
        return np.clip(out, 0.5, 5.5)

    return prever


def p4_topk(corpus, frac=0.3):
    perfil = corpus.mean(0)

    def prever(hist, objs):
        v = perfil[objs]
        corte = np.sort(v)[-max(1, int(round(frac * len(objs))))]
        return np.where(v >= corte, v, 0.5)

    return prever


POLITICAS = {
    "P1 global": p1_global,
    "P2 item-item": p2_item_item,
    "P3 fatoracao": p3_fatoracao,
    "P4 top-30%": p4_topk,
}
MET = {
    "Meta-Imersao": lambda K, P, dl, bep, lat: meta_imersao(K, P, dl, bep),
    "QoE-CAC": qoe_cac,
}


# --------------------------------------------------------------------------- #
def condicoes_rede(n, semente=1234):
    """Condicoes de rede fixas por usuario, iguais nos dois bracos.

    Sao fatores multiplicativos; manter fixos isola o efeito da politica de
    alocacao, que e o objeto do teste.
    """
    r = np.random.default_rng(semente)
    return {
        "downlink": r.uniform(*LIM_DOWNLINK, size=n),
        "bep": 10.0 ** r.uniform(-8, -2, size=n),
        "latencia": sum(r.uniform(a, b, size=n)
                        for a, b in [(0.5, 2), (1, 3), (2, 10), (5, 10)]),
    }


def avalia(prever, gd, hist, cenas, rede, metrica, cap=CAP_POR_OBJETO):
    vals = []
    for u, objs in enumerate(cenas):
        P = aloca(prever(hist[u], objs), len(objs) * cap, P_TH)
        vals.append(metrica(gd[u, objs], P, rede["downlink"][u], rede["bep"][u],
                            rede["latencia"][u]))
    return float(np.mean(vals))


def avalia_uniforme(gd, cenas, rede, metrica, cap=CAP_POR_OBJETO):
    vals = []
    for u, objs in enumerate(cenas):
        P = aloca_uniforme(len(objs), len(objs) * cap, P_TH)
        vals.append(metrica(gd[u, objs], P, rede["downlink"][u], rede["bep"][u],
                            rede["latencia"][u]))
    return float(np.mean(vals))


# --------------------------------------------------------------------------- #
# Figuras
# --------------------------------------------------------------------------- #
def fig_perda_politicas(res, saida):
    pols = list(POLITICAS)
    x = np.arange(len(pols))
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    for i, (nome, cor) in enumerate(zip(MET, (AZUL, LARANJA))):
        m = [res[nome][p]["perda"] for p in pols]
        e = [res[nome][p]["dp"] for p in pols]
        ax.bar(x + (i - 0.5) * 0.38, m, 0.38, yerr=e, capsize=3, label=nome, color=cor)
    ax.set_xticks(x); ax.set_xticklabels(pols, rotation=12)
    ax.set_ylabel("perda de transferência (%)")
    ax.axhline(0, color="k", lw=0.8); ax.legend(frameon=False)
    fig.savefig(os.path.join(saida, "perda_por_politica.pdf")); plt.close(fig)


def fig_corpus(dados, saida):
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    for (nome, serie), cor in zip(dados.items(), (AZUL, LARANJA)):
        n = [d["n"] for d in serie]
        m = np.array([d["perda"] for d in serie]); e = np.array([d["dp"] for d in serie])
        ax.plot(n, m, "o-", color=cor, label=nome, ms=4)
        ax.fill_between(n, m - e, m + e, color=cor, alpha=0.18)
    ax.set_xscale("log"); ax.set_xlabel("usuários no corpus sintético")
    ax.set_ylabel("perda de transferência (%)")
    ax.axhline(0, color="k", lw=0.8); ax.legend(frameon=False)
    fig.savefig(os.path.join(saida, "perda_por_corpus.pdf")); plt.close(fig)


def fig_escassez(dados, saida):
    cap = [d["cap"] for d in dados]
    fig, a1 = plt.subplots(figsize=(5.4, 3.0))
    a1.plot(cap, [d["ganho"] for d in dados], "s-", color=AZUL, ms=4)
    a1.set_xlabel("orçamento por objeto (K)")
    a1.set_ylabel("ganho sobre alocação uniforme (%)", color=AZUL)
    a1.tick_params(axis="y", labelcolor=AZUL)
    a2 = a1.twinx()
    a2.plot(cap, [d["perda"] for d in dados], "o--", color=LARANJA, ms=4)
    a2.set_ylabel("perda de transferência (%)", color=LARANJA)
    a2.tick_params(axis="y", labelcolor=LARANJA); a2.grid(False)
    fig.savefig(os.path.join(saida, "regime_escassez.pdf")); plt.close(fig)


def fig_espectro(gd, sint, saida):
    def esp(A):
        R = A - A.mean(0, keepdims=True)
        w = np.linalg.eigvalsh(R @ R.T / A.shape[1])[::-1]
        return w / w.sum()
    er, es = esp(gd), esp(sint[: gd.shape[0]])
    k = np.arange(1, 11)
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    ax.bar(k - 0.2, er[:10], 0.4, label="amostra real", color=AZUL)
    ax.bar(k + 0.2, es[:10], 0.4, label="sintético", color=LARANJA)
    ax.set_xticks(k); ax.set_xlabel("componente do resíduo")
    ax.set_ylabel("fração da variância"); ax.legend(frameon=False)
    fig.savefig(os.path.join(saida, "espectro_residuo.pdf")); plt.close(fig)


def fig_atencao(gd, sint, saida):
    fig, ax = plt.subplots(1, 2, figsize=(6.8, 2.8))
    ordem = np.argsort(gd.mean(0))
    ax[0].plot(gd.mean(0)[ordem], lw=1.2, color=AZUL, label="real")
    ax[0].plot(sint.mean(0)[ordem], lw=1.2, color=LARANJA, alpha=0.85, label="sintético")
    ax[0].set_xlabel("objeto (ordenado pela popularidade real)")
    ax[0].set_ylabel("atenção média"); ax[0].legend(frameon=False)
    niv = np.arange(1, 6)
    ax[1].bar(niv - 0.2, [(gd == v).mean() for v in niv], 0.4, color=AZUL)
    ax[1].bar(niv + 0.2, [(sint == v).mean() for v in niv], 0.4, color=LARANJA)
    ax[1].set_xticks(niv); ax[1].set_xlabel("nível de atenção")
    ax[1].set_ylabel("frequência")
    fig.savefig(os.path.join(saida, "distribuicao_atencao.pdf")); plt.close(fig)


def fig_rmse(dados, saida):
    rot = [d["rot"] for d in dados]
    x = np.arange(len(rot))
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    ax.bar(x - 0.2, [d["rmse_real"] for d in dados], 0.4, label="amostra real", color=AZUL)
    ax.bar(x + 0.2, [d["rmse_sint"] for d in dados], 0.4, label="sintético", color=LARANJA)
    ax.set_xticks(x); ax.set_xticklabels(rot)
    ax.set_ylabel("RMSE da atenção predita"); ax.legend(frameon=False)
    fig.savefig(os.path.join(saida, "rmse_mascarado.pdf")); plt.close(fig)


def fig_convergencia(hist_als, hist_anls, saida):
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    ax.plot(np.arange(1, len(hist_als) + 1), hist_als, "-", color=AZUL, label="ALS")
    ax.plot(np.arange(1, len(hist_anls) + 1), hist_anls, "-", color=VERDE, label="ANLS (não negativa)")
    ax.set_yscale("log"); ax.set_xlabel("iteração")
    ax.set_ylabel("função objetivo"); ax.legend(frameon=False)
    fig.savefig(os.path.join(saida, "convergencia_fatoracao.pdf")); plt.close(fig)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Valida o dataset sintetico.")
    ap.add_argument("--dados", default="dados")
    ap.add_argument("--figuras", default="figuras")
    ap.add_argument("--resultados", default="resultados")
    ap.add_argument("--usuarios", type=int, default=150)
    ap.add_argument("--repeticoes", type=int, default=8)
    ap.add_argument("--fatores", type=int, default=S_FATORES)
    args = ap.parse_args()

    for d in (args.figuras, args.resultados):
        os.makedirs(d, exist_ok=True)

    gd, tr, cenas = carrega_referencia(args.dados)
    NU, NO = gd.shape
    rede = condicoes_rede(NU)
    modelo = ajusta_atencao(gd, args.fatores)
    sintetico = lambda n, s: gera_atencao(modelo, n, np.random.default_rng(s))
    reg = []

    print("=" * 72)
    print("VALIDACAO DO DATASET SINTETICO")
    print(f"amostra real: {NU} x {NO} | cena media {np.mean([len(c) for c in cenas]):.1f}"
          f" | corpus sintetico: {args.usuarios} | {args.repeticoes} sementes")
    print("=" * 72)

    # ---- A. ensaio interno -------------------------------------------------- #
    print("\n[A] ENSAIO INTERNO — mascarar, prever, medir (Melhoria I)")
    print(f"    {'condicao':22s}{'RMSE real':>11s}{'RMSE sint':>11s}{'MAE real':>10s}"
          f"{'exato real':>12s}")
    dados_rmse = []
    sint_ref = sintetico(args.usuarios, 0)
    for metodo in ("als", "anls"):
        for frac in (0.2, 0.4):
            rr = [rmse_mascarado(gd, frac, metodo, semente=s, S=args.fatores)
                  for s in range(3)]
            rs = [rmse_mascarado(sint_ref.astype(float), frac, metodo, semente=s,
                                 S=args.fatores) for s in range(3)]
            d = {"rot": f"{metodo.upper()}\n{int(frac * 100)}%",
                 "rmse_real": np.mean([x[0] for x in rr]),
                 "rmse_sint": np.mean([x[0] for x in rs])}
            dados_rmse.append(d)
            print(f"    {metodo.upper() + f' mascara {int(frac*100)}%':22s}"
                  f"{d['rmse_real']:11.4f}{d['rmse_sint']:11.4f}"
                  f"{np.mean([x[1] for x in rr]):10.4f}"
                  f"{100 * np.mean([x[2] for x in rr]):11.1f}%")
            reg.append(("ensaio", metodo, f"mascara={frac}", d["rmse_real"], d["rmse_sint"]))
    fig_rmse(dados_rmse, args.figuras)

    from predicao import als, anls
    mk = np.ones(gd.shape, bool)
    _, _, i_als = als(gd, mk, S=args.fatores)
    _, _, i_anls = anls(gd, mk, S=args.fatores)
    fig_convergencia(i_als["historico"], i_anls["historico"], args.figuras)
    for i in (i_als, i_anls):
        estado = "convergiu" if i["convergiu"] else "TETO ATINGIDO"
        print(f"    {i['metodo']:5s} {i['iteracoes']:4d} iteracoes | objetivo {i['objetivo']:.4f} | delta {i['delta_relativo']:.2e} | {estado}")
        reg.append(("convergencia", i["metodo"], estado, i["iteracoes"], i["objetivo"]))

    # ---- B. transferencia --------------------------------------------------- #
    print("\n[B] TRANSFERENCIA — politica do sintetico aplicada ao real (Melhoria IV)")
    res = {}
    for met_nome, met in MET.items():
        res[met_nome] = {}
        unif = avalia_uniforme(gd, cenas, rede, met)
        print(f"\n  {met_nome}  (uniforme = {unif:.3f})")
        print(f"    {'politica':14s}{'real':>9s}{'sintetico':>11s}{'perda':>9s}{'ganho':>9s}")
        for pol, fab in POLITICAS.items():
            real = avalia(fab(gd), gd, tr, cenas, rede, met)
            vals = [avalia(fab(sintetico(args.usuarios, s)), gd, tr, cenas, rede, met)
                    for s in range(args.repeticoes)]
            perda = 100 * (1 - np.mean(vals) / real)
            dp = 100 * np.std(vals) / real
            res[met_nome][pol] = {"perda": perda, "dp": dp}
            print(f"    {pol:14s}{real:9.3f}{np.mean(vals):11.3f}{perda:8.3f}%"
                  f"{100 * (real / unif - 1):8.2f}%")
            reg.append(("transferencia", met_nome, pol, perda, dp))
    fig_perda_politicas(res, args.figuras)

    print("\n    perda por tamanho do corpus (politica P2)")
    dados_corpus = {}
    for met_nome, met in MET.items():
        real = avalia(p2_item_item(gd), gd, tr, cenas, rede, met)
        serie = []
        for n in (10, 30, 60, 150, 500, 1500):
            vals = [avalia(p2_item_item(sintetico(n, s)), gd, tr, cenas, rede, met)
                    for s in range(args.repeticoes)]
            serie.append({"n": n, "perda": 100 * (1 - np.mean(vals) / real),
                          "dp": 100 * np.std(vals) / real})
            reg.append(("corpus", met_nome, f"N={n}", serie[-1]["perda"], serie[-1]["dp"]))
        dados_corpus[met_nome] = serie
        print(f"      {met_nome}: " + "  ".join(f"N={d['n']}:{d['perda']:+.2f}%" for d in serie))
    fig_corpus(dados_corpus, args.figuras)

    # ---- C. robustez -------------------------------------------------------- #
    print("\n[C] ROBUSTEZ NUMERICA (Melhoria III)")
    testes = []
    try:
        aloca(np.array([1.0, 0.0, 3.0]), 100.0)
        testes.append(("atencao nula recusada", False))
    except ValueError:
        testes.append(("atencao nula recusada", True))
    try:
        aloca(np.array([1.0, np.nan]), 100.0)
        testes.append(("NaN recusado", False))
    except ValueError:
        testes.append(("NaN recusado", True))
    try:
        aloca(np.array([1.0, 2.0, 3.0]), 40.0)
        testes.append(("inviabilidade detectada", False))
    except InviavelError:
        testes.append(("inviabilidade detectada", True))
    P = aloca(np.array([1.0, 2.0, 3.0]), 40.0, ajustar_se_inviavel=True)
    testes.append(("ajuste automatico do orcamento", bool((P >= P_TH - 1e-9).all())))
    Kt = np.array([5.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    P = aloca(Kt, len(Kt) * CAP_POR_OBJETO)
    testes.append(("piso respeitado com atencao desigual", bool((P >= P_TH - 1e-9).all())))
    testes.append(("orcamento respeitado", bool(P.sum() <= len(Kt) * CAP_POR_OBJETO + 1e-6)))
    K_anls, _ = completa(gd, np.random.default_rng(0).random(gd.shape) < 0.6, metodo="anls")
    testes.append(("ANLS sem atencao <= 0", bool((K_anls > 0).all())))
    v = verifica_viabilidade(10, 100.0)
    testes.append(("diagnostico de viabilidade", v["minimo"] == 150.0 and not v["viavel"]))
    for nome, ok in testes:
        print(f"    [{'OK ' if ok else 'FALHA'}] {nome}")
        reg.append(("robustez", "-", nome, float(ok), 0.0))

    # ---- D. regime de recurso ----------------------------------------------- #
    print("\n[D] REGIME DE RECURSO (Melhoria II)")
    met = MET["Meta-Imersao"]
    dados_esc = []
    for cap in (15.5, 16, 18, 20, 25, 30, 40):
        unif = avalia_uniforme(gd, cenas, rede, met, cap)
        real = avalia(p1_global(gd), gd, tr, cenas, rede, met, cap)
        vals = [avalia(p1_global(sintetico(args.usuarios, s)), gd, tr, cenas, rede, met, cap)
                for s in range(max(3, args.repeticoes // 2))]
        d = {"cap": cap, "ganho": 100 * (real / unif - 1),
             "perda": 100 * (1 - np.mean(vals) / real)}
        dados_esc.append(d)
        print(f"    cap={cap:5.1f}K   ganho {d['ganho']:6.2f}%   perda {d['perda']:+.3f}%")
        reg.append(("escassez", "Meta-Imersao", f"cap={cap}", d["perda"], d["ganho"]))
    fig_escassez(dados_esc, args.figuras)

    fig_espectro(gd, sint_ref, args.figuras)
    fig_atencao(gd, sint_ref, args.figuras)

    c = os.path.join(args.resultados, "validacao.csv")
    with open(c, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bloco", "metrica", "condicao", "valor", "valor_2"])
        w.writerows(reg)
    print(f"\nresultados: {c}")
    for nome in sorted(os.listdir(args.figuras)):
        if nome.endswith(".pdf"):
            print(f"figura:     {os.path.join(args.figuras, nome)}")


if __name__ == "__main__":
    main()
