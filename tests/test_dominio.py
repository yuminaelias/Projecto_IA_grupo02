import heapq
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from dominio import EstadoContentores, ProblemaContentores
from problema import No, Problema, caminho


def test_sucessores_estado_inicial():
    dados = json.loads((Path(__file__).parents[1] / "instancias/base.json").read_text(encoding="utf-8"))
    problema = ProblemaContentores(**dados)
    assert isinstance(problema, Problema)
    assert len(Problema.__abstractmethods__) == 6
    inicial = problema.estado_inicial()
    esperado = ((8, 2, 10), (5, 1, 6), (9, 4), (7, 3))
    assert inicial == EstadoContentores(esperado, 1)
    assert isinstance(problema.pesados, frozenset)
    assert isinstance(problema.refrigerados, frozenset)
    assert set(problema.accoes(inicial)) == {
        ("mover", i, j) for i in range(4) for j in range(4) if i != j
    }
    for a in problema.accoes(inicial):
        s2 = problema.resultado(inicial, a)
        i, j = a[1:]
        assert s2.pilhas[i] == inicial.pilhas[i][:-1]
        assert s2.pilhas[j] == inicial.pilhas[j] + (inicial.pilhas[i][-1],)
        assert all(s2.pilhas[k] == inicial.pilhas[k] for k in range(4) if k not in (i, j))
        assert s2.proximo == 1
        assert problema.custo(inicial, a, s2) == pytest.approx(1 + 0.1 * abs(i-j))
        assert hash(s2) == hash(EstadoContentores(s2.pilhas, 1))
    assert inicial.pilhas == esperado
    for a in [("levantar", 0), ("mover", 0, 0), ("mover", -1, 0), ("mover", 0, 4)]:
        with pytest.raises(ValueError):
            problema.resultado(inicial, a)

    # Uma sequência curta verifica levantamento, objectivo e contrato dos nós.
    pequeno = ProblemaContentores(2, 1, [[1], []])
    s0 = pequeno.estado_inicial()
    s1 = pequeno.resultado(s0, ("mover", 0, 1))
    assert ("mover", 0, 1) not in pequeno.accoes(s1)  # origem vazia
    s2 = pequeno.resultado(s1, ("levantar", 1))
    assert pequeno.custo(s1, ("levantar", 1), s2) == 0
    assert pequeno.e_objectivo(s2)
    assert not pequeno.e_objectivo(EstadoContentores(((), ()), 1))
    assert pequeno.accoes(s2) == []
    raiz = No(s0)
    filho = No(s1, raiz, ("mover", 0, 1), 1.1, 1)
    fim = No(s2, filho, ("levantar", 1), 1.1, 2)
    assert caminho(fim) == ([s0, s1, s2], [("mover", 0, 1), ("levantar", 1)])
    assert caminho(raiz) == ([s0], [])
    heap = [(1, filho), (1, raiz)]
    heapq.heapify(heap)
    assert heapq.heappop(heap)[1] is raiz
    cheio = ProblemaContentores(2, 1, [[1], [2]])
    assert ("mover", 0, 1) not in cheio.accoes(cheio.estado_inicial())
    with pytest.raises(ValueError):
        cheio.resultado(cheio.estado_inicial(), ("mover", 0, 1))
    with pytest.raises(ValueError):
        pequeno.custo(s0, ("mover", 0, 1), s0)
    with pytest.raises(NotImplementedError):
        pequeno.heuristica(s0, "h1")


def test_pesado_nao_pode_ficar_sobre_leve():
    problema = ProblemaContentores(4, 2, [[2], [1], [3], []], pesados={2, 3})
    s = problema.estado_inicial()
    assert ("mover", 0, 1) not in problema.accoes(s)
    with pytest.raises(ValueError):
        problema.resultado(s, ("mover", 0, 1))
    assert ("mover", 0, 2) in problema.accoes(s)  # pesado sobre pesado
    assert ("mover", 0, 3) in problema.accoes(s)  # pesado numa pilha vazia
    assert ("mover", 1, 0) in problema.accoes(s)  # leve sobre pesado


def test_refrigerados_apenas_em_pilhas_com_tomadas():
    problema = ProblemaContentores(4, 2, [[2], [1], [], []], refrigerados={2})
    s = problema.estado_inicial()
    assert ("mover", 0, 1) in problema.accoes(s)
    for j in (2, 3):
        assert ("mover", 0, j) not in problema.accoes(s)
        with pytest.raises(ValueError):
            problema.resultado(s, ("mover", 0, j))
    s2 = problema.resultado(s, ("mover", 0, 1))
    assert ("mover", 1, 0) in problema.accoes(s2)
    assert s.pilhas == ((2,), (1,), (), ())


@pytest.mark.parametrize("alteracoes", [
    {"S": 0}, {"S": True}, {"H": 0}, {"H": 1.5},
    {"pilhas": [[1]]}, {"pilhas": [[1, 2, 3], []]},
    {"pilhas": [[1], [1]]}, {"pilhas": [[1], [3]]},
    {"pilhas": [[0], [1]]}, {"pilhas": [[True], [2]]},
    {"pilhas": [[1.0], [2]]}, {"pilhas": None},
    {"pesados": [3]}, {"refrigerados": [3]},
    {"pesados": [True]}, {"refrigerados": [2.0]},
    {"pesados": None}, {"pilhas": [[1, 2], []], "pesados": [2]},
    {"S": 3, "pilhas": [[1], [], [2]], "refrigerados": [2]},
])
def test_configuracoes_iniciais_invalidas(alteracoes):
    dados = {"S": 2, "H": 2, "pilhas": [[1], [2]]}
    dados.update(alteracoes)
    with pytest.raises(ValueError):
        ProblemaContentores(**dados)


def test_estado_imutavel_e_independente_das_listas_recebidas():
    pilhas = [[1], []]
    estado = EstadoContentores(pilhas, 1)
    problema = ProblemaContentores(2, 2, pilhas)
    pilhas[0].append(2)
    assert estado.pilhas == problema.estado_inicial().pilhas == ((1,), ())
    assert {estado: "visitado"}[EstadoContentores(((1,), ()), 1)] == "visitado"
    with pytest.raises(FrozenInstanceError):
        estado.proximo = 2
    with pytest.raises(TypeError):
        estado.pilhas[0][0] = 2


@pytest.mark.parametrize("accao", [
    (), ("desconhecida", 0), ("levantar",), ("mover", 0),
    ("mover", 0, 1, 2), ("mover", False, 1), ("mover", 0, 1.0),
    ["levantar", 0], None,
])
def test_formato_de_accao_invalido(accao):
    problema = ProblemaContentores(2, 2, [[1], []])
    with pytest.raises(ValueError):
        problema.resultado(problema.estado_inicial(), accao)


def test_contrato_abstracto_exactamente_seis_metodos():
    assert Problema.__abstractmethods__ == {
        "estado_inicial", "accoes", "resultado", "custo", "e_objectivo", "heuristica"
    }
    with pytest.raises(TypeError):
        Problema()
    assert not ProblemaContentores.__abstractmethods__
