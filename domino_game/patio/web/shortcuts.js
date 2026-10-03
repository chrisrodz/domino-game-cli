// One table drives both the key handler and the shortcuts dialog, so they cannot drift apart.
export const SHORTCUTS = [
  { keys: ["1", "7"], range: true, command: "select", label: "Select a tile, counted from your left" },
  { keys: ["←", "→"], command: "cycle", label: "Step through your playable tiles" },
  { keys: ["L"], command: "left", label: "Play the selected tile on the left end" },
  { keys: ["R"], command: "right", label: "Play the selected tile on the right end" },
  { keys: ["Enter"], command: "play", label: "Play or lead when only one end fits" },
  { keys: ["P"], command: "pass", label: "Pass when nothing fits" },
  { keys: ["N"], command: "continue", label: "Next round, or a new game after the match" },
  { keys: ["Esc"], command: "clear", label: "Clear the selection" },
  { keys: ["A"], command: "autoplay", label: "Autoplay: CPUs play every seat, yours too" },
  { keys: ["Z"], command: "zen", label: "Zen mode: only the table" },
  { keys: ["T"], command: "view", label: "Switch between patio and table view" },
  { keys: ["B"], command: "book", label: "Open La libreta" },
  { keys: ["S"], command: "sound", label: "Table sounds on or off" },
  { keys: ["?"], command: "help", label: "Show these shortcuts" },
];

const LETTERS = {
  l: "left",
  r: "right",
  p: "pass",
  n: "continue",
  a: "autoplay",
  z: "zen",
  t: "view",
  b: "book",
  s: "sound",
};

/** Map a keydown event to `{ command, index? }`, or null to leave the key to the browser. */
export function commandFor(event) {
  if (event.ctrlKey || event.metaKey || event.altKey || event.repeat) return null;
  const key = event.key;
  if (/^[1-7]$/.test(key)) return { command: "select", index: Number(key) - 1 };
  if (key === "ArrowLeft") return { command: "cycle", step: -1 };
  if (key === "ArrowRight") return { command: "cycle", step: 1 };
  if (key === "Enter") return { command: "play" };
  if (key === "Escape") return { command: "clear" };
  // Some keyboards and automation report Shift+/ instead of "?".
  if (key === "?" || (key === "/" && event.shiftKey)) return { command: "help" };
  const letter = key.length === 1 ? LETTERS[key.toLowerCase()] : undefined;
  return letter ? { command: letter } : null;
}

/** Next playable tile id in hand order, wrapping; starts at the first or last tile when nothing is selected. */
export function cycleTile(hand, playable, selected, step) {
  const ids = hand.map((tile) => tile.id).filter((id) => playable.has(id));
  if (!ids.length) return null;
  const at = ids.indexOf(selected);
  if (at < 0) return step > 0 ? ids[0] : ids.at(-1);
  return ids[(at + step + ids.length) % ids.length];
}
