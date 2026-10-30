"""Heurísticas e métricas de pesquisa para o problema P2.

Inclui as heurísticas h0, h1 e h2, bem como o cálculo do factor de
ramificação efectivo através do método da bissecção.
"""

from typing import Any, Optional, Set, Tuple


def h0(estado: Any, problema: Optional[Any] = None) -> float:
    """Devolve zero para qualquer estado, equivalendo a custo uniforme no A*."""
    return 0.0


def h1(estado: Any, problema: Optional[Any] = None) -> float:
    """Estima o custo restante contando os contentores que bloqueiam outros.

    Um contentor é contabilizado quando existe, abaixo dele na mesma pilha,
    pelo menos um contentor com identificador inferior. Cada bloqueador exige
    pelo menos uma deslocação antes de o contentor pretendido poder ser
    levantado; por isso, a contribuição unitária não excede o custo mínimo
    dessa deslocação.
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
    """Indica se existe um destino permitido sem bloqueio por contentores intermédios."""
    for j in range(num_pilhas):
        if j == idx_origem:
            continue
        # Os contentores refrigerados só podem ser colocados nas pilhas 0 e 1.
        if c in refrigerados and j not in (0, 1):
            continue
        pilha_dest = pilhas[j]
        if not pilha_dest:
            return True
        # Um contentor intermédio pode obrigar a deslocar c novamente.
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
    """Verifica se a pilha refrigerada alternativa está cheia e indisponível."""
    if c not in refrigerados or num_pilhas < 2:
        return False
    outra = 1 if idx_origem == 0 else (0 if idx_origem == 1 else None)
    if outra is None:
        return False
    pilha_outra = pilhas[outra]
    return len(pilha_outra) >= altura_max and all(k > c_min for k in pilha_outra)


def h2(estado: Any, problema: Optional[Any] = None) -> float:
    """Calcula uma estimativa informada com base nos bloqueios e restrições.

    A estimativa considera o custo mínimo de deslocação, a necessidade de
    movimentos adicionais e as restrições de colocação dos contentores
    refrigerados.
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

            # O custo mínimo de deslocação entre pilhas é 1.1.
            custo_total += 1.1
            c_min = min(bloqueados_abaixo)

            if not _pode_evitar_duplo_movimento(contentor, c_min, i, pilhas, num_pilhas, refrigerados):
                custo_total += 1.1

            if _desvio_refrigerado_bloqueado(contentor, c_min, i, pilhas, num_pilhas, altura_maxima, refrigerados):
                custo_total += 1.1

    return round(custo_total, 2)


def calcular_b_estrela(N: int, d: int, tol: float = 1e-7, max_iter: int = 100) -> float:
    """Calcula o factor de ramificação efectivo para N nós e profundidade d.

    Resolve por bissecção a equação N = b + b² + ... + bᵈ. Devolve 1.0
    quando N ou d não são positivos.
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
