# Frente 4 — Heurísticas

Esta parte do projecto implementa e testa as heurísticas usadas nas buscas para
o problema de reordenação de contentores.

## Heurísticas

- **`h0`** devolve sempre zero e funciona como referência equivalente à busca
  de custo uniforme quando usada no A*.
- **`h1`** conta os contentores bloqueadores. Um contentor é contado se existir
  um contentor menor abaixo dele na mesma pilha.
- **`h2`** estima pelo menos um movimento para cada bloqueador. Cada movimento
  entre pilhas tem custo mínimo `1.1`, pelo que a implementação actual devolve
  `1.1 * h1`.

As pilhas são percorridas da base para o topo. `h1` e `h2` aceitam um estado com
o atributo `pilhas` ou uma sequência de pilhas.

## Admissibilidade e contraexemplo

Uma heurística admissível não pode exceder o custo óptimo restante `h*`. A
versão anterior de `h2` adicionava penalizações por movimentos adicionais que
não eram sempre obrigatórios. No estado
`((2,), (1, 4, 5), (3,))`, com `proximo=1`, essa versão estimava `4.4`, embora o
custo óptimo restante fosse `3.4`.

A implementação actual remove essas penalizações e usa apenas o custo mínimo
dos movimentos dos bloqueadores. O teste de regressão em
`tests/test_heuristicas.py` compara `h2` com o custo óptimo calculado por UCS
nesse estado. A verificação em estados finitos é evidência experimental, não
substitui uma demonstração para todos os estados possíveis.

Na instância base, os valores iniciais são `h0 = 0`, `h1 = 2` e `h2 = 2.2`.
`h2` é mais conservadora do que a versão anterior e pode não reduzir as
expansões em relação a `h1`; admissibilidade e desempenho são propriedades
distintas.

## Factor de ramificação efectivo

`calcular_b_estrela(N, d)` aproxima por bissecção a solução positiva da equação
`N = b + b² + ... + bᵈ`. O valor `b*` permite resumir o crescimento efectivo da
busca para o número de nós `N` e a profundidade `d` medidos. Não é uma
propriedade fixa da heurística: depende dos resultados da execução.

## Testes

Executar os testes específicos da Frente 4 a partir da raiz do projecto:

```powershell
python -m pytest tests/test_heuristicas.py -q
```

Para executar todos os testes:

```powershell
python -m pytest -q
```
