"""Buscas não informadas genéricas: BFS, DFS, IDS e UCS.

Contrato do domínio: estado_inicial(), accoes(s), resultado(s,a),
custo(s,a,s2), e_objectivo(s). Estados devem ser imutáveis e hashable.
BFS testa objectivo na geração; DFS evita ciclos no caminho; IDS repete
DFS limitada; UCS usa heapq e ignora entradas obsoletas.
"""
from collections import deque
from dataclasses import dataclass, field
import heapq
import itertools
import math
import time
import tracemalloc
from typing import Any, Optional


@dataclass
class NoBusca:
    """Nó compatível com caminho(no) de problema.py."""
    estado: Any
    pai: Optional['NoBusca'] = None
    accao: Any = None
    g: float = 0.0
    profundidade: int = 0


@dataclass
class ResultadoBusca:
    algoritmo: str
    no: Optional[NoBusca] = None
    estado: str = 'sem_solucao'  # sucesso, sem_solucao, limite, timeout
    gerados: int = 0  # inclui raiz e nós gerados, mesmo que repetidos
    expandidos: int = 0
    fronteira_maxima: int = 0
    reexpansoes: int = 0
    tempo: float = 0.0
    memoria_pico: int = 0  # bytes; pico incremental da medição
    iteracoes: int = 1

    @property
    def sucesso(self):
        return self.estado == 'sucesso'

    @property
    def custo(self):
        return self.no.g if self.no is not None else None

    @property
    def comprimento(self):
        return self.no.profundidade if self.no is not None else None

    def caminho(self):
        """Devolve (estados, accoes) sem depender de implementações externas."""
        estados, accoes = [], []
        no = self.no
        while no is not None:
            estados.append(no.estado)
            if no.pai is not None:
                accoes.append(no.accao)
            no = no.pai
        return list(reversed(estados)), list(reversed(accoes))


def _iniciar(nome):
    iniciou_tracing = not tracemalloc.is_tracing()
    if iniciou_tracing:
        tracemalloc.start()
    inicio_memoria, _ = tracemalloc.get_traced_memory()
    return ResultadoBusca(nome), time.perf_counter(), iniciou_tracing, inicio_memoria


def _terminar(r, inicio, iniciou_tracing, inicio_memoria):
    r.tempo = time.perf_counter() - inicio
    _, pico = tracemalloc.get_traced_memory()
    r.memoria_pico = max(0, pico - inicio_memoria)
    if iniciou_tracing:
        tracemalloc.stop()
    return r


def _prazo(inicio, limite_tempo):
    return limite_tempo is not None and time.perf_counter() - inicio >= limite_tempo


def _validar(limite_tempo, limite_profundidade=None):
    if limite_tempo is not None and (not math.isfinite(limite_tempo) or limite_tempo <= 0):
        raise ValueError('limite_tempo deve ser positivo e finito.')
    if limite_profundidade is not None and (type(limite_profundidade) is not int or limite_profundidade < 0):
        raise ValueError('limite_profundidade deve ser inteiro não negativo.')


def _filho(problema, no, accao):
    s2 = problema.resultado(no.estado, accao)
    custo = problema.custo(no.estado, accao, s2)
    if not isinstance(custo, (int, float)) or not math.isfinite(custo) or custo < 0:
        raise ValueError('As buscas exigem custos finitos e não negativos.')
    return NoBusca(s2, no, accao, no.g + custo, no.profundidade + 1)


def bfs(problema, limite_tempo=60.0):
    """Busca em largura, com teste de objectivo na GERAÇÃO.

    Minimiza número de acções, não necessariamente o custo do P2.
    """
    _validar(limite_tempo)
    r, inicio, tr, mem = _iniciar('BFS')
    try:
        raiz = NoBusca(problema.estado_inicial())
        r.gerados, r.fronteira_maxima = 1, 1
        if problema.e_objectivo(raiz.estado):
            r.no, r.estado = raiz, 'sucesso'
            return r
        fila = deque([raiz])
        visitados = {raiz.estado}
        while fila:
            if _prazo(inicio, limite_tempo):
                r.estado = 'timeout'
                return r
            no = fila.popleft()
            r.expandidos += 1
            for a in problema.accoes(no.estado):
                filho = _filho(problema, no, a)
                r.gerados += 1
                if filho.estado in visitados:
                    continue
                visitados.add(filho.estado)
                if problema.e_objectivo(filho.estado):
                    r.no, r.estado = filho, 'sucesso'
                    return r
                fila.append(filho)
            r.fronteira_maxima = max(r.fronteira_maxima, len(fila))
        return r
    finally:
        _terminar(r, inicio, tr, mem)


def _dfs_limitada(problema, limite, r, inicio, limite_tempo, expandidos_anteriores=None):
    """Iteração DFS com detecção de ciclos no caminho; devolve (nó, corte)."""
    raiz = NoBusca(problema.estado_inicial())
    r.gerados += 1
    pilha = [(raiz, frozenset((raiz.estado,)))]
    r.fronteira_maxima = max(r.fronteira_maxima, len(pilha))
    houve_corte = False
    while pilha:
        if _prazo(inicio, limite_tempo):
            r.estado = 'timeout'
            return None, False
        no, ancestrais = pilha.pop()
        if problema.e_objectivo(no.estado):
            return no, False
        accoes = problema.accoes(no.estado)
        if no.profundidade >= limite:
            # Há corte somente se existe sucessor que não cria ciclo no caminho.
            for a in accoes:
                filho = _filho(problema, no, a)
                r.gerados += 1
                if filho.estado not in ancestrais:
                    houve_corte = True
            continue
        r.expandidos += 1
        if expandidos_anteriores is not None:
            if no.estado in expandidos_anteriores:
                r.reexpansoes += 1
            expandidos_anteriores.add(no.estado)
        filhos = []
        for a in accoes:
            filho = _filho(problema, no, a)
            r.gerados += 1
            if filho.estado not in ancestrais:
                filhos.append((filho, ancestrais | {filho.estado}))
        # Reverter para explorar primeiro a primeira acção gerada.
        pilha.extend(reversed(filhos))
        r.fronteira_maxima = max(r.fronteira_maxima, len(pilha))
    return None, houve_corte


def dfs(problema, limite_profundidade=50, limite_tempo=60.0):
    """DFS limitada, evitando ciclos apenas ao longo do caminho actual."""
    _validar(limite_tempo, limite_profundidade)
    r, inicio, tr, mem = _iniciar('DFS')
    try:
        no, corte = _dfs_limitada(problema, limite_profundidade, r, inicio, limite_tempo)
        if no is not None:
            r.no, r.estado = no, 'sucesso'
        elif r.estado != 'timeout' and corte:
            r.estado = 'limite'
        return r
    finally:
        _terminar(r, inicio, tr, mem)


def ids(problema, limite_profundidade=50, limite_tempo=60.0):
    """Aprofundamento iterativo; contabiliza expansões repetidas entre iterações."""
    _validar(limite_tempo, limite_profundidade)
    r, inicio, tr, mem = _iniciar('IDS')
    try:
        anteriores = set()
        for limite in range(limite_profundidade + 1):
            r.iteracoes = limite + 1
            no, corte = _dfs_limitada(problema, limite, r, inicio, limite_tempo, anteriores)
            if no is not None:
                r.no, r.estado = no, 'sucesso'
                return r
            if r.estado == 'timeout':
                return r
            if not corte:
                return r
        r.estado = 'limite'
        return r
    finally:
        _terminar(r, inicio, tr, mem)


def ucs(problema, limite_tempo=60.0):
    """Custo uniforme: fila de prioridade por g, com descarte de entradas obsoletas."""
    _validar(limite_tempo)
    r, inicio, tr, mem = _iniciar('UCS')
    try:
        raiz = NoBusca(problema.estado_inicial())
        contador = itertools.count()
        fronteira = [(0.0, next(contador), raiz)]
        melhor_g = {raiz.estado: 0.0}
        r.gerados, r.fronteira_maxima = 1, 1
        while fronteira:
            if _prazo(inicio, limite_tempo):
                r.estado = 'timeout'
                return r
            _, _, no = heapq.heappop(fronteira)
            if no.g > melhor_g.get(no.estado, math.inf):
                continue  # entrada obsoleta
            if problema.e_objectivo(no.estado):
                r.no, r.estado = no, 'sucesso'
                return r  # em UCS o teste é na REMOÇÃO da fronteira
            r.expandidos += 1
            for a in problema.accoes(no.estado):
                filho = _filho(problema, no, a)
                r.gerados += 1
                if filho.g < melhor_g.get(filho.estado, math.inf):
                    melhor_g[filho.estado] = filho.g
                    heapq.heappush(fronteira, (filho.g, next(contador), filho))
            r.fronteira_maxima = max(r.fronteira_maxima, len(fronteira))
        return r
    finally:
        _terminar(r, inicio, tr, mem)


# Aliases opcionais para menus e testes.
busca_largura = bfs
busca_profundidade = dfs
aprofundamento_iterativo = ids
custo_uniforme = ucs

