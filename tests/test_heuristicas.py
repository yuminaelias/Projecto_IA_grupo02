"""
Testes Unitários para o Módulo de Heurísticas (heuristicas.py).
Disciplina: Inteligência Artificial I (2026) - UEM / Faculdade de Engenharia
Frente 4: Caravela, Rosário Pompílio

Testes Obrigatórios:
  1. test_h_menor_ou_igual_h_estrela_todos_estados:
     Verificação exaustiva de que 0 <= h1(s) <= h2(s) <= h*(s) em TODOS os estados
     alcançáveis de instâncias pequenas (h* calculado com UCS).
  2. test_heuristicas_instancia_base_e_propriedades:
     Validação de h0, h1 e h2 na Instância Base oficial (S=4, H=4, 10 contentores)
     e propriedades de estados terminais e ordenados.
  3. test_calcular_b_estrela:
     Validação numérica do factor de ramificação efectivo b* com casos analíticos
     e propriedades de monotonia.
"""

from collections import deque
from dataclasses import dataclass
import heapq
import math
from typing import FrozenSet, List, Tuple

from heuristicas import calcular_b_estrela, h0, h1, h2


# Definição do Estado conforme Contrato Técnico de Integração
@dataclass(frozen=True)
class EstadoContentores:
    pilhas: Tuple[Tuple[int, ...], ...]
    proximo: int


class DominioReferencia:
    """
    Implementação de referência estrita das regras do Problema P2
    para cálculo exaustivo de estados alcançáveis e custo óptimo h*(s).
    """

    def __init__(
        self,
        S: int,
        H: int,
        pesados: FrozenSet[int],
        refrigerados: FrozenSet[int],
        max_contentor: int,
    ):
        self.S = S
        self.H = H
        self.pesados = pesados
        self.refrigerados = refrigerados
        self.max_contentor = max_contentor

    def accoes(self, s: EstadoContentores) -> List[Tuple]:
        acts = []
        for i, p in enumerate(s.pilhas):
            if p and p[-1] == s.proximo:
                acts.append(("levantar", i))

        for i, pi in enumerate(s.pilhas):
            if not pi:
                continue
            c = pi[-1]
            for j, pj in enumerate(s.pilhas):
                if i == j or len(pj) >= self.H:
                    continue
                if c in self.refrigerados and j not in (0, 1):
                    continue
                if c in self.pesados and pj and pj[-1] not in self.pesados:
                    continue
                acts.append(("mover", i, j))
        return acts

    def resultado(self, s: EstadoContentores, a: Tuple) -> EstadoContentores:
        pilhas = [list(p) for p in s.pilhas]
        if a[0] == "levantar":
            pilhas[a[1]].pop()
            return EstadoContentores(
                tuple(tuple(p) for p in pilhas),
                s.proximo + 1,
            )
        else:
            c = pilhas[a[1]].pop()
            pilhas[a[2]].append(c)
            return EstadoContentores(
                tuple(tuple(p) for p in pilhas),
                s.proximo,
            )

    def custo(self, s: EstadoContentores, a: Tuple) -> float:
        if a[0] == "levantar":
            return 0.0
        return 1.0 + 0.1 * abs(a[1] - a[2])

    def e_objectivo(self, s: EstadoContentores) -> bool:
        return s.proximo > self.max_contentor and all(len(p) == 0 for p in s.pilhas)

    def _obter_alcancaveis(self, s_inicial: EstadoContentores) -> set:
        alcancaveis = set()
        fila = deque([s_inicial])
        alcancaveis.add(s_inicial)
        while fila:
            curr = fila.popleft()
            if self.e_objectivo(curr):
                continue
            for a in self.accoes(curr):
                prox = self.resultado(curr, a)
                if prox not in alcancaveis:
                    alcancaveis.add(prox)
                    fila.append(prox)
        return alcancaveis

    def _calcular_ucs(self, s_start: EstadoContentores) -> float:
        pq = [(0.0, 0, s_start)]
        best_g = {s_start: 0.0}
        counter = 0
        while pq:
            g, _, s = heapq.heappop(pq)
            if g > best_g.get(s, float("inf")) + 1e-9:
                continue
            if self.e_objectivo(s):
                return g
            for a in self.accoes(s):
                s2 = self.resultado(s, a)
                c = self.custo(s, a)
                g2 = g + c
                if g2 < best_g.get(s2, float("inf")) - 1e-9:
                    best_g[s2] = g2
                    counter += 1
                    heapq.heappush(pq, (g2, counter, s2))
        return float("inf")

    def calcular_h_estrela_todos_estados(self, s_inicial: EstadoContentores):
        alcancaveis = self._obter_alcancaveis(s_inicial)
        h_star = {s: self._calcular_ucs(s) for s in alcancaveis}
        return alcancaveis, h_star


def test_h_menor_ou_igual_h_estrela_todos_estados():
    """
    Teste Obrigatório 1 (Tarefa 4.3):
    Gera todos os estados alcançáveis de instâncias pequenas, calcula h*(s)
    exacto para cada um com UCS e verifica:
        0 <= h1(s) <= h2(s) <= h*(s)
    em 100% dos estados gerados.
    """
    # Instância Pequena 1: S=3, H=3, 4 contentores
    s_pequena1 = EstadoContentores(
        pilhas=((2, 1), (4, 3), ()),
        proximo=1,
    )
    dom1 = DominioReferencia(
        S=3,
        H=3,
        pesados=frozenset({3, 4}),
        refrigerados=frozenset({2}),
        max_contentor=4,
    )
    estados1, h_star1 = dom1.calcular_h_estrela_todos_estados(s_pequena1)
    assert len(estados1) > 50

    for s in estados1:
        hs = h_star1[s]
        val_h0 = h0(s, dom1)
        val_h1 = h1(s, dom1)
        val_h2 = h2(s, dom1)

        assert val_h0 == 0.0
        assert 0.0 <= val_h1
        assert val_h1 <= val_h2 + 1e-6
        assert val_h2 <= hs + 1e-6

    # Instância Pequena 2: S=3, H=3, 5 contentores com inversões
    s_pequena2 = EstadoContentores(
        pilhas=((3, 1), (5, 2), (4,)),
        proximo=1,
    )
    dom2 = DominioReferencia(
        S=3,
        H=3,
        pesados=frozenset({4, 5}),
        refrigerados=frozenset({2, 5}),
        max_contentor=5,
    )
    estados2, h_star2 = dom2.calcular_h_estrela_todos_estados(s_pequena2)
    assert len(estados2) > 80

    for s in estados2:
        hs = h_star2[s]
        val_h1 = h1(s, dom2)
        val_h2 = h2(s, dom2)
        assert 0.0 <= val_h1 <= val_h2 + 1e-6 <= hs + 1e-6


def test_heuristicas_instancia_base_e_propriedades():
    """
    Teste Obrigatório 2:
    Valida o comportamento de h0, h1 e h2 na Instância Base oficial (S=4, H=4, 10 contentores)
    e testa propriedades essenciais de consistência em estados ordenados e terminais.
    """
    s_base = EstadoContentores(
        pilhas=((8, 2, 10), (5, 1, 6), (9, 4), (7, 3)),
        proximo=1,
    )
    dom_base = DominioReferencia(
        S=4,
        H=4,
        pesados=frozenset({5, 7, 8, 9}),
        refrigerados=frozenset({2, 5}),
        max_contentor=10,
    )

    val_h0 = h0(s_base, dom_base)
    val_h1 = h1(s_base, dom_base)
    val_h2 = h2(s_base, dom_base)

    assert val_h0 == 0.0
    assert val_h1 == 2.0
    assert val_h2 == 4.4
    assert 0.0 <= val_h1 <= val_h2 <= 4.8

    # Estado Objectivo deve ter heurística zero
    s_obj = EstadoContentores(pilhas=((), (), (), ()), proximo=11)
    assert h0(s_obj, dom_base) == 0.0
    assert h1(s_obj, dom_base) == 0.0
    assert h2(s_obj, dom_base) == 0.0

    # Pilhas ordenadas devem ter h=0
    s_ordenado = EstadoContentores(
        pilhas=((3, 2, 1), (6, 5, 4), (8, 7)),
        proximo=1,
    )
    assert h1(s_ordenado, dom_base) == 0.0
    assert h2(s_ordenado, dom_base) == 0.0


def test_calcular_b_estrela():
    """
    Teste Obrigatório 3 (Tarefa 4.3):
    Valida a implementação da função calcular_b_estrela(N, d) que resolve
        N + 1 = 1 + b* + (b*)^2 + ... + (b*)^d.
    """
    assert calcular_b_estrela(N=5, d=1) == 5.0
    assert calcular_b_estrela(N=12, d=1) == 12.0
    assert calcular_b_estrela(N=10, d=10) == 1.0
    assert calcular_b_estrela(N=4, d=4) == 1.0

    b_calc = calcular_b_estrela(N=10, d=2)
    b_teorico = (math.sqrt(41.0) - 1.0) / 2.0
    assert abs(b_calc - b_teorico) < 1e-3

    b_h0 = calcular_b_estrela(1535, 14)
    assert 1.55 <= b_h0 <= 1.60

    b_h1 = calcular_b_estrela(124, 14)
    assert 1.25 <= b_h1 <= 1.30

    b_h2 = calcular_b_estrela(28, 14)
    assert 1.05 <= b_h2 <= 1.15

    assert b_h2 < b_h1 < b_h0
    assert calcular_b_estrela(0, 5) == 1.0
    assert calcular_b_estrela(10, 0) == 1.0
