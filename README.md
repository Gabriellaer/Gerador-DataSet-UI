# Simulador de datasets sintéticos de QoE para ambientes imersivos

Gerador de dados artificiais para gerenciamento de recursos em realidade virtual
e aumentada, com validação por transferência de política.

O problema: existe uma única amostra real de atenção usuário-objeto, com 30
participantes. Trinta observações não sustentam varredura de cenários, teste de
robustez nem avaliação comparativa de esquemas de alocação. Este trabalho gera
dados sintéticos que substituem essa amostra para tais fins, e mede quanto se
perde na substituição.

## Resultado

Uma política de alocação de renderização derivada **inteiramente** de dados
sintéticos, aplicada aos usuários reais, perde entre **0,02% e 0,29%** da
qualidade obtida pela política derivada dos dados reais. As duas métricas de
avaliação concordam.

| Política | Meta-Imersão | QoE-CAC |
|---|---|---|
| P1 perfil global | 0,018% | 0,016% |
| P2 colaborativa item-item | 0,216% | 0,125% |
| P3 fatoração | 0,150% | 0,079% |
| P4 top-30% (discreta) | 0,221% | 0,298% |

A perda não cresce com o tamanho do corpus sintético: de 10 a 1500 usuários ela
permanece abaixo de 0,26%. O ganho da alocação ótima sobre a uniforme vai de
8,4% com folga de recurso a 46,5% sob restrição apertada, e a transferência se
mantém estável em toda a faixa.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10 ou superior.

## Uso

```bash
python src/gerador.py --usuarios 30       # gera o dataset sintético
python src/validacao.py                   # valida e produz as figuras
```
```UI
  A partir da root do projeto
  python3 run_ui.py
```
O gerador aceita `--usuarios`, `--fatores`, `--semente` e `--cenario`
(`normal`, `congestionado`, `edge`, `render_limitado`). A validação aceita
`--usuarios` (tamanho do corpus sintético) e `--repeticoes` (sementes por
condição).

Saídas em `resultados/` (dataset, matriz de atenção, conjuntos, configuração e
tabela de validação) e `figuras/` (PDFs vetoriais). Ambas as pastas são geradas
pelo código e não são versionadas.

## Estrutura

```
dados/        amostra real de referência (30 × 96)
src/
  metricas.py   Meta-Imersão, QoE-CAC, alocação por water-filling
  predicao.py   ALS regularizado e fatoração não negativa
  gerador.py    geração do dataset sintético completo
  validacao.py  quatro ensaios e figuras
figuras/      saída, PDF vetorial
resultados/   saída, CSV e JSON
```

## Métricas de avaliação

Duas métricas distintas, ambas publicadas, usadas aqui como **instrumentos de
medida** — o objeto sob teste é o dataset sintético, não as métricas.

**Meta-Imersão** (Du et al., IEEE JSAC 41(1), 2023)

```
MI(u) = T(R_u) · T(1 − E_u) · Σ_n K_nu · ln( P_nu / P_th )
```

**QoE-CAC** (Santos et al., SBrT 2025)

```
QoE-CAC(u) = T(1 − I_u) · T(R_u) · T(1 − E_u) · Σ_n K_nu · ln( P_nu / P_th )
```

A diferença é o fator de latência `T(1 − I_u)`, presente apenas na QoE-CAC.
Cada métrica sonda um conjunto parcialmente distinto de variáveis, de modo que
concordância entre elas é evidência independente.

A normalização `T(·)` usa limites externos fixos, nunca calculados dos dados:
limites derivados dos dados fariam real e sintético cair na mesma escala por
construção, tornando a comparação tautológica.

## Modelo de geração

**Atenção.** A matriz real tem posto efetivo 1,18, com 91,9% da variância no
primeiro componente e Spearman médio +0,916 entre usuários: existe um perfil
global de popularidade de objetos, e cada usuário é esse perfil mais um desvio
de baixa dimensão. Contra 500 réplicas de um modelo de ruído branco, quatro
componentes do resíduo excedem o percentil 97,5, concentrando 46,1% da variância
residual contra 29,3% esperados.

```
s[k,n] = p[n] + Σ_j f[k,j] · B[j,n] + σ · ε[k,n]
```

com `B` estimado por SVD do resíduo real e mantido fixo — as categorias de
objeto não mudam com a população, o que é o que permite escalar de 30 para N
usuários. Os escores são discretizados em cinco níveis por quantis, por usuário;
discretização por largura igual empilharia a maioria dos objetos no nível 1,
porque os escores brutos são assimétricos à direita.

**Latência.** Motion-to-photon decomposta em sensor, processamento,
renderização e rede, cada componente com faixa própria. Não é sorteada de uma
faixa única nem derivada como inverso da taxa de transmissão, o que seria
dimensionalmente incoerente.

**Faixas.** MTP de 7 a 20 ms, downlink de 10 a 100 Mbit/s, BEP de 1e−8 a 1e−2 em
escala logarítmica, FPS de 60 a 120 com 90 Hz como referência, dispositivos em
30/50/20. Ancoradas em recomendação ITU-T e em literatura de referência; a
fundamentação normativa detalhada está no texto do trabalho.

## Critério de validação

O critério é a **perda de transferência**, não a acurácia de predição nem a
semelhança distribucional. Ambos foram testados e descartados:

- Um preditor que reproduz apenas o perfil global de popularidade acerta mais
  células do que a fatoração, e ainda assim aloca pior. A métrica pondera por
  atenção; a acurácia trata toda célula como igual. Por isso o ensaio de RMSE em
  `validacao.py` é diagnóstico, não critério de aceite.
- Um gerador que reproduzia simultaneamente posto efetivo, Spearman, variância
  do primeiro componente e marginais ainda produzia decisões vários pontos
  percentuais fora. Fidelidade distribucional não implica consistência de
  decisão.

## Limitações

O RMSE de predição é sistematicamente menor no sintético que no real (0,40
contra 0,45 com máscara de 20%): os dados gerados são mais previsíveis, ou seja,
mais simples que o fenômeno.

O modelo é estimado a partir dos mesmos 30 usuários contra os quais é comparado.
É inerente ao método — o gerador existe justamente porque essa é a única amostra
disponível — e precisa ser considerado ao interpretar a magnitude da perda.

A validação cobre quatro classes de decisão e duas métricas. Não esgota o espaço
de políticas nem de métricas possíveis.

## Em desenvolvimento

O caso de uso — roteiro turístico otimizado por QoE sobre malha viária real, com
modos a pé e de carro — está em desenvolvimento e será acrescentado em versão
posterior. Ele separa preferência do visitante (escolha da rota) de atenção
visual (alocação de renderização), que são variáveis distintas com papéis
distintos.

## Dados

A amostra de referência em `dados/` deriva do conjunto UOAL, construído a partir
do dataset PSM. Consulte os termos de uso das fontes originais antes de
redistribuir derivados.

## Referências

- Xu, Y.; Gao, S.; Wu, J.; Li, N.; Yu, J. *Personalized saliency and its
  prediction*. IEEE TPAMI 41(12), 2018. — amostra de rastreamento ocular.
- Du, H. et al. *Attention-aware Resource Allocation and QoE Analysis for
  Metaverse xURLLC Services*. IEEE JSAC 41(1), 2023. — métrica Meta-Imersão.
- Du, H. et al. *Exploring Attention-Aware Network Resource Allocation for
  Customized Metaverse Services*. IEEE Network. — conjunto UOAL.
- Santos, R. O.; Gomes Jr., B. C.; Santos, C. E. S.; Macedo, C. J. A.;
  Oliveira Jr., A. *QoE-CAC*. SBrT 2025. — métrica QoE-CAC.
- Zhang, W. et al. *K-Net: towards unified image segmentation*. NeurIPS 2021. —
  rótulos de segmentação do UOAL.
- ITU-T G.1035, *Influencing factors on quality of experience for virtual
  reality services*, 2021.
- ITU-T P.10/G.100, *Vocabulary for performance, quality of service and quality
  of experience*, 2017.
- ITU-T P.800.1, *Mean opinion score (MOS) terminology*, 2006.
