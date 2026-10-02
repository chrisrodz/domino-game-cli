import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { layoutBoard, overlaps } from "../domino_game/patio/web/domino-layout.js";

const spec = JSON.parse(await readFile(new URL("../domino_game/patio/web/assets/domino-spec.json", import.meta.url)));
const tile = (left, right) => ({ id: `${Math.min(left, right)}-${Math.max(left, right)}`, left, right });

function verify(board, opening) {
  const { tiles, scale } = layoutBoard(board, { spec, opening });
  assert.equal(tiles.length, board.length);
  tiles.forEach((placed, index) => {
    assert.equal(placed.id, board[index].id);
    assert.ok(placed.bounds.minX >= -2.4 - 1e-6 && placed.bounds.maxX <= 2.4 + 1e-6);
    assert.ok(placed.bounds.minZ >= -2.05 - 1e-6 && placed.bounds.maxZ <= 2.05 + 1e-6);
    if (index) {
      const previous = tiles[index - 1];
      assert.ok(
        Math.hypot(previous.outgoing[0] - placed.incoming[0], previous.outgoing[1] - placed.incoming[1]) < 1e-6,
        `Gap at ${index}`,
      );
      const a = previous.bounds,
        b = placed.bounds;
      const gapX = Math.max(0, a.minX - b.maxX, b.minX - a.maxX);
      const gapZ = Math.max(0, a.minZ - b.maxZ, b.minZ - a.maxZ);
      assert.ok(Math.hypot(gapX, gapZ) < 1e-6, `Bodies do not touch at ${index}`);
    }
    for (const other of tiles.slice(0, index))
      assert.ok(!overlaps(placed.bounds, other.bounds), `Overlap ${placed.id} with ${other.id}`);
    if (board[index].left === board[index].right) {
      const longAxis = [Math.cos(placed.angle), -Math.sin(placed.angle)];
      assert.ok(Math.abs(longAxis[0] * placed.outDirection[0] + longAxis[1] * placed.outDirection[1]) < 1e-6);
    } else {
      const axis = [Math.cos(placed.angle), -Math.sin(placed.angle)];
      const firstHalf = (placed.incoming[0] - placed.x) * axis[0] + (placed.incoming[1] - placed.z) * axis[1];
      const lastHalf = (placed.outgoing[0] - placed.x) * axis[0] + (placed.outgoing[1] - placed.z) * axis[1];
      const sign = board[index].left < board[index].right ? 1 : -1;
      assert.ok(firstHalf * sign < 0 && lastHalf * sign > 0, `Wrong pip half connected on ${placed.id}`);
    }
  });
  assert.ok(scale > 0);
  return tiles;
}

test("single opening double is centered and perpendicular", () => {
  const [placed] = verify([tile(6, 6)], "6-6");
  assert.equal(placed.x, 0);
  assert.equal(placed.z, 0);
});

test("doubles consume their width along the chain, not their length", () => {
  const placed = verify([tile(1, 6), tile(6, 6), tile(6, 2)], "6-6");
  assert.ok(Math.abs(placed[2].x - placed[1].x - (spec.width + spec.length) / 2) < 1e-6);
});

test("full double-six set remains flush through bends and asymmetric growth", () => {
  // Euler circuit through K7 with loops: each of the 28 real tiles appears once.
  const edges = [];
  for (let i = 0; i < 7; i++) for (let j = i; j < 7; j++) edges.push([i, j]);
  function circuit(seed) {
    const remaining = edges.map((edge) => edge.slice()),
      stack = [6],
      vertices = [];
    let state = seed + 1;
    while (stack.length) {
      const current = stack.at(-1),
        valid = [];
      remaining.forEach((edge, index) => {
        if (edge && edge.includes(current)) valid.push(index);
      });
      if (!valid.length) {
        vertices.push(stack.pop());
        continue;
      }
      state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
      const index = valid[state % valid.length],
        [a, b] = remaining[index];
      remaining[index] = null;
      stack.push(a === current ? b : a);
    }
    vertices.reverse();
    return vertices.slice(0, -1).map((value, index) => tile(value, vertices[index + 1]));
  }
  for (let seed = 0; seed < 100; seed++) {
    const chain = circuit(seed);
    assert.equal(new Set(chain.map((tile) => tile.id)).size, 28);
    for (const anchor of [0, 7, 14, 21, 27]) {
      verify(chain, chain[anchor].id);
      let lower = anchor,
        upper = anchor;
      while (lower > 0 || upper < 27) {
        if (lower > 0 && (upper === 27 || (lower + upper + seed) % 2)) lower--;
        else upper++;
        verify(chain.slice(lower, upper + 1), chain[anchor].id);
      }
    }
  }
});
