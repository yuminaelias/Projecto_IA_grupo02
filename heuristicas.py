"""
Módulo de Heurísticas para o Problema P2: Reordenação de Contentores no Porto de Maputo.
Disciplina: Inteligência Artificial I (2026) - UEM / Faculdade de Engenharia
Frente 4: Caravela, Rosário Pompílio

Este módulo implementa:
  - h0: Heurística trivial (h0(s) = 0.0), para busca cega / UCS.
  - h1: Heurística base admissível baseada na contagem de contentores bloqueadores.
  - h2: Heurística mais informada combinando:
        1. Custo mínimo real de deslocação do pórtico (1.1 em vez de 1.0).
        2. Penalização de duplo movimento (+1.1 extra).
        3. Custo de desvio de contentores refrigerados (+1.1 extra).
  - calcular_b_estrela: Cálculo numérico do factor de ramificação efectivo b* por bissecção.
"""

from typing import Any, Optional, Set, Tuple


def h0(estado: Any, problema: Optional[Any] = None) -> float:
    """
    Heurística trivial (nula).
    Garante h0(s) = 0.0 para qualquer estado s.
    Quando usada no A*, equivale à Busca de Custo Uniforme (UCS).
    """
    return 0.0


def h1(estado: Any, problema: Optional[Any] = None) -> float:
    """
    Heurística h1 (Admissível):
    Conta o número de contentores bloqueadores no bloco do terminal.

    Um contentor c na pilha i é considerado 'bloqueador' se existir algum
    contentor c' < c abaixo dele nessa mesma pilha i.
    Como c' tem de ser levantado antes de c, e c está por cima de c',
    c terá obrigatoriamente de sofrer pelo menos uma acção 'mover' para outra pilha,
    cujo custo mínimo real é 1.1 >= 1.0.

    Logo, a soma simples de 1.0 por cada contentor bloqueador nunca sobrestima
    o custo real h*(s) até ao estado objectivo:
        h1(s) <= h*(s).
    """
    pilhas: Tuple[Tuple[int, ...], ...] = getattr(estado, "pilhas", estado)
    bloqueadores: int = 0

    for pilha in pilhas:
        for idx, contentor in enumerate(pilha):
            if any(c_abaixo < contentor for c_abaixo in pilha[:idx]):
                bloqueadores += 1

    return float(bloqueadores)


def _pode_evitar_duplo_movimento(
    c: int,
    c_min: int,
    idx_origem: int,
    pilhas: Tuple[Tuple[int, ...], ...],
    num_pilhas: int,
    refrigerados: Set[int],
) -> bool:
    """Verifica se existe pilha de destino onde c não cause bloqueio incontornável."""
    for j in range(num_pilhas):
        if j == idx_origem:
            continue
        # Contentor refrigerado só pode ir para pilhas 0 ou 1
        if c in refrigerados and j not in (0, 1):
            continue
        pilha_dest = pilhas[j]
        if not pilha_dest:
            return True
        # Bloqueio incontornável: se existir k tal que c_min <= k < c
        tem_bloqueio = any(c_min <= k < c for k in pilha_dest)
        if not tem_bloqueio:
            return True
    return False


def _desvio_refrigerado_bloqueado(
    c: int,
    c_min: int,
    idx_origem: int,
    pilhas: Tuple[Tuple[int, ...], ...],
    num_pilhas: int,
    altura_max: int,
    refrigerados: Set[int],
) -> bool:
    """Verifica se a outra tomada eléctrica está saturada com contentores > c_min."""
    if c not in refrigerados or num_pilhas < 2:
        return False
    outra = 1 if idx_origem == 0 else (0 if idx_origem == 1 else None)
    if outra is None:
        return False
    pilha_outra = pilhas[outra]
    return len(pilha_outra) >= altura_max and all(k > c_min for k in pilha_outra)


def h2(estado: Any, problema: Optional[Any] = None) -> float:
    """
    Heurística h2 (Mais informada e estritamente admissível):
    Combina três refinamentos admissíveis sobre h1:

    1. Custo mínimo do pórtico: Custo mínimo por movimento é 1.1 (em vez de 1.0).
    2. Penalização de duplo movimento (+1.1 extra).
    3. Custo de desvio refrigerado (+1.1 extra).
    """
    pilhas: Tuple[Tuple[int, ...], ...] = getattr(estado, "pilhas", estado)
    refrigerados: Set[int] = getattr(problema, "refrigerados", frozenset({2, 5}))
    num_pilhas: int = getattr(problema, "S", len(pilhas))
    altura_maxima: int = getattr(problema, "H", 4)

    custo_total: float = 0.0

    for i, pilha in enumerate(pilhas):
        for idx, contentor in enumerate(pilha):
            bloqueados_abaixo = [c for c in pilha[:idx] if c < contentor]
            if not bloqueados_abaixo:
                continue

            # Melhoria 1: Custo mínimo de deslocação do pórtico = 1.1
            custo_total += 1.1
            c_min = min(bloqueados_abaixo)

            # Melhoria 2: Penalização de duplo movimento
            if not _pode_evitar_duplo_movimento(contentor, c_min, i, pilhas, num_pilhas, refrigerados):
                custo_total += 1.1

            # Melhoria 3: Custo de desvio refrigerado
            if _desvio_refrigerado_bloqueado(contentor, c_min, i, pilhas, num_pilhas, altura_maxima, refrigerados):
                custo_total += 1.1

    return round(custo_total, 2)


def calcular_b_estrela(N: int, d: int, tol: float = 1e-7, max_iter: int = 100) -> float:
    """
    Calcula numericamente o factor de ramificação efectivo b* usando o método da bissecção.

    Equação a resolver:
        N + 1 = 1 + b* + (b*)^2 + ... + (b*)^d
        <=> N = b* + (b*)^2 + ... + (b*)^d
    """
    if d <= 0 or N <= 0:
        return 1.0
    if d == 1:
        return float(N)
    if N == d:
        return 1.0

    low: float = 0.0
    high: float = max(2.0, float(N))

    def f(b: float) -> float:
        if abs(b - 1.0) < 1e-12:
            return float(d) - N
        return (b * (b**d - 1.0)) / (b - 1.0) - N

    for _ in range(max_iter):
        mid: float = (low + high) / 2.0
        val: float = f(mid)

        if abs(val) < tol or (high - low) / 2.0 < tol:
            return round(mid, 4)

        if val < 0:
            low = mid
        else:
            high = mid

    return round((low + high) / 2.0, 4)
