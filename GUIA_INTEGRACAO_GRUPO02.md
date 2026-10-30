# Guia de integração — Grupo 02 · IA I

## PARTE 1 — O que estamos a construir?

No P2, reorganizamos contentores no Porto de Maputo para os levantar por ordem numérica.
Só se movimenta o topo de cada pilha, respeitando altura, peso e refrigeração.
As buscas procurarão sequências legais e permitirão comparar custos e esforço de procura.
O domínio define as regras; os algoritmos escolhem a ordem de exploração.

## PARTE 2 — Estrutura do projecto

`[existe]` indica ficheiros verificados; `[previsto]` indica trabalho pendente.

```text
projecto_ia_grupo02/
├── problema.py                     [existe] interface, No, caminho
├── dominio.py                      [existe] regras P2 e estado
├── instancias/base.json            [existe] dados oficiais
├── tests/
│   ├── test_dominio.py             [existe] F1
│   ├── test_nao_informadas.py       [previsto] F2
│   ├── test_informadas.py           [previsto] F3
│   ├── test_heuristicas.py          [previsto] F4
│   └── test_gerador.py              [previsto] F5
├── buscas.py                       [previsto] F2 e F3
├── heuristicas.py                  [previsto] F4
├── gerador.py                      [previsto] F5
├── experiencias.py                 [previsto] F5
├── main.py                         [previsto] F5
├── README.md                       [previsto] F5
├── FRENTE1.md                      [existe] estudo da F1
├── GUIA_INTEGRACAO_GRUPO02.md       [existe] contratos da equipa
├── requirements-dev.txt            [existe] pytest
└── .gitignore                      [existe] exclusões locais
```

## PARTE 3 — O que já está feito?

A F1 permite carregar a base, gerar acções legais, obter sucessores, calcular custos
e reconhecer o objectivo. Inclui validação inicial, estados imutáveis e hashable,
nós e reconstrução do caminho. Os testes cobrem sucessores, pesos, refrigeração,
capacidade, levantamento, objectivo, imutabilidade, entradas inválidas e interface.

As buscas e o módulo de heurísticas ainda não existem. `heuristica(s, nome)` lança
`NotImplementedError`. As buscas não informadas podem utilizar o domínio;
as informadas dependem da F4. Os testes disponíveis verificam apenas a F1.

Validação desta revisão: **33 casos aprovados** na F1 (0,17 s) e **33 aprovados**
na execução de todos os testes disponíveis (0,12 s), com Python 3.13.

## PARTE 4 — Responsabilidades dos cinco membros

| Frente | Responsável | O que deve implementar | Ficheiros principais |
|---|---|---|---|
| F1 | Matola, Paulo Jorge | Arquitectura base, domínio, testes; Cap. 3 | `problema.py`, `dominio.py`, `instancias/base.json`, `tests/test_dominio.py` |
| F2 | Cossa, Yúmina Elias | BFS, DFS, IDS, UCS; arquitectura e estruturas; testes; Cap. 2.1–2.2, 5.1–5.2 | `buscas.py`, `tests/test_nao_informadas.py` |
| F3 | Kimemia Júnior, Peter Njau | Gulosa, A*, IDA*; testes; comparação A*/IDA*; Cap. 2.3–2.5, 5.3, 6.4 | `buscas.py`, `tests/test_informadas.py` |
| F4 | Caravela, Rosário Pompílio | h0/h1/h2, provas de admissibilidade/consistência, factor b*, testes; Cap. 4 | `heuristicas.py`, `tests/test_heuristicas.py` |
| F5 | Manuel, Modesta Cipriano | Gerador, experiências, gráficos, interface, README; testes; Cap. 1, 5.4–5.6, 6.1–6.3, 7–8 e anexos | `gerador.py`, `experiencias.py`, `main.py`, `README.md`, `tests/test_gerador.py` |

## PARTE 5 — Como os módulos comunicam?

`Problema → ProblemaContentores → Algoritmos de Busca → Heurísticas → Resultados`

O domínio concretiza `Problema`; as buscas consultam o domínio e, quando necessário,
pedem estimativas à F4. Depois produzem resultados para a interface e experiências.
As heurísticas não substituem as regras. Não alterar directamente as pilhas.

| Assinatura comum | Contrato |
|---|---|
| `estado_inicial()` | Devolve `EstadoContentores` |
| `accoes(s)` | Lista de tuplos legais |
| `resultado(s, a)` | Novo estado; `ValueError` para acção inválida |
| `custo(s, a, s2)` | Custo float; valida a transição |
| `e_objectivo(s)` | Booleano |
| `heuristica(s, nome)` | Estimativa a ligar pela F4 |

Estado: `EstadoContentores(pilhas: tuple[tuple[int, ...], ...], proximo: int)`.
Pilhas da base para o topo; índices internos de 0 a S−1; interface exibe 1 a S.
Acções: `("levantar", i)` e `("mover", i, j)`. Levantar custa 0; mover custa
`1 + 0.1 * abs(i-j)`. Os parâmetros fixos ficam no problema, não no estado.

```python
import json
from pathlib import Path
from dominio import ProblemaContentores
from problema import No, caminho

dados = json.loads(Path("instancias/base.json").read_text(encoding="utf-8"))
p = ProblemaContentores(**dados)
s = p.estado_inicial()
a = p.accoes(s)[0]
s2 = p.resultado(s, a)
c = p.custo(s, a, s2)
atingido = p.e_objectivo(s2)
raiz = No(s)
filho = No(s2, raiz, a, raiz.g + c, raiz.profundidade + 1)
estados, accoes = caminho(filho)
```

`No(estado, pai=None, accao=None, g=0.0, profundidade=0)` guarda a acção de chegada.
`caminho` inclui a raiz nos estados, sem acção fictícia inicial. O heap usa a chave
do algoritmo; `No.__lt__` apenas desempata por `(g, profundidade)`. Para A*, usar
menor h antes do nó na chave; um contador estabiliza empates completos.

O guião exige uma dataclass `ResultadoBusca`, a definir por F2/F3, com estes campos:

```text
algoritmo: str, heuristica: str, resolvido: bool, custo: float,
comprimento: int, acoes: list, nos_expandidos: int, nos_gerados: int,
nos_reexpandidos: int, max_fronteira: int, tempo_s: float,
memoria_mb: float, status: str
```

`status`: `"ok"`, `"sem_solucao"`, `"falhou (tempo)"` ou `"falhou (memoria)"`.
O campo oficial `acoes` tem um c; o método `accoes` e `No.accao` mantêm dois.

## PARTE 6 — Como cada colega deve integrar a sua parte?

1. Trabalhar nos ficheiros atribuídos e respeitar assinaturas e estruturas.
2. Coordenar alterações em ficheiros de outros membros e comunicar incompatibilidades.
3. Escrever os testes da frente e executar também os testes disponíveis da equipa.
4. Fazer commits pequenos com mensagens claras, por exemplo `F2: adicionar UCS`.
5. Validar a integração com a F1 antes de dar a tarefa por concluída.

**F2 e F3:** acordar assinaturas e um único local para `ResultadoBusca` antes de editar
`buscas.py`. Trabalhar em ramos Git separados, actualizar a partir do ramo comum e
integrar uma alteração de cada vez. Resolver conflitos em conjunto; não substituir
o ficheiro inteiro pela cópia local. Executar os testes das duas frentes após a junção.

**F4:** não é necessária alteração adicional na F1. Uma subclasse pode ligar as
funções do futuro `heuristicas.py`, mantendo `heuristica(s, nome)`:

```python
# Proposta para a F4; estas funções ainda não existem.
from dominio import ProblemaContentores
from heuristicas import h0, h1, h2

class ProblemaComHeuristicas(ProblemaContentores):
    def heuristica(self, s, nome):
        funcoes = {"h0": h0, "h1": h1, "h2": h2}
        if nome not in funcoes:
            raise ValueError(f"Heurística desconhecida: {nome}")
        return funcoes[nome](s, self)
```

`h(s, problema)` é uma proposta a acordar com F4, permitindo consultar pesados e
refrigerados. Não é uma exigência oficial nem código já implementado.
F3/F5 instanciarão a subclasse para buscas informadas. F5 mantém o formato de
`base.json` no carregamento; a semente oficial do futuro gerador é **202602**.

Os documentos não fixam o retorno exacto de `caminho`, o construtor ou a ligação
às heurísticas. As convenções aqui documentadas são decisões de integração a
validar pela equipa, sem acrescentar regras ao P2.

## PARTE 7 — Como executar e testar?

No PowerShell do Windows 10, na raiz do projecto, com Python 3.10+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests/test_dominio.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Não é necessário activar o ambiente. A última linha executa todos os testes disponíveis.
Para integrar, confirmar testes sem falhas, contratos respeitados, base preservada e
ausência de alterações inesperadas nos ficheiros dos colegas. As buscas informadas
só estarão prontas após a ligação e os testes da F4.
