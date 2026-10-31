# Porto de Maputo — TOS Simulator (Interface Web P2)

**Universidade Eduardo Mondlane (UEM) · Faculdade de Engenharia · Inteligência Artificial I (2026)**  
**Grupo 02 (Laboral)** — Problema P2: *Reordenação de Contentores no Porto de Maputo*

---

## 1. Como iniciar o simulador (100% Offline, Biblioteca Padrão Python 3.10+)

A partir da raiz do repositório `Projecto_IA_grupo02`, execute no terminal (PowerShell ou CMD):

```powershell
python interface_web/servidor.py
```

Em seguida, abra no navegador:

```text
http://127.0.0.1:8000
```

> **Nota**: Não requer qualquer biblioteca externa (`pip install`) para funcionar. O servidor utiliza exclusivamente `http.server` da biblioteca padrão do Python e importa diretamente os módulos oficiais do grupo na raiz (`problema.py`, `dominio.py`, `buscas.py` e `heuristicas.py`).

---

## 2. Funcionalidades das 3 Abas

1. **Simulador de Algoritmos**:
   - Corre qualquer um dos **7 algoritmos de busca** (`BFS`, `DFS`, `IDS`, `UCS`, `Gulosa`, `A*`, `IDA*`) com as heurísticas `h0`, `h1` e `h2`.
   - Anima o **Pórtico RTG-02** e reconstrói todos os estados intermédios passo a passo (`Play / Pausa`, `Início`, `Anterior`, `Seguinte`, `Fim`, velocidade `0,5x / 1x / 2x` e clique direto na lista de ações).
   - Exibe os **13 campos do Contrato Técnico** (`ResultadoBusca`), o fator de ramificação efetivo `b*` e a evolução dos patamares `limite_f` do **IDA\***.

2. **Modo Operador Manual**:
   - Permite operar o pátio manualmente clicando no contentor do topo de qualquer pilha:
     - Pilhas de destino válidas destacam-se a **verde** com o custo exato (`1 + 0,1|i - j|`);
     - Pilhas bloqueadas destacam-se a **vermelho** indicando o motivo exato segundo as 5 regras do domínio (`H`, tomadas elétricas nas Pilhas 1 e 2, pesados sobre leves).
   - Inclui botão **Undo**, **Reiniciar** e **Pedir Dica ao A\* (h2)** em tempo real.
   - Inclui o painel de **Treino de Defesa ao Vivo** (Permitir `R` na Pilha 3, Custo de levantar = `0,5`, Proibir dois `R` juntos).

3. **Laboratório & Gráficos**:
   - Executa ao vivo a bateria comparativa dos algoritmos sobre a instância ativa, apresenta a tabela consolidada exportável para **CSV** e desenha os **3 gráficos SVG**:
     1. Nós expandidos em escala logarítmica ($\log_{10}$);
     2. Fronteira Máxima: A\* $O(b^d)$ vs. IDA\* $O(d)$;
     3. Rácio de qualidade da solução ($C / C^*$).
