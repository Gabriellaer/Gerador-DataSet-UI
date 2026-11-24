===============================================================================
SIMULADOR DE DATASETS SINTÉTICOS DE QoE — INTERFACE GRÁFICA (Tkinter)
===============================================================================

Este documento descreve a UI desktop construída sobre os módulos originais
(gerador.py, metricas.py, predicao.py, validacao.py, caso_uso.py).


-------------------------------------------------------------------------------
1. VISÃO GERAL
-------------------------------------------------------------------------------

A UI é uma janela Tkinter com cinco abas:

    - Gerar dataset        (gerador.gera_dataset + escreve)
    - Alocar recursos      (metricas.aloca + métricas)
    - Completar atenção    (predicao.completa)
    - Validar              (subprocesso de src/validacao.py)
    - Caso de uso          (subprocesso de src/caso_uso.py)

Sem servidor, banco ou rede (exceto caso_uso.py, que pode baixar do OSM).
A UI nunca modifica os módulos originais.


-------------------------------------------------------------------------------
2. ESTRUTURA DE ARQUIVOS
-------------------------------------------------------------------------------

    <raiz>/
    ├── README_UI.txt
    ├── requirements.txt
    ├── run_ui.py
    ├── dados/
    │   ├── gd.txt                 (30 x 96, atenção real)
    │   ├── train.txt              (-1 = ausente)
    │   ├── experiment.txt         (cena por usuário)
    │   ├── my_rating.csv          (extra, ignorado)
    │   └── pois_pirenopolis.csv   (caso de uso; opcional)
    ├── figuras/
    ├── resultados/
    └── src/
        ├── gerador.py
        ├── metricas.py
        ├── predicao.py
        ├── validacao.py
        ├── caso_uso.py
        └── ui_desktop/
            ├── __init__.py
            ├── app.py
            ├── widgets.py
            ├── runner.py
            ├── aba_gerar.py
            ├── aba_alocar.py
            ├── aba_completar.py
            ├── aba_validar.py
            └── aba_caso_uso.py


-------------------------------------------------------------------------------
3. DEPENDÊNCIAS
-------------------------------------------------------------------------------

    numpy       (todos os módulos)
    matplotlib  (validação e caso de uso)
    scipy       (validacao.py: rankdata)

    Opcionais, só para o caso de uso:
    networkx    (malha sintética e caminhos)
    osmnx       (baixar malha do OSM; use --sem-osm para evitar)
    pyproj      (conversão de coordenadas com osmnx)

Instalação mínima (para UI + gerador + validação):

    pip install numpy matplotlib scipy

Instalação completa (inclui caso de uso sem OSM):

    pip install numpy matplotlib scipy networkx

Instalação completa com OSM:

    pip install numpy matplotlib scipy networkx osmnx pyproj

Tkinter (Debian/Ubuntu): sudo apt install python3-tk


-------------------------------------------------------------------------------
4. COMO EXECUTAR
-------------------------------------------------------------------------------

    cd <raiz do projeto>
    python3 run_ui.py
    # ou
    python3 -m src.ui_desktop.app

Verificação prévia (sem abrir janela):

    python3 -c "import sys; sys.path.insert(0,'src'); \
                import ui_desktop.app; print('ui ok')"


-------------------------------------------------------------------------------
5. O QUE CADA ABA FAZ
-------------------------------------------------------------------------------

5.1 Gerar dataset
    Campos: usuários, semente, fatores (S), cenário, pasta de saída.
    Chama gerador.gera_dataset + gerador.escreve.
    Saída: resultados/sint_{dataset.csv, atencao.txt, historico.txt, cenas.txt,
    config.json}. Log mostra registros gerados, variância nos fatores,
    amplitude do perfil e caminhos.

5.2 Alocar recursos
    Campos: vetor K (atenção), orçamento, downlink, BEP, latência, checkbox
    "ajustar se inviável". Chama metricas.aloca + aloca_uniforme + métricas.
    Mostra P ótima, P uniforme, Meta-Imersão e QoE-CAC (ótimas e uniformes) e
    o ganho percentual. Não lê dados/ (única aba autossuficiente).

5.3 Completar atenção
    Campos: método (als/anls), fração mascarada, S, lambda. Mascara parte de
    dados/gd.txt, chama predicao.completa, mede RMSE/MAE nas células ocultas
    e mostra min(K) (deve ser > 0).

5.4 Validar
    Campos: usuários (default 60), repetições (3), fatores (4). Dispara
    subprocesso de src/validacao.py (9 blocos: A, B, B.1–B.4, C, D, E, F, G,
    H, I). Saída: resultados/validacao.csv + resultados/relatorio_validacao.txt
    + figuras/*.pdf. ATENÇÃO: leva 20–40 min com defaults antigos; os novos
    defaults (60/3) levam ~5–8 min.

5.5 Caso de uso
    Campos: modo (pe/carro), tempo (vazio = default), permanência, perfis,
    réplicas, semente, checkboxes --sem-osm e --excluir-sem-avaliacao.
    Dispara subprocesso de src/caso_uso.py. Requer dados/pois_pirenopolis.csv
    (formato: nome;categoria;avaliacoes;lat;lon;nota, com '#' para comentários;
    primeira linha = partida, Igreja Matriz). Saída: resultados/caso_uso_*.csv
    + relatorio_caso_uso_*.txt + figuras/caso_uso_*.pdf.


-------------------------------------------------------------------------------
6. LIMITAÇÕES CONHECIDAS
-------------------------------------------------------------------------------

6.1 Aba Validar roda todos os blocos sempre. Os checkboxes A/B/C/D foram
    removidos porque validacao.py não aceita seleção de bloco.

6.2 Aba Caso de uso depende de dados/pois_pirenopolis.csv, que não é gerado
    pela UI. Se o arquivo faltar, a aba avisa em vermelho antes de rodar.

6.3 OSM pode falhar (rede, rate limit). Use --sem-osm para malha sintética.

6.4 gerador.sementes() ainda compartilha o RNG de latência e rede. Não afeta
    a UI; afeta reprodutibilidade fina do gerador.

6.5 Sem persistência de sessão: fechar descarta o estado.


-------------------------------------------------------------------------------
7. SOLUÇÃO DE PROBLEMAS
-------------------------------------------------------------------------------

7.1 ModuleNotFoundError: tkinter
    sudo apt install python3-tk

7.2 ModuleNotFoundError: scipy
    pip install scipy

7.3 ModuleNotFoundError: networkx (aba Caso de uso)
    pip install networkx
    (ou marque --sem-osm; networkx ainda é necessário para malha sintética)

7.4 Aba Validar falha no import de scipy
    pip install scipy
    (validacao.py usa scipy.stats.rankdata)

7.5 Aba Caso de uso falha com FileNotFoundError
    Falta dados/pois_pirenopolis.csv. Crie o arquivo ou ignore a aba.

7.6 Aba Gerar/Completar falha com FileNotFoundError
    Falta dados/gd.txt, train.txt ou experiment.txt. Confira:
        python3 -c "import numpy as np; print(np.loadtxt('dados/gd.txt').shape)"
    Esperado: (30, 96).

7.7 Aba Validar demora muito
    Reduza usuários (60 → 30) e repetições (3 → 2). O bloco B.2 (corpus com
    N=1500) é o mais lento; não há como desativá-lo pela UI.


-------------------------------------------------------------------------------
8. RESUMO DAS DECISÕES DE PROJETO
-------------------------------------------------------------------------------

    - Tkinter puro (sem dependência externa além de numpy/matplotlib/scipy).
    - Cinco abas, uma por operação. Cada aba conhece só seu módulo.
    - Execução em thread + poll via root.after: UI nunca congela.
    - Log centralizado com tags de cor (ok/aviso/erro).
    - RAIZ calculado a partir de __file__: independe do CWD.
    - Sem abertura de pastas: o log mostra os caminhos (decisão após testar
      xdg-open no WSL2).
    - Validar e Caso de uso disparam subprocesso (isolam estado do matplotlib
      e capturam stdout/stderr de forma limpa).

===============================================================================
FIM
===============================================================================
