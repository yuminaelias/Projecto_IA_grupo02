# Frente 1 — Guia de estudo de Paulo Jorge

## 1. Objectivo da Frente 1

Representar o terminal P2 e garantir que cada transição respeita as regras oficiais.
Esta frente fornece a base para as buscas; não procura soluções.

## 2. Ficheiros implementados

| Ficheiro | Função |
|---|---|
| `problema.py` | Interface comum, nós e reconstrução do caminho |
| `dominio.py` | Estado, validação inicial e regras P2 |
| `instancias/base.json` | Instância oficial com 10 contentores |
| `tests/test_dominio.py` | Testes obrigatórios e complementares |
| `requirements-dev.txt`, `.gitignore` | Dependências de testes e exclusões do Git |

## 3. Principais classes e funções

**Problema** é abstracta: define exactamente seis operações, deixando a implementação
ao domínio. Não se pode instanciar directamente.

**ProblemaContentores** concretiza as regras P2. O construtor valida dimensões,
alturas, numeração única de 1 a N, classificações, peso e tomadas. Os identificadores
são inteiros, sem booleanos ou decimais. Entradas inválidas produzem `ValueError`.

**EstadoContentores** guarda `pilhas` e `proximo`. Cada pilha vai da base ao topo.
As listas recebidas são copiadas para tuplos; `frozen=True` impede reatribuir campos.
Com os identificadores inteiros do contrato, o estado é imutável e hashable: pode
entrar num conjunto de estados visitados. Os conjuntos fixos `pesados` e
`refrigerados` ficam no problema como `frozenset`.

**accoes(s)** considera apenas topos não vazios. Permite levantar o próximo contentor
esperado ou mover para outra pilha com espaço. Refrigerados só vão para índices
0 e 1; pesados só vão para pilhas vazias ou sobre pesados. Leves podem ficar sobre
pesados. Não força o levantamento quando existem movimentos legais.

**resultado(s, a)** rejeita acções ilegais com `ValueError` e cria um novo estado,
preservando o anterior. Levantar incrementa `proximo`; mover mantém esse valor.
**custo(s, a, s2)** confirma a transição: levantar custa 0.0, mover custa
`1.0 + 0.1 * abs(i-j)`. Os índices internos começam em zero.

**e_objectivo(s)** exige pilhas vazias e `proximo == N + 1`. Na base, N = 10,
logo o identificador esperado no final é 11.

**No** guarda estado, pai, acção de chegada, custo acumulado `g` e profundidade.
A busca preenche esses valores. `__lt__` desempata por `(g, profundidade)` sem
comparar estados. **caminho(no)** segue os pais e devolve `(estados, accoes)` da raiz
até ao nó: há mais um estado do que acções.

## 4. Exemplo de movimentação de contentores

```python
from dominio import ProblemaContentores
p = ProblemaContentores(2, 2, [[1, 2], []])
s0 = p.estado_inicial()
s1 = p.resultado(s0, ("mover", 0, 1))
assert s0.pilhas == ((1, 2), ())  # original preservado
assert s1.pilhas == ((1,), (2,))
assert p.custo(s0, ("mover", 0, 1), s1) == 1.1
s2 = p.resultado(s1, ("levantar", 0))
s3 = p.resultado(s2, ("levantar", 1))
assert p.e_objectivo(s3)
```

O contentor 2 bloqueava o 1. Movemos 2 e levantamos 1 e 2 pela ordem exigida.

## 5. Testes realizados

Mantiveram-se os três testes obrigatórios: sucessores, pesos e refrigeração.
As verificações anteriores de levantamento, objectivo, caminho, heap e pilhas cheias
continuam presentes num teste separado. Acrescentaram-se entradas iniciais inválidas,
acções malformadas, imutabilidade e contrato abstracto exacto. As parametrizações
apresentam cada entrada inválida como um caso independente.

```powershell
python -m pytest tests/test_dominio.py -q
```

O guia da equipa apresenta a preparação do ambiente. Passar estes testes confirma
apenas a F1; não confirma buscas, heurísticas ou o projecto completo.

## 6. Pontos de integração com os colegas

F2/F3 devem usar a interface sem alterar pilhas directamente. Devem preencher `g`
e `profundidade`. Para A*, menor h deve aparecer na chave do heap antes do nó;
um contador permite estabilizar empates completos.

F4 deverá ligar as heurísticas: `heuristica` ainda lança `NotImplementedError`,
inclusive para h0. O guia apresenta uma ligação por subclasse sem alterar o domínio.
F5 pode carregar o JSON e usar `ProblemaContentores(**dados)`.

O enunciado, o guião e o Capítulo 3 fornecido são coerentes nas regras usadas.
Não fixam completamente o retorno de `caminho`, o construtor ou a ligação às heurísticas;
as convenções adoptadas devem ser validadas pela equipa. Os dados oficiais e o
relatório não foram alterados. Não se calcularam soluções nem resultados experimentais.

Ver [GUIA_INTEGRACAO_GRUPO02.md](GUIA_INTEGRACAO_GRUPO02.md) para os contratos da equipa.
