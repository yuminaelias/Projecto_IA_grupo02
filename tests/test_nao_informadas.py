"""Testes para buscas não informadas (pytest)."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from buscas import bfs, dfs, ids, ucs


class Grafo:
    """Problema pequeno para testar algoritmos independentemente do domínio."""
    def __init__(self, arestas, inicio='A', objectivo='G'):
        self.arestas = arestas
        self.inicio = inicio
        self.objectivo = objectivo

    def estado_inicial(self):
        return self.inicio

    def accoes(self, s):
        return list(range(len(self.arestas.get(s, []))))

    def resultado(self, s, a):
        return self.arestas[s][a][0]

    def custo(self, s, a, s2):
        destino, custo = self.arestas[s][a]
        assert destino == s2
        return custo

    def e_objectivo(self, s):
        return s == self.objectivo


def test_bfs_evitar_ciclos_e_testar_objectivo_na_geracao():
    p = Grafo({'A': [('A', 1), ('B', 1)], 'B': [('A', 1), ('G', 1)]})
    r = bfs(p)
    assert r.sucesso
    assert r.caminho()[0] == ['A', 'B', 'G']
    assert r.expandidos == 2  # G é detectado antes de ser expandido


def test_dfs_ciclo_no_caminho():
    p = Grafo({'A': [('B', 1)], 'B': [('A', 1), ('G', 1)]})
    r = dfs(p, limite_profundidade=4)
    assert r.sucesso and r.comprimento == 2


def test_ids_reexpansoes():
    p = Grafo({'A': [('B', 1)], 'B': [('G', 1)]})
    r = ids(p, limite_profundidade=4)
    assert r.sucesso and r.comprimento == 2
    assert r.iteracoes == 3
    assert r.reexpansoes >= 1


def test_ucs_menor_custo_nao_menor_profundidade():
    p = Grafo({'A': [('G', 9), ('B', 1)], 'B': [('G', 1)]})
    assert bfs(p).custo == 9
    r = ucs(p)
    assert r.sucesso and r.custo == 2
    assert r.caminho()[0] == ['A', 'B', 'G']


def test_ucs_entrada_obsoleta():
    p = Grafo({'A': [('B', 10), ('C', 1)], 'C': [('B', 1)], 'B': [('G', 1)]})
    r = ucs(p)
    assert r.sucesso and r.custo == 3
    assert r.caminho()[0] == ['A', 'C', 'B', 'G']


@pytest.mark.parametrize('algoritmo,kwargs', [
    (bfs, {}), (dfs, {'limite_profundidade': 5}),
    (ids, {'limite_profundidade': 5}), (ucs, {})
])
def test_sem_solucao_com_ciclo(algoritmo, kwargs):
    p = Grafo({'A': [('B', 1)], 'B': [('A', 1)]})
    r = algoritmo(p, **kwargs)
    assert r.estado == 'sem_solucao'
    assert r.no is None


def test_limite_dfs_e_ids():
    p = Grafo({'A': [('B', 1)], 'B': [('G', 1)]})
    assert dfs(p, limite_profundidade=1).estado == 'limite'
    assert ids(p, limite_profundidade=1).estado == 'limite'


def test_objectivo_inicial():
    p = Grafo({}, inicio='G')
    for algoritmo in (bfs, dfs, ids, ucs):
        assert algoritmo(p).custo == 0


def test_custo_negativo_rejeitado():
    p = Grafo({'A': [('G', -1)]})
    with pytest.raises(ValueError):
        ucs(p)
