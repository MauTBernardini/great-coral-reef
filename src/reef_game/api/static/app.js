const state = { cards: [], types: [], activeType: "all", search: "" };
const $ = (selector) => document.querySelector(selector);

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");

const labelFor = (key) => ({
  coral_id: "ID do coral", fauna_id: "ID da fauna", soil_id: "ID do solo",
  instinct_id: "ID do instinto", upgrade_id: "ID da melhoria", card_id: "ID da carta",
  cost: "Custo", points: "Pontos", victory_points: "Pontos de vitória",
  effect: "Efeito", description: "Descrição", layer: "Camada", requirements: "Requisitos",
  production: "Produção", temperature_delta: "Variação de temperatura", ph_delta: "Variação de pH",
})[key] || key.replaceAll("_", " ");

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Falha ao consultar ${url}`);
  return response.json();
}

function notify(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 3200);
}

function valueText(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function usefulText(card) {
  const data = card.data || {};
  return card.description || data.effect || data.trigger || data.requirement || "Consulte os atributos desta carta.";
}

function renderGameStats(game) {
  $("#game-stats").innerHTML = [
    [game.total_cards, "cartas catalogadas"],
    [game.player_count, "jogadores"],
    [`${game.board.width}×${game.board.height}×${game.board.max_layers}`, "tabuleiro"],
    [game.rules_sections, "seções de regras"],
  ].map(([value, label]) => `<div class="stat"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`).join("");
}

function renderFilters() {
  const allCount = state.types.reduce((sum, type) => sum + type.count, 0);
  const filters = [{ id: "all", label: "Todas", count: allCount }, ...state.types];
  $("#type-filters").innerHTML = filters.map((type) => `
    <button class="filter-button ${type.id === state.activeType ? "active" : ""}" data-type="${type.id}" type="button">
      ${escapeHtml(type.label)} <span>${type.count}</span>
    </button>`).join("");
  document.querySelectorAll(".filter-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeType = button.dataset.type;
      renderFilters();
      renderCards();
    });
  });
}

function renderCards() {
  const needle = state.search.trim().toLocaleLowerCase("pt-BR");
  const cards = state.cards.filter((card) => {
    const typeMatch = state.activeType === "all" || card.type === state.activeType;
    const searchMatch = !needle || JSON.stringify(card).toLocaleLowerCase("pt-BR").includes(needle);
    return typeMatch && searchMatch;
  });
  $("#card-count").textContent = `${cards.length} ${cards.length === 1 ? "carta" : "cartas"}`;
  const active = state.types.find((type) => type.id === state.activeType);
  $("#active-filter").textContent = active?.label || "Todo o catálogo";
  $("#card-grid").innerHTML = cards.length ? cards.map((card) => `
    <button class="game-card" data-id="${escapeHtml(card.id)}" data-type="${escapeHtml(card.type)}" type="button">
      <span class="card-top"><span class="type-badge">${escapeHtml(card.type_label)}</span><span class="card-glyph">${escapeHtml(card.name.charAt(0))}</span></span>
      <h3>${escapeHtml(card.name)}</h3>
      <p>${escapeHtml(usefulText(card))}</p>
      <span class="card-meta">
        ${card.cost !== null && card.cost !== undefined ? `<span class="meta-pill">Custo ${escapeHtml(valueText(card.cost))}</span>` : ""}
        ${card.points !== null && card.points !== undefined ? `<span class="meta-pill">${escapeHtml(valueText(card.points))} pts</span>` : ""}
      </span>
    </button>`).join("") : '<div class="empty-state">Nenhuma carta corresponde aos filtros.</div>';
  document.querySelectorAll(".game-card").forEach((button) => button.addEventListener("click", () => {
    const card = state.cards.find((item) => item.id === button.dataset.id && item.type === button.dataset.type);
    openCard(card);
  }));
}

function openCard(card) {
  const fields = Object.entries(card.data || {}).map(([key, value]) => `
    <div class="detail-field"><dt>${escapeHtml(labelFor(key))}</dt><dd>${escapeHtml(valueText(value))}</dd></div>`).join("");
  $("#card-detail").innerHTML = `<span class="detail-label">${escapeHtml(card.type_label)}</span><h2 class="detail-title">${escapeHtml(card.name)}</h2><dl class="detail-grid">${fields}</dl>`;
  $("#card-dialog").showModal();
}

function renderRules(payload) {
  $("#rules-grid").innerHTML = payload.sections.map((section, index) => `
    <article class="rule-card">
      <span class="rule-number">0${index + 1}</span>
      <h3>${escapeHtml(section.title)}</h3>
      <p>${escapeHtml(section.summary)}</p>
      <ul>${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </article>`).join("");
}

function pickSummary(summary, keys, fallback = "—") {
  for (const key of keys) if (summary[key] !== undefined) return summary[key];
  return fallback;
}

function renderTournaments(payload) {
  if (!payload.items.length) {
    $("#tournament-grid").innerHTML = '<div class="empty-state">Nenhum torneio persistido foi encontrado em <code>artifacts/tournaments</code>.</div>';
    return;
  }
  $("#tournament-grid").innerHTML = payload.items.map((item) => {
    const summary = item.summary || {};
    const games = pickSummary(summary, ["games", "paired_games", "total_games", "n_games"]);
    const agents = item.agents?.length ? item.agents.join(" × ") : "Estratégias do torneio";
    const rawRate = pickSummary(summary, ["win_rate", "winner_win_rate", "p1_winrate", "a_winrate"]);
    const rate = typeof rawRate === "number" ? `${(rawRate * 100).toFixed(1)}%` : rawRate;
    const files = item.files.filter((name) => name !== "metadata.json").slice(0, 5);
    const fileLinks = files.map((name) => name.endsWith(".html")
      ? `<a class="file-link" href="/api/tournaments/${encodeURIComponent(item.id)}/report" target="_blank">Relatório HTML ↗</a>`
      : `<a class="file-link" href="/api/tournaments/${encodeURIComponent(item.id)}/files/${encodeURIComponent(name)}">${escapeHtml(name)}</a>`).join("");
    return `<article class="tournament-card">
      <div class="tournament-head"><div><span class="tournament-id">${escapeHtml(item.id)}</span><h3>${escapeHtml(agents)}</h3></div><span class="mode-badge">${escapeHtml(item.mode)}</span></div>
      <div class="tournament-stats">
        <div><strong>${escapeHtml(games)}</strong><span>partidas</span></div>
        <div><strong>${escapeHtml(rate)}</strong><span>taxa destaque</span></div>
        <div><strong>${escapeHtml(item.version || "—")}</strong><span>versão</span></div>
      </div>
      <div class="file-list">${fileLinks || '<span class="tournament-id">Somente metadados disponíveis</span>'}</div>
    </article>`;
  }).join("");
}

async function bootstrap() {
  try {
    const [game, types, cards, rules, tournaments] = await Promise.all([
      getJson("/api/game"), getJson("/api/cards/types"), getJson("/api/cards?limit=1000"),
      getJson("/api/rules"), getJson("/api/tournaments"),
    ]);
    state.types = types;
    state.cards = cards.items;
    renderGameStats(game);
    renderFilters();
    renderCards();
    renderRules(rules);
    renderTournaments(tournaments);
  } catch (error) {
    console.error(error);
    notify("Não foi possível carregar os dados da API.");
  }
}

$("#card-search").addEventListener("input", (event) => { state.search = event.target.value; renderCards(); });
$(".dialog-close").addEventListener("click", () => $("#card-dialog").close());
$("#card-dialog").addEventListener("click", (event) => { if (event.target === $("#card-dialog")) $("#card-dialog").close(); });
bootstrap();
