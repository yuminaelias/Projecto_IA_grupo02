"""

Menu de terminal que permite:
    • Escolher a instância (ficheiro JSON existente ou gerar uma nova na hora);
    • Escolher o algoritmo (BFS, DFS, IDS, UCS, Gulosa, A*, IDA*);
    • Escolher a heurística (h0, h1, h2) para algoritmos informados;
    • Definir limites de tempo (s) e memória (MB);
    • Visualizar passo a passo as pilhas de contentores em ASCII;
    • Ver o resumo das métricas no final (nós, custo, tempo, memória).


"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RAIZ: Path = Path(__file__).parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from dominio import ProblemaContentores
from problema import No, caminho
from buscas import bfs, dfs, ids, ucs, gulosa, a_estrela, ida_estrela

# Algoritmos disponíveis (nome, função, exige_heuristica).
ALGORITMOS: Dict[str, Tuple[Any, bool]] = {
    "BFS":    (bfs, False),
    "DFS":    (dfs, False),
    "IDS":    (ids, False),
    "UCS":    (ucs, False),
    "Gulosa": (gulosa, True),
    "A*":     (a_estrela, True),
    "IDA*":   (ida_estrela, True),
}

HEURISTICAS = ["h0", "h1", "h2"]


# =============================================================================
# Visualização ASCII
# =============================================================================

def _marcacoes(contentor: int, pesados: set, refrigerados: set) -> str:
    """Devolve os marcadores de pesado (P) e refrigerado (R) para o contentor."""
    marca = ""
    if contentor in pesados:
        marca += "P"
    if contentor in refrigerados:
        marca += "R"
    return marca


def _formatar_contentor(contentor: int, pesados: set, refrigerados: set, largura: int = 4) -> str:
    """Formata um contentor como ``[NN]`` ou ``[NNR]`` (com marcadores)."""
    marca = _marcacoes(contentor, pesados, refrigerados)
    texto = f"{contentor}{marca}"
    # Centraliza dentro da largura: ``[ NN ]``
    return f"[{texto:^{largura - 2}}]"


def renderizar_pilhas(
    estado: Any,
    S: int,
    H: int,
    pesados: set,
    refrigerados: set,
    proximo: int,
    largura_pilha: int = 6,
) -> str:
    """Desenha as pilhas em ASCII, da base para o topo, em colunas.

    Cada pilha é desenhada verticalmente (base em baixo). Os índices de pilha
    aparecem na base (1..S) para corresponder à interface humana do P2.
    """
    pilhas = getattr(estado, "pilhas", estado)
    largura = largura_pilha
    # Linhas do topo (H) para a base (1).
    linhas: List[str] = []
    # Cabeçalho de tomadas: T T . . . (pilhas 0 e 1 têm tomada para refrigerados).
    tomadas = []
    for i in range(S):
        tomadas.append(" T " if i < 2 else "   ")
    linhas.append(" " * 4 + " ".join(tomadas))
    linhas.append(" " * 4 + "-" * (S * (largura + 1) + 1))
    # Linhas de contentores, do topo (H) para baixo (1).
    for nivel in range(H, 0, -1):
        partes = [" " * 4]
        for i in range(S):
            pilha = pilhas[i] if i < len(pilhas) else ()
            if len(pilha) >= nivel:
                c = pilha[nivel - 1]  # base -> topo
                partes.append(_formatar_contentor(c, pesados, refrigerados, largura))
            else:
                partes.append(" " * largura)
        linhas.append(" ".join(partes))
    # Base de cada pilha (índice 1..S).
    bases = [" " * 4] + [f"  {i+1} " for i in range(S)]
    linhas.append(" ".join(bases))
    linhas.append(" " * 4 + "=" * (S * (largura + 1) + 1))
    # Linha do próximo contentor a levantar.
    linhas.append(f"  >> Próximo a levantar: {proximo}")
    return "\n".join(linhas)


def explicar_accao(accao: tuple, pesados: set, refrigerados: set) -> str:
    """Traduz uma acção interna (0-indexed) para uma descrição humana (1-indexed)."""
    if accao[0] == "levantar":
        i = accao[1]
        return f"levantar contentor do topo da pilha {i + 1}"
    # mover i -> j
    _, i, j = accao
    return f"mover topo da pilha {i + 1} para a pilha {j + 1}"


def visualizar_solucao(
    problema: ProblemaContentores,
    estados: List[Any],
    accoes: List[tuple],
    pausa_interactiva: bool = True,
) -> None:
    """Mostra a sequência de estados e acções passo a passo."""
    S, H = problema.S, problema.H
    pesados = set(problema.pesados)
    refrigerados = set(problema.refrigerados)
    print("\n" + "=" * 70)
    print("Estado inicial:")
    print(renderizar_pilhas(estados[0], S, H, pesados, refrigerados, estados[0].proximo))
    if pausa_interactiva:
        try:
            input("\n[Enter para continuar...]")
        except EOFError:
            print()

    for k, (estado, accao) in enumerate(zip(estados[1:], accoes), start=1):
        print("\n" + "-" * 70)
        print(f"Passo {k}/{len(accoes)}: {explicar_accao(accao, pesados, refrigerados)}")
        print(renderizar_pilhas(estado, S, H, pesados, refrigerados, estado.proximo))
        if pausa_interactiva and k < len(accoes):
            try:
                input("\n[Enter para continuar...]")
            except EOFError:
                print()

    print("\n" + "=" * 70)
    print(f"Estado final — todos os contentores levantados.")
    print("=" * 70)


# =============================================================================
# Resumo de métricas
# =============================================================================

def mostrar_resumo(resultado: Any, problema: ProblemaContentores) -> None:
    """Apresenta as métricas finais de uma execução."""
    print("\n" + "=" * 70)
    print("Resumo da execução")
    print("=" * 70)
    print(f"  Algoritmo          : {resultado.algoritmo}")
    print(f"  Heurística         : {resultado.heuristica}")
    print(f"  Status             : {resultado.status}")
    print(f"  Resolvido          : {'sim' if resultado.resolvido else 'não'}")
    if resultado.resolvido:
        print(f"  Custo da solução   : {resultado.custo}")
        print(f"  Nº de acções       : {resultado.comprimento}")
    print(f"  Nós expandidos     : {resultado.nos_expandidos}")
    print(f"  Nós gerados        : {resultado.nos_gerados}")
    print(f"  Nós re-expandidos  : {resultado.nos_reexpandidos}")
    print(f"  Tamanho máx. front.: {resultado.max_fronteira}")
    print(f"  Tempo              : {resultado.tempo_s:.6f} s")
    print(f"  Memória (pico)     : {resultado.memoria_mb:.6f} MB")
    print(f"  Instância          : S={problema.S}, H={problema.H}, "
          f"N={problema.total_contentores}")
    print("=" * 70)


# =============================================================================
# Menu interactivo
# =============================================================================

def _ler_int(prompt: str, minimo: int, maximo: int, padrao: Optional[int] = None) -> int:
    """Lê um inteiro do utilizador com validação."""
    while True:
        try:
            txt = input(prompt).strip()
            if not txt and padrao is not None:
                return padrao
            v = int(txt)
            if minimo <= v <= maximo:
                return v
            print(f"  Valor fora do intervalo [{minimo}, {maximo}]. Tente novamente.")
        except (ValueError, EOFError):
            print("  Entrada inválida. Tente novamente.")


def _ler_float(prompt: str, padrao: float) -> float:
    while True:
        try:
            txt = input(prompt).strip()
            if not txt:
                return padrao
            return float(txt)
        except (ValueError, EOFError):
            print("  Entrada inválida. Tente novamente.")


def escolher_instancia() -> Optional[Dict[str, Any]]:
    """Menu para escolher ou gerar uma instância."""
    print("\n--- Escolha da instância ---")
    print("  1. Carregar ficheiro JSON existente")
    print("  2. Gerar uma nova instância na hora")
    print("  0. Voltar")
    op = _ler_int("Opção: ", 0, 2, padrao=1)
    if op == 0:
        return None
    if op == 1:
        # Listar ficheiros disponíveis
        diretorio = RAIZ / "instancias"
        ficheiros = sorted(diretorio.glob("*.json"))
        if not ficheiros:
            print("  Não há ficheiros JSON em instancias/.")
            return None
        print("\n  Ficheiros disponíveis:")
        for i, f in enumerate(ficheiros):
            print(f"    {i + 1:>2}. {f.name}")
        idx = _ler_int(f"  Escolha [1-{len(ficheiros)}]: ", 1, len(ficheiros), padrao=1)
        caminho = ficheiros[idx - 1]
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        dados["_caminho"] = str(caminho)
        return dados
    # op == 2: gerar nova
    try:
        from gerador import gerar_instancia, NIVEIS
    except ImportError:
        print("  Módulo gerador não disponível.")
        return None
    print("\n  Níveis disponíveis: " + ", ".join(NIVEIS.keys()))
    niveis = list(NIVEIS.keys())
    nivel_idx = _ler_int(f"  Nível [1-{len(niveis)}]: ", 1, len(niveis), padrao=1)
    nivel = niveis[nivel_idx - 1]
    indice = _ler_int(f"  Índice [0-9]: ", 0, 9, padrao=0)
    dados = gerar_instancia(nivel, indice)
    dados["_caminho"] = "(gerada na hora)"
    return dados


def escolher_algoritmo() -> Optional[Tuple[str, str]]:
    """Menu para escolher algoritmo e heurística."""
    print("\n--- Escolha do algoritmo ---")
    nomes = list(ALGORITMOS.keys())
    for i, n in enumerate(nomes):
        heur = " (heurística)" if ALGORITMOS[n][1] else ""
        print(f"  {i + 1}. {n}{heur}")
    print("  0. Voltar")
    idx = _ler_int(f"Opção [1-{len(nomes)}]: ", 0, len(nomes), padrao=5)
    if idx == 0:
        return None
    nome = nomes[idx - 1]
    heur = "—"
    if ALGORITMOS[nome][1]:
        print(f"\n  Heurísticas disponíveis: {', '.join(HEURISTICAS)}")
        h_idx = _ler_int(f"  Heurística [1-{len(HEURISTICAS)}]: ", 1, len(HEURISTICAS), padrao=2)
        heur = HEURISTICAS[h_idx - 1]
    return nome, heur


def escolher_limites() -> Tuple[float, float]:
    """Lê os limites de tempo e memória."""
    print("\n--- Limites de execução ---")
    t = _ler_float("  Limite de tempo (s) [padrão 60]: ", 60.0)
    m = _ler_float("  Limite de memória (MB) [padrão 2048]: ", 2048.0)
    return t, m


def executar_e_mostrar(
    dados: Dict[str, Any],
    nome_algo: str,
    heur: str,
    limite_t: float,
    limite_m: float,
    mostrar_passos: bool = True,
    pausa_interactiva: Optional[bool] = None,
) -> None:
    """Executa o algoritmo pedido e mostra visualização + métricas.

    - ``mostrar_passos``: se True, mostra a sequência de estados passo a passo.
    - ``pausa_interactiva``: se True, pede Enter entre passos. Se None, usa
      ``sys.stdin.isatty()`` (pausa só em terminal interactivo).
    """
    problema = ProblemaContentores(
        dados["S"], dados["H"], dados["pilhas"],
        dados.get("pesados", []), dados.get("refrigerados", []),
    )
    fn, exige_h = ALGORITMOS[nome_algo]
    print(f"\nA executar {nome_algo}" + (f" com heurística {heur}" if exige_h else "") + "...")
    if exige_h:
        resultado = fn(problema, heur, limite_tempo_s=limite_t, limite_memoria_mb=limite_m)
    else:
        resultado = fn(problema, limite_tempo_s=limite_t, limite_memoria_mb=limite_m)
    mostrar_resumo(resultado, problema)
    if resultado.resolvido and mostrar_passos:
        estados, accoes = resultado.caminho()
        if estados:
            if pausa_interactiva is None:
                pausa_interactiva = sys.stdin.isatty()
            try:
                visualizar_solucao(problema, estados, accoes, pausa_interactiva=pausa_interactiva)
            except KeyboardInterrupt:
                print("\n\nVisualização interrompida.")


def menu_principal() -> None:
    """Loop principal do menu."""
    print("=" * 70)
    print("  P2 — Reordenação de Contentores no Porto de Maputo")
    print("  Inteligência Artificial I · Grupo 02 (Laboral) · UEM 2026")
    print("=" * 70)
    while True:
        print("\n--- Menu principal ---")
        print("  1. Escolher instância e executar algoritmo")
        print("  2. Ver bateria de instâncias geradas")
        print("  3. Ver algoritmos disponíveis")
        print("  0. Sair")
        op = _ler_int("Opção: ", 0, 3, padrao=1)
        if op == 0:
            print("Adeus!")
            return
        if op == 2:
            _mostrar_bateria()
            continue
        if op == 3:
            _mostrar_algoritmos()
            continue
        # op == 1
        dados = escolher_instancia()
        if dados is None:
            continue
        escolha = escolher_algoritmo()
        if escolha is None:
            continue
        nome_algo, heur = escolha
        limite_t, limite_m = escolher_limites()
        executar_e_mostrar(dados, nome_algo, heur, limite_t, limite_m)


def _mostrar_bateria() -> None:
    """Lista as instâncias geradas (nível, N, pesados, refrigerados)."""
    diretorio = RAIZ / "instancias"
    ficheiros = sorted(diretorio.glob("*.json"))
    if not ficheiros:
        print("  Nenhuma instância encontrada. Execute `python gerador.py`.")
        return
    print(f"\n  {'Ficheiro':<22} {'Nível':<10} {'S':>3} {'H':>3} {'N':>4} {'#P':>4} {'#R':>4}")
    print("  " + "-" * 60)
    for f in ficheiros:
        d = json.loads(f.read_text(encoding="utf-8"))
        N = sum(len(p) for p in d.get("pilhas", []))
        nivel = d.get("nivel", f.stem.split("_")[0])
        print(f"  {f.name:<22} {nivel:<10} {d.get('S', '?'):>3} {d.get('H', '?'):>3} "
              f"{N:>4} {len(d.get('pesados', [])):>4} {len(d.get('refrigerados', [])):>4}")


def _mostrar_algoritmos() -> None:
    print("\n  Algoritmos disponíveis:")
    for nome, (_, exige_h) in ALGORITMOS.items():
        heur = " (exige heurística h0/h1/h2)" if exige_h else ""
        print(f"    • {nome}{heur}")


# =============================================================================
# Modo CLI (argumentos)
# =============================================================================

def _processar_args() -> int:
    parser = argparse.ArgumentParser(
        description="Interface para o P2 — Reordenação de Contentores."
    )
    parser.add_argument("--instancia", type=str, default=None,
                        help="Caminho para o ficheiro JSON da instância.")
    parser.add_argument("--algoritmo", type=str, default=None,
                        choices=list(ALGORITMOS.keys()),
                        help="Algoritmo a executar.")
    parser.add_argument("--heuristica", type=str, default="h1",
                        choices=HEURISTICAS,
                        help="Heurística para algoritmos informados.")
    parser.add_argument("--limite-tempo", type=float, default=60.0,
                        help="Limite de tempo em segundos (padrão 60).")
    parser.add_argument("--limite-memoria", type=float, default=2048.0,
                        help="Limite de memória em MB (padrão 2048).")
    parser.add_argument("--sem-pausa", action="store_true",
                        help="Não pedir Enter entre passos da visualização.")
    args = parser.parse_args()
    if not args.instancia or not args.algoritmo:
        return 0  # cai no menu interactivo
    caminho = Path(args.instancia)
    if not caminho.exists():
        print(f"Ficheiro não encontrado: {caminho}")
        return 1
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    executar_e_mostrar(
        dados, args.algoritmo, args.heuristica,
        args.limite_tempo, args.limite_memoria,
        mostrar_passos=True,
        pausa_interactiva=not args.sem_pausa,
    )
    return 0


def main() -> None:
    """Ponto de entrada."""
    if len(sys.argv) > 1:
        rc = _processar_args()
        if rc != 0 or any(a in sys.argv for a in ("--instancia", "--algoritmo")):
            return
    menu_principal()


if __name__ == "__main__":
    main()
