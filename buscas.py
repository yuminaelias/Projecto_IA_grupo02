"""Implementação dos algoritmos de busca sobre a interface genérica `Problema`.

Universidade Eduardo Mondlane — Inteligência Artificial I (2026)
Grupo 02 (Laboral) — P2: Reordenação de Contentores no Porto de Maputo

Compatível a 100% com:
- `problema.py` e `dominio.py` (Frente 1 — Paulo Matola, `origin/branch_paulo`)
- `tests/test_nao_informadas.py` (Frente 2 — Yúmina Cossa)
- `tests/test_informadas.py` (Frente 3 — Peter Kimemia)
- `heuristicas.py` (Frente 4 — Rosário Caravela, `origin/feat/heuristicas`)
- Contrato Técnico de Integração (Secção 2 do Guião do Grupo 02)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from itertools import count
import heapq
import math
import sys
import time
import tracemalloc
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from problema import No, Problema, caminho
except ImportError:
    class Problema(ABC):
        @abstractmethod
        def estado_inicial(self): ...
        @abstractmethod
        def accoes(self, s): ...
        @abstractmethod
        def resultado(self, s, a): ...
        @abstractmethod
        def custo(self, s, a, s2): ...
        @abstractmethod
        def e_objectivo(self, s): ...
        @abstractmethod
        def heuristica(self, s, nome): ...

    @dataclass
    class No:
        estado: Any
        pai: "No | None" = None
        accao: Any = None
        g: float = 0.0
        profundidade: int = 0

        def __lt__(self, outro):
            if not isinstance(outro, No):
                return NotImplemented
            return (self.g, self.profundidade) < (outro.g, outro.profundidade)

    def caminho(no: No) -> tuple[list, list]:
        estados, accoes = [], []
        actual = no
        while actual is not None:
            estados.append(actual.estado)
            if actual.pai is not None:
                accoes.append(actual.accao)
            actual = actual.pai
        return estados[::-1], accoes[::-1]

# Alias de compatibilidade com a Frente 2
NoBusca = No

try:
    from heuristicas import h0 as _h0_fn, h1 as _h1_fn, h2 as _h2_fn
    _MAPA_HEURISTICAS = {"h0": _h0_fn, "h1": _h1_fn, "h2": _h2_fn}
except ImportError:
    _MAPA_HEURISTICAS = {}

if sys.getrecursionlimit() < 5000:
    sys.setrecursionlimit(5000)


@dataclass
class ResultadoBusca:
    """Estrutura unificada de retorno dos 7 algoritmos de busca em `buscas.py`.

    Contém exatamente os 13 campos exigidos pelo Contrato Técnico de Integração
    (Secção 2 do Guião e `GUIA_INTEGRACAO_GRUPO02.md` da Frente 1), bem como as
    propriedades e métodos de compatibilidade com os testes da Frente 2.
    """

    algoritmo: str
    heuristica: str = "—"
    resolvido: bool = False
    custo: float = math.inf
    comprimento: int = 0
    acoes: list = field(default_factory=list)
    nos_expandidos: int = 0
    nos_gerados: int = 0
    nos_reexpandidos: int = 0
    max_fronteira: int = 0
    tempo_s: float = 0.0
    memoria_mb: float = 0.0
    status: str = "sem_solucao"
    # Atributos auxiliares compatíveis com os testes da Frente 2 (Yúmina):
    no: Optional[No] = field(default=None, repr=False)
    estado: str = field(default="sem_solucao", repr=False)
    memoria_pico: int = field(default=0, repr=False)
    iteracoes: int = field(default=1, repr=False)

    @property
    def sucesso(self) -> bool:
        return self.resolvido

    @property
    def expandidos(self) -> int:
        return self.nos_expandidos

    @property
    def gerados(self) -> int:
        return self.nos_gerados

    @property
    def reexpansoes(self) -> int:
        return self.nos_reexpandidos

    @property
    def fronteira_maxima(self) -> int:
        return self.max_fronteira

    @property
    def tempo(self) -> float:
        return self.tempo_s

    def caminho(self) -> Tuple[list, list]:
        """Devolve `(estados, accoes)` a partir do nó solução."""
        if self.no is None:
            return [], []
        return caminho(self.no)


def _avaliar_heuristica(problema: Any, estado: Any, nome_h: str) -> float:
    """Avalia a heurística `nome_h` no `estado` dado `problema`.

    1. Tenta primeiro `problema.heuristica(estado, nome_h)` (respeitando subclasses
       ou problemas genéricos de teste).
    2. Caso `ProblemaContentores.heuristica` lance `NotImplementedError` (como
       definido na Frente 1 para manter isolado o teste unitário de `dominio.py`),
       delega diretamente para `h0`, `h1` ou `h2` do módulo `heuristicas.py` da
       Frente 4.
    """
    if hasattr(problema, "heuristica"):
        try:
            val = problema.heuristica(estado, nome_h)
            if val is not None:
                return float(val)
        except NotImplementedError:
            pass

    if nome_h in _MAPA_HEURISTICAS:
        return float(_MAPA_HEURISTICAS[nome_h](estado, problema))
    if nome_h == "h0":
        return 0.0
    raise ValueError(f"Heurística desconhecida ou não disponível: {nome_h!r}")


def _extrair_accoes(no_solucao: No) -> list:
    """Extrai a lista de ações a partir de `caminho(no_solucao)`.

    Suporta a convenção de `problema.py` da Frente 1, onde `caminho(no)` devolve
    o tuplo `(estados, accoes)`.
    """
    res = caminho(no_solucao)
    if (
        isinstance(res, tuple)
        and len(res) == 2
        and isinstance(res[0], list)
        and isinstance(res[1], list)
    ):
        if len(res[0]) == len(res[1]) + 1:
            return res[1]
        return res[0]
    return list(res)


def _validar_custo_transicao(problema: Any, s: Any, a: Any, s2: Any) -> float:
    """Obtém e valida que o custo da transição é finito e não negativo."""
    custo = problema.custo(s, a, s2)
    if not isinstance(custo, (int, float)) or not math.isfinite(custo) or custo < 0:
        raise ValueError("As buscas exigem custos finitos e não negativos.")
    return float(custo)


def _validar_limites(
    limite_tempo: Optional[float], limite_profundidade: Optional[int] = None
) -> None:
    if limite_tempo is not None and (
        not math.isfinite(limite_tempo) or limite_tempo <= 0
    ):
        raise ValueError("limite_tempo deve ser positivo e finito.")
    if limite_profundidade is not None and (
        type(limite_profundidade) is not int or limite_profundidade < 0
    ):
        raise ValueError("limite_profundidade deve ser inteiro não negativo.")


class LimiteExcedidoError(Exception):
    """Exceção interna para sinalizar excesso de tempo (60 s) ou memória (2 GB)."""

    def __init__(self, status: str):
        super().__init__(status)
        self.status = status


class _MonitorExecucao:
    """Monitoriza `time.perf_counter()` e `tracemalloc` durante a busca."""

    def __init__(
        self,
        limite_tempo_s: float = 60.0,
        limite_memoria_mb: float = 2048.0,
        intervalo_verificacao: int = 64,
    ):
        self.limite_tempo_s = limite_tempo_s
        self.limite_memoria_bytes = limite_memoria_mb * 1024 * 1024
        self.intervalo_verificacao = intervalo_verificacao
        self.passos = 0
        self.inicio = 0.0
        self.inicio_memoria = 0
        self._iniciou_tracemalloc = False

    def iniciar(self) -> None:
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self._iniciou_tracemalloc = True
        else:
            tracemalloc.reset_peak()
        self.inicio_memoria, _ = tracemalloc.get_traced_memory()
        self.inicio = time.perf_counter()

    def verificar(self) -> None:
        self.passos += 1
        if self.passos % self.intervalo_verificacao != 0:
            return
        if (
            self.limite_tempo_s is not None
            and (time.perf_counter() - self.inicio) >= self.limite_tempo_s
        ):
            raise LimiteExcedidoError("falhou (tempo)")
        _, pico = tracemalloc.get_traced_memory()
        if pico > self.limite_memoria_bytes:
            raise LimiteExcedidoError("falhou (memoria)")

    def finalizar(self) -> Tuple[float, float, int]:
        tempo_s = time.perf_counter() - self.inicio
        _, pico = tracemalloc.get_traced_memory()
        memoria_pico = max(0, pico - self.inicio_memoria)
        if self._iniciou_tracemalloc:
            tracemalloc.stop()
        return round(tempo_s, 6), round(pico / (1024 * 1024), 6), memoria_pico


def _formatar_resultado(
    algoritmo: str,
    heuristica: str,
    status: str,
    no_solucao: Optional[No],
    nos_expandidos: int,
    nos_gerados: int,
    nos_reexpandidos: int,
    max_fronteira: int,
    tempo_s: float,
    memoria_mb: float,
    memoria_pico: int = 0,
    iteracoes: int = 1,
    estado_f2: Optional[str] = None,
) -> ResultadoBusca:
    """Empacota as métricas e a solução no objeto `ResultadoBusca`."""
    if status == "ok" and no_solucao is not None:
        acoes_sol = _extrair_accoes(no_solucao)
        return ResultadoBusca(
            algoritmo=algoritmo,
            heuristica=heuristica,
            resolvido=True,
            custo=round(no_solucao.g, 6),
            comprimento=len(acoes_sol),
            acoes=acoes_sol,
            nos_expandidos=nos_expandidos,
            nos_gerados=nos_gerados,
            nos_reexpandidos=nos_reexpandidos,
            max_fronteira=max_fronteira,
            tempo_s=tempo_s,
            memoria_mb=memoria_mb,
            status="ok",
            no=no_solucao,
            estado=estado_f2 or "sucesso",
            memoria_pico=memoria_pico,
            iteracoes=iteracoes,
        )
    if estado_f2 is None:
        if status == "falhou (tempo)":
            estado_f2 = "timeout"
        else:
            estado_f2 = status
    return ResultadoBusca(
        algoritmo=algoritmo,
        heuristica=heuristica,
        resolvido=False,
        custo=math.inf,
        comprimento=0,
        acoes=[],
        nos_expandidos=nos_expandidos,
        nos_gerados=nos_gerados,
        nos_reexpandidos=nos_reexpandidos,
        max_fronteira=max_fronteira,
        tempo_s=tempo_s,
        memoria_mb=memoria_mb,
        status=status,
        no=None,
        estado=estado_f2,
        memoria_pico=memoria_pico,
        iteracoes=iteracoes,
    )


# =============================================================================
# FRENTE 2 — COSSA, Yúmina Elias (Buscas Não Informadas: BFS, DFS, IDS e UCS)
# =============================================================================

def bfs(
    problema: Problema,
    limite_tempo: Optional[float] = None,
    limite_tempo_s: float = 60.0,
    limite_memoria_mb: float = 2048.0,
) -> ResultadoBusca:
    """1. Busca em Largura (BFS) com teste de objetivo na geração e `deque`."""
    prazo = limite_tempo if limite_tempo is not None else limite_tempo_s
    _validar_limites(prazo)
    monitor = _MonitorExecucao(prazo, limite_memoria_mb)
    monitor.iniciar()

    nos_expandidos = 0
    nos_gerados = 1
    max_fronteira = 1

    try:
        s0 = problema.estado_inicial()
        raiz = No(estado=s0, pai=None, accao=None, g=0.0, profundidade=0)

        if problema.e_objectivo(s0):
            tempo_s, mem_mb, mem_pico = monitor.finalizar()
            return _formatar_resultado(
                "BFS", "—", "ok", raiz, 0, 1, 0, 1, tempo_s, mem_mb, mem_pico
            )

        fronteira: deque[No] = deque([raiz])
        visitados: Set[Any] = {s0}

        while fronteira:
            monitor.verificar()
            no = fronteira.popleft()
            nos_expandidos += 1

            for accao in problema.accoes(no.estado):
                s_filho = problema.resultado(no.estado, accao)
                custo_passo = _validar_custo_transicao(problema, no.estado, accao, s_filho)
                filho = No(
                    estado=s_filho,
                    pai=no,
                    accao=accao,
                    g=no.g + custo_passo,
                    profundidade=no.profundidade + 1,
                )
                nos_gerados += 1

                if s_filho in visitados:
                    continue
                visitados.add(s_filho)

                if problema.e_objectivo(s_filho):
                    tempo_s, mem_mb, mem_pico = monitor.finalizar()
                    return _formatar_resultado(
                        "BFS", "—", "ok", filho,
                        nos_expandidos, nos_gerados, 0, max_fronteira,
                        tempo_s, mem_mb, mem_pico
                    )

                fronteira.append(filho)

            if len(fronteira) > max_fronteira:
                max_fronteira = len(fronteira)

        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "BFS", "—", "sem_solucao", None,
            nos_expandidos, nos_gerados, 0, max_fronteira,
            tempo_s, mem_mb, mem_pico
        )

    except LimiteExcedidoError as exc:
        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "BFS", "—", exc.status, None,
            nos_expandidos, nos_gerados, 0, max_fronteira,
            tempo_s, mem_mb, mem_pico
        )


def dfs(
    problema: Problema,
    limite_profundidade: int = 50,
    limite_tempo: Optional[float] = None,
    limite_tempo_s: float = 60.0,
    limite_memoria_mb: float = 2048.0,
) -> ResultadoBusca:
    """2. Busca em Profundidade (DFS) com controlo de ciclos no caminho atual."""
    prazo = limite_tempo if limite_tempo is not None else limite_tempo_s
    _validar_limites(prazo, limite_profundidade)
    monitor = _MonitorExecucao(prazo, limite_memoria_mb)
    monitor.iniciar()

    nos_expandidos = 0
    nos_gerados = 1
    max_fronteira = 1
    houve_corte = False

    try:
        s0 = problema.estado_inicial()
        raiz = No(estado=s0, pai=None, accao=None, g=0.0, profundidade=0)
        pilha: List[Tuple[No, Optional[List[No]]]] = [(raiz, None)]
        caminho_actual: Set[Any] = {s0}

        while pilha:
            monitor.verificar()
            no, filhos_pendentes = pilha[-1]

            if filhos_pendentes is None:
                if problema.e_objectivo(no.estado):
                    tempo_s, mem_mb, mem_pico = monitor.finalizar()
                    return _formatar_resultado(
                        "DFS", "—", "ok", no,
                        nos_expandidos, nos_gerados, 0, max_fronteira,
                        tempo_s, mem_mb, mem_pico
                    )

                accoes = problema.accoes(no.estado)
                if limite_profundidade is not None and no.profundidade >= limite_profundidade:
                    for accao in accoes:
                        s_filho = problema.resultado(no.estado, accao)
                        _validar_custo_transicao(problema, no.estado, accao, s_filho)
                        nos_gerados += 1
                        if s_filho not in caminho_actual:
                            houve_corte = True
                    pilha.pop()
                    caminho_actual.remove(no.estado)
                    continue

                nos_expandidos += 1
                sucessores: List[No] = []
                for accao in accoes:
                    s_filho = problema.resultado(no.estado, accao)
                    custo_passo = _validar_custo_transicao(problema, no.estado, accao, s_filho)
                    nos_gerados += 1
                    if s_filho not in caminho_actual:
                        filho = No(
                            estado=s_filho,
                            pai=no,
                            accao=accao,
                            g=no.g + custo_passo,
                            profundidade=no.profundidade + 1,
                        )
                        sucessores.append(filho)

                sucessores.reverse()
                pilha[-1] = (no, sucessores)
                tam = len(pilha) + sum(len(p) for _, p in pilha if p is not None)
                if tam > max_fronteira:
                    max_fronteira = tam
            else:
                if filhos_pendentes:
                    prox = filhos_pendentes.pop()
                    caminho_actual.add(prox.estado)
                    pilha.append((prox, None))
                else:
                    pilha.pop()
                    caminho_actual.remove(no.estado)

        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        estado_f2 = "limite" if houve_corte else "sem_solucao"
        return _formatar_resultado(
            "DFS", "—", "sem_solucao", None,
            nos_expandidos, nos_gerados, 0, max_fronteira,
            tempo_s, mem_mb, mem_pico, estado_f2=estado_f2
        )

    except LimiteExcedidoError as exc:
        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "DFS", "—", exc.status, None,
            nos_expandidos, nos_gerados, 0, max_fronteira,
            tempo_s, mem_mb, mem_pico
        )


def ids(
    problema: Problema,
    limite_profundidade: int = 50,
    limite_max_profundidade: Optional[int] = None,
    limite_tempo: Optional[float] = None,
    limite_tempo_s: float = 60.0,
    limite_memoria_mb: float = 2048.0,
) -> ResultadoBusca:
    """3. Aprofundamento Iterativo (IDS) contabilizando `nos_reexpandidos`."""
    limite_max = (
        limite_max_profundidade
        if limite_max_profundidade is not None
        else limite_profundidade
    )
    prazo = limite_tempo if limite_tempo is not None else limite_tempo_s
    _validar_limites(prazo, limite_max)
    monitor = _MonitorExecucao(prazo, limite_memoria_mb)
    monitor.iniciar()

    nos_expandidos = 0
    nos_gerados = 0
    nos_reexpandidos = 0
    max_fronteira = 1
    iteracoes = 0
    expandidos_global: Set[Any] = set()

    try:
        s0 = problema.estado_inicial()

        for limite in range(limite_max + 1):
            iteracoes = limite + 1
            raiz = No(estado=s0, pai=None, accao=None, g=0.0, profundidade=0)
            nos_gerados += 1
            pilha: List[Tuple[No, Optional[List[No]]]] = [(raiz, None)]
            caminho_actual: Set[Any] = {s0}
            houve_corte = False

            while pilha:
                monitor.verificar()
                no, filhos_pendentes = pilha[-1]

                if filhos_pendentes is None:
                    if problema.e_objectivo(no.estado):
                        tempo_s, mem_mb, mem_pico = monitor.finalizar()
                        return _formatar_resultado(
                            "IDS", "—", "ok", no,
                            nos_expandidos, nos_gerados, nos_reexpandidos,
                            max_fronteira, tempo_s, mem_mb, mem_pico,
                            iteracoes=iteracoes
                        )

                    accoes = problema.accoes(no.estado)
                    if no.profundidade >= limite:
                        for accao in accoes:
                            s_filho = problema.resultado(no.estado, accao)
                            _validar_custo_transicao(problema, no.estado, accao, s_filho)
                            nos_gerados += 1
                            if s_filho not in caminho_actual:
                                houve_corte = True
                        pilha.pop()
                        caminho_actual.remove(no.estado)
                        continue

                    nos_expandidos += 1
                    if no.estado in expandidos_global:
                        nos_reexpandidos += 1
                    else:
                        expandidos_global.add(no.estado)

                    sucessores: List[No] = []
                    for accao in accoes:
                        s_filho = problema.resultado(no.estado, accao)
                        custo_passo = _validar_custo_transicao(
                            problema, no.estado, accao, s_filho
                        )
                        nos_gerados += 1
                        if s_filho not in caminho_actual:
                            filho = No(
                                estado=s_filho,
                                pai=no,
                                accao=accao,
                                g=no.g + custo_passo,
                                profundidade=no.profundidade + 1,
                            )
                            sucessores.append(filho)

                    sucessores.reverse()
                    pilha[-1] = (no, sucessores)
                    tam = len(pilha) + sum(len(p) for _, p in pilha if p is not None)
                    if tam > max_fronteira:
                        max_fronteira = tam
                else:
                    if filhos_pendentes:
                        prox = filhos_pendentes.pop()
                        caminho_actual.add(prox.estado)
                        pilha.append((prox, None))
                    else:
                        pilha.pop()
                        caminho_actual.remove(no.estado)

            if not houve_corte:
                tempo_s, mem_mb, mem_pico = monitor.finalizar()
                return _formatar_resultado(
                    "IDS", "—", "sem_solucao", None,
                    nos_expandidos, nos_gerados, nos_reexpandidos,
                    max_fronteira, tempo_s, mem_mb, mem_pico,
                    iteracoes=iteracoes, estado_f2="sem_solucao"
                )

        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "IDS", "—", "sem_solucao", None,
            nos_expandidos, nos_gerados, nos_reexpandidos,
            max_fronteira, tempo_s, mem_mb, mem_pico,
            iteracoes=iteracoes, estado_f2="limite"
        )

    except LimiteExcedidoError as exc:
        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "IDS", "—", exc.status, None,
            nos_expandidos, nos_gerados, nos_reexpandidos,
            max_fronteira, tempo_s, mem_mb, mem_pico,
            iteracoes=iteracoes
        )


def ucs(
    problema: Problema,
    limite_tempo: Optional[float] = None,
    limite_tempo_s: float = 60.0,
    limite_memoria_mb: float = 2048.0,
) -> ResultadoBusca:
    """4. Busca de Custo Uniforme (UCS) com fila `heapq` e `melhor_g`."""
    prazo = limite_tempo if limite_tempo is not None else limite_tempo_s
    _validar_limites(prazo)
    monitor = _MonitorExecucao(prazo, limite_memoria_mb)
    monitor.iniciar()

    nos_expandidos = 0
    nos_gerados = 1
    max_fronteira = 1

    try:
        s0 = problema.estado_inicial()
        raiz = No(estado=s0, pai=None, accao=None, g=0.0, profundidade=0)

        contador = count()
        fronteira: List[Tuple[float, int, No]] = [(0.0, next(contador), raiz)]
        melhor_g: Dict[Any, float] = {s0: 0.0}
        fechados: Set[Any] = set()

        while fronteira:
            monitor.verificar()
            g_actual, _, no = heapq.heappop(fronteira)

            if no.estado in fechados or g_actual > melhor_g.get(no.estado, math.inf) + 1e-9:
                continue

            fechados.add(no.estado)

            if problema.e_objectivo(no.estado):
                tempo_s, mem_mb, mem_pico = monitor.finalizar()
                return _formatar_resultado(
                    "UCS", "—", "ok", no,
                    nos_expandidos, nos_gerados, 0, max_fronteira,
                    tempo_s, mem_mb, mem_pico
                )

            nos_expandidos += 1

            for accao in problema.accoes(no.estado):
                s_filho = problema.resultado(no.estado, accao)
                custo_passo = _validar_custo_transicao(problema, no.estado, accao, s_filho)
                nos_gerados += 1
                if s_filho in fechados:
                    continue
                novo_g = no.g + custo_passo
                if novo_g + 1e-9 < melhor_g.get(s_filho, math.inf):
                    melhor_g[s_filho] = novo_g
                    filho = No(
                        estado=s_filho,
                        pai=no,
                        accao=accao,
                        g=novo_g,
                        profundidade=no.profundidade + 1,
                    )
                    heapq.heappush(fronteira, (novo_g, next(contador), filho))

            if len(fronteira) > max_fronteira:
                max_fronteira = len(fronteira)

        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "UCS", "—", "sem_solucao", None,
            nos_expandidos, nos_gerados, 0, max_fronteira,
            tempo_s, mem_mb, mem_pico
        )

    except LimiteExcedidoError as exc:
        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "UCS", "—", exc.status, None,
            nos_expandidos, nos_gerados, 0, max_fronteira,
            tempo_s, mem_mb, mem_pico
        )


# =============================================================================
# FRENTE 3 — KIMEMIA JÚNIOR, Peter Njau (Buscas Informadas: Gulosa, A* e IDA*)
# =============================================================================

def gulosa(
    problema: Problema,
    nome_h: str = "h1",
    limite_tempo_s: float = 60.0,
    limite_memoria_mb: float = 2048.0,
) -> ResultadoBusca:
    """5. Busca Gulosa pela Melhor Escolha (`f(n) = h(n)`), testada com `h1` e `h2`."""
    _validar_limites(limite_tempo_s)
    monitor = _MonitorExecucao(limite_tempo_s, limite_memoria_mb)
    monitor.iniciar()

    nos_expandidos = 0
    nos_gerados = 1
    max_fronteira = 1

    try:
        s0 = problema.estado_inicial()
        raiz = No(estado=s0, pai=None, accao=None, g=0.0, profundidade=0)
        h0_val = _avaliar_heuristica(problema, s0, nome_h)

        contador = count()
        fronteira: List[Tuple[float, float, int, No]] = [
            (h0_val, 0.0, next(contador), raiz)
        ]
        explorados: Set[Any] = set()
        na_fronteira: Set[Any] = {s0}

        while fronteira:
            monitor.verificar()
            _, _, _, no = heapq.heappop(fronteira)

            if no.estado in explorados:
                continue
            explorados.add(no.estado)

            if problema.e_objectivo(no.estado):
                tempo_s, mem_mb, mem_pico = monitor.finalizar()
                return _formatar_resultado(
                    "Gulosa", nome_h, "ok", no,
                    nos_expandidos, nos_gerados, 0, max_fronteira,
                    tempo_s, mem_mb, mem_pico
                )

            nos_expandidos += 1

            for accao in problema.accoes(no.estado):
                s_filho = problema.resultado(no.estado, accao)
                custo_passo = _validar_custo_transicao(problema, no.estado, accao, s_filho)
                if s_filho not in explorados and s_filho not in na_fronteira:
                    novo_g = no.g + custo_passo
                    filho = No(
                        estado=s_filho,
                        pai=no,
                        accao=accao,
                        g=novo_g,
                        profundidade=no.profundidade + 1,
                    )
                    nos_gerados += 1
                    h_filho = _avaliar_heuristica(problema, s_filho, nome_h)
                    na_fronteira.add(s_filho)
                    heapq.heappush(
                        fronteira, (h_filho, novo_g, next(contador), filho)
                    )

            if len(fronteira) > max_fronteira:
                max_fronteira = len(fronteira)

        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "Gulosa", nome_h, "sem_solucao", None,
            nos_expandidos, nos_gerados, 0, max_fronteira,
            tempo_s, mem_mb, mem_pico
        )

    except LimiteExcedidoError as exc:
        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "Gulosa", nome_h, exc.status, None,
            nos_expandidos, nos_gerados, 0, max_fronteira,
            tempo_s, mem_mb, mem_pico
        )


def a_estrela(
    problema: Problema,
    nome_h: str = "h1",
    limite_tempo_s: float = 60.0,
    limite_memoria_mb: float = 2048.0,
) -> ResultadoBusca:
    """6. Algoritmo A* em Grafo (`f(n) = g(n) + h(n)`), com desempate por menor `h(n)`.

    Suporta reabertura de estados fechados caso um caminho com menor `g(n)` seja
    descoberto, registando `nos_reexpandidos`.
    """
    _validar_limites(limite_tempo_s)
    monitor = _MonitorExecucao(limite_tempo_s, limite_memoria_mb)
    monitor.iniciar()

    nos_expandidos = 0
    nos_gerados = 1
    nos_reexpandidos = 0
    max_fronteira = 1

    try:
        s0 = problema.estado_inicial()
        raiz = No(estado=s0, pai=None, accao=None, g=0.0, profundidade=0)
        h_inicial = _avaliar_heuristica(problema, s0, nome_h)
        f_inicial = round(raiz.g + h_inicial, 9)

        contador = count()
        fronteira: List[Tuple[float, float, int, No]] = [
            (f_inicial, h_inicial, next(contador), raiz)
        ]
        melhor_g: Dict[Any, float] = {s0: 0.0}
        fechados: Set[Any] = set()

        while fronteira:
            monitor.verificar()
            _, _, _, no = heapq.heappop(fronteira)

            if no.g > melhor_g.get(no.estado, math.inf) + 1e-9:
                continue

            if no.estado in fechados:
                nos_reexpandidos += 1
            else:
                fechados.add(no.estado)

            if problema.e_objectivo(no.estado):
                tempo_s, mem_mb, mem_pico = monitor.finalizar()
                return _formatar_resultado(
                    "A*", nome_h, "ok", no,
                    nos_expandidos, nos_gerados, nos_reexpandidos,
                    max_fronteira, tempo_s, mem_mb, mem_pico
                )

            nos_expandidos += 1

            for accao in problema.accoes(no.estado):
                s_filho = problema.resultado(no.estado, accao)
                custo_passo = _validar_custo_transicao(problema, no.estado, accao, s_filho)
                novo_g = no.g + custo_passo

                if novo_g + 1e-9 < melhor_g.get(s_filho, math.inf):
                    melhor_g[s_filho] = novo_g
                    filho = No(
                        estado=s_filho,
                        pai=no,
                        accao=accao,
                        g=novo_g,
                        profundidade=no.profundidade + 1,
                    )
                    nos_gerados += 1
                    h_filho = _avaliar_heuristica(problema, s_filho, nome_h)
                    f_filho = round(novo_g + h_filho, 9)
                    heapq.heappush(
                        fronteira,
                        (f_filho, h_filho, next(contador), filho),
                    )

            if len(fronteira) > max_fronteira:
                max_fronteira = len(fronteira)

        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "A*", nome_h, "sem_solucao", None,
            nos_expandidos, nos_gerados, nos_reexpandidos,
            max_fronteira, tempo_s, mem_mb, mem_pico
        )

    except LimiteExcedidoError as exc:
        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "A*", nome_h, exc.status, None,
            nos_expandidos, nos_gerados, nos_reexpandidos,
            max_fronteira, tempo_s, mem_mb, mem_pico
        )


def ida_estrela(
    problema: Problema,
    nome_h: str = "h2",
    limite_tempo_s: float = 60.0,
    limite_memoria_mb: float = 2048.0,
) -> ResultadoBusca:
    """7. Algoritmo Avançado IDA* (Iterative Deepening A* — Korf, 1985)."""
    EPS = 1e-9
    _validar_limites(limite_tempo_s)
    monitor = _MonitorExecucao(limite_tempo_s, limite_memoria_mb)
    monitor.iniciar()

    nos_expandidos = 0
    nos_gerados = 1
    nos_reexpandidos = 0
    max_fronteira = 1
    iteracoes = 0
    estados_ja_expandidos: Set[Any] = set()

    try:
        s0 = problema.estado_inicial()
        raiz = No(estado=s0, pai=None, accao=None, g=0.0, profundidade=0)

        limite_f: float = _avaliar_heuristica(problema, s0, nome_h)
        caminho_actual: Set[Any] = {s0}

        def _dfs_f_limitada(
            no: No, patamar: float, tamanho_fronteira_actual: int
        ) -> Tuple[Optional[No], float]:
            nonlocal nos_expandidos, nos_gerados, nos_reexpandidos, max_fronteira

            monitor.verificar()
            if tamanho_fronteira_actual > max_fronteira:
                max_fronteira = tamanho_fronteira_actual

            h_actual = _avaliar_heuristica(problema, no.estado, nome_h)
            f_actual = no.g + h_actual

            if f_actual > patamar + EPS:
                return None, f_actual

            if problema.e_objectivo(no.estado):
                return no, f_actual

            nos_expandidos += 1
            if no.estado in estados_ja_expandidos:
                nos_reexpandidos += 1
            else:
                estados_ja_expandidos.add(no.estado)

            sucessores_ordenados: List[Tuple[float, float, No]] = []
            for accao in problema.accoes(no.estado):
                s_filho = problema.resultado(no.estado, accao)
                custo_passo = _validar_custo_transicao(problema, no.estado, accao, s_filho)
                if s_filho not in caminho_actual:
                    novo_g = no.g + custo_passo
                    filho = No(
                        estado=s_filho,
                        pai=no,
                        accao=accao,
                        g=novo_g,
                        profundidade=no.profundidade + 1,
                    )
                    nos_gerados += 1
                    h_filho = _avaliar_heuristica(problema, s_filho, nome_h)
                    f_filho = novo_g + h_filho
                    sucessores_ordenados.append((f_filho, h_filho, filho))

            sucessores_ordenados.sort(
                key=lambda item: (round(item[0], 9), round(item[1], 9))
            )

            proximo_limite_local = math.inf
            num_sucessores = len(sucessores_ordenados)

            for idx, (_, _, filho) in enumerate(sucessores_ordenados):
                caminho_actual.add(filho.estado)
                fronteira_ramo = tamanho_fronteira_actual + (num_sucessores - idx - 1)
                solucao, limiar_candidato = _dfs_f_limitada(
                    filho, patamar, fronteira_ramo
                )
                caminho_actual.remove(filho.estado)

                if solucao is not None:
                    return solucao, limiar_candidato
                if limiar_candidato < proximo_limite_local:
                    proximo_limite_local = limiar_candidato

            return None, proximo_limite_local

        while True:
            iteracoes += 1
            no_solucao, proximo_limite = _dfs_f_limitada(raiz, limite_f, 1)

            if no_solucao is not None:
                tempo_s, mem_mb, mem_pico = monitor.finalizar()
                return _formatar_resultado(
                    "IDA*", nome_h, "ok", no_solucao,
                    nos_expandidos, nos_gerados, nos_reexpandidos,
                    max_fronteira, tempo_s, mem_mb, mem_pico,
                    iteracoes=iteracoes
                )

            if math.isinf(proximo_limite):
                tempo_s, mem_mb, mem_pico = monitor.finalizar()
                return _formatar_resultado(
                    "IDA*", nome_h, "sem_solucao", None,
                    nos_expandidos, nos_gerados, nos_reexpandidos,
                    max_fronteira, tempo_s, mem_mb, mem_pico,
                    iteracoes=iteracoes
                )

            limite_f = proximo_limite

    except LimiteExcedidoError as exc:
        tempo_s, mem_mb, mem_pico = monitor.finalizar()
        return _formatar_resultado(
            "IDA*", nome_h, exc.status, None,
            nos_expandidos, nos_gerados, nos_reexpandidos,
            max_fronteira, tempo_s, mem_mb, mem_pico,
            iteracoes=iteracoes
        )


# Aliases opcionais para menus e testes (Frente 2 e Frente 3).
busca_largura = bfs
busca_profundidade = dfs
aprofundamento_iterativo = ids
custo_uniforme = ucs
busca_gulosa = gulosa
