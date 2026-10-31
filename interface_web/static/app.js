/**
 * Simulador Visual e Interativo do Terminal de Contentores do Porto de Maputo (P2)
 * Universidade Eduardo Mondlane — Inteligência Artificial I (2026) — Grupo 02 Laboral
 * Ligado diretamente aos módulos reais em Python (`problema.py`, `dominio.py`, `buscas.py`, `heuristicas.py`)
 */

const fmt = (n, decimals = 1) => {
  if (n === null || n === undefined || Number.isNaN(Number(n)) || !Number.isFinite(Number(n))) {
    return "—";
  }
  return Number(n).toFixed(decimals).replace(".", ",");
};

const fmtInt = (n) => {
  if (n === null || n === undefined) return "—";
  return Number(n).toLocaleString("pt-PT");
};

const state = {
  mode: "sim", // 'sim' | 'manual' | 'lab'
  instances: {},
  currentInstanceId: "base",
  instanceConfig: {
    id: "base",
    nome: "Base Oficial · S4 H4 N10",
    S: 4,
    H: 4,
    pesados: [5, 7, 8, 9],
    refrigerados: [2, 5],
    pilhas: [[8, 2, 10], [5, 1, 6], [9, 4], [7, 3]],
  },
  algo: "A*",
  heuristic: "h2",
  mods: {
    reefer3: false,
    liftCost: false,
    separateR: false,
  },
  // Simulador
  simResult: null,
  step: 0,
  playing: false,
  speed: 1,
  timerId: null,
  // Modo Operador Manual
  manualStacks: [],
  manualProximo: 1,
  manualCost: 0.0,
  manualSelectedStack: null,
  manualHistory: [],
  manualActions: [],
  manualStateInfo: null,
  optimumReferenceCost: 4.8,
  // Laboratório
  labResults: [],
  labOptimum: 4.8,
  activeChart: "expanded",
};

function boxLabel(id) {
  const isR = state.instanceConfig.refrigerados.includes(id);
  const isP = state.instanceConfig.pesados.includes(id);
  return `${id}${isR ? "R" : ""}${isP ? "P" : ""}`;
}

function totalContainers() {
  const all = state.instanceConfig.pilhas.flat();
  return all.length ? Math.max(...all) : 10;
}

// ============================================================================
// COMUNICAÇÃO COM O BACKEND PYTHON (`servidor.py`)
// ============================================================================

async function apiGet(url) {
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || `Erro HTTP ${res.status}`);
  }
  return res.json();
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.erro || `Erro HTTP ${res.status}`);
  }
  return data;
}

async function loadInstances() {
  try {
    const data = await apiGet("/api/instancias");
    if (data.instancias) {
      data.instancias.forEach((inst) => {
        state.instances[inst.id] = inst;
      });
      if (state.instances.base) {
        state.instanceConfig = structuredClone(state.instances.base);
      }
    }
  } catch (err) {
    console.error("Erro ao carregar instâncias:", err);
  }
}

async function runSimulation(autoPlay = false) {
  stopPlayback();
  const btnLabel = document.getElementById("btn-solve-label");
  if (btnLabel) btnLabel.textContent = "A calcular no motor Python...";

  try {
    const cfg = state.instanceConfig;
    const res = await apiPost("/api/resolver", {
      S: cfg.S,
      H: cfg.H,
      pilhas: cfg.pilhas,
      pesados: cfg.pesados,
      refrigerados: cfg.refrigerados,
      proximo: 1,
      algoritmo: state.algo,
      heuristica: state.heuristic,
      limite_profundidade: 45,
      limite_tempo_s: 15.0,
      mods: state.mods,
    });

    state.simResult = res;
    state.step = 0;

    if (
      res.resolvido &&
      ["UCS", "A*", "IDA*"].includes(state.algo) &&
      !state.mods.reefer3 &&
      !state.mods.liftCost &&
      !state.mods.separateR
    ) {
      state.optimumReferenceCost = res.custo;
    }

    renderAll();
    if (autoPlay && res.resolvido && res.passos.length > 1) {
      startPlayback();
    }
  } catch (err) {
    alert(`Erro ao executar algoritmo: ${err.message}`);
  } finally {
    if (btnLabel) btnLabel.textContent = "Resolver e simular solução";
  }
}

async function refreshManualStateInfo() {
  try {
    const cfg = state.instanceConfig;
    const info = await apiPost("/api/estado", {
      S: cfg.S,
      H: cfg.H,
      pilhas: state.manualStacks,
      pesados: cfg.pesados,
      refrigerados: cfg.refrigerados,
      proximo: state.manualProximo,
      mods: state.mods,
    });
    state.manualStateInfo = info;
    renderAll();
  } catch (err) {
    console.error("Erro ao validar estado manual:", err);
  }
}

function resetManualMode() {
  const cfg = state.instanceConfig;
  state.manualStacks = cfg.pilhas.map((p) => [...p]);
  state.manualProximo = 1;
  state.manualCost = 0.0;
  state.manualSelectedStack = null;
  state.manualHistory = [];
  state.manualActions = [];
  const hintBox = document.getElementById("manual-hint-box");
  if (hintBox) hintBox.classList.add("hidden");
  refreshManualStateInfo();
}

// ============================================================================
// REPRODUÇÃO PASSO A PASSO (PLAYBACK)
// ============================================================================

function startPlayback() {
  if (!state.simResult || !state.simResult.passos) return;
  const maxStep = state.simResult.passos.length - 1;
  if (state.step >= maxStep) {
    state.step = 0;
  }
  state.playing = true;
  renderPlaybackControls();
  scheduleNextTick();
}

function stopPlayback() {
  state.playing = false;
  if (state.timerId) {
    clearInterval(state.timerId);
    state.timerId = null;
  }
  renderPlaybackControls();
}

function scheduleNextTick() {
  if (state.timerId) clearInterval(state.timerId);
  if (!state.playing) return;
  const intervalMs = Math.round(850 / state.speed);
  state.timerId = setInterval(() => {
    if (!state.simResult || state.mode !== "sim") {
      stopPlayback();
      return;
    }
    const maxStep = state.simResult.passos.length - 1;
    if (state.step >= maxStep) {
      stopPlayback();
      return;
    }
    state.step += 1;
    renderAll();
  }, intervalMs);
}

// ============================================================================
// OPERADOR MANUAL — INTERAÇÃO COM AS PILHAS
// ============================================================================

function getBlockReason(fromIdx, toIdx) {
  if (state.manualStateInfo && state.manualStateInfo.motivos_bloqueio) {
    const m = state.manualStateInfo.motivos_bloqueio[String(fromIdx)];
    if (m && m[String(toIdx)] !== undefined) {
      return m[String(toIdx)];
    }
  }
  // Fallback síncrono imediato
  const cfg = state.instanceConfig;
  const orig = state.manualStacks[fromIdx];
  const dest = state.manualStacks[toIdx];
  if (!orig || !orig.length) return "Pilha de origem vazia";
  const box = orig[orig.length - 1];
  if (dest.length >= cfg.H) return `Altura máxima H = ${cfg.H} atingida na Pilha ${toIdx + 1}`;
  const allowedReefer = state.mods.reefer3 ? [0, 1, 2] : [0, 1];
  if (cfg.refrigerados.includes(box) && !allowedReefer.includes(toIdx)) {
    return `Contentor ${box}R exige tomada elétrica nas Pilhas ${state.mods.reefer3 ? "1, 2 ou 3" : "1 ou 2"}`;
  }
  if (cfg.pesados.includes(box) && dest.length > 0 && !cfg.pesados.includes(dest[dest.length - 1])) {
    return `Contentor pesado #${box}P não pode ficar sobre leve #${dest[dest.length - 1]}`;
  }
  if (state.mods.separateR && cfg.refrigerados.includes(box) && dest.some((c) => cfg.refrigerados.includes(c))) {
    return "Restrição de defesa ativa: dois refrigerados (R) não podem ficar juntos";
  }
  return null;
}

function handleStackClick(stackIdx) {
  if (state.mode !== "manual") return;
  const hintBox = document.getElementById("manual-hint-box");
  if (hintBox) hintBox.classList.add("hidden");

  if (state.manualSelectedStack === null) {
    if (state.manualStacks[stackIdx].length > 0) {
      state.manualSelectedStack = stackIdx;
      renderAll();
    }
    return;
  }

  if (state.manualSelectedStack === stackIdx) {
    state.manualSelectedStack = null;
    renderAll();
    return;
  }

  const fromIdx = state.manualSelectedStack;
  const reason = getBlockReason(fromIdx, stackIdx);
  if (reason) {
    const msgEl = document.getElementById("selection-message");
    if (msgEl) {
      msgEl.classList.remove("hidden");
      msgEl.innerHTML = `<span style="color:#dc2626;font-weight:700;">Movimento bloqueado:</span> ${reason}`;
    }
    return;
  }

  // Salva no histórico para Undo
  state.manualHistory.push({
    stacks: state.manualStacks.map((p) => [...p]),
    proximo: state.manualProximo,
    cost: state.manualCost,
    actions: [...state.manualActions],
  });

  const box = state.manualStacks[fromIdx].pop();
  state.manualStacks[stackIdx].push(box);
  const moveCost = Number((1.0 + 0.1 * Math.abs(fromIdx - stackIdx)).toFixed(4));
  state.manualCost = Number((state.manualCost + moveCost).toFixed(4));

  state.manualActions.push({
    ordem: state.manualActions.length + 1,
    tipo: "mover",
    origem: fromIdx,
    destino: stackIdx,
    contentor: box,
    custo: moveCost,
    g_acumulado: state.manualCost,
  });

  state.manualSelectedStack = null;
  refreshManualStateInfo();
}

function handleManualLift(stackIdx) {
  if (state.mode !== "manual") return;
  const pilha = state.manualStacks[stackIdx];
  if (!pilha || !pilha.length) return;
  const topo = pilha[pilha.length - 1];
  if (topo !== state.manualProximo) return;

  state.manualHistory.push({
    stacks: state.manualStacks.map((p) => [...p]),
    proximo: state.manualProximo,
    cost: state.manualCost,
    actions: [...state.manualActions],
  });

  state.manualStacks[stackIdx].pop();
  const liftCost = state.mods.liftCost ? 0.5 : 0.0;
  state.manualCost = Number((state.manualCost + liftCost).toFixed(4));
  state.manualProximo += 1;

  state.manualActions.push({
    ordem: state.manualActions.length + 1,
    tipo: "levantar",
    origem: stackIdx,
    destino: null,
    contentor: topo,
    custo: liftCost,
    g_acumulado: state.manualCost,
  });

  state.manualSelectedStack = null;
  refreshManualStateInfo();
}

function handleManualUndo() {
  if (!state.manualHistory.length) return;
  const prev = state.manualHistory.pop();
  state.manualStacks = prev.stacks;
  state.manualProximo = prev.proximo;
  state.manualCost = prev.cost;
  state.manualActions = prev.actions;
  state.manualSelectedStack = null;
  refreshManualStateInfo();
}

async function handleManualHint() {
  const hintBox = document.getElementById("manual-hint-box");
  if (!hintBox) return;
  hintBox.classList.remove("hidden");
  hintBox.textContent = "A consultar o A* (h2) para o estado actual...";

  try {
    const cfg = state.instanceConfig;
    const res = await apiPost("/api/resolver", {
      S: cfg.S,
      H: cfg.H,
      pilhas: state.manualStacks,
      pesados: cfg.pesados,
      refrigerados: cfg.refrigerados,
      proximo: state.manualProximo,
      algoritmo: "A*",
      heuristica: "h2",
      limite_tempo_s: 10.0,
      mods: state.mods,
    });

    if (!res.resolvido) {
      hintBox.innerHTML = `<strong>Sem solução a partir deste estado!</strong> Use o botão <b>Undo</b> para retroceder.`;
      return;
    }
    if (res.acoes.length === 0) {
      hintBox.innerHTML = `<strong>Parabéns!</strong> Todos os contentores foram levantados com sucesso!`;
      return;
    }
    const next = res.acoes[0];
    const acaoDesc =
      next.tipo === "levantar"
        ? `<b>levantar(Pilha ${next.origem + 1})</b> — retirar Contentor <b>#${boxLabel(next.contentor)}</b> (custo +${fmt(next.custo)})`
        : `<b>mover(Pilha ${next.origem + 1} → Pilha ${next.destino + 1})</b> — deslocar Contentor <b>#${boxLabel(next.contentor)}</b> (custo +${fmt(next.custo)})`;

    hintBox.innerHTML = `<strong>Dica Óptima A* (h2):</strong> Próximo passo: ${acaoDesc}.<br/><small>Faltam ${res.comprimento} acções (custo mínimo restante: <b>+${fmt(res.custo)}</b> · total previsto: <b>${fmt(state.manualCost + res.custo)}</b>).</small>`;
  } catch (err) {
    hintBox.textContent = `Erro ao pedir dica: ${err.message}`;
  }
}

// ============================================================================
// RENDERIZAÇÃO DA INTERFACE
// ============================================================================

function renderAll() {
  const isLab = state.mode === "lab";
  document.getElementById("workspace-view").classList.toggle("hidden", isLab);
  document.getElementById("lab-view").classList.toggle("hidden", !isLab);

  document.querySelectorAll(".mode-tabs button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === state.mode);
  });

  if (isLab) {
    renderLabView();
    return;
  }

  const isManual = state.mode === "manual";
  document.getElementById("left-sim-panel").classList.toggle("hidden", isManual);
  document.getElementById("left-manual-panel").classList.toggle("hidden", !isManual);
  document.getElementById("playback-bar").classList.toggle("disabled", isManual);

  renderLeftPanel();
  renderYard();
  renderPlaybackControls();
  renderRightPanel();
}

function renderLeftPanel() {
  // Botões de algoritmo
  document.querySelectorAll("#algo-grid button").forEach((btn) => {
    btn.classList.toggle("selected", btn.dataset.algo === state.algo);
  });

  // Botões de heurística
  const usesH = ["Gulosa", "A*", "IDA*"].includes(state.algo);
  document.querySelectorAll("#heuristic-grid button").forEach((btn) => {
    const h = btn.dataset.h;
    btn.classList.toggle("selected", h === state.heuristic);
    const dis = !usesH || (state.algo === "Gulosa" && h === "h0");
    btn.classList.toggle("disabled-h", dis);
  });

  // Regras no modo manual
  document.getElementById("rule-h-text").textContent = `H = ${state.instanceConfig.H} respeitada`;
  document.getElementById("rule-lift-text").textContent = `Custo ${state.mods.liftCost ? "0,5" : "0,0"} · apenas próximo`;
  document.getElementById("rule-reefer-text").textContent = state.mods.reefer3
    ? "Pilhas 1, 2 e 3 (mod. defesa)"
    : "Só Pilhas 1 e 2 (tomadas)";

  document.getElementById("manual-cost-display").textContent = fmt(state.manualCost);
  document.getElementById("manual-optimum-display").textContent = fmt(state.optimumReferenceCost);

  // Inspector Heurístico
  const stepData = getCurrentStepData();
  document.getElementById("inspector-step-badge").textContent = `ESTADO S${String(stepData.passo).padStart(2, "0")}`;
  document.getElementById("insp-g").textContent = fmt(stepData.g);
  document.getElementById("insp-h1").textContent = fmt(stepData.h1);
  document.getElementById("insp-h2").textContent = fmt(stepData.h2);
  document.getElementById("insp-f").textContent = fmt(stepData.f);
  document.getElementById("insp-formula").textContent =
    state.algo === "Gulosa"
      ? `f(s) = ${state.heuristic}(s)`
      : `f(s) = g(s) + ${state.heuristic}(s)`;

  // Nota de solução
  const noteEl = document.getElementById("solver-note-text");
  if (state.simResult) {
    if (state.simResult.resolvido) {
      noteEl.textContent = `${state.simResult.algoritmo} (${state.simResult.heuristica}) · custo ${fmt(state.simResult.custo)} em ${state.simResult.comprimento} acções`;
    } else {
      noteEl.textContent = `Sem solução (${state.simResult.status})`;
    }
  }
}

function getCurrentStepData() {
  if (state.mode === "manual") {
    const h = state.manualStateInfo?.heuristicas || { h0: 0, h1: 0, h2: 0 };
    const hSel = state.heuristic === "h0" ? h.h0 : state.heuristic === "h1" ? h.h1 : h.h2;
    return {
      passo: state.manualActions.length,
      pilhas: state.manualStacks,
      proximo: state.manualProximo,
      accao: state.manualActions.at(-1) || null,
      g: state.manualCost,
      h0: h.h0,
      h1: h.h1,
      h2: h.h2,
      f: state.manualCost + hSel,
    };
  }
  if (state.simResult && state.simResult.passos && state.simResult.passos[state.step]) {
    return state.simResult.passos[state.step];
  }
  return {
    passo: 0,
    pilhas: state.instanceConfig.pilhas,
    proximo: 1,
    accao: null,
    g: 0,
    h0: 0,
    h1: 2.0,
    h2: 4.4,
    f: 4.4,
  };
}

function renderYard() {
  const cfg = state.instanceConfig;
  const stepData = getCurrentStepData();
  const maxN = totalContainers();
  const totalSteps =
    state.mode === "manual"
      ? state.manualActions.length
      : state.simResult?.comprimento || 0;

  // Ribbon superior
  const doneAll = stepData.proximo > maxN;
  document.getElementById("ribbon-target").textContent = doneAll
    ? "Concluído ✓"
    : `Contentor #${stepData.proximo}`;
  document.getElementById("ribbon-step").textContent =
    state.mode === "manual"
      ? `${state.manualActions.length} acções`
      : `${stepData.passo} / ${totalSteps}`;
  document.getElementById("ribbon-cost").textContent = fmt(stepData.g);

  const act = stepData.accao;
  const lastActEl = document.getElementById("ribbon-last-action");
  const lastCostEl = document.getElementById("ribbon-last-cost");
  const craneBadge = document.getElementById("crane-action-badge");

  if (act) {
    const desc =
      act.tipo === "mover"
        ? `mover(${act.origem + 1} → ${act.destino + 1})`
        : `levantar(${act.origem + 1})`;
    lastActEl.textContent = `${desc} · #${boxLabel(act.contentor)}`;
    lastCostEl.textContent = `Custo +${fmt(act.custo)} · g(n) = ${fmt(stepData.g)}`;
    craneBadge.textContent = desc.toUpperCase();
  } else {
    lastActEl.textContent = "— sistema pronto —";
    lastCostEl.textContent = "Estado inicial S00";
    craneBadge.textContent = "PRONTO";
  }

  document.getElementById("yard-instance-title").textContent = `${cfg.nome} · Pátio & Pórtico RTG (S=${cfg.S}, H=${cfg.H})`;

  // Posição do Trolley do Pórtico RTG
  const activeStackIdx =
    state.mode === "manual" && state.manualSelectedStack !== null
      ? state.manualSelectedStack
      : act
      ? act.destino !== null && act.destino !== undefined
        ? act.destino
        : act.origem
      : 0;

  const pct = ((activeStackIdx + 0.5) / cfg.S) * 100;
  const trolleyEl = document.getElementById("crane-trolley");
  if (trolleyEl) {
    trolleyEl.style.left = `${Math.min(92, Math.max(8, pct))}%`;
  }

  // Régua de custo de deslocação
  const rulerEl = document.getElementById("distance-ruler");
  if (rulerEl) {
    rulerEl.innerHTML = Array.from({ length: cfg.S }, (_, idx) => {
      const dist = Math.abs(activeStackIdx - idx);
      const c = dist === 0 ? "origem" : `mover: +${fmt(1 + 0.1 * dist)}`;
      return `<span>P${idx + 1} (${c})</span>`;
    }).join("");
  }

  // Renderização das Pilhas
  const stacksContainer = document.getElementById("stacks-container");
  stacksContainer.style.setProperty("--num-stacks", cfg.S);
  stacksContainer.innerHTML = "";

  const isManual = state.mode === "manual";
  const selIdx = state.manualSelectedStack;

  stepData.pilhas.forEach((pilha, i) => {
    const col = document.createElement("div");
    col.className = "stack-column";

    let blockReason = null;
    let isValidDest = false;
    if (isManual && selIdx !== null && selIdx !== i) {
      blockReason = getBlockReason(selIdx, i);
      isValidDest = !blockReason;
    }

    if (isManual && selIdx === i) col.classList.add("source-selected");
    if (isValidDest) col.classList.add("valid-dest");
    if (blockReason) {
      col.classList.add("invalid-dest");
      col.title = blockReason;
    }

    // Indicador no topo da pilha
    const indicator = document.createElement("div");
    indicator.className = "move-indicator";

    const topBox = pilha.length ? pilha[pilha.length - 1] : null;
    const topIsTarget = topBox === stepData.proximo;

    if (isManual && topIsTarget && (selIdx === null || selIdx === i)) {
      const liftBtn = document.createElement("button");
      liftBtn.type = "button";
      liftBtn.className = "lift-btn";
      const lCost = state.mods.liftCost ? "0,5" : "0,0";
      liftBtn.textContent = `▲ Levantar #${topBox} (${lCost})`;
      liftBtn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        handleManualLift(i);
      });
      indicator.appendChild(liftBtn);
    } else if (isValidDest) {
      const costBadge = document.createElement("span");
      costBadge.className = "valid-badge";
      costBadge.textContent = `Mover aqui · +${fmt(1 + 0.1 * Math.abs(selIdx - i))}`;
      indicator.appendChild(costBadge);
    } else if (blockReason) {
      const invBadge = document.createElement("span");
      invBadge.className = "invalid-badge";
      invBadge.textContent = "✕ BLOQUEADO";
      indicator.appendChild(invBadge);
    }

    col.appendChild(indicator);

    // Slots de H-1 até 0 (de cima para baixo visualmente)
    const slotsWrap = document.createElement("div");
    slotsWrap.className = "slots";
    for (let level = cfg.H - 1; level >= 0; level--) {
      const slot = document.createElement("div");
      slot.className = "slot";
      const boxId = pilha[level];
      if (boxId !== undefined) {
        const isR = cfg.refrigerados.includes(boxId);
        const isP = cfg.pesados.includes(boxId);
        const isTarget = boxId === stepData.proximo;
        const isTop = level === pilha.length - 1;

        const boxEl = document.createElement("div");
        boxEl.className = `container ${isR ? "reefer" : ""} ${isP ? "heavy" : ""} ${isTarget ? "target" : ""} ${isTop ? "top" : ""}`;
        boxEl.innerHTML = `
          <div class="container-ribs"></div>
          <div class="box-id">
            ${isR ? '<span>❄</span>' : ""}
            <b>${boxLabel(boxId)}</b>
          </div>
          <div class="badges-right">
            ${isTarget ? '<span class="target-badge">ALVO</span>' : ""}
            ${isP ? '<span class="weight-badge">PESADO</span>' : ""}
          </div>
        `;
        slot.appendChild(boxEl);
      }
      slotsWrap.appendChild(slot);
    }
    col.appendChild(slotsWrap);

    // Base da Pilha
    const hasPower = i === 0 || i === 1 || (state.mods.reefer3 && i === 2);
    const baseEl = document.createElement("div");
    baseEl.className = `stack-base ${hasPower ? "powered" : ""}`;
    baseEl.innerHTML = `
      <strong>PILHA ${i + 1}</strong>
      <span>${pilha.length} / ${cfg.H}</span>
      ${hasPower ? '<span class="power-tag">⚡ TOMADA R</span>' : ""}
    `;
    col.appendChild(baseEl);

    col.addEventListener("click", () => handleStackClick(i));
    stacksContainer.appendChild(col);
  });

  // Mensagem de seleção no Modo Manual
  const msgEl = document.getElementById("selection-message");
  if (isManual && selIdx !== null && state.manualStacks[selIdx]?.length) {
    const selBox = state.manualStacks[selIdx].at(-1);
    msgEl.classList.remove("hidden");
    msgEl.innerHTML = `Contentor <b>#${boxLabel(selBox)}</b> seleccionado no topo da <b>Pilha ${selIdx + 1}</b> · clique numa pilha a verde para mover ou passe o rato nas vermelhas para ver o motivo do bloqueio.`;
  } else if (isManual && doneAll) {
    msgEl.classList.remove("hidden");
    msgEl.innerHTML = `🎉 <b>Operação concluída!</b> Todos os contentores foram levantados. O teu custo total foi <b>${fmt(state.manualCost)}</b> (Óptimo de referência: <b>${fmt(state.optimumReferenceCost)}</b>).`;
  } else {
    msgEl.classList.add("hidden");
  }
}

function renderPlaybackControls() {
  const playLabel = document.getElementById("label-play");
  const playIcon = document.getElementById("icon-play");
  if (playLabel) playLabel.textContent = state.playing ? "Pausa" : "Reproduzir";
  if (playIcon) {
    playIcon.innerHTML = state.playing
      ? '<path d="M9 7v10M15 7v10" />'
      : '<path d="m9 7 7 5-7 5z" />';
  }

  const timelineEl = document.getElementById("timeline-steps");
  if (!timelineEl) return;
  timelineEl.innerHTML = "";

  const totalSteps = state.simResult?.passos?.length || 1;
  for (let i = 0; i < totalSteps; i++) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = String(i);
    if (i === state.step) btn.className = "active";
    else if (i < state.step) btn.className = "done";
    btn.addEventListener("click", () => {
      stopPlayback();
      state.step = i;
      renderAll();
    });
    timelineEl.appendChild(btn);
  }
}

function renderRightPanel() {
  const isManual = state.mode === "manual";
  const res = state.simResult;

  if (!isManual && res) {
    document.getElementById("kpi-cost").textContent = res.resolvido ? fmt(res.custo) : "—";
    document.getElementById("kpi-status").textContent = res.status.toUpperCase();
    document.getElementById("kpi-length").textContent = String(res.comprimento);
    document.getElementById("kpi-expanded").textContent = fmtInt(res.nos_expandidos);
    document.getElementById("kpi-expanded-sub").textContent = `${res.algoritmo} (${res.heuristica})`;
    document.getElementById("kpi-generated").textContent = fmtInt(res.nos_gerados);
    document.getElementById("kpi-reexpanded-sub").textContent = `Re-exp.: ${fmtInt(res.nos_reexpandidos)}`;
    document.getElementById("kpi-frontier").textContent = fmtInt(res.max_fronteira);
    document.getElementById("kpi-time").textContent = `${fmt(res.tempo_s, 4)}s`;
    document.getElementById("kpi-memory").textContent = `${fmt(res.memoria_mb, 3)} MB`;
    document.getElementById("kpi-bstar").textContent = `b* = ${fmt(res.b_estrela, 4)}`;
  } else if (isManual) {
    document.getElementById("kpi-cost").textContent = fmt(state.manualCost);
    document.getElementById("kpi-status").textContent = "OPERADOR MANUAL";
    document.getElementById("kpi-length").textContent = String(state.manualActions.length);
  }

  const actions = isManual ? state.manualActions : res?.acoes || [];
  const activeStep = isManual ? state.manualActions.length : state.step;

  document.getElementById("log-count-badge").textContent = `${actions.length} REGISTOS`;
  const logContainer = document.getElementById("action-log");
  logContainer.innerHTML = "";

  if (!actions.length) {
    logContainer.innerHTML = `<div class="empty-log">${
      isManual
        ? "Nenhuma operação manual registada. Seleccione um contentor do topo para começar."
        : "Nenhuma acção disponível."
    }</div>`;
  } else {
    actions.forEach((a, idx) => {
      const stepNum = idx + 1;
      const row = document.createElement("div");
      row.className = `log-row ${stepNum === activeStep ? "active" : ""} ${stepNum < activeStep ? "past" : ""}`;
      const desc =
        a.tipo === "mover"
          ? `mover(${a.origem + 1} → ${a.destino + 1})`
          : `levantar(${a.origem + 1})`;
      row.innerHTML = `
        <span class="log-index">${String(stepNum).padStart(2, "0")}</span>
        <span class="action-type ${a.tipo}">${a.tipo === "mover" ? "MOV" : "LEV"}</span>
        <div>
          <b>${desc}</b>
          <small>Contentor #${boxLabel(a.contentor)}</small>
        </div>
        <div class="log-cost">
          <b>+${fmt(a.custo)}</b>
          <small>g = ${fmt(a.g_acumulado)}</small>
        </div>
      `;
      if (!isManual) {
        row.addEventListener("click", () => {
          stopPlayback();
          state.step = stepNum;
          renderAll();
        });
      }
      logContainer.appendChild(row);
    });
  }

  // Patamares limite_f do IDA*
  const threshBox = document.getElementById("thresholds-box");
  const threshList = document.getElementById("thresholds-list");
  const threshSum = document.getElementById("thresholds-summary");

  if (!isManual && res && res.algoritmo === "IDA*" && res.patamares_f && res.patamares_f.length) {
    threshBox.classList.remove("hidden");
    threshList.innerHTML = res.patamares_f
      .map((t, idx) => `<b>${fmt(t, 2)}${idx < res.patamares_f.length - 1 ? " →" : ""}</b>`)
      .join("");
    threshSum.textContent = `Solução óptima encontrada na ${res.patamares_f.length}.ª iteração (limite_f = ${fmt(res.custo, 2)})`;
  } else {
    threshBox.classList.add("hidden");
  }
}

// ============================================================================
// ABA 3: LABORATÓRIO EXPERIMENTAL & GRÁFICOS SVG
// ============================================================================

async function runLabBenchmark() {
  const btn = document.getElementById("btn-run-benchmark");
  const statusBadge = document.getElementById("lab-status-badge");
  if (btn) btn.textContent = "⏳ A executar os 7 algoritmos...";
  if (statusBadge) statusBadge.textContent = "A EXECUTAR";

  try {
    const cfg = state.instanceConfig;
    const data = await apiPost("/api/comparar", {
      S: cfg.S,
      H: cfg.H,
      pilhas: cfg.pilhas,
      pesados: cfg.pesados,
      refrigerados: cfg.refrigerados,
      limite_tempo_s: 3.0,
    });
    state.labResults = data.resultados || [];
    state.labOptimum = data.custo_optimo || 4.8;
    renderLabView();
  } catch (err) {
    alert(`Erro na bateria experimental: ${err.message}`);
  } finally {
    if (btn) btn.textContent = "▶ Executar Bateria ao Vivo na Instância Activa";
    if (statusBadge) statusBadge.textContent = "VALIDADO";
  }
}

function renderLabView() {
  const cfg = state.instanceConfig;
  document.getElementById("lab-table-subtitle").textContent =
    `Resultados consolidados — ${cfg.nome} (S=${cfg.S}, H=${cfg.H})`;
  document.getElementById("lab-runs-count").textContent = String(state.labResults.length);
  document.getElementById("lab-best-cost").textContent = fmt(state.labOptimum);

  const tbody = document.getElementById("lab-table-body");
  tbody.innerHTML = "";

  state.labResults.forEach((r) => {
    const tr = document.createElement("tr");
    if (r.rotulo === "A* h2" || r.rotulo === "IDA* h2") {
      tr.className = "featured";
    }
    tr.innerHTML = `
      <td>${r.rotulo}</td>
      <td>${r.status}</td>
      <td>${r.resolvido ? fmt(r.custo) : "—"}</td>
      <td>${r.resolvido ? r.comprimento : "—"}</td>
      <td>${fmtInt(r.nos_expandidos)}</td>
      <td>${fmtInt(r.nos_gerados)}</td>
      <td>${fmtInt(r.nos_reexpandidos)}</td>
      <td>${fmtInt(r.max_fronteira)}</td>
      <td>${r.resolvido ? fmt(r.b_estrela, 4) : "—"}</td>
      <td>${fmt(r.tempo_s, 4)}</td>
      <td>${fmt(r.memoria_mb, 3)}</td>
    `;
    tbody.appendChild(tr);
  });

  renderLabCharts();
}

function renderLabCharts() {
  const rows = state.labResults;
  if (!rows.length) return;

  // 1. Gráfico de barras (escala log10): Nós expandidos
  const wrapExp = document.getElementById("svg-chart-expanded");
  if (wrapExp) {
    const items = rows.filter((r) =>
      ["BFS", "UCS", "Gulosa h1", "Gulosa h2", "A* h0", "A* h1", "A* h2", "IDA* h1", "IDA* h2"].includes(r.rotulo)
    );
    wrapExp.innerHTML = buildBarChartSvg(
      items.map((r) => ({
        label: r.rotulo.replace("Gulosa ", "G."),
        value: Math.max(1, r.nos_expandidos),
        display: fmtInt(r.nos_expandidos),
        highlight: r.rotulo.includes("h2"),
      })),
      true
    );
  }

  // 2. Gráfico comparativo A* vs IDA* (Fronteira Máxima vs Re-expansões)
  const wrapMem = document.getElementById("svg-chart-memory");
  if (wrapMem) {
    const items = rows.filter((r) =>
      ["UCS", "A* h1", "A* h2", "IDA* h1", "IDA* h2"].includes(r.rotulo)
    );
    wrapMem.innerHTML = buildBarChartSvg(
      items.map((r) => ({
        label: r.rotulo,
        value: Math.max(1, r.max_fronteira),
        display: `${r.max_fronteira}`,
        highlight: r.rotulo.startsWith("IDA*"),
      })),
      false
    );
  }

  // 3. Gráfico Rácio C / C*
  const wrapRatio = document.getElementById("svg-chart-ratio");
  if (wrapRatio) {
    const items = rows.filter((r) => r.resolvido && r.racio_optimo);
    wrapRatio.innerHTML = buildBarChartSvg(
      items.map((r) => ({
        label: r.rotulo.replace("Gulosa ", "G."),
        value: r.racio_optimo,
        display: fmt(r.racio_optimo, 2),
        highlight: Math.abs(r.racio_optimo - 1.0) < 1e-4,
      })),
      false
    );
  }
}

function buildBarChartSvg(bars, useLogScale = false) {
  if (!bars.length) return "";
  const width = 420;
  const height = 195;
  const padLeft = 36;
  const padRight = 14;
  const padTop = 22;
  const padBottom = 38;
  const plotW = width - padLeft - padRight;
  const plotH = height - padTop - padBottom;

  const vals = bars.map((b) => (useLogScale ? Math.log10(Math.max(1, b.value)) : b.value));
  const maxVal = Math.max(...vals, 1);

  const slotW = plotW / bars.length;
  const barW = Math.min(30, slotW * 0.65);

  const gridLines = [0.25, 0.5, 0.75, 1].map((p) => {
    const y = padTop + plotH * (1 - p);
    return `<line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="#e2e8f0" stroke-dasharray="3,3" />`;
  }).join("");

  const barsSvg = bars.map((b, i) => {
    const v = useLogScale ? Math.log10(Math.max(1, b.value)) : b.value;
    const h = Math.max(6, (v / maxVal) * plotH);
    const x = padLeft + i * slotW + (slotW - barW) / 2;
    const y = padTop + plotH - h;
    const color = b.highlight ? "#0284c7" : "#64748b";
    return `
      <g>
        <rect x="${x}" y="${y}" width="${barW}" height="${h}" rx="3" fill="${color}" />
        <text x="${x + barW / 2}" y="${y - 5}" text-anchor="middle" font-family="monospace" font-size="9.5" font-weight="700" fill="#0f172a">${b.display}</text>
        <text x="${x + barW / 2}" y="${height - 14}" text-anchor="middle" font-size="9" fill="#334155">${b.label}</text>
      </g>
    `;
  }).join("");

  return `
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="195" role="img">
      ${gridLines}
      <line x1="${padLeft}" y1="${padTop}" x2="${padLeft}" y2="${padTop + plotH}" stroke="#94a3b8" />
      <line x1="${padLeft}" y1="${padTop + plotH}" x2="${width - padRight}" y2="${padTop + plotH}" stroke="#94a3b8" />
      ${barsSvg}
    </svg>
  `;
}

function exportCsv() {
  if (!state.labResults.length) return;
  const headers = [
    "algoritmo",
    "heuristica",
    "status",
    "custo",
    "comprimento",
    "nos_expandidos",
    "nos_gerados",
    "nos_reexpandidos",
    "max_fronteira",
    "b_estrela",
    "tempo_s",
    "memoria_mb",
  ];
  const lines = [
    headers.join(","),
    ...state.labResults.map((r) =>
      [
        `"${r.rotulo}"`,
        `"${r.heuristica}"`,
        `"${r.status}"`,
        r.custo ?? "",
        r.comprimento,
        r.nos_expandidos,
        r.nos_gerados,
        r.nos_reexpandidos,
        r.max_fronteira,
        r.b_estrela,
        r.tempo_s,
        r.memoria_mb,
      ].join(",")
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `resultados_porto_maputo_${state.currentInstanceId}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ============================================================================
// REGISTO DE EVENTOS E INICIALIZAÇÃO
// ============================================================================

function setupEvents() {
  // Abas principais
  document.querySelectorAll(".mode-tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      stopPlayback();
      state.mode = btn.dataset.mode;
      if (state.mode === "manual" && !state.manualStacks.length) {
        resetManualMode();
      } else if (state.mode === "lab" && !state.labResults.length) {
        runLabBenchmark();
      } else {
        renderAll();
      }
    });
  });

  // Seletor de instância
  const instSelect = document.getElementById("instance-select");
  instSelect.addEventListener("change", () => {
    const val = instSelect.value;
    if (val === "custom") {
      const dlg = document.getElementById("custom-instance-dialog");
      dlg.showModal();
      return;
    }
    if (state.instances[val]) {
      state.currentInstanceId = val;
      state.instanceConfig = structuredClone(state.instances[val]);
      resetManualMode();
      state.labResults = [];
      runSimulation(false);
    }
  });

  // Botões de Algoritmo
  document.querySelectorAll("#algo-grid button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.algo = btn.dataset.algo;
      if (state.algo === "Gulosa" && state.heuristic === "h0") {
        state.heuristic = "h2";
      }
      runSimulation(false);
    });
  });

  // Botões de Heurística
  document.querySelectorAll("#heuristic-grid button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.heuristic = btn.dataset.h;
      runSimulation(false);
    });
  });

  // Botão Resolver e Simular
  document.getElementById("btn-solve").addEventListener("click", () => {
    runSimulation(true);
  });

  // Controlos de Playback
  document.getElementById("btn-first").addEventListener("click", () => {
    stopPlayback();
    state.step = 0;
    renderAll();
  });
  document.getElementById("btn-prev").addEventListener("click", () => {
    stopPlayback();
    state.step = Math.max(0, state.step - 1);
    renderAll();
  });
  document.getElementById("btn-play").addEventListener("click", () => {
    if (state.playing) stopPlayback();
    else startPlayback();
  });
  document.getElementById("btn-next").addEventListener("click", () => {
    stopPlayback();
    const maxStep = (state.simResult?.passos?.length || 1) - 1;
    state.step = Math.min(maxStep, state.step + 1);
    renderAll();
  });
  document.getElementById("btn-last").addEventListener("click", () => {
    stopPlayback();
    const maxStep = (state.simResult?.passos?.length || 1) - 1;
    state.step = maxStep;
    renderAll();
  });
  document.getElementById("speed-select").addEventListener("change", (ev) => {
    state.speed = Number(ev.target.value);
    if (state.playing) scheduleNextTick();
  });

  // Modo Manual
  document.getElementById("btn-manual-reset").addEventListener("click", resetManualMode);
  document.getElementById("btn-manual-undo").addEventListener("click", handleManualUndo);
  document.getElementById("btn-manual-hint").addEventListener("click", handleManualHint);

  // Treino de Defesa ao Vivo
  document.getElementById("defense-toggle").addEventListener("click", () => {
    const opts = document.getElementById("defense-options");
    const icon = document.getElementById("defense-toggle-icon");
    const isHidden = opts.classList.toggle("hidden");
    icon.textContent = isHidden ? "+" : "−";
  });

  ["reefer3", "liftCost", "separateR"].forEach((modKey) => {
    const btn = document.getElementById(`mod-${modKey}`);
    btn.addEventListener("click", () => {
      state.mods[modKey] = !state.mods[modKey];
      btn.classList.toggle("on", state.mods[modKey]);
      if (state.mode === "manual") {
        refreshManualStateInfo();
      } else {
        runSimulation(false);
      }
    });
  });

  // Laboratório
  document.getElementById("btn-run-benchmark").addEventListener("click", runLabBenchmark);
  document.getElementById("btn-export-csv").addEventListener("click", exportCsv);

  document.querySelectorAll(".chart-tabs button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.chart;
      document.querySelectorAll(".chart-tabs button").forEach((b) =>
        b.classList.toggle("active", b === btn)
      );
      ["expanded", "memory", "ratio"].forEach((k) => {
        document.getElementById(`chart-card-${k}`).classList.toggle("active", k === target);
      });
    });
  });

  // Dialog de Instância Personalizada
  const dlg = document.getElementById("custom-instance-dialog");
  const closeDlg = () => {
    dlg.close();
    document.getElementById("instance-select").value = state.currentInstanceId;
  };
  document.getElementById("btn-close-dialog").addEventListener("click", closeDlg);
  document.getElementById("btn-cancel-dialog").addEventListener("click", closeDlg);

  document.getElementById("custom-instance-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const errEl = document.getElementById("dialog-error");
    errEl.classList.add("hidden");
    try {
      const S = Number(document.getElementById("inp-S").value);
      const H = Number(document.getElementById("inp-H").value);
      const pilhas = JSON.parse(document.getElementById("inp-pilhas").value);
      const parseList = (str) =>
        str
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
          .map(Number);
      const pesados = parseList(document.getElementById("inp-pesados").value);
      const refrigerados = parseList(document.getElementById("inp-refrigerados").value);

      if (!Array.isArray(pilhas) || pilhas.length !== S) {
        throw new Error(`A lista 'pilhas' deve conter exatamente S = ${S} sub-listas.`);
      }

      state.instances.custom = {
        id: "custom",
        nome: `Personalizada · S${S} H${H} N${pilhas.flat().length}`,
        S,
        H,
        pilhas,
        pesados,
        refrigerados,
      };
      state.currentInstanceId = "custom";
      state.instanceConfig = structuredClone(state.instances.custom);
      dlg.close();
      resetManualMode();
      state.labResults = [];
      runSimulation(false);
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    }
  });
}

async function initApp() {
  setupEvents();
  await loadInstances();
  resetManualMode();
  await runSimulation(false);
}

window.addEventListener("DOMContentLoaded", initApp);
