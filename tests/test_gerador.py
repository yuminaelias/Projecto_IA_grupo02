"""Testes unitários do gerador de instâncias da Frente 5 (`gerador.py`).

Universidade Eduardo Mondlane — Inteligência Artificial I (2026)
Grupo 02 (Laboral) — Frente 5: Modesta Cipriano Manuel
"""

from __future__ import annotations

from pathlib import Path

from buscas import a_estrela, bfs
from dominio import ProblemaContentores
from gerador import (
    NIVEIS,
    SEMENTE_OFICIAL,
    carregar_instancia,
    gerar_bateria,
    gerar_instancia,
)


def test_gerador_produz_instancias_deterministicas_e_validas():
    """Verifica que a semente oficial 202602 gera instâncias determinísticas e válidas."""
    assert SEMENTE_OFICIAL == 202602

    for nivel, limites in NIVEIS.items():
        for indice in range(3):
            inst1 = gerar_instancia(nivel, indice, semente=SEMENTE_OFICIAL)
            inst2 = gerar_instancia(nivel, indice, semente=SEMENTE_OFICIAL)
            assert inst1 == inst2

            s_min, s_max = limites["S"]
            h_min, h_max = limites["H"]
            n_min, n_max = limites["N"]
            assert s_min <= inst1["S"] <= s_max
            assert h_min <= inst1["H"] <= h_max
            assert n_min <= inst1["num_contentores"] <= n_max
            assert inst1["S"] <= 6 and inst1["H"] <= 5

            problema = ProblemaContentores(
                inst1["S"],
                inst1["H"],
                inst1["pilhas"],
                inst1["pesados"],
                inst1["refrigerados"],
            )
            assert problema.total_contentores == inst1["num_contentores"]


def test_bateria_completa_e_solvabilidade_pequenas(tmp_path: Path):
    """Gera as 30 instâncias (3 níveis x 10) e comprova solvabilidade nas pequenas."""
    ficheiros = gerar_bateria(semente=SEMENTE_OFICIAL, diretorio=tmp_path)
    assert len(ficheiros) == 30

    for idx in range(3):
        dados = carregar_instancia(tmp_path / f"Pequeno_{idx}.json")
        problema = ProblemaContentores(
            dados["S"],
            dados["H"],
            dados["pilhas"],
            dados["pesados"],
            dados["refrigerados"],
        )
        res_bfs = bfs(problema, limite_tempo_s=10.0)
        res_astar = a_estrela(problema, "h1", limite_tempo_s=10.0)
        assert res_bfs.resolvido is True
        assert res_astar.resolvido is True


def test_restricoes_estruturais_sao_respeitadas():
    """Valida altura <= H, tomadas refrigeradas (0/1) e pesados sobre pesados."""
    for nivel in NIVEIS:
        for indice in range(10):
            dados = gerar_instancia(nivel, indice, semente=SEMENTE_OFICIAL)
            S = dados["S"]
            H = dados["H"]
            pilhas = dados["pilhas"]
            pesados = set(dados["pesados"])
            refrigerados = set(dados["refrigerados"])

            assert len(pilhas) == S
            assert pesados.isdisjoint(refrigerados)

            todos = [c for p in pilhas for c in p]
            assert sorted(todos) == list(range(1, dados["num_contentores"] + 1))

            for idx_pilha, pilha in enumerate(pilhas):
                assert len(pilha) <= H
                for pos, c in enumerate(pilha):
                    if c in refrigerados:
                        assert idx_pilha in (0, 1)
                    if c in pesados and pos > 0:
                        assert pilha[pos - 1] in pesados

