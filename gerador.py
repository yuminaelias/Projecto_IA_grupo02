"""Gerador de instâncias aleatórias para o P2 — Porto de Maputo.

Universidade Eduardo Mondlane — Inteligência Artificial I (2026)
Grupo 02 (Laboral) — Frente 5: Modesta Cipriano Manuel

Semente oficial do grupo: 202602.

Estratégia de construção (garante solvabilidade E dificuldade graduada):
    1. Coloca os contentores por ordem DECRESCENTE de identificador (N, N-1, ..., 1)
       sobre pilhas aleatórias válidas. Como o contentor 1 é sempre o último a ser
       colocado, fica no topo de alguma pilha; a sequência de levantamentos
       1, 2, ..., N é, por construção, uma solução viável (custo 0).
    2. Fase de "enterro" do contentor 1: move-se o topo de outras pilhas para a
       pilha que contém 1, de modo a que 1 fique enterrado sob ``target_bury``
       contentores (1 no nível Pequeno, 2 no Médio, 3 no Grande).
    3. Fase de "embaralhamento" geral: aplicam-se K movimentos aleatórios
       válidos (K = 2 / 6 / 12 por nível) para diversificar a configuração.

    Cada movimento aplicado é uma acção legal do P2; por isso a configuração
    final permanece solvável (basta desfazer os movimentos por ordem inversa
    e depois levantar 1, 2, ..., N). A colocação respeita as três restrições:
        • altura máxima H de cada pilha;
        • contentores pesados apenas sobre pilhas vazias ou sobre outros pesados;
        • contentores refrigerados apenas nas pilhas 0 e 1 (com tomada).

Formato JSON de saída (compatível com ``ProblemaContentores(**dados)``):

    {
      "S": 4, "H": 4,
      "pesados": [5, 7, 8, 9],
      "refrigerados": [2, 5],
      "pilhas": [[8, 2, 10], [5, 1, 6], [9, 4], [7, 3]],
      "nivel": "Pequeno", "indice": 0, "semente": 202602,
      "num_contentores": 10
    }
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dominio import ProblemaContentores
except ImportError:  # pragma: no cover — tolera importação isolada
    ProblemaContentores = None  # type: ignore

# Semente oficial do Grupo 02 — definida no GUIA_INTEGRACAO_GRUPO02.md.
SEMENTE_OFICIAL: int = 202602

# Directório por omissão para as instâncias geradas.
DIRETORIO_INSTANCIAS: Path = Path(__file__).parent / "instancias"

# Definição dos três níveis de dificuldade — intervalos inclusivos.
NIVEIS: Dict[str, Dict[str, Tuple[int, int]]] = {
    "Pequeno": {"S": (3, 4), "H": (3, 4), "N": (6, 8)},
    "Medio":   {"S": (4, 5), "H": (4, 4), "N": (10, 14)},
    "Grande":  {"S": (5, 6), "H": (4, 5), "N": (16, 25)},
}

# Compensação determinística por nível — garante reprodutibilidade cruzada.
_OFFSET_NIVEL: Dict[str, int] = {"Pequeno": 0, "Medio": 1000, "Grande": 2000}

# Parâmetros de dificuldade por nível: (enterro-alvo-de-1, movimentos-extra).
# Calibrados para que:
#   • Pequeno: todos os 7 algoritmos terminam em <60 s (instâncias triviais);
#   • Médio:   BFS/DFS/IDS começam a exceder 60 s, UCS e informadas terminam;
#   • Grande:  apenas Gulosa/A*/IDA* terminam dentro de 60 s.
_DIFICULDADE: Dict[str, Tuple[int, int]] = {
    "Pequeno": (0, 0),
    "Medio":   (1, 4),
    "Grande":  (2, 10),
}


def _pode_colocar(
    c: int,
    i: int,
    pilhas: List[List[int]],
    H: int,
    pesados_set: set,
    refri_set: set,
) -> bool:
    """Indica se o contentor ``c`` pode ser colocado no topo da pilha ``i``."""
    if len(pilhas[i]) >= H:
        return False
    if c in refri_set and i not in (0, 1):
        return False
    if c in pesados_set:
        if pilhas[i] and pilhas[i][-1] not in pesados_set:
            return False
    return True


def _containers_acima(pilha: List[int], c: int) -> int:
    """Número de contentores acima de ``c`` na ``pilha`` (-1 se ausente)."""
    if c not in pilha:
        return -1
    return len(pilha) - pilha.index(c) - 1


def _escolher_parametros(
    rng: random.Random, nivel: str
) -> Tuple[int, int, int, List[int], List[int]]:
    """Escolhe S, H, N, pesados e refrigerados dentro dos intervalos do nível."""
    cfg = NIVEIS[nivel]
    # Garante capacidade mínima: S*H >= N com folga de pelo menos 2 posições
    # para que existam manobras de reorganização (mover contentores).
    for _ in range(64):
        S = rng.randint(*cfg["S"])
        H = rng.randint(*cfg["H"])
        N = rng.randint(*cfg["N"])
        if S * H >= N + 2:
            break
    else:
        S, H = max(cfg["S"]), max(cfg["H"])
        N = min(cfg["N"])

    # Pesados: entre 20 % e 35 % dos contentores, mínimo 1.
    n_pesados = max(1, round(N * rng.uniform(0.20, 0.35)))
    # Refrigerados: entre 15 % e 25 %, mínimo 1, no máximo N - n_pesados.
    n_refri = max(1, min(N - n_pesados, round(N * rng.uniform(0.15, 0.25))))
    pesados = sorted(rng.sample(range(1, N + 1), n_pesados))
    # Refrigerados escolhidos de entre os NÃO-pesados (não há contentor pesado
    # e refrigerado em simultâneo, para evitar casos patológicos).
    candidatos_refri = [c for c in range(1, N + 1) if c not in pesados]
    if len(candidatos_refri) < n_refri:
        n_refri = len(candidatos_refri)
    refrigerados = sorted(rng.sample(candidatos_refri, n_refri))
    return S, H, N, pesados, refrigerados


def _construir_pilhas(
    S: int,
    H: int,
    N: int,
    pesados: List[int],
    refrigerados: List[int],
    rng: random.Random,
    nivel: str,
) -> Optional[List[List[int]]]:
    """Constrói pilhas solváveis com dificuldade controlada por ``nivel``.

    Pipeline:
      1. Coloca contentores N, N-1, ..., 2 em pilhas aleatórias válidas
         (1 é tratado à parte, para garantir que tem espaço acima).
      2. Coloca 1 numa pilha com pelo menos ``target_bury`` slots livres acima
         (respeitando refrigeração se 1 for refrigerado).
      3. Embaralhamento aleatório com ``n_scramble`` movimentos válidos, preservando
         a pilha de 1 (não se mexe em topos dessa pilha, nem se move para ela).
      4. Enterra 1 movendo topos leves de outras pilhas para a pilha de 1.
    """
    pesados_set = set(pesados)
    refri_set = set(refrigerados)
    pilhas: List[List[int]] = [[] for _ in range(S)]
    target_bury, n_scramble = _DIFICULDADE[nivel]

    # ---------- Fase 1: colocação decrescente (N..2) ----------
    for c in range(N, 1, -1):
        validos = [
            i for i in range(S)
            if _pode_colocar(c, i, pilhas, H, pesados_set, refri_set)
        ]
        if not validos:
            return None
        i = rng.choice(validos)
        pilhas[i].append(c)

    # ---------- Fase 1b: colocar 1 com espaço para enterro ----------
    valid_idx_1 = [0, 1] if 1 in refri_set else list(range(S))
    # Garante que cabem target_bury contentores acima de 1: len + 1 + target_bury ≤ H
    valid_idx_1 = [
        i for i in valid_idx_1
        if len(pilhas[i]) + 1 + target_bury <= H
    ]
    if not valid_idx_1:
        return None
    idx_1 = rng.choice(valid_idx_1)
    pilhas[idx_1].append(1)

    # ---------- Fase 2: embaralhamento aleatório (preserva a pilha de 1) ----------
    # Não se mexe em topos da pilha idx_1 (para não desenterrar 1), mas pode-se
    # mover topos de outras pilhas entre si.
    for _ in range(n_scramble):
        movimentos: List[Tuple[int, int]] = []
        for i in range(S):
            if i == idx_1 or not pilhas[i]:
                continue
            topo = pilhas[i][-1]
            for j in range(S):
                if i == j or j == idx_1:
                    continue
                if _pode_colocar(topo, j, pilhas, H, pesados_set, refri_set):
                    movimentos.append((i, j))
        if not movimentos:
            break
        i, j = rng.choice(movimentos)
        pilhas[j].append(pilhas[i].pop())

    # ---------- Fase 3: enterro do contentor 1 (após embaralhamento) ----------
    tentativas = 0
    while _containers_acima(pilhas[idx_1], 1) < target_bury and tentativas < 60:
        tentativas += 1
        if len(pilhas[idx_1]) >= H:
            break
        candidatos = [
            i for i in range(S)
            if i != idx_1 and pilhas[i]
            and _pode_colocar(pilhas[i][-1], idx_1, pilhas, H, pesados_set, refri_set)
        ]
        if not candidatos:
            break
        i = rng.choice(candidatos)
        pilhas[idx_1].append(pilhas[i].pop())

    return pilhas


def _validar_instancia(
    S: int,
    H: int,
    pilhas: List[List[int]],
    pesados: List[int],
    refrigerados: List[int],
) -> bool:
    """Valida a instância através do construtor de ``ProblemaContentores``.

    Caso o módulo ``dominio`` não esteja disponível, faz apenas uma validação
    sintáctica interna (contagem, intervalos, alturas).
    """
    if ProblemaContentores is not None:
        try:
            ProblemaContentores(S, H, pilhas, pesados, refrigerados)
            return True
        except ValueError:
            return False
    # Validação sintáctica de recurso.
    if len(pilhas) != S:
        return False
    contentores = [c for p in pilhas for c in p]
    if sorted(contentores) != list(range(1, len(contentores) + 1)):
        return False
    if any(len(p) > H for p in pilhas):
        return False
    return True


def gerar_instancia(
    nivel: str, indice: int, semente: int = SEMENTE_OFICIAL
) -> Dict[str, Any]:
    """Gera uma instância para o nível e índice pedidos.

    O índice varia de 0 a 9 (10 instâncias por nível). A semente derivada é
    ``semente + offset(nivel) + indice``, garantindo reprodutibilidade.
    """
    if nivel not in NIVEIS:
        raise ValueError(f"Nível desconhecido: {nivel!r}")
    if not (0 <= indice < 10):
        raise ValueError(f"Índice fora do intervalo [0, 9]: {indice!r}")

    semente_derivada = semente + _OFFSET_NIVEL[nivel] + indice
    rng = random.Random(semente_derivada)

    for _ in range(200):
        S, H, N, pesados, refrigerados = _escolher_parametros(rng, nivel)
        pilhas = _construir_pilhas(S, H, N, pesados, refrigerados, rng, nivel)
        if pilhas is None:
            continue
        if not _validar_instancia(S, H, pilhas, pesados, refrigerados):
            continue
        return {
            "S": S,
            "H": H,
            "pesados": pesados,
            "refrigerados": refrigerados,
            "pilhas": [list(p) for p in pilhas],
            "nivel": nivel,
            "indice": indice,
            "semente": semente,
            "num_contentores": N,
        }
    raise RuntimeError(
        f"Não foi possível gerar uma instância válida para {nivel}/{indice} "
        f"com a semente {semente}."
    )


def gerar_bateria(
    semente: int = SEMENTE_OFICIAL,
    diretorio: Path = DIRETORIO_INSTANCIAS,
    niveis: Optional[List[str]] = None,
    por_nivel: int = 10,
) -> List[Path]:
    """Gera todos os ficheiros JSON (30 por omissão) e devolve os caminhos.

    Os ficheiros são nomeados ``<nivel>_<indice>.json`` (ex.: ``Pequeno_0.json``)
    e escritos em ``diretorio``. A instância ``base.json`` NÃO é sobreposta.
    """
    diretorio = Path(diretorio)
    diretorio.mkdir(parents=True, exist_ok=True)
    niveis = niveis or list(NIVEIS.keys())
    ficheiros: List[Path] = []
    for nivel in niveis:
        for indice in range(por_nivel):
            dados = gerar_instancia(nivel, indice, semente=semente)
            nome = f"{nivel}_{indice}.json"
            caminho = diretorio / nome
            caminho.write_text(
                json.dumps(dados, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            ficheiros.append(caminho)
    return ficheiros


def carregar_instancia(caminho: Path) -> Dict[str, Any]:
    """Carrega um ficheiro JSON de instância (compatível com ``ProblemaContentores``)."""
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def resumo_bateria(diretorio: Path = DIRETORIO_INSTANCIAS) -> str:
    """Devolve um resumo textual da bateria gerada (para diagnóstico e README)."""
    diretorio = Path(diretorio)
    linhas = [f"Bateria de instâncias — semente {SEMENTE_OFICIAL}"]
    for nivel in NIVEIS:
        ficheiros = sorted(diretorio.glob(f"{nivel}_*.json"))
        if not ficheiros:
            continue
        total_n = 0
        for f in ficheiros:
            dados = carregar_instancia(f)
            total_n += dados["num_contentores"]
        media = total_n / len(ficheiros)
        linhas.append(
            f"  {nivel:<8}: {len(ficheiros):>2} instâncias, "
            f"N médio = {media:.1f}"
        )
    return "\n".join(linhas)


def main() -> None:
    """Ponto de entrada para ``python gerador.py``."""
    ficheiros = gerar_bateria()
    print(f"Geradas {len(ficheiros)} instâncias em {DIRETORIO_INSTANCIAS}.")
    print(resumo_bateria())


if __name__ == "__main__":
    main()
