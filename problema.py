"""Contrato comum aos domínios e estruturas usadas pelas buscas (Python 3.10+)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class Problema(ABC):
    """Define as seis operações que qualquer algoritmo pode consultar."""

    @abstractmethod
    def estado_inicial(self):
        """Devolve o estado de partida."""

    @abstractmethod
    def accoes(self, s):
        """Devolve as acções legais no estado s."""

    @abstractmethod
    def resultado(self, s, a):
        """Devolve o sucessor de s pela acção a."""

    @abstractmethod
    def custo(self, s, a, s2):
        """Devolve o custo da transição de s para s2 por a."""

    @abstractmethod
    def e_objectivo(self, s):
        """Indica se s satisfaz o objectivo."""

    @abstractmethod
    def heuristica(self, s, nome):
        """Devolve a estimativa identificada por nome."""


@dataclass
class No:
    """Guarda um estado e a ligação ao pai para reconstruir o caminho."""

    estado: Any
    pai: "No | None" = None
    accao: tuple | None = None
    g: float = 0.0
    profundidade: int = 0

    def __lt__(self, outro):
        # O heap define a prioridade principal; este método resolve empates.
        if not isinstance(outro, No):
            return NotImplemented
        return (self.g, self.profundidade) < (outro.g, outro.profundidade)


def caminho(no: No) -> tuple[list, list]:
    """Segue os pais e devolve (estados, accoes), da raiz até ao nó recebido."""
    estados, accoes = [], []
    actual = no
    while actual is not None:
        estados.append(actual.estado)
        if actual.pai is not None:
            accoes.append(actual.accao)
        actual = actual.pai
    return estados[::-1], accoes[::-1]
