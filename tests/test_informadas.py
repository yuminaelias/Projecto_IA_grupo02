"""Testes Unitários Obrigatórios da Frente 3 — KIMEMIA JÚNIOR, Peter Njau.

Universidade Eduardo Mondlane — Inteligência Artificial I (2026)
Grupo 02 (Laboral) — P2: Reordenação de Contentores no Porto de Maputo

Compatível com:
- `problema.py` e `dominio.py` (`origin/branch_paulo` — Paulo Matola)
- `heuristicas.py` (`origin/feat/heuristicas` — Rosário Caravela)
- `buscas.py` (Frente 2 e Frente 3)
"""

from __future__ import annotations
from dataclasses import dataclass
import math
import os
import sys

_RAIZ_PROJECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ_PROJECTO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJECTO)

import buscas
from buscas import a_estrela, gulosa, ida_estrela, ucs

try:
    from dominio import ProblemaContentores
except ImportError:
    @dataclass(frozen=True)
    class _EstadoFallback:
        pilhas: tuple[tuple[int, ...], ...]
        proximo: int

    class ProblemaContentores(buscas.Problema):
        def __init__(self, S, H, pilhas, pesados=(), refrigerados=()):
            self.S, self.H = S, H
            self.pesados = frozenset(pesados)
            self.refrigerados = frozenset(refrigerados)
            pilhas_t = tuple(tuple(p) for p in pilhas)
            self.total_contentores = sum(len(p) for p in pilhas_t)
            self._inicial = _EstadoFallback(pilhas_t, 1)

        def estado_inicial(self):
            return self._inicial

        def accoes(self, s):
            res = []
            for i, orig in enumerate(s.pilhas):
                if not orig:
                    continue
                topo = orig[-1]
                if topo == s.proximo:
                    res.append(("levantar", i))
                for j, dest in enumerate(s.pilhas):
                    if i == j or len(dest) >= self.H:
                        continue
                    if topo in self.refrigerados and j not in (0, 1):
                        continue
                    if topo in self.pesados and dest and dest[-1] not in self.pesados:
                        continue
                    res.append(("mover", i, j))
            return res

        def resultado(self, s, a):
            pilhas = list(s.pilhas)
            i = a[1]
            topo = pilhas[i][-1]
            pilhas[i] = pilhas[i][:-1]
            prox = s.proximo + 1 if a[0] == "levantar" else s.proximo
            if a[0] != "levantar":
                pilhas[a[2]] = pilhas[a[2]] + (topo,)
            return _EstadoFallback(tuple(pilhas), prox)

        def custo(self, s, a, s2):
            return 0.0 if a[0] == "levantar" else 1.0 + 0.1 * abs(a[1] - a[2])

        def e_objectivo(self, s):
            return s.proximo == self.total_contentores + 1 and all(not p for p in s.pilhas)

        def heuristica(self, s, nome):
            if nome == "h0":
                return 0.0
            total_b = 0
            custo_h2 = 0.0
            for i, pilha in enumerate(s.pilhas):
                menor = None
                for c in pilha:
                    if menor is not None and menor < c:
                        total_b += 1
                        custo_h2 += 1.1
                        c_min = menor
                        evita = False
                        for j in range(self.S):
                            if j == i or (c in self.refrigerados and j not in (0, 1)):
                                continue
                            if not s.pilhas[j] or not any(c_min <= k < c for k in s.pilhas[j]):
                                evita = True
                                break
                        if not evita:
                            custo_h2 += 1.1
                        if c in self.refrigerados and self.S >= 2 and i in (0, 1):
                            outra = 1 - i
                            if len(s.pilhas[outra]) >= self.H and all(k > c_min for k in s.pilhas[outra]):
                                custo_h2 += 1.1
                    if menor is None or c < menor:
                        menor = c
            if nome == "h1":
                return float(total_b)
            if nome == "h2":
                return round(custo_h2, 2)
            raise ValueError(nome)


def _criar_instancia_base() -> ProblemaContentores:
    """Constrói a instância base oficial do Grupo 02 usando a assinatura de `dominio.py`."""
    return ProblemaContentores(
        S=4,
        H=4,
        pilhas=((8, 2, 10), (5, 1, 6), (9, 4), (7, 3)),
        pesados=(5, 7, 8, 9),
        refrigerados=(2, 5),
    )


def test_optimalidade_a_estrela_vs_ucs_instancia_base() -> None:
    """Teste 1 (Tarefa 3.4):
    Comprova que UCS e A* (com h0=0, h1 e h2) devolvem exatamente o mesmo custo
    ótimo (4.8) na instância base, e que a dominância h2 >= h1 >= h0 reduz o
    número de nós expandidos (27 < 123 < 1534).
    """
    problema = _criar_instancia_base()

    res_ucs = ucs(problema)
    res_a0 = a_estrela(problema, "h0")
    res_a1 = a_estrela(problema, "h1")
    res_a2 = a_estrela(problema, "h2")

    assert res_ucs.resolvido is True and res_ucs.status == "ok"
    assert res_a0.resolvido is True and res_a0.status == "ok"
    assert res_a1.resolvido is True and res_a1.status == "ok"
    assert res_a2.resolvido is True and res_a2.status == "ok"

    custo_esperado = 4.8
    assert math.isclose(res_ucs.custo, custo_esperado, abs_tol=1e-6)
    assert math.isclose(res_a0.custo, res_ucs.custo, abs_tol=1e-6)
    assert math.isclose(res_a1.custo, res_ucs.custo, abs_tol=1e-6)
    assert math.isclose(res_a2.custo, res_ucs.custo, abs_tol=1e-6)

    assert res_a2.nos_expandidos < res_a1.nos_expandidos < res_a0.nos_expandidos


def test_optimalidade_ida_estrela_vs_a_estrela_instancia_base() -> None:
    """Teste 2 (Tarefa 3.4):
    Comprova que o algoritmo avançado IDA* (com h1 e h2) devolve exatamente o
    mesmo custo ótimo (4.8) e comprimento (14 ações) que o A* e o UCS na
    instância base, mantendo uma fronteira máxima estritamente menor que o A*.
    """
    problema = _criar_instancia_base()

    res_a2 = a_estrela(problema, "h2")
    res_ida1 = ida_estrela(problema, "h1")
    res_ida2 = ida_estrela(problema, "h2")

    assert res_ida1.resolvido is True and res_ida1.status == "ok"
    assert res_ida2.resolvido is True and res_ida2.status == "ok"

    assert math.isclose(res_ida1.custo, res_a2.custo, abs_tol=1e-6)
    assert math.isclose(res_ida2.custo, res_a2.custo, abs_tol=1e-6)
    assert res_ida2.comprimento == res_a2.comprimento == 14

    assert res_ida2.nos_expandidos < res_ida1.nos_expandidos
    assert res_ida2.max_fronteira < res_a2.max_fronteira


def test_busca_gulosa_e_instancia_sem_solucao() -> None:
    """Teste 3 (Tarefa 3.4):
    Valida a Busca Gulosa (com h1 e h2) na instância base e comprova que A*,
    IDA* e Gulosa terminam e reportam `resolvido=False` e `status='sem_solucao'`
    numa instância bloqueada sem solução.
    """
    problema_base = _criar_instancia_base()
    res_g1 = gulosa(problema_base, "h1")
    res_g2 = gulosa(problema_base, "h2")

    assert res_g1.resolvido is True and res_g1.status == "ok"
    assert res_g2.resolvido is True and res_g2.status == "ok"
    assert res_g2.custo >= 4.8 - 1e-6
    assert len(res_g2.acoes) == res_g2.comprimento

    # Instância sem solução: S=2 pilhas de altura máxima H=2, ambas cheias ((1, 2), (3, 4)).
    # O contentor 1 está soterrado pelo 2 e nenhuma pilha tem espaço livre -> 0 ações possíveis.
    problema_impossivel = ProblemaContentores(
        S=2,
        H=2,
        pilhas=((1, 2), (3, 4)),
        pesados=(),
        refrigerados=(),
    )

    res_a_imp = a_estrela(problema_impossivel, "h2")
    res_ida_imp = ida_estrela(problema_impossivel, "h2")
    res_gul_imp = gulosa(problema_impossivel, "h2")

    assert res_a_imp.resolvido is False and res_a_imp.status == "sem_solucao"
    assert res_ida_imp.resolvido is False and res_ida_imp.status == "sem_solucao"
    assert res_gul_imp.resolvido is False and res_gul_imp.status == "sem_solucao"
