"""Modelação do P2: pilhas representadas da base para o topo."""

from dataclasses import dataclass
from problema import Problema


@dataclass(frozen=True)
class EstadoContentores:
    pilhas: tuple[tuple[int, ...], ...]
    proximo: int

    def __post_init__(self):
        # Também protege estados construídos directamente a partir de listas.
        object.__setattr__(self, "pilhas", tuple(tuple(p) for p in self.pilhas))


class ProblemaContentores(Problema):
    def __init__(self, S, H, pilhas, pesados=(), refrigerados=()):
        """Recebe os parâmetros da instância; a numeração inicial deve ser 1..N."""
        if type(S) is not int or type(H) is not int or S < 1 or H < 1:
            raise ValueError("S e H devem ser inteiros positivos.")
        self.S, self.H = S, H
        try:
            pesados, refrigerados = tuple(pesados), tuple(refrigerados)
            pilhas = tuple(tuple(pilha) for pilha in pilhas)
        except TypeError as erro:
            raise ValueError("Pilhas e classificações devem ser colecções válidas.") from erro
        if any(type(c) is not int for c in pesados + refrigerados):
            raise ValueError("As classificações devem conter identificadores inteiros.")
        self.pesados = frozenset(pesados)
        self.refrigerados = frozenset(refrigerados)
        if len(pilhas) != S or any(len(pilha) > H for pilha in pilhas):
            raise ValueError("Número de pilhas ou altura inválidos.")
        contentores = [c for pilha in pilhas for c in pilha]
        self.total_contentores = len(contentores)
        if (any(type(c) is not int for c in contentores)
                or sorted(contentores) != list(range(1, self.total_contentores + 1))):
            raise ValueError("Os contentores devem ser únicos e numerados de 1 a N.")
        if not (self.pesados | self.refrigerados) <= set(contentores):
            raise ValueError("Classificação de um contentor inexistente.")
        for i, pilha in enumerate(pilhas):
            if i not in (0, 1) and any(c in self.refrigerados for c in pilha):
                raise ValueError("Contentor refrigerado numa pilha sem tomada.")
            for baixo, cima in zip(pilha, pilha[1:]):
                if cima in self.pesados and baixo not in self.pesados:
                    raise ValueError("Contentor pesado sobre um leve.")
        self._inicial = EstadoContentores(pilhas, 1)

    def estado_inicial(self):
        return self._inicial

    def accoes(self, s):
        """Enumera levantamentos e movimentos legais, sem modificar s."""
        accoes = []
        for i, origem in enumerate(s.pilhas):
            if not origem:
                continue
            topo = origem[-1]
            if topo == s.proximo:
                accoes.append(("levantar", i))
            for j, destino in enumerate(s.pilhas):
                if i == j or len(destino) >= self.H:
                    continue
                if topo in self.refrigerados and j not in (0, 1):
                    continue
                if topo in self.pesados and destino and destino[-1] not in self.pesados:
                    continue
                accoes.append(("mover", i, j))
        return accoes

    def resultado(self, s, a):
        """Rejeita acções ilegais e constrói um novo estado imutável."""
        if (not isinstance(a, tuple)
                or any(type(i) is not int for i in a[1:])
                or a not in self.accoes(s)):
            raise ValueError(f"Acção inválida: {a!r}")
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

    def custo(self, s, a, s2):
        """Valida a transição e calcula o custo definido no enunciado."""
        if self.resultado(s, a) != s2:
            raise ValueError("O estado s2 não corresponde à transição indicada.")
        if a[0] == "levantar":
            return 0.0
        return 1.0 + 0.1 * abs(a[1] - a[2])

    def e_objectivo(self, s):
        return (s.proximo == self.total_contentores + 1
                and all(not pilha for pilha in s.pilhas))

    def heuristica(self, s, nome):
        """Ponto de integração da F4; nenhuma heurística é implementada na F1."""
        raise NotImplementedError("A ligação às heurísticas pertence à Frente 4.")
