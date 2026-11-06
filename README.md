# Projecto de Inteligência Artificial I — Problema P2: Reordenação de Contentores no Porto de Maputo

**Universidade Eduardo Mondlane (UEM) — Faculdade de Engenharia (DEEL)**  
**Unidade Curricular:** Inteligência Artificial I (2026)  
**Grupo:** 02 (Regime Laboral) — Semente Oficial: `202602`

---

## Equipa de Desenvolvimento (Grupo 02 — Laboral)

| Frente | Estudante | Responsabilidade Principal |
|---|---|---|
| **Frente 1** | **Paulo Matola** (`branch_paulo`) | Modelação do domínio (`problema.py`, `dominio.py`, `instancias/base.json`, `tests/test_dominio.py`) |
| **Frente 2** | **Yúmina Elias Cossa** (`feat/buscas-nao-informadas`) | Buscas não informadas: BFS, DFS, IDS e UCS (`buscas.py`, `tests/test_nao_informadas.py`) |
| **Frente 3** | **Peter Njau Kimemia Júnior** (`feat/buscas-informadas`) | Buscas informadas: Gulosa, A\* e IDA\* (`buscas.py`, `tests/test_informadas.py`) e Simulador Web (`interface_web/`) |
| **Frente 4** | **Rosário Caravela** (`feat/heuristicas`) | Heurísticas $h_0, h_1, h_2$ e factor de ramificação efectivo $b^*$ (`heuristicas.py`, `tests/test_heuristicas.py`) |
| **Frente 5** | **Modesta Cipriano Manuel** (`branch_modesta`) | Gerador de instâncias, bateria experimental, gráficos/CSV e CLI (`gerador.py`, `experiencias.py`, `main.py`, `tests/test_gerador.py`) |

---

## Estrutura do Repositório

```text
Projecto_IA_grupo02/
├── problema.py                  # Interface Problema, classe No e função caminho(no)
├── dominio.py                   # EstadoContentores e ProblemaContentores (P2 - Porto de Maputo)
├── buscas.py                    # 7 algoritmos: BFS, DFS, IDS, UCS, Gulosa, A*, IDA* + ResultadoBusca
├── heuristicas.py               # Heurísticas admissíveis h0, h1, h2 e cálculo de b* (Newton-Raphson)
├── gerador.py                   # Gerador determinístico de 30 instâncias (semente oficial 202602)
├── experiencias.py              # Bateria experimental completa, exportação CSV e 3 gráficos matplotlib
├── main.py                      # Interface interativa de linha de comandos (CLI) e visualização ASCII
├── instancias/                  # base.json + 30 instâncias geradas (Pequeno_0..9, Medio_0..9, Grande_0..9)
├── resultados/                  # resultados.csv e gráficos PNG gerados por experiencias.py
├── tests/                       # 54 testes unitários (Frentes 1 a 5)
│   ├── test_dominio.py          # 33 testes da Frente 1
│   ├── test_nao_informadas.py   # 8 testes da Frente 2
│   ├── test_informadas.py       # 7 testes da Frente 3
│   ├── test_heuristicas.py      # 3 testes da Frente 4
│   └── test_gerador.py          # 3 testes da Frente 5
└── interface_web/               # Simulador Visual e Interativo TOS (Porto de Maputo)
    ├── README_WEB.md
    ├── servidor.py              # Servidor HTTP local (biblioteca padrão Python)
    └── static/                  # Frontend (index.html, styles.css, app.js)
```

---

## Como Executar

### 1. Executar a Suite Completa de Testes Unitários (`pytest`)
```bash
python -m pytest -v
```

### 2. Menu Interativo de Terminal e Visualização ASCII (`main.py`)
Para iniciar o menu interativo no terminal:
```bash
python main.py
```
Ou em modo direto via argumentos de linha de comando:
```bash
python main.py --instancia instancias/base.json --algoritmo A* --heuristica h2 --sem-pausa
```

### 3. Simulador Visual Web — Terminal de Contentores do Porto de Maputo (`interface_web/`)
O simulador visual liga-se diretamente aos módulos Python do projeto sem exigir dependências externas:
```bash
python interface_web/servidor.py
```
Depois, abra no navegador:
- **`http://127.0.0.1:8000`**

Funcionalidades do Simulador Web:
- **Simulador Passo a Passo**: Animação do pórtico RTG nos 7 algoritmos (`BFS`, `DFS`, `IDS`, `UCS`, `Gulosa`, `A*`, `IDA*`) e 3 heurísticas (`h0`, `h1`, `h2`), com inspeção em tempo real de $g(n)$, $h_1(n)$, $h_2(n)$, $f(n)$ e $b^*$.
- **Modo Manual**: Jogue manualmente movendo/levantando contentores com validação das restrições do domínio e peça dicas ótimas ao `A* (h2)`.
- **Métricas & Gráficos**: Compare os algoritmos em simultâneo na instância ativa e exporte a tabela consolidada para CSV.
- **Regras do Domínio**: Teste modificações de regras em tempo real.

### 4. Gerar as 30 Instâncias Aleatórias (`gerador.py`)
```bash
python gerador.py
```

### 5. Executar a Bateria Experimental e Gráficos (`experiencias.py`)
```bash
python experiencias.py
```
Os resultados são exportados para `resultados/resultados.csv` e para os 3 gráficos em `resultados/`:
- `resultados/graf_nos_vs_tamanho.png`
- `resultados/graf_tempo_vs_tamanho.png`
- `resultados/graf_custo_vs_optimo.png`
