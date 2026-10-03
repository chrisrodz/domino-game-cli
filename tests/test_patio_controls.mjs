import assert from "node:assert/strict";
import test from "node:test";
import { SHORTCUTS, commandFor, cycleTile } from "../domino_game/patio/web/shortcuts.js";

const key = (key, extra = {}) =>
  commandFor({ key, ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, ...extra });

test("number keys select hand positions and stay within seven tiles", () => {
  assert.deepEqual(key("1"), { command: "select", index: 0 });
  assert.deepEqual(key("7"), { command: "select", index: 6 });
  assert.equal(key("8"), null);
  assert.equal(key("0"), null);
});

test("letters map to table actions in either case, but never with modifiers", () => {
  assert.deepEqual(key("l"), { command: "left" });
  assert.deepEqual(key("R"), { command: "right" });
  assert.deepEqual(key("R", { shiftKey: true }), { command: "right" }, "Shift+R and Caps Lock still play right");
  assert.deepEqual(key("p"), { command: "pass" });
  assert.deepEqual(key("z"), { command: "zen" });
  assert.equal(key("r", { metaKey: true }), null, "Cmd+R must still reload the page");
  assert.equal(key("a", { ctrlKey: true }), null);
  assert.equal(key("p", { repeat: true }), null, "a held key must not pass repeatedly");
  assert.deepEqual(key("?", { shiftKey: true }), { command: "help" });
  assert.deepEqual(key("/", { shiftKey: true }), { command: "help" });
  assert.equal(key("/"), null);
});

test("every documented command has a handler key", () => {
  const reachable = new Set(
    ["1", "ArrowLeft", "l", "r", "Enter", "p", "n", "Escape", "a", "z", "t", "b", "s", "?"].map((k) => key(k).command),
  );
  for (const shortcut of SHORTCUTS) assert.ok(reachable.has(shortcut.command), shortcut.command);
});

test("cycling visits only playable tiles in hand order and wraps", () => {
  const hand = ["0-1", "2-3", "4-5", "5-6"].map((id) => ({ id }));
  const playable = new Set(["2-3", "5-6"]);
  assert.equal(cycleTile(hand, playable, null, 1), "2-3");
  assert.equal(cycleTile(hand, playable, null, -1), "5-6");
  assert.equal(cycleTile(hand, playable, "2-3", 1), "5-6");
  assert.equal(cycleTile(hand, playable, "5-6", 1), "2-3");
  assert.equal(cycleTile(hand, playable, "2-3", -1), "5-6");
  assert.equal(cycleTile(hand, new Set(), null, 1), null);
});
