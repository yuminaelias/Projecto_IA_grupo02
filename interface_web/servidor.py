"""Servidor HTTP local e API JSON para o Simulador Visual do Porto de Maputo (P2).

Universidade Eduardo Mondlane — Inteligência Artificial I (2026)
Grupo 02 (Laboral) — P2: Reordenação de Contentores no Porto de Maputo

Execução:
    python interface_web/servidor.py

Abre em:
    http://127.0.0.1:8000
"""

from __future__ import annotations
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

RAIZ_PROJECTO = Path(__file__).resolve().parent.parent
DIR_STATIC = Path(__file__).resolve().parent / "static"
DIR_INSTANCIAS = RAIZ_PROJECTO / "instancias"

if str(RAIZ_PROJECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJECTO))

from buscas import a_estrela, bfs, dfs, gulosa, ida_estrela, ids, ucs
from dominio import EstadoContentores, ProblemaContentores
from heuristicas import calcular_b_estrela, h0, h1, h2
from problema import Problema


class ProblemaSimulador(Problema):
    """Adapta `ProblemaContentores` para suportar:
    1. Estados intermédios no Modo Operador Manual (onde `proximo > 1` e alguns
       contentores `1..proximo-1` já foram levantados);
    2. Modificações ao vivo de Treino de Defesa (quando ativadas na UI):
       - `reefer3`: permitir contentores refrigerados também na Pilha 3 (índice 2);
       - `liftCost`: ação levantar com custo 0.5 em vez de 0.0;
       - `separateR`: impedir dois contentores refrigerados na mesma pilha.
    Quando `proximo == 1` e `mods` estão desativados, delega 100% para a instância
    oficial de `ProblemaContentores` de `dominio.py`.
    """

    def __init__(
        self,
        S: int,
        H: int,
        pilhas: Any,
        pesados: Any = (),
        refrigerados: Any = (),
        proximo: int = 1,
        mods: Optional[Dict[str, bool]] = None,
    ):
        self.S = int(S)
        self.H = int(H)
        self.pilhas_iniciais = tuple(tuple(int(c) for c in p) for p in pilhas)
        self.pesados = frozenset(int(c) for c in pesados)
        self.refrigerados = frozenset(int(c) for c in refrigerados)
        self.proximo_inicial = int(proximo)
        self.mods = mods or {}
        self.reefer3 = bool(self.mods.get("reefer3", False))
        self.lift_cost = 0.5 if self.mods.get("liftCost", False) else 0.0
        self.separate_r = bool(self.mods.get("separateR", False))

        todos = [c for p in self.pilhas_iniciais for c in p]
        self.total_contentores = max(todos) if todos else (self.proximo_inicial - 1)
        self._inicial = EstadoContentores(self.pilhas_iniciais, self.proximo_inicial)

        # Se for estado inicial padrão sem mods, valida também com ProblemaContentores oficial
        if (
            self.proximo_inicial == 1
            and not self.reefer3
            and self.lift_cost == 0.0
            and not self.separate_r
            and sorted(todos) == list(range(1, len(todos) + 1))
        ):
            self._oficial: Optional[ProblemaContentores] = ProblemaContentores(
                self.S, self.H, self.pilhas_iniciais, self.pesados, self.refrigerados
            )
        else:
            self._oficial = None

    def estado_inicial(self) -> EstadoContentores:
        return self._inicial

    def _tomadas_permitidas(self) -> Tuple[int, ...]:
        return (0, 1, 2) if self.reefer3 else (0, 1)

    def motivo_bloqueio(self, s: EstadoContentores, i: int, j: int) -> Optional[str]:
        """Devolve `None` se `mover(i, j)` for válido, ou uma mensagem explicativa."""
        if i == j:
            return "Mesma pilha de origem"
        if not (0 <= i < self.S and 0 <= j < self.S):
            return "Índice de pilha fora dos limites"
        if not s.pilhas[i]:
            return "Pilha de origem vazia"
        topo = s.pilhas[i][-1]
        destino = s.pilhas[j]
        if len(destino) >= self.H:
            return f"Altura máxima H = {self.H} atingida na Pilha {j + 1}"
        tomadas = self._tomadas_permitidas()
        if topo in self.refrigerados and j not in tomadas:
            pilhas_str = "1, 2 ou 3" if self.reefer3 else "1 ou 2"
            return f"Contentor {topo}R exige tomada elétrica nas Pilhas {pilhas_str}"
        if topo in self.pesados and destino and destino[-1] not in self.pesados:
            return f"Contentor pesado #{topo}P não pode ficar sobre leve #{destino[-1]}"
        if self.separate_r and topo in self.refrigerados and any(c in self.refrigerados for c in destino):
            return "Restrição de defesa ativa: dois refrigerados (R) não podem ficar juntos"
        return None

    def accoes(self, s: EstadoContentores) -> List[Tuple]:
        if self._oficial is not None:
            return self._oficial.accoes(s)
        accoes_legais: List[Tuple] = []
        for i, origem in enumerate(s.pilhas):
            if not origem:
                continue
            topo = origem[-1]
            if topo == s.proximo:
                accoes_legais.append(("levantar", i))
            for j in range(self.S):
                if i == j:
                    continue
                if self.motivo_bloqueio(s, i, j) is None:
                    accoes_legais.append(("mover", i, j))
        return accoes_legais

    def resultado(self, s: EstadoContentores, a: Tuple) -> EstadoContentores:
        if self._oficial is not None:
            return self._oficial.resultado(s, a)
        if a not in self.accoes(s):
            raise ValueError(f"Ação inválida: {a!r}")
        pilhas = list(s.pilhas)
        i = a[1]
        topo = pilhas[i][-1]
        pilhas[i] = pilhas[i][:-1]
        proximo = s.proximo
        if a[0] == "levantar":
            proximo += 1
        else:
            j = a[2]
            pilhas[j] = pilhas[j] + (topo,)
        return EstadoContentores(tuple(pilhas), proximo)

    def custo(self, s: EstadoContentores, a: Tuple, s2: EstadoContentores) -> float:
        if self._oficial is not None and self.lift_cost == 0.0:
            return self._oficial.custo(s, a, s2)
        if a[0] == "levantar":
            return self.lift_cost
        return 1.0 + 0.1 * abs(a[1] - a[2])

    def e_objectivo(self, s: EstadoContentores) -> bool:
        if self._oficial is not None:
            return self._oficial.e_objectivo(s)
        return s.proximo == self.total_contentores + 1 and all(not p for p in s.pilhas)

    def heuristica(self, s: EstadoContentores, nome: str) -> float:
        if nome == "h0":
            return float(h0(s, self))
        if nome == "h1":
            return float(h1(s, self))
        if nome == "h2":
            return float(h2(s, self))
        raise ValueError(f"Heurística desconhecida: {nome!r}")


INSTANCIAS_PREDEFINIDAS: Dict[str, Dict[str, Any]] = {
    "base": {
        "id": "base",
        "nome": "Base Oficial · S4 H4 N10",
        "nivel": "Base Oficial",
        "descricao": "Instância oficial do enunciado (Grupo 02 Laboral) — Custo óptimo = 4,8 em 14 acções",
        "S": 4,
        "H": 4,
        "pesados": [5, 7, 8, 9],
        "refrigerados": [2, 5],
        "pilhas": [[8, 2, 10], [5, 1, 6], [9, 4], [7, 3]],
    },
    "pequena": {
        "id": "pequena",
        "nome": "Pequeno · S3 H3 N6",
        "nivel": "Pequena",
        "descricao": "Instância rápida de validação (S=3, H=3, 6 contentores) — Todos os 7 algoritmos terminam",
        "S": 3,
        "H": 3,
        "pesados": [4, 5, 6],
        "refrigerados": [2],
        "pilhas": [[5, 2, 3], [6, 4, 1], []],
    },
    "media": {
        "id": "media",
        "nome": "Médio · S5 H4 N12",
        "nivel": "Média",
        "descricao": "Instância intermédia (S=5, H=4, 12 contentores) — Mostra vantagem de h2 sobre h1",
        "S": 5,
        "H": 4,
        "pesados": [8, 9, 10, 11, 12],
        "refrigerados": [2, 8],
        "pilhas": [[10, 2, 7], [8, 12, 1, 6], [11, 4, 5], [9, 3], []],
    },
    "grande": {
        "id": "grande",
        "nome": "Grande · S6 H5 N16",
        "nivel": "Grande",
        "descricao": "Instância exigente (S=6, H=5, 16 contentores) — Destaca eficiência de A* (h2) e IDA* (h2)",
        "S": 6,
        "H": 5,
        "pesados": [11, 12, 13, 14, 15, 16],
        "refrigerados": [2, 5, 11],
        "pilhas": [
            [14, 2, 10],
            [11, 5, 1, 9],
            [15, 16, 4, 7],
            [12, 3, 8],
            [13, 6],
            [],
        ],
    },
}


def carregar_instancias() -> List[Dict[str, Any]]:
    """Devolve as instâncias disponíveis enriquecidas com h0, h1, h2 iniciais."""
    # Garante que `base` usa exatamente o ficheiro `instancias/base.json`
    fich_base = DIR_INSTANCIAS / "base.json"
    if fich_base.exists():
        dados_base = json.loads(fich_base.read_text(encoding="utf-8"))
        INSTANCIAS_PREDEFINIDAS["base"].update(dados_base)

    lista: List[Dict[str, Any]] = []
    for chave, inst in INSTANCIAS_PREDEFINIDAS.items():
        prob = ProblemaSimulador(
            inst["S"],
            inst["H"],
            inst["pilhas"],
            inst["pesados"],
            inst["refrigerados"],
        )
        s0 = prob.estado_inicial()
        copia = dict(inst)
        copia["proximo"] = 1
        copia["heuristicas_iniciais"] = {
            "h0": round(h0(s0, prob), 2),
            "h1": round(h1(s0, prob), 2),
            "h2": round(h2(s0, prob), 2),
        }
        lista.append(copia)
    return lista


def avaliar_estado_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Avalia um estado arbitrário e devolve ações legais, bloqueios e heurísticas."""
    S = int(payload["S"])
    H = int(payload["H"])
    pilhas = payload["pilhas"]
    pesados = payload.get("pesados", [])
    refrigerados = payload.get("refrigerados", [])
    proximo = int(payload.get("proximo", 1))
    mods = payload.get("mods", {})

    prob = ProblemaSimulador(S, H, pilhas, pesados, refrigerados, proximo, mods)
    s = prob.estado_inicial()

    accoes_formatadas = []
    for a in prob.accoes(s):
        s2 = prob.resultado(s, a)
        custo = round(prob.custo(s, a, s2), 4)
        if a[0] == "levantar":
            i = a[1]
            contentor = s.pilhas[i][-1]
            accoes_formatadas.append({
                "tipo": "levantar",
                "origem": i,
                "destino": None,
                "contentor": contentor,
                "custo": custo,
                "tuplo": list(a),
            })
        else:
            i, j = a[1], a[2]
            contentor = s.pilhas[i][-1]
            accoes_formatadas.append({
                "tipo": "mover",
                "origem": i,
                "destino": j,
                "contentor": contentor,
                "custo": custo,
                "tuplo": list(a),
            })

    motivos_bloqueio: Dict[str, Dict[str, Optional[str]]] = {}
    for i in range(S):
        motivos_bloqueio[str(i)] = {}
        for j in range(S):
            if i == j:
                continue
            motivos_bloqueio[str(i)][str(j)] = prob.motivo_bloqueio(s, i, j)

    val_h0 = round(h0(s, prob), 4)
    val_h1 = round(h1(s, prob), 4)
    val_h2 = round(h2(s, prob), 4)

    return {
        "pilhas": [list(p) for p in s.pilhas],
        "proximo": s.proximo,
        "e_objectivo": prob.e_objectivo(s),
        "accoes_legais": accoes_formatadas,
        "motivos_bloqueio": motivos_bloqueio,
        "heuristicas": {"h0": val_h0, "h1": val_h1, "h2": val_h2},
    }


def _calcular_patamares_ida(
    prob: ProblemaSimulador, nome_h: str, custo_final: float
) -> List[float]:
    """Reconstrói os patamares `limite_f` explorados pelo IDA* até encontrar a solução."""
    EPS = 1e-9
    s0 = prob.estado_inicial()
    limite_f = round(prob.heuristica(s0, nome_h), 4)
    patamares = [limite_f]
    caminho_actual: Set[Any] = {s0}
    passos = 0

    def dfs_patamar(s: EstadoContentores, g: float, patamar: float) -> Tuple[bool, float]:
        nonlocal passos
        passos += 1
        if passos > 40000:
            return True, patamar
        f_val = g + prob.heuristica(s, nome_h)
        if f_val > patamar + EPS:
            return False, f_val
        if prob.e_objectivo(s):
            return True, f_val
        menor_excesso = math.inf
        sucessores = []
        for a in prob.accoes(s):
            s2 = prob.resultado(s, a)
            if s2 not in caminho_actual:
                c = prob.custo(s, a, s2)
                g2 = g + c
                f2 = g2 + prob.heuristica(s2, nome_h)
                sucessores.append((f2, g2, s2))
        sucessores.sort(key=lambda x: round(x[0], 9))
        for _, g2, s2 in sucessores:
            caminho_actual.add(s2)
            achou, lim = dfs_patamar(s2, g2, patamar)
            caminho_actual.remove(s2)
            if achou:
                return True, lim
            if lim < menor_excesso:
                menor_excesso = lim
        return False, menor_excesso

    while len(patamares) < 25:
        achou, prox = dfs_patamar(s0, 0.0, limite_f)
        if achou or math.isinf(prox):
            break
        limite_f = round(prox, 4)
        patamares.append(limite_f)
        if limite_f >= custo_final - 1e-6:
            break

    return patamares


def resolver_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Executa um dos 7 algoritmos de `buscas.py` e devolve os passos detalhados."""
    S = int(payload["S"])
    H = int(payload["H"])
    pilhas = payload["pilhas"]
    pesados = payload.get("pesados", [])
    refrigerados = payload.get("refrigerados", [])
    proximo = int(payload.get("proximo", 1))
    mods = payload.get("mods", {})

    algoritmo = str(payload.get("algoritmo", "A*")).strip()
    nome_h = str(payload.get("heuristica", "h2")).strip()
    limite_profundidade = int(payload.get("limite_profundidade", 50))
    limite_tempo_s = float(payload.get("limite_tempo_s", 15.0))

    prob = ProblemaSimulador(S, H, pilhas, pesados, refrigerados, proximo, mods)

    alg_upper = algoritmo.upper()
    if alg_upper == "BFS":
        res = bfs(prob, limite_tempo_s=limite_tempo_s)
    elif alg_upper == "DFS":
        res = dfs(
            prob,
            limite_profundidade=limite_profundidade,
            limite_tempo_s=limite_tempo_s,
        )
    elif alg_upper == "IDS":
        res = ids(
            prob,
            limite_profundidade=limite_profundidade,
            limite_tempo_s=limite_tempo_s,
        )
    elif alg_upper == "UCS":
        res = ucs(prob, limite_tempo_s=limite_tempo_s)
    elif alg_upper in ("GULOSA", "GREEDY"):
        h_uso = nome_h if nome_h in ("h1", "h2") else "h2"
        res = gulosa(prob, nome_h=h_uso, limite_tempo_s=limite_tempo_s)
    elif alg_upper in ("A*", "A_ESTRELA", "ASTAR"):
        res = a_estrela(prob, nome_h=nome_h, limite_tempo_s=limite_tempo_s)
    elif alg_upper in ("IDA*", "IDA_ESTRELA", "IDASTAR"):
        res = ida_estrela(prob, nome_h=nome_h, limite_tempo_s=limite_tempo_s)
    else:
        raise ValueError(f"Algoritmo desconhecido: {algoritmo!r}")

    # Reconstrói todos os estados passo a passo (k = 0 .. d)
    s_actual = prob.estado_inicial()
    g_acum = 0.0
    h0_i = round(h0(s_actual, prob), 4)
    h1_i = round(h1(s_actual, prob), 4)
    h2_i = round(h2(s_actual, prob), 4)
    h_sel_i = h0_i if nome_h == "h0" else (h1_i if nome_h == "h1" else h2_i)

    passos: List[Dict[str, Any]] = [
        {
            "passo": 0,
            "pilhas": [list(p) for p in s_actual.pilhas],
            "proximo": s_actual.proximo,
            "accao": None,
            "custo_passo": 0.0,
            "g": 0.0,
            "h0": h0_i,
            "h1": h1_i,
            "h2": h2_i,
            "f": round(h_sel_i, 4),
        }
    ]

    acoes_formatadas: List[Dict[str, Any]] = []
    if res.resolvido:
        for idx, a in enumerate(res.acoes, start=1):
            i = a[1]
            contentor = s_actual.pilhas[i][-1]
            s_prox = prob.resultado(s_actual, a)
            c_passo = round(prob.custo(s_actual, a, s_prox), 4)
            g_acum = round(g_acum + c_passo, 4)

            info_accao = {
                "ordem": idx,
                "tipo": a[0],
                "origem": i,
                "destino": a[2] if a[0] == "mover" else None,
                "contentor": contentor,
                "custo": c_passo,
                "g_acumulado": g_acum,
                "tuplo": list(a),
            }
            acoes_formatadas.append(info_accao)

            s_actual = s_prox
            vh0 = round(h0(s_actual, prob), 4)
            vh1 = round(h1(s_actual, prob), 4)
            vh2 = round(h2(s_actual, prob), 4)
            vhsel = vh0 if nome_h == "h0" else (vh1 if nome_h == "h1" else vh2)

            passos.append(
                {
                    "passo": idx,
                    "pilhas": [list(p) for p in s_actual.pilhas],
                    "proximo": s_actual.proximo,
                    "accao": info_accao,
                    "custo_passo": c_passo,
                    "g": g_acum,
                    "h0": vh0,
                    "h1": vh1,
                    "h2": vh2,
                    "f": round(g_acum + vhsel, 4),
                }
            )

    b_est = (
        calcular_b_estrela(res.nos_expandidos, res.comprimento)
        if res.resolvido and res.comprimento > 0 and res.nos_expandidos > 0
        else 1.0
    )

    patamares_f: List[float] = []
    if alg_upper in ("IDA*", "IDA_ESTRELA", "IDASTAR") and res.resolvido:
        patamares_f = _calcular_patamares_ida(prob, nome_h, res.custo)

    return {
        "algoritmo": res.algoritmo,
        "heuristica": res.heuristica,
        "resolvido": res.resolvido,
        "custo": round(res.custo, 4) if math.isfinite(res.custo) else None,
        "comprimento": res.comprimento,
        "acoes": acoes_formatadas,
        "nos_expandidos": res.nos_expandidos,
        "nos_gerados": res.nos_gerados,
        "nos_reexpandidos": res.nos_reexpandidos,
        "max_fronteira": res.max_fronteira,
        "tempo_s": res.tempo_s,
        "memoria_mb": res.memoria_mb,
        "status": res.status,
        "b_estrela": b_est,
        "iteracoes": getattr(res, "iteracoes", 1),
        "patamares_f": patamares_f,
        "passos": passos,
    }


def comparar_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Executa a bateria comparativa dos algoritmos na instância selecionada."""
    S = int(payload.get("S", 4))
    H = int(payload.get("H", 4))
    pilhas = payload.get("pilhas", INSTANCIAS_PREDEFINIDAS["base"]["pilhas"])
    pesados = payload.get("pesados", INSTANCIAS_PREDEFINIDAS["base"]["pesados"])
    refrigerados = payload.get(
        "refrigerados", INSTANCIAS_PREDEFINIDAS["base"]["refrigerados"]
    )
    limite_tempo_s = float(payload.get("limite_tempo_s", 3.0))

    configuracoes = [
        ("BFS", "—", lambda p: bfs(p, limite_tempo_s=limite_tempo_s)),
        ("DFS (L=28)", "—", lambda p: dfs(p, limite_profundidade=28, limite_tempo_s=limite_tempo_s)),
        ("IDS (L=16)", "—", lambda p: ids(p, limite_profundidade=16, limite_tempo_s=min(limite_tempo_s, 1.5))),
        ("UCS", "—", lambda p: ucs(p, limite_tempo_s=limite_tempo_s)),
        ("Gulosa h1", "h1", lambda p: gulosa(p, "h1", limite_tempo_s=limite_tempo_s)),
        ("Gulosa h2", "h2", lambda p: gulosa(p, "h2", limite_tempo_s=limite_tempo_s)),
        ("A* h0", "h0", lambda p: a_estrela(p, "h0", limite_tempo_s=limite_tempo_s)),
        ("A* h1", "h1", lambda p: a_estrela(p, "h1", limite_tempo_s=limite_tempo_s)),
        ("A* h2", "h2", lambda p: a_estrela(p, "h2", limite_tempo_s=limite_tempo_s)),
        ("IDA* h1", "h1", lambda p: ida_estrela(p, "h1", limite_tempo_s=limite_tempo_s)),
        ("IDA* h2", "h2", lambda p: ida_estrela(p, "h2", limite_tempo_s=limite_tempo_s)),
    ]

    linhas = []
    custo_optimo: Optional[float] = None

    for rotulo, heur, fn in configuracoes:
        prob = ProblemaSimulador(S, H, pilhas, pesados, refrigerados)
        res = fn(prob)
        if rotulo in ("UCS", "A* h2", "IDA* h2") and res.resolvido:
            if custo_optimo is None or res.custo < custo_optimo:
                custo_optimo = round(res.custo, 4)

        b_est = (
            calcular_b_estrela(res.nos_expandidos, res.comprimento)
            if res.resolvido and res.comprimento > 0 and res.nos_expandidos > 0
            else 1.0
        )

        linhas.append({
            "rotulo": rotulo,
            "algoritmo": res.algoritmo,
            "heuristica": heur,
            "resolvido": res.resolvido,
            "status": res.status,
            "custo": round(res.custo, 4) if res.resolvido else None,
            "comprimento": res.comprimento,
            "nos_expandidos": res.nos_expandidos,
            "nos_gerados": res.nos_gerados,
            "nos_reexpandidos": res.nos_reexpandidos,
            "max_fronteira": res.max_fronteira,
            "b_estrela": b_est,
            "tempo_s": res.tempo_s,
            "memoria_mb": res.memoria_mb,
        })

    for item in linhas:
        if item["resolvido"] and custo_optimo and custo_optimo > 0:
            item["racio_optimo"] = round(item["custo"] / custo_optimo, 4)
        else:
            item["racio_optimo"] = None

    return {
        "custo_optimo": custo_optimo,
        "resultados": linhas,
    }


class SimuladorHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Serve `interface_web/static/` e responde aos endpoints `/api/*`."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIR_STATIC), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        # Log conciso no terminal
        sys.stderr.write(f"[TOS-PortMaputo] {self.address_string()} - {format % args}\n")

    def _enviar_json(self, dados: Any, status: int = 200) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _ler_json(self) -> Dict[str, Any]:
        tamanho = int(self.headers.get("Content-Length", "0"))
        if tamanho <= 0:
            return {}
        bruto = self.rfile.read(tamanho).decode("utf-8")
        return json.loads(bruto) if bruto else {}

    def do_GET(self) -> None:
        rota = urlparse(self.path).path
        if rota == "/api/instancias":
            try:
                self._enviar_json({"instancias": carregar_instancias()})
            except Exception as exc:
                self._enviar_json({"erro": str(exc)}, status=400)
            return
        super().do_GET()

    def do_POST(self) -> None:
        rota = urlparse(self.path).path
        try:
            payload = self._ler_json()
            if rota == "/api/estado":
                self._enviar_json(avaliar_estado_api(payload))
            elif rota == "/api/resolver":
                self._enviar_json(resolver_api(payload))
            elif rota == "/api/comparar":
                self._enviar_json(comparar_api(payload))
            else:
                self._enviar_json({"erro": f"Rota desconhecida: {rota}"}, status=404)
        except Exception as exc:
            self._enviar_json({"erro": str(exc)}, status=400)


def iniciar_servidor(host: str = "127.0.0.1", porta: int = 8000) -> None:
    servidor = ThreadingHTTPServer((host, porta), SimuladorHTTPRequestHandler)
    print("=" * 68)
    print("  PORTO DE MAPUTO — TOS SIMULATOR (UEM · IA I 2026 · GRUPO 02)")
    print(f"  Servidor ativo em: http://{host}:{porta}")
    print("  Pressione Ctrl+C para encerrar.")
    print("=" * 68)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    porta_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    iniciar_servidor(porta=porta_arg)
