"""Bateria experimental, CSV e gráficos para o P2 — Porto de Maputo.

Universidade Eduardo Mondlane — Inteligência Artificial I (2026)
Grupo 02 (Laboral) — Frente 5: Modesta Cipriano Manuel

Executa os 7 algoritmos de busca (BFS, DFS, IDS, UCS, Gulosa, A*, IDA*) sobre as
30 instâncias geradas (3 níveis) mais a instância base, com:
    • tempo medido por ``time.perf_counter()`` (limite 60 s);
    • memória medida por ``tracemalloc`` (limite 2 GB);
    • execuções que excedem os limites marcadas como "falhou (tempo)" ou
      "falhou (memoria)" — SEM omiti-las do CSV.

Saídas (em ``resultados/``):
    • ``resultados.csv``         — tabela completa (31 instâncias × 7 algoritmos = 217 linhas);
    • ``graf_nos_vs_tamanho.png`` — nós expandidos vs. N (escala log);
    • ``graf_tempo_vs_tamanho.png`` — tempo (s) vs. N;
    • ``graf_custo_vs_optimo.png``  — rácio custo / custo_óptimo por algoritmo.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Garante que a raiz do projecto está no sys.path para importações relativas.
RAIZ: Path = Path(__file__).parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

try:
    import matplotlib
    matplotlib.use("Agg")  # backend headless — não abre janela
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    try:
        fm.fontManager.addfont("/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf")
    except Exception:
        pass
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Noto Sans SC", "Liberation Sans"]
    plt.rcParams["axes.unicode_minus"] = False
except ImportError:  # pragma: no cover — permite importar experiencias sem matplotlib instalado
    matplotlib = None  # type: ignore
    plt = None  # type: ignore

from dominio import ProblemaContentores
from buscas import bfs, dfs, ids, ucs, gulosa, a_estrela, ida_estrela

# Configurações da bateria.
# O limite oficial é 60 s / 2 GB. Para a bateria completa (217 execuções) o
# tempo total pode ser proibitivo no pior caso; por isso admite-se override via
# variável de ambiente para permitir uma execução mais curta em desenvolvimento.
DIRETORIO_INSTANCIAS: Path = RAIZ / "instancias"
DIRETORIO_RESULTADOS: Path = RAIZ / "resultados"
FICHEIRO_CSV: Path = DIRETORIO_RESULTADOS / "resultados.csv"
LIMITE_TEMPO_S: float = float(os.environ.get("EXP_LIMITE_TEMPO_S", "60.0"))
LIMITE_MEMORIA_MB: float = float(os.environ.get("EXP_LIMITE_MEMORIA_MB", "2048.0"))

# Algoritmos a executar (nome, heurística, callable).
#   As buscas não informadas não recebem heurística; as informadas são testadas
#   com a sua heurística de referência (h1 para Gulosa e A*, h2 para IDA*).
ALGORITMOS: List[Tuple[str, str, Callable[..., Any]]] = [
    ("BFS",    "—",  bfs),
    ("DFS",    "—",  dfs),
    ("IDS",    "—",  ids),
    ("UCS",    "—",  ucs),
    ("Gulosa", "h1", gulosa),
    ("A*",     "h1", a_estrela),
    ("IDA*",   "h2", ida_estrela),
]

# Paleta consistente para os gráficos (uma cor por algoritmo).
CORES: Dict[str, str] = {
    "BFS":    "#1f77b4",
    "DFS":    "#ff7f0e",
    "IDS":    "#2ca02c",
    "UCS":    "#d62728",
    "Gulosa": "#9467bd",
    "A*":     "#8c564b",
    "IDA*":   "#e377c2",
}

# Marcadores para distinguir algoritmos em gráficos com muitas séries.
MARCADORES: Dict[str, str] = {
    "BFS": "o", "DFS": "s", "IDS": "^", "UCS": "D",
    "Gulosa": "v", "A*": "P", "IDA*": "X",
}


def _carregar_instancias() -> List[Tuple[str, Path, Dict[str, Any]]]:
    """Carrega todas as instâncias (base + 30 geradas), ordenadas por nível e índice."""
    instancias: List[Tuple[str, Path, Dict[str, Any]]] = []
    # Instância base primeiro.
    caminho_base = DIRETORIO_INSTANCIAS / "base.json"
    if caminho_base.exists():
        dados = json.loads(caminho_base.read_text(encoding="utf-8"))
        dados.setdefault("nivel", "Base")
        dados.setdefault("num_contentores", len(dados.get("pesados", [])) + sum(len(p) for p in dados.get("pilhas", [])))
        # Recalcula N a partir das pilhas (a base pode não ter num_contentores).
        dados["num_contentores"] = sum(len(p) for p in dados["pilhas"])
        instancias.append(("Base", caminho_base, dados))
    # Geradas, ordenadas por nível e índice.
    ordem_niveis = {"Pequeno": 1, "Medio": 2, "Grande": 3}
    ficheiros = sorted(DIRETORIO_INSTANCIAS.glob("*_*.json"))
    ficheiros.sort(
        key=lambda f: (
            ordem_niveis.get(f.stem.split("_")[0], 99),
            int(f.stem.split("_")[1]),
        )
    )
    for f in ficheiros:
        dados = json.loads(f.read_text(encoding="utf-8"))
        nivel = dados.get("nivel", f.stem.split("_")[0])
        instancias.append((f"{nivel}_{dados.get('indice', f.stem.split('_')[1])}", f, dados))
    return instancias


def _executar_algoritmo(
    nome_algo: str, nome_h: str, fn: Callable[..., Any], problema: ProblemaContentores
) -> Dict[str, Any]:
    """Executa um algoritmo com os limites oficiais e devolve o dicionário de métricas."""
    if nome_h == "—":
        resultado = fn(problema, limite_tempo_s=LIMITE_TEMPO_S, limite_memoria_mb=LIMITE_MEMORIA_MB)
    else:
        resultado = fn(
            problema, nome_h,
            limite_tempo_s=LIMITE_TEMPO_S, limite_memoria_mb=LIMITE_MEMORIA_MB,
        )
    return {
        "algoritmo": nome_algo,
        "heuristica": nome_h,
        "status": resultado.status,
        "resolvido": resultado.resolvido,
        "custo": resultado.custo if math.isfinite(resultado.custo) else "",
        "comprimento": resultado.comprimento,
        "nos_expandidos": resultado.nos_expandidos,
        "nos_gerados": resultado.nos_gerados,
        "nos_reexpandidos": resultado.nos_reexpandidos,
        "max_fronteira": resultado.max_fronteira,
        "tempo_s": f"{resultado.tempo_s:.6f}",
        "memoria_mb": f"{resultado.memoria_mb:.6f}",
    }


def correr_bateria(
    instancias: Optional[List[Tuple[str, Path, Dict[str, Any]]]] = None,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """Executa todos os algoritmos em todas as instâncias.

    Devolve uma lista de dicionários (um por par instância × algoritmo) com todas
    as métricas. As execuções que excedem tempo/memória são registadas com
    ``status = "falhou (tempo)"`` ou ``"falhou (memoria)"`` — NUNCA omitidas.
    """
    instancias = instancias or _carregar_instancias()
    linhas: List[Dict[str, Any]] = []
    total = len(instancias) * len(ALGORITMOS)
    passo = 0
    for nome_inst, caminho, dados in instancias:
        problema = ProblemaContentores(
            dados["S"], dados["H"], dados["pilhas"],
            dados.get("pesados", []), dados.get("refrigerados", []),
        )
        N = sum(len(p) for p in dados["pilhas"])
        nivel = dados.get("nivel", "?")
        for nome_algo, nome_h, fn in ALGORITMOS:
            passo += 1
            if verbose:
                print(
                    f"[{passo:>3}/{total}] {nome_inst:<14} {nome_algo:<8} "
                    f"{nome_h:<3} ...",
                    end=" ",
                    flush=True,
                )
            metricas = _executar_algoritmo(nome_algo, nome_h, fn, problema)
            linha = {
                "instancia": nome_inst,
                "nivel": nivel,
                "ficheiro": caminho.name,
                "S": dados["S"],
                "H": dados["H"],
                "N": N,
                "num_contentores": N,
                "pesados": "|".join(str(c) for c in dados.get("pesados", [])),
                "refrigerados": "|".join(str(c) for c in dados.get("refrigerados", [])),
            }
            linha.update(metricas)
            linhas.append(linha)
            if verbose:
                status = metricas["status"]
                custo = metricas["custo"]
                nos = metricas["nos_expandidos"]
                t = metricas["tempo_s"]
                print(f"{status:<18} custo={custo!s:<6} nos={nos:<10} t={t}s")
    return linhas


def exportar_csv(linhas: List[Dict[str, Any]], caminho: Path = FICHEIRO_CSV) -> Path:
    """Exporta as linhas para CSV (utf-8, separador vírgula)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not linhas:
        caminho.write_text("", encoding="utf-8")
        return caminho
    campos = list(linhas[0].keys())
    with caminho.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for linha in linhas:
            writer.writerow(linha)
    return caminho


def _agrupar_para_graficos(
    linhas: List[Dict[str, Any]],
) -> Tuple[Dict[str, List[Tuple[int, float]]], Dict[str, List[Tuple[int, float]]], Dict[str, List[Tuple[int, float]]]]:
    """Agrupa dados por algoritmo: (N, nos_expandidos), (N, tempo_s), (N, rácio custo/óptimo)."""
    # Custo óptimo por instância = menor custo finito entre todos os algoritmos.
    custos_por_instancia: Dict[str, float] = {}
    for linha in linhas:
        if linha["resolvido"] and linha["custo"] != "":
            inst = linha["instancia"]
            try:
                c = float(linha["custo"])
            except (TypeError, ValueError):
                continue
            if inst not in custos_por_instancia or c < custos_por_instancia[inst]:
                custos_por_instancia[inst] = c

    nos_por_algo: Dict[str, List[Tuple[int, float]]] = {a: [] for a, _, _ in ALGORITMOS}
    tempo_por_algo: Dict[str, List[Tuple[int, float]]] = {a: [] for a, _, _ in ALGORITMOS}
    racio_por_algo: Dict[str, List[Tuple[int, float]]] = {a: [] for a, _, _ in ALGORITMOS}

    for linha in linhas:
        algo = linha["algoritmo"]
        N = linha["N"]
        inst = linha["instancia"]
        nos = linha["nos_expandidos"]
        try:
            t = float(linha["tempo_s"])
        except (TypeError, ValueError):
            t = float("nan")
        nos_por_algo[algo].append((N, float(nos) if nos else 0.0))
        tempo_por_algo[algo].append((N, t))
        # Rácio custo/custo_óptimo.
        custo_opt = custos_por_instancia.get(inst)
        if custo_opt and custo_opt > 0 and linha["custo"] != "":
            try:
                c = float(linha["custo"])
                racio = c / custo_opt
                racio_por_algo[algo].append((N, racio))
            except (TypeError, ValueError):
                pass
        elif not linha["resolvido"]:
            # Sem solução: rácio = infinito (representado como NaN para o gráfico).
            racio_por_algo[algo].append((N, float("nan")))
    return nos_por_algo, tempo_por_algo, racio_por_algo


def grafico_nos_vs_tamanho(
    nos_por_algo: Dict[str, List[Tuple[int, float]]],
    caminho: Path,
) -> Path:
    """Gráfico 1 — Nós expandidos vs. tamanho da instância (escala logarítmica)."""
    fig, ax = plt.subplots(figsize=(11, 6.5), constrained_layout=True)
    for nome_algo, pontos in nos_por_algo.items():
        if not pontos:
            continue
        xs = [p[0] for p in pontos]
        ys = [p[1] if p[1] > 0 else 0.5 for p in pontos]  # 0 -> 0.5 para escala log
        ax.plot(
            xs, ys, marker=MARCADORES.get(nome_algo, "o"),
            color=CORES.get(nome_algo, "black"),
            label=nome_algo, linewidth=1.5, markersize=6, alpha=0.85,
        )
    ax.set_xlabel("Número de contentores (N) — tamanho da instância")
    ax.set_ylabel("Nós expandidos (escala log)")
    ax.set_yscale("log")
    ax.set_title("Nós expandidos vs. tamanho da instância (escala log)", fontsize=13)
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend(title="Algoritmo", loc="best", fontsize=10)
    fig.savefig(caminho, dpi=120)
    plt.close(fig)
    return caminho


def grafico_tempo_vs_tamanho(
    tempo_por_algo: Dict[str, List[Tuple[int, float]]],
    caminho: Path,
) -> Path:
    """Gráfico 2 — Tempo de execução (s) vs. tamanho da instância."""
    fig, ax = plt.subplots(figsize=(11, 6.5), constrained_layout=True)
    for nome_algo, pontos in tempo_por_algo.items():
        if not pontos:
            continue
        xs = [p[0] for p in pontos]
        ys = [p[1] if not math.isnan(p[1]) else LIMITE_TEMPO_S for p in pontos]
        ax.plot(
            xs, ys, marker=MARCADORES.get(nome_algo, "o"),
            color=CORES.get(nome_algo, "black"),
            label=nome_algo, linewidth=1.5, markersize=6, alpha=0.85,
        )
    # Linha horizontal com o limite de 60 s.
    ax.axhline(LIMITE_TEMPO_S, color="red", linestyle=":", linewidth=1.2,
               label="Limite 60 s")
    ax.set_xlabel("Número de contentores (N) — tamanho da instância")
    ax.set_ylabel("Tempo de execução (s)")
    ax.set_yscale("log")
    ax.set_title("Tempo de execução vs. tamanho da instância", fontsize=13)
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    ax.legend(title="Algoritmo", loc="best", fontsize=10)
    fig.savefig(caminho, dpi=120)
    plt.close(fig)
    return caminho


def grafico_racio_custo(
    racio_por_algo: Dict[str, List[Tuple[int, float]]],
    caminho: Path,
) -> Path:
    """Gráfico 3 — Rácio custo / custo_óptimo por algoritmo (média por nível)."""
    # Calcula a média do rácio por algoritmo em cada faixa de N.
    faixas = [("Pequeno", (0, 9)), ("Medio", (10, 15)), ("Grande", (16, 99))]
    medias: Dict[str, List[float]] = {a: [] for a in racio_por_algo}
    for _, (lo, hi) in faixas:
        for algo, pontos in racio_por_algo.items():
            valores = [p[1] for p in pontos if lo <= p[0] <= hi and not math.isnan(p[1])]
            medias[algo].append(float(sum(valores) / len(valores)) if valores else float("nan"))

    fig, ax = plt.subplots(figsize=(11, 6.5), constrained_layout=True)
    nomes_niveis = [f[0] for f in faixas]
    x = list(range(len(nomes_niveis)))
    largura = 0.10
    for i, (algo, valores) in enumerate(medias.items()):
        ys = [v if not math.isnan(v) else 0.0 for v in valores]
        offset = (i - len(medias) / 2 + 0.5) * largura
        ax.bar(
            [xi + offset for xi in x], ys, width=largura,
            color=CORES.get(algo, "black"),
            label=algo, edgecolor="black", linewidth=0.4, alpha=0.88,
        )
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1.0, label="Rácio = 1 (óptimo)")
    ax.set_xticks(x)
    ax.set_xticklabels(nomes_niveis)
    ax.set_xlabel("Nível da instância")
    ax.set_ylabel("Rácio custo / custo óptimo (média)")
    ax.set_title("Qualidade da solução: rácio custo / custo óptimo por algoritmo", fontsize=13)
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    ax.legend(title="Algoritmo", loc="upper left", fontsize=9, ncol=2)
    fig.savefig(caminho, dpi=120)
    plt.close(fig)
    return caminho


def main(verbose: bool = True) -> None:
    """Ponto de entrada: corre a bateria, exporta CSV e gera os 3 gráficos."""
    DIRETORIO_RESULTADOS.mkdir(parents=True, exist_ok=True)
    instancias = _carregar_instancias()
    if verbose:
        print(f"Encontradas {len(instancias)} instâncias em {DIRETORIO_INSTANCIAS}.")
        print(f"A executar {len(ALGORITMOS)} algoritmos × {len(instancias)} instâncias "
              f"= {len(ALGORITMOS) * len(instancias)} execuções (limite {LIMITE_TEMPO_S}s).\n")
    linhas = correr_bateria(instancias, verbose=verbose)
    csv_path = exportar_csv(linhas)
    if verbose:
        print(f"\nCSV gravado em {csv_path}")
    nos, tempo, racio = _agrupar_para_graficos(linhas)
    g1 = grafico_nos_vs_tamanho(nos, DIRETORIO_RESULTADOS / "graf_nos_vs_tamanho.png")
    g2 = grafico_tempo_vs_tamanho(tempo, DIRETORIO_RESULTADOS / "graf_tempo_vs_tamanho.png")
    g3 = grafico_racio_custo(racio, DIRETORIO_RESULTADOS / "graf_custo_vs_optimo.png")
    if verbose:
        print(f"Gráfico 1 (nós vs tamanho): {g1}")
        print(f"Gráfico 2 (tempo vs tamanho): {g2}")
        print(f"Gráfico 3 (rácio custo/óptimo): {g3}")
        # Resumo rápido
        resolvidos = sum(1 for l in linhas if l["resolvido"])
        timeouts = sum(1 for l in linhas if l["status"] == "falhou (tempo)")
        memfail = sum(1 for l in linhas if l["status"] == "falhou (memoria)")
        print(f"\nResumo: {resolvidos} OK, {timeouts} timeout, {memfail} memória excedida, "
              f"{len(linhas)} execuções totais.")


if __name__ == "__main__":
    main()
