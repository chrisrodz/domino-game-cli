import { PatioScene } from "./scene.js";

const $ = (selector) => document.querySelector(selector);
const pipCells = [[], [4], [0, 8], [0, 4, 8], [0, 2, 6, 8], [0, 2, 4, 6, 8], [0, 2, 3, 5, 6, 8]];
let state,
  scene,
  selected = null,
  busy = false,
  cpuTimer,
  overhead = false,
  sceneReady = false,
  previousPhase;

function showError(message) {
  $("#error-text").textContent = message;
  $("#error").hidden = false;
}

async function request(path, payload) {
  const response = await fetch(
    `/api/${path}`,
    payload === undefined
      ? { cache: "no-store" }
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
  );
  if (!response.headers.get("content-type")?.includes("application/json"))
    throw new Error("The game server is unavailable. Restart it and refresh the page.");
  const data = await response.json();
  if (!response.ok) {
    if (data.state) {
      state = data.state;
      render();
    }
    throw new Error(data.error || `Game request failed (${response.status}).`);
  }
  return data;
}

function scheduleCPU() {
  clearTimeout(cpuTimer);
  if (!state || state.phase !== "playing" || state.turn === 0 || busy || document.hidden) return;
  cpuTimer = setTimeout(() => action("step"), 950);
}

async function action(path, payload = {}) {
  if (busy) return;
  clearTimeout(cpuTimer);
  busy = true;
  render();
  try {
    state = await request(path, { ...payload, revision: state.revision });
    selected = null;
    $("#error").hidden = true;
  } catch (error) {
    showError(error.message);
    busy = false;
    render();
    return;
  }
  busy = false;
  render();
  scheduleCPU();
}

function selectTile(id) {
  if (busy || state?.phase !== "playing" || state.turn !== 0 || !state.moves.some((move) => move.tile === id)) return;
  selected = selected === id ? null : id;
  render();
}

function half(value) {
  const element = document.createElement("span");
  element.className = "pip-half";
  element.setAttribute("aria-hidden", "true");
  for (let cell = 0; cell < 9; cell++) {
    const dot = document.createElement("i");
    dot.className = pipCells[value].includes(cell) ? "pip" : "pip empty";
    element.append(dot);
  }
  return element;
}

function renderHand() {
  const hand = state.players[0].hand;
  const humanTurn = state.phase === "playing" && state.turn === 0;
  const previousFocus = document.activeElement?.dataset.tile;
  $("#hand").replaceChildren(
    ...hand.map((tile, index) => {
      const legal = humanTurn && state.moves.some((move) => move.tile === tile.id);
      const button = document.createElement("button");
      button.className = `domino${legal ? " legal" : ""}${selected === tile.id ? " selected" : ""}`;
      button.dataset.tile = tile.id;
      button.dataset.key = index + 1;
      button.disabled = busy || !legal;
      button.setAttribute("aria-label", `${tile.left}-${tile.right}${legal ? ", playable" : ", unavailable"}`);
      button.setAttribute("aria-pressed", String(selected === tile.id));
      button.append(half(tile.left), half(tile.right));
      button.addEventListener("click", () => selectTile(tile.id));
      return button;
    }),
  );
  if (previousFocus) $(`#hand [data-tile="${previousFocus}"]`)?.focus({ preventScroll: true });
  $("#hand-value").textContent =
    `${hand.length} ${hand.length === 1 ? "tile" : "tiles"} / ${state.players[0].value} pips`;
  $("#hand-title").textContent =
    state.phase !== "playing"
      ? "A hand well played."
      : !humanTurn
        ? "Let the table play."
        : state.moves.length
          ? "Your move."
          : "Nothing to play.";
  const choices = state.moves.filter((move) => move.tile === selected);
  const first = choices.some((move) => move.position === "first");
  $("#play-left").textContent = first ? "Place first tile" : "Play left";
  $("#play-left").disabled = busy || !choices.some((move) => ["left", "first"].includes(move.position));
  $("#play-right").disabled = busy || !choices.some((move) => move.position === "right");
  $("#play-right").hidden = first;
  $("#placement").hidden = humanTurn && !state.moves.length;
  $("#pass-button").hidden = !humanTurn || state.moves.length > 0;
  $("#pass-button").disabled = busy;
  $("#end-values").innerHTML = `${state.ends.left ?? "-"} <span>&amp;</span> ${state.ends.right ?? "-"}`;
  $("#hand-hint").textContent =
    state.phase !== "playing"
      ? "The remaining hands are revealed on the table."
      : !humanTurn
        ? "The highlighted seat is playing. Your turn is coming."
        : !state.moves.length
          ? "No tiles match the open ends. Pass to keep the game moving."
          : selected
            ? `Selected ${selected}. Choose an available end.`
            : "Select a highlighted tile, then choose an end. Keys 1-7 also work.";
}

function renderResult() {
  $("#result").hidden = state.phase === "playing";
  if (!state.result) return;
  const won = state.result.team === 0;
  const match = state.phase === "match_over";
  $("#result-kicker").textContent = match
    ? state.mode === "single_round"
      ? "SINGLE ROUND / COMPLETE"
      : "MATCH COMPLETE"
    : `ROUND ${String(state.round).padStart(2, "0")} / COMPLETE`;
  $("#result-title").textContent = won ? "This one is yours." : "The other side takes it.";
  $("#result-description").textContent =
    `${won ? "You & Ally" : "The opponents"} earn ${state.result.points} points. ${state.result.blocked ? "Trancado. The lowest hand wins the blocked round." : "Someone cleared their hand."}`;
  const table = document.createElement("table");
  table.innerHTML =
    '<thead><tr><th scope="col">Player</th><th scope="col">Tiles left</th><th scope="col">Pips</th></tr></thead>';
  const body = document.createElement("tbody");
  state.players.forEach((player) => {
    const row = document.createElement("tr");
    [player.name, player.count, player.value].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });
    body.append(row);
  });
  table.append(body);
  $("#remaining-hands").replaceChildren(table);
  $("#continue-button").textContent = match ? "Play again" : "Next round";
}

function render() {
  if (!state) return;
  $("#score-us").textContent = state.scores[0];
  $("#score-them").textContent = state.scores[1];
  $("#target").textContent = state.mode === "single_round" ? "ONE ROUND" : `FIRST TO ${state.target}`;
  $("#round-label").textContent = `ROUND ${String(state.round).padStart(2, "0")}`;
  $("#turn-label").textContent =
    state.phase !== "playing"
      ? "Round complete"
      : state.turn === 0
        ? "Your turn"
        : `${state.players[state.turn].name} is thinking`;
  const event = state.history.at(-1);
  if (event)
    $("#last-move").textContent =
      event.type === "pass"
        ? `${event.name} passed.`
        : `${event.name} played ${event.tile.left}-${event.tile.right}${event.position === "first" ? " to open the round." : ` on the ${event.position}.`}`;
  else $("#last-move").textContent = `Seven tiles each. ${state.players[state.turn].name} opens this round.`;
  renderHand();
  renderResult();
  if (previousPhase !== state.phase && state.phase !== "playing") $("#continue-button").focus({ preventScroll: true });
  previousPhase = state.phase;
  if (sceneReady) scene.update(state, selected);
}

$("#play-left").addEventListener("click", () =>
  action("move", {
    tile: selected,
    position: state.moves.find((move) => move.tile === selected && ["left", "first"].includes(move.position))?.position,
  }),
);
$("#play-right").addEventListener("click", () => action("move", { tile: selected, position: "right" }));
$("#pass-button").addEventListener("click", () => action("pass"));
$("#continue-button").addEventListener("click", () =>
  state.phase === "match_over" ? $("#setup-dialog").showModal() : action("next"),
);
$("#rules-button").addEventListener("click", () => $("#rules-dialog").showModal());
$("#new-button").addEventListener("click", () => {
  $("#target-score").value = state?.target ?? 200;
  $("#mode").value = state?.mode ?? "target_score";
  updateMode();
  $("#setup-dialog").showModal();
});
document
  .querySelectorAll("[data-close]")
  .forEach((button) => button.addEventListener("click", () => button.closest("dialog").close()));
document.querySelectorAll("dialog").forEach((dialog) =>
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      const rect = dialog.getBoundingClientRect();
      if (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      )
        dialog.close();
    }
  }),
);
document.querySelectorAll("[data-target]").forEach((button) =>
  button.addEventListener("click", () => {
    $("#target-score").value = button.dataset.target;
  }),
);
function updateMode() {
  $("#target-score").disabled = $("#mode").value === "single_round";
  document.querySelectorAll("[data-target]").forEach((button) => {
    button.disabled = $("#mode").value === "single_round";
  });
}
$("#mode").addEventListener("change", updateMode);
$("#setup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  $("#setup-dialog").close();
  await action("game", { mode: $("#mode").value, target: Number($("#target-score").value) });
});
$("#view-button").addEventListener("click", () => {
  if (!sceneReady) return;
  overhead = !overhead;
  scene.setView(overhead);
  $("#view-button").setAttribute("aria-pressed", String(overhead));
  $("#view-button").textContent = overhead ? "Patio view" : "Table view";
});
$("#reset-view").addEventListener("click", () => {
  if (!sceneReady) return;
  overhead = false;
  scene.setView(false);
  $("#view-button").setAttribute("aria-pressed", "false");
  $("#view-button").textContent = "Table view";
});
$("#dismiss-error").addEventListener("click", () => {
  $("#error").hidden = true;
});
$("#retry-button").addEventListener("click", async () => {
  try {
    state = await request("state");
    $("#error").hidden = true;
    render();
    scheduleCPU();
    if (!sceneReady) location.reload();
  } catch (error) {
    showError(error.message);
  }
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) clearTimeout(cpuTimer);
  else scheduleCPU();
});
document.addEventListener("keydown", (event) => {
  if (
    document.querySelector("dialog[open]") ||
    ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)
  )
    return;
  if (/^[1-7]$/.test(event.key)) selectTile(state?.players[0].hand[Number(event.key) - 1]?.id);
  if (
    event.key === "Enter" &&
    (document.activeElement.closest("#hand") || document.activeElement.tagName !== "BUTTON")
  ) {
    const choices = state?.moves.filter((move) => move.tile === selected) ?? [];
    if (choices.length === 1) {
      event.preventDefault();
      action("move", { tile: selected, position: choices[0].position });
    }
  }
});

async function boot() {
  try {
    scene = new PatioScene($("#scene"), selectTile);
    const [initial] = await Promise.all([request("state"), scene.load()]);
    state = initial;
    sceneReady = true;
    render();
    $("#loading").hidden = true;
    scheduleCPU();
  } catch (error) {
    $("#loading p").textContent = "The table could not open.";
    $("#loading small").textContent = "Use a browser with WebGL 2, or refresh to retry.";
    showError(error.message);
  }
}
boot();
