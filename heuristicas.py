"""Heurísticas admissíveis e métrica de ramificação efectiva para o P2.

Inclui as heurísticas h0, h1 e h2, bem como o cálculo do factor de
ramificação efectivo através do método da bissecção.
As pilhas são representadas da base para o topo.
"""

from typing import Any, Optional, Set, Tuple


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
        # Um contentor intermédio k (c_min <= k < c) que não esteja acima de
        # nenhum contentor < c_min obrigará a deslocar c uma segunda vez.
        menor_ate_agora = None
        tem_bloqueio = False
        for k in pilha_dest:
            if menor_ate_agora is not None and menor_ate_agora < c_min:
                break
            if c_min <= k < c:
                tem_bloqueio = True
                break
            if menor_ate_agora is None or k < menor_ate_agora:
                menor_ate_agora = k
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

    A estimativa considera o custo mínimo de deslocação (1.1), a necessidade de
    duplo movimento e as restrições de colocação dos contentores refrigerados.
    """
    pilhas = _pilhas(estado)
    refrigerados: Set[int] = getattr(problema, "refrigerados", frozenset({2, 5}))
    num_pilhas: int = getattr(problema, "S", len(pilhas))
    altura_maxima: int = getattr(problema, "H", 4)

    custo_total: float = 0.0

    for i, pilha in enumerate(pilhas):
        menor_abaixo = None
        for contentor in pilha:
            if menor_abaixo is not None and menor_abaixo < contentor:
                # O custo mínimo de deslocação entre pilhas é 1.1.
                custo_total += 1.1
                c_min = menor_abaixo

                if not _pode_evitar_duplo_movimento(
                    contentor, c_min, i, pilhas, num_pilhas, refrigerados
                ):
                    custo_total += 1.1

                if _desvio_refrigerado_bloqueado(
                    contentor, c_min, i, pilhas, num_pilhas, altura_maxima, refrigerados
                ):
                    custo_total += 1.1

            if menor_abaixo is None or contentor < menor_abaixo:
                menor_abaixo = contentor

    return round(custo_total, 2)


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
