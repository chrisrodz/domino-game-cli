import { PatioScene } from "./scene.js";
import { tileFace } from "./tile-face.js";
import { clearedHand, renderScorebook } from "./scorebook.js";
import { TableSound } from "./table-sound.js";
import { SHORTCUTS, commandFor, cycleTile } from "./shortcuts.js";

const $ = (selector) => document.querySelector(selector);
const CPU_DELAY = 950;
const AUTOPLAY_DELAY = 420;
const AUTOPLAY_NEXT_ROUND_DELAY = 1800;
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

function stored(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function store(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Private windows may block storage; the preference then lasts for this page only.
  }
}

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

const touch = matchMedia("(pointer: coarse)").matches;
const humanTurn = () => state?.phase === "playing" && state.turn === 0 && !state.autoplay;

function scheduleCPU() {
  clearTimeout(cpuTimer);
  if (!state || busy || document.hidden || document.querySelector("dialog[open]")) return;
  if (state.phase === "playing" && (state.turn !== 0 || state.autoplay))
    cpuTimer = setTimeout(() => action("step"), state.autoplay ? AUTOPLAY_DELAY : CPU_DELAY);
  else if (state.phase === "round_over" && state.autoplay)
    cpuTimer = setTimeout(() => action("next"), AUTOPLAY_NEXT_ROUND_DELAY);
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

const choicesFor = (id) => state?.moves.filter((move) => move.tile === id) ?? [];

function selectTile(id, { toggle = true } = {}) {
  if (busy || !humanTurn() || !choicesFor(id).length) return;
  if (selected === id && toggle) {
    // A second click on the selected tile plays it when there is only one place for it.
    const choices = choicesFor(id);
    if (choices.length === 1) return action("move", { tile: id, position: choices[0].position });
    selected = null;
  } else selected = id;
  render();
}

function previewEnd(position) {
  if (sceneReady) scene.preview(busy ? null : selected, position);
}

function openDialog(selector) {
  clearTimeout(cpuTimer);
  $(selector).showModal();
}

function placeAt(position) {
  if (busy || !humanTurn()) return;
  const move = choicesFor(selected).find((move) => move.position === position);
  if (move) action("move", { tile: selected, position });
}

function playOnlyChoice() {
  if (!humanTurn()) return;
  const choices = choicesFor(selected);
  if (choices.length === 1) placeAt(choices[0].position);
  else if (!selected && state.moves.length === 1) action("move", state.moves[0]);
}

function continueMatch() {
  if (busy) return;
  if (state.phase === "match_over") openNewGame();
  else if (state.phase === "round_over") action("next");
}

function turnHint() {
  if (state.phase !== "playing") return "";
  if (state.autoplay)
    return touch ? "Autoplay is on. Tap Autoplay to take your seat." : "Autoplay is on. Press A to take your seat.";
  if (state.turn !== 0) return `${state.players[state.turn].name} is playing.`;
  if (!state.moves.length) return "Nothing fits either end. Pass to keep the game moving.";
  const choices = choicesFor(selected);
  if (!selected)
    return state.board.length
      ? `Your move. ${touch ? "Tap" : "Pick"} a glowing tile${touch ? "" : ", or press 1-7"}.`
      : state.round === 1
        ? "You hold the double-six. Lead with it."
        : "You open this round. Lead with any tile.";
  if (choices.length > 1)
    return `${selected} fits both ends. ${touch ? "Tap an end." : "Click an end, or press L or R."}`;
  return `${selected} selected. ${touch ? "Tap it again or tap the end." : "Click it again, click the end, or press Enter."}`;
}

// Screen readers and Tab users get real buttons for the tiles drawn in the canvas.
function renderHandAccess() {
  const focused = document.activeElement?.closest("#hand-access") ? document.activeElement.dataset.tile : null;
  $("#hand-access").replaceChildren(
    ...state.players[0].hand.map((tile, index) => {
      const playable = humanTurn() && choicesFor(tile.id).length > 0;
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.tile = tile.id;
      button.textContent = `${index + 1}: ${tile.left}-${tile.right}${playable ? ", playable" : ""}`;
      button.setAttribute("aria-pressed", String(selected === tile.id));
      button.setAttribute("aria-disabled", String(busy || !playable));
      button.addEventListener("click", () => selectTile(tile.id));
      button.addEventListener("focus", () => sceneReady && scene.highlight(tile.id));
      button.addEventListener("blur", () => sceneReady && scene.highlight(null));
      return button;
    }),
  );
  if (focused) $(`#hand-access [data-tile="${focused}"]`)?.focus({ preventScroll: true });
}

function renderTurnBar() {
  const mustPass = humanTurn() && !state.moves.length;
  $("#pass-button").hidden = !mustPass;
  $("#pass-button").disabled = busy;
  $("#turn-hint").textContent = turnHint();
  $("#turn-bar").hidden = state.phase !== "playing";
}

function renderResult() {
  $("#result").hidden = state.phase === "playing" || !resultVisible;
  $("#show-result").hidden = state.phase === "playing" || resultVisible;
  if (!state.result) return;
  const won = state.result.team === 0;
  const match = state.phase === "match_over";
  const round = state.rounds.at(-1);
  $("#result-kicker").textContent = match
    ? state.mode === "single_round"
      ? "SINGLE ROUND / COMPLETE"
      : "MATCH COMPLETE"
    : `ROUND ${String(state.round).padStart(2, "0")} / COMPLETE`;
  $("#result-title").textContent = match
    ? won
      ? "You & Ally take the match."
      : "The opponents take the match."
    : state.result.blocked
      ? "¡Trancado!"
      : "¡Dominó!";
  const how = state.result.blocked
    ? round.teamPips[0] === round.teamPips[1]
      ? `Both teams held ${round.teamPips[0]} pips; the team that closed the game wins.`
      : `Pips left: You & Ally ${round.teamPips[0]}, Opponents ${round.teamPips[1]}. Fewer pips wins.`
    : clearedHand(round.winner);
  const next = match ? "" : ` ${round.nextLeader} opens the next round.`;
  $("#result-description").textContent =
    `${won ? "You & Ally" : "The opponents"} earn ${state.result.points} points. ${how}${next}`;
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
  $("#continue-button").innerHTML = match ? "Play again <kbd>N</kbd>" : "Next round <kbd>N</kbd>";
}

function renderToggles() {
  $("#autoplay-button").setAttribute("aria-pressed", String(Boolean(state?.autoplay)));
  $("#zen-button").setAttribute("aria-pressed", String(document.body.classList.contains("zen")));
  $("#sound-button").setAttribute("aria-pressed", String(sound.enabled));
  $("#sound-button .control-label").textContent = sound.enabled ? "Sound on" : "Sound off";
}

function render() {
  if (!state) return;
  if (selected && !choicesFor(selected).length) selected = null;
  $("#score-us").textContent = state.scores[0];
  $("#score-them").textContent = state.scores[1];
  $("#zen-us").textContent = state.scores[0];
  $("#zen-them").textContent = state.scores[1];
  $("#target").textContent = state.mode === "single_round" ? "ONE ROUND" : `FIRST TO ${state.target}`;
  $("#round-label").textContent = `ROUND ${String(state.round).padStart(2, "0")}`;
  $("#turn-label").textContent =
    state.phase !== "playing"
      ? "Round complete"
      : state.turn === 0 && !state.autoplay
        ? "Your turn"
        : `${state.players[state.turn].name}${state.autoplay ? " (auto)" : ""}`;
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
  } else $("#last-move").textContent = `Seven tiles each. ${state.players[state.leader].name} opens this round.`;
  renderTurnBar();
  renderHandAccess();
  renderScorebook(state);
  if (previousPhase !== state.phase) resultVisible = true;
  renderResult();
  renderToggles();
  if (previousPhase !== state.phase && state.phase !== "playing") $("#continue-button").focus({ preventScroll: true });
  if (previousPhase === "playing" && previousTurn !== 0 && humanTurn()) sound.play("turn");
  previousPhase = state.phase;
  previousTurn = state.turn;
  if (sceneReady) scene.update(state, { selected, busy, active: humanTurn() });
}

function openNewGame() {
  $("#target-score").value = state?.target ?? 200;
  $("#mode").value = state?.mode ?? "target_score";
  $("#setup-autoplay").checked = Boolean(state?.autoplay);
  updateMode();
  openDialog("#setup-dialog");
}

function toggleView(next = !overhead) {
  if (!sceneReady) return;
  overhead = next;
  scene.setView(overhead);
  $("#view-button").setAttribute("aria-pressed", String(overhead));
  $("#view-button .control-label").textContent = overhead ? "Patio view" : "Table view";
  $("#view-button").setAttribute("aria-label", overhead ? "Switch to patio view" : "Switch to table view");
}

function setZen(on) {
  document.body.classList.toggle("zen", on);
  store("patio-zen", on ? "1" : "0");
  renderToggles();
}

async function toggleSound() {
  try {
    await sound.toggle();
  } catch (error) {
    showError(`Table sounds could not start: ${error.message}`);
  }
  renderToggles();
}

function toggleAutoplay() {
  if (state) action("autoplay", { enabled: !state.autoplay });
}

function updateMode() {
  $("#target-score").disabled = $("#mode").value === "single_round";
  document.querySelectorAll("[data-target]").forEach((button) => {
    button.disabled = $("#mode").value === "single_round";
  });
}

function renderShortcutList() {
  $("#keys-list").replaceChildren(
    ...SHORTCUTS.flatMap(({ keys, range, label }) => {
      const term = document.createElement("dt");
      keys.forEach((key, index) => {
        if (index) term.append(range ? "–" : " ");
        const kbd = document.createElement("kbd");
        kbd.textContent = key;
        term.append(kbd);
      });
      const detail = document.createElement("dd");
      detail.textContent = label;
      return [term, detail];
    }),
  );
}

const commands = {
  select: ({ index }) => {
    const tile = state?.players[0].hand[index];
    if (tile) selectTile(tile.id, { toggle: false });
  },
  cycle: ({ step }) => {
    if (!humanTurn()) return;
    const playable = new Set(state.moves.map((move) => move.tile));
    const id = cycleTile(state.players[0].hand, playable, selected, step);
    if (id) selectTile(id, { toggle: false });
  },
  left: () => placeAt(state?.board.length ? "left" : "first"),
  right: () => placeAt(state?.board.length ? "right" : "first"),
  play: playOnlyChoice,
  pass: () => {
    if (humanTurn() && !state.moves.length) action("pass");
  },
  continue: continueMatch,
  clear: () => {
    selected = null;
    render();
  },
  autoplay: toggleAutoplay,
  zen: () => setZen(!document.body.classList.contains("zen")),
  view: () => toggleView(),
  book: () => openDialog("#scorebook-dialog"),
  sound: toggleSound,
  help: () => openDialog("#keys-dialog"),
};

document.addEventListener("keydown", (event) => {
  sound.unlock().catch((error) => showError(`Table sounds could not start: ${error.message}`));
  if (
    document.querySelector("dialog[open]") ||
    ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)
  )
    return;
  const found = commandFor(event);
  // Enter on a focused button keeps its native click.
  if (!found || (found.command === "play" && document.activeElement.tagName === "BUTTON")) return;
  event.preventDefault();
  commands[found.command](found);
});

$("#pass-button").addEventListener("click", () => commands.pass());
$("#continue-button").addEventListener("click", continueMatch);
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
$("#keys-button").addEventListener("click", () => openDialog("#keys-dialog"));
$("#new-button").addEventListener("click", openNewGame);
$("#autoplay-button").addEventListener("click", toggleAutoplay);
$("#zen-button").addEventListener("click", () => commands.zen());
$("#view-button").addEventListener("click", () => toggleView());
$("#reset-view").addEventListener("click", () => toggleView(false));
$("#sound-button").addEventListener("click", toggleSound);
document
  .querySelectorAll("[data-close]")
  .forEach((button) => button.addEventListener("click", () => button.closest("dialog").close()));
document.querySelectorAll("dialog").forEach((dialog) => {
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    )
      dialog.close();
  });
  dialog.addEventListener("close", scheduleCPU);
});
document.querySelectorAll("[data-target]").forEach((button) =>
  button.addEventListener("click", () => {
    $("#target-score").value = button.dataset.target;
  }),
);
$("#mode").addEventListener("change", updateMode);
$("#setup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  $("#setup-dialog").close();
  await action("game", {
    mode: $("#mode").value,
    target: Number($("#target-score").value),
    autoplay: $("#setup-autoplay").checked,
  });
});
document.addEventListener("pointerdown", () =>
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

async function boot() {
  setZen(stored("patio-zen") === "1");
  renderShortcutList();
  try {
    const response = await fetch("/assets/domino-spec.json");
    if (!response.ok) throw new Error(`Could not load the domino specification (${response.status}).`);
    spec = await response.json();
    $(".brand-mark").append(tileFace({ left: 2, right: 2 }, spec));
    $(".loading-mark").append(tileFace({ left: 6, right: 6 }, spec));
    scene = new PatioScene($("#scene"), {
      onSelect: (id) => selectTile(id),
      onPlace: placeAt,
      onPreview: previewEnd,
      onLand: () => sound.play("tile"),
      spec,
    });
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
