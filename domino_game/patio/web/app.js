import { PatioScene } from "./scene.js";
import { tileFace } from "./tile-face.js";
import { enableHandDrag } from "./hand-drag.js";
import { renderScorebook } from "./scorebook.js";
import { TableSound } from "./table-sound.js";

const $ = (selector) => document.querySelector(selector);
const sound = new TableSound();
let state,
  scene,
  spec,
  selected = null,
  busy = false,
  cpuTimer,
  overhead = false,
  sceneReady = false,
  resultVisible = true,
  previousPhase,
  previousTurn;

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
  if (
    !state ||
    state.phase !== "playing" ||
    state.turn === 0 ||
    busy ||
    document.hidden ||
    document.querySelector("dialog[open]")
  )
    return;
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

function selectTile(id, { ensure = false } = {}) {
  if (busy || state?.phase !== "playing" || state.turn !== 0 || !state.moves.some((move) => move.tile === id)) return;
  selected = selected === id && !ensure ? null : id;
  render();
  const tile = $(`#hand [data-tile="${id}"]`)?.getBoundingClientRect();
  const rack = $("#hand").getBoundingClientRect();
  if (tile && tile.left < rack.left) $("#hand").scrollLeft += tile.left - rack.left - 4;
  else if (tile && tile.right > rack.right) $("#hand").scrollLeft += tile.right - rack.right + 4;
}

function previewEnd(position) {
  if (!sceneReady) return;
  const end = position === "left" && !state.board.length ? "first" : position;
  scene.preview(busy ? null : selected, end);
}

function openDialog(selector) {
  clearTimeout(cpuTimer);
  $(selector).showModal();
}

function placeAt(position) {
  const move = state.moves.find(
    (move) =>
      move.tile === selected && (move.position === position || (position === "left" && move.position === "first")),
  );
  if (move) action("move", { tile: selected, position: move.position });
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
      button.append(tileFace(tile, spec));
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
  $("#play-left").textContent = first ? "Place first tile" : `Left \u00b7 ${state.ends.left ?? "-"}`;
  $("#play-right").textContent = `Right \u00b7 ${state.ends.right ?? "-"}`;
  $("#play-left").setAttribute("aria-label", first ? "Place first tile" : "Play on the left end");
  $("#play-right").setAttribute("aria-label", "Play on the right end");
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
            ? `${selected} selected. ${choices.length > 1 ? "Both ends are yours to choose." : "Choose the highlighted end."}`
            : matchMedia("(pointer: fine)").matches
              ? "Drag a tile to an open end, or click to select. Keys: 1-7."
              : "Select a tile, then an open end. Keyboard: 1-7.";
}

function renderResult() {
  $("#result").hidden = state.phase === "playing" || !resultVisible;
  $("#show-result").hidden = state.phase === "playing" || resultVisible;
  if (!state.result) return;
  const won = state.result.team === 0;
  const match = state.phase === "match_over";
  $("#result-kicker").textContent = match
    ? state.mode === "single_round"
      ? "SINGLE ROUND / COMPLETE"
      : "MATCH COMPLETE"
    : `ROUND ${String(state.round).padStart(2, "0")} / COMPLETE`;
  $("#result-title").textContent = state.result.blocked ? "\u00a1Trancado!" : "\u00a1Domin\u00f3!";
  const winner = state.rounds?.at(-1)?.winner;
  $("#result-description").textContent =
    `${won ? "You & Ally" : "The opponents"} earn ${state.result.points} points. ${state.result.blocked ? "The lowest hand wins the blocked round." : `${winner ?? "A player"} cleared their hand.`}`;
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
  if (event) {
    const text =
      event.type === "pass"
        ? `${event.name} passed.`
        : `${event.name} played ${event.tile.left}-${event.tile.right}${event.position === "first" ? " to open the round." : ` on the ${event.position}.`}`;
    $("#last-move").replaceChildren();
    if (event.tile) $("#last-move").append(tileFace(event.tile, spec));
    const label = document.createElement("span");
    label.textContent = text;
    $("#last-move").append(label);
  } else $("#last-move").textContent = `Seven tiles each. ${state.players[state.turn].name} opens this round.`;
  renderHand();
  renderScorebook(state);
  if (previousPhase !== state.phase) resultVisible = true;
  renderResult();
  if (previousPhase !== state.phase && state.phase !== "playing") $("#continue-button").focus({ preventScroll: true });
  if (previousPhase === "playing" && previousTurn !== 0 && state.phase === "playing" && state.turn === 0)
    sound.play("turn");
  previousPhase = state.phase;
  previousTurn = state.turn;
  if (sceneReady) scene.update(state, { selected, busy });
}

$("#play-left").addEventListener("click", () => placeAt("left"));
$("#play-right").addEventListener("click", () => placeAt("right"));
$("#pass-button").addEventListener("click", () => action("pass"));
$("#continue-button").addEventListener("click", () =>
  state.phase === "match_over" ? openDialog("#setup-dialog") : action("next"),
);
$("#view-board").addEventListener("click", () => {
  resultVisible = false;
  renderResult();
  $("#show-result").focus({ preventScroll: true });
});
$("#show-result").addEventListener("click", () => {
  resultVisible = true;
  renderResult();
  $("#continue-button").focus({ preventScroll: true });
});
$("#rules-button").addEventListener("click", () => openDialog("#rules-dialog"));
$("#scorebook-button").addEventListener("click", () => openDialog("#scorebook-dialog"));
$("#new-button").addEventListener("click", () => {
  $("#target-score").value = state?.target ?? 200;
  $("#mode").value = state?.mode ?? "target_score";
  updateMode();
  openDialog("#setup-dialog");
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
document.querySelectorAll("dialog").forEach((dialog) => dialog.addEventListener("close", scheduleCPU));
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
  await action("game", {
    mode: $("#mode").value,
    target: Number($("#target-score").value),
  });
});
$("#view-button").addEventListener("click", () => {
  if (!sceneReady) return;
  overhead = !overhead;
  scene.setView(overhead);
  $("#view-button").setAttribute("aria-pressed", String(overhead));
  $("#view-button .control-label").textContent = overhead ? "Patio view" : "Table view";
  $("#view-button").setAttribute("aria-label", overhead ? "Switch to patio view" : "Switch to table view");
});
$("#reset-view").addEventListener("click", () => {
  if (!sceneReady) return;
  overhead = false;
  scene.setView(false);
  $("#view-button").setAttribute("aria-pressed", "false");
  $("#view-button .control-label").textContent = "Table view";
  $("#view-button").setAttribute("aria-label", "Switch to table view");
});
function renderSound() {
  $("#sound-button").setAttribute("aria-pressed", String(sound.enabled));
  $("#sound-button .control-label").textContent = sound.enabled ? "Sound on" : "Sound off";
}
$("#sound-button").addEventListener("click", async () => {
  try {
    await sound.toggle();
  } catch (error) {
    showError(`Table sounds could not start: ${error.message}`);
  }
  renderSound();
});
document.addEventListener("pointerdown", () =>
  sound.unlock().catch((error) => showError(`Table sounds could not start: ${error.message}`)),
);
document.addEventListener("keydown", () =>
  sound.unlock().catch((error) => showError(`Table sounds could not start: ${error.message}`)),
);
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
    const response = await fetch("/assets/domino-spec.json");
    if (!response.ok) throw new Error(`Could not load the domino specification (${response.status}).`);
    spec = await response.json();
    $(".brand-mark").append(tileFace({ left: 2, right: 2 }, spec));
    $(".loading-mark").append(tileFace({ left: 6, right: 6 }, spec));
    scene = new PatioScene($("#scene"), {
      onSelect: selectTile,
      onPlace: placeAt,
      onLand: () => sound.play("tile"),
      spec,
    });
    document.querySelectorAll("#board-ends button, #placement button").forEach((button) => {
      const end = button.dataset.end ?? (button.id === "play-right" ? "right" : "left");
      button.addEventListener("pointerenter", () => previewEnd(end));
      button.addEventListener("focus", () => previewEnd(end));
      button.addEventListener("pointerleave", () => previewEnd(null));
      button.addEventListener("blur", () => previewEnd(null));
    });
    enableHandDrag({
      rack: $("#hand"),
      spec,
      select: (id) => selectTile(id, { ensure: true }),
      preview: previewEnd,
      place: placeAt,
    });
    const [initial] = await Promise.all([request("state"), scene.load()]);
    state = initial;
    sceneReady = true;
    render();
    renderSound();
    $("#loading").hidden = true;
    scheduleCPU();
  } catch (error) {
    $("#loading p").textContent = "The table could not open.";
    $("#loading small").textContent = "Use a browser with WebGL 2, or refresh to retry.";
    showError(error.message);
  }
}
boot();
