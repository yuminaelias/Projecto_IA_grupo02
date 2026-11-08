"""Heurísticas admissíveis e métrica de ramificação efectiva para o P2.

Inclui as heurísticas h0, h1 e h2, bem como o cálculo do factor de
ramificação efectivo através do método da bissecção.
As pilhas são representadas da base para o topo.
"""

from typing import Any, Optional, Tuple


def _pilhas(estado: Any) -> Tuple[Tuple[int, ...], ...]:
    """Aceita EstadoContentores ou uma sequência de pilhas."""
    return getattr(estado, "pilhas", estado)


def _numero_bloqueadores(estado: Any) -> int:
    """Conta cada contentor uma única vez se houver algum menor abaixo dele."""
    total = 0
    for pilha in _pilhas(estado):
        menor_abaixo = None
        for contentor in pilha:  # base -> topo
            if menor_abaixo is not None and menor_abaixo < contentor:
                total += 1
            if menor_abaixo is None or contentor < menor_abaixo:
                menor_abaixo = contentor
    return total


def h0(estado: Any, problema: Optional[Any] = None) -> float:
    """Heurística nula: A* com h0 comporta-se como UCS."""
    return 0.0


def h1(estado: Any, problema: Optional[Any] = None) -> float:
    """Número de bloqueadores distintos (limite inferior admissível)."""
    return float(_numero_bloqueadores(estado))


def h2(estado: Any, problema: Optional[Any] = None) -> float:
    """Estima o custo mínimo de mover cada contentor bloqueador pelo menos uma vez.

    Cada bloqueador contado por ``h1`` tem de sair da pilha antes que um
    contentor menor abaixo possa ser levantado. Um movimento entre pilhas custa
    pelo menos 1.1; por isso, 1.1 * h1 é um limite inferior admissível. Não se
    somam penalizações por movimentos adicionais sem uma prova independente.
    """
    return 1.1 * _numero_bloqueadores(estado)


def calcular_b_estrela(
    N: int, d: int, tol: float = 1e-7, max_iter: int = 200
) -> float:
    """Calcula o factor de ramificação efectivo para N nós e profundidade d.

    Resolve por bissecção a equação N = b + b² + ... + bᵈ (equivalente a
    N + 1 = 1 + b + b² + ... + bᵈ). Devolve 1.0 quando N ou d são nulos.
    """
    if not isinstance(N, int) or not isinstance(d, int) or N < 0 or d < 0:
        raise ValueError("N e d devem ser inteiros não negativos.")
    if tol <= 0 or max_iter <= 0:
        raise ValueError("tol e max_iter devem ser positivos.")
    if d == 0 or N == 0:
        return 1.0
    if d == 1:
        return float(N)
    if N == d:
        return 1.0

    def soma_potencias(b: float) -> float:
        soma = 0.0
        termo = 1.0
        for _ in range(d):
            termo *= b
            soma += termo
            if soma > N:
                return soma
        return soma

    low, high = 0.0, max(2.0, float(N))
    for _ in range(max_iter):
        mid = (low + high) / 2.0
        soma = soma_potencias(mid)
        if abs(soma - N) <= tol or (high - low) / 2.0 <= tol:
            return round(mid, 4)
        if soma < N:
            low = mid
        else:
            high = mid

    return round((low + high) / 2.0, 4)
