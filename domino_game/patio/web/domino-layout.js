const EPSILON = 1e-7;
const LIMIT = 2.4;

const add = (a, b, factor = 1) => [a[0] + b[0] * factor, a[1] + b[1] * factor];
const negate = (direction) => [-direction[0], -direction[1]];
const same = (a, b) => a[0] === b[0] && a[1] === b[1];

export function overlaps(a, b) {
  return (
    Math.min(a.maxX, b.maxX) - Math.max(a.minX, b.minX) > EPSILON &&
    Math.min(a.maxZ, b.maxZ) - Math.max(a.minZ, b.minZ) > EPSILON
  );
}

function place(tile, cursor, direction, spec) {
  const double = tile.left === tile.right;
  const turn = !same(cursor.direction, direction);
  const along = double ? spec.width : spec.length;
  let center;
  if (!turn) center = add(cursor.point, direction, along / 2);
  else center = add(add(cursor.point, cursor.direction, spec.width / 2), direction, spec.length / 4);
  const longAxis = double ? [-direction[1], direction[0]] : direction;
  const halfX = (Math.abs(longAxis[0]) * spec.length + Math.abs(longAxis[1]) * spec.width) / 2;
  const halfZ = (Math.abs(longAxis[1]) * spec.length + Math.abs(longAxis[0]) * spec.width) / 2;
  return {
    id: tile.id,
    x: center[0],
    z: center[1],
    angle: -Math.atan2(longAxis[1], longAxis[0]) + (tile.left > tile.right ? Math.PI : 0),
    incoming: cursor.point,
    outgoing: add(center, direction, along / 2),
    inDirection: cursor.direction,
    outDirection: direction,
    bounds: { minX: center[0] - halfX, maxX: center[0] + halfX, minZ: center[1] - halfZ, maxZ: center[1] + halfZ },
  };
}

function arm(tiles, config) {
  const { origin, direction, vertical, spec, obstacles } = config;
  let attempts = 0;
  function route(index, cursor, placed, heading) {
    if (index === tiles.length) return placed;
    if (++attempts > 12000) return null;
    const options = cursor.direction[1] ? [[-heading, 0], cursor.direction] : [cursor.direction, [0, vertical]];
    for (const next of options) {
      if (tiles[index].left === tiles[index].right && !same(next, cursor.direction)) continue;
      const candidate = place(tiles[index], cursor, next, spec);
      if (candidate.bounds.minX < -LIMIT - EPSILON || candidate.bounds.maxX > LIMIT + EPSILON) continue;
      if ([...obstacles, ...placed].some((other) => overlaps(candidate.bounds, other.bounds))) continue;
      const result = route(
        index + 1,
        { point: candidate.outgoing, direction: next },
        [...placed, candidate],
        next[0] || heading,
      );
      if (result) return result;
    }
    return null;
  }
  const result = route(0, { point: origin, direction }, [], direction[0]);
  if (!result) throw new Error(`Could not place ${tiles.length} dominoes without overlap.`);
  return result;
}

export function layoutBoard(board, { spec, opening }) {
  if (!board.length) return { tiles: [], scale: 1, ends: null };
  const found = board.findIndex((tile) => tile.id === opening);
  const anchor = found < 0 ? Math.floor(board.length / 2) : found;
  const first = board[anchor];
  const root = place(
    first,
    { point: [-(first.left === first.right ? spec.width : spec.length) / 2, 0], direction: [1, 0] },
    [1, 0],
    spec,
  );
  const right = arm(board.slice(anchor + 1), {
    origin: root.outgoing,
    direction: [1, 0],
    vertical: -1,
    spec,
    obstacles: [root],
  });
  const left = arm(
    board
      .slice(0, anchor)
      .reverse()
      .map((tile) => ({ ...tile, left: tile.right, right: tile.left })),
    { origin: root.incoming, direction: [-1, 0], vertical: 1, spec, obstacles: [root, ...right] },
  );
  const tiles = [
    ...left.reverse().map((tile) => ({
      ...tile,
      incoming: tile.outgoing,
      outgoing: tile.incoming,
      inDirection: negate(tile.outDirection),
      outDirection: negate(tile.inDirection),
    })),
    root,
    ...right,
  ];
  const minX = Math.min(...tiles.map((tile) => tile.bounds.minX));
  const maxX = Math.max(...tiles.map((tile) => tile.bounds.maxX));
  const minZ = Math.min(...tiles.map((tile) => tile.bounds.minZ));
  const maxZ = Math.max(...tiles.map((tile) => tile.bounds.maxZ));
  const scale = Math.min(1, 4.8 / (maxX - minX), 4.1 / (maxZ - minZ));
  const offset = [(minX + maxX) / 2, (minZ + maxZ) / 2];
  const transform = (point) => [(point[0] - offset[0]) * scale, (point[1] - offset[1]) * scale];
  tiles.forEach((tile) => {
    [tile.x, tile.z] = transform([tile.x, tile.z]);
    tile.incoming = transform(tile.incoming);
    tile.outgoing = transform(tile.outgoing);
    const lower = transform([tile.bounds.minX, tile.bounds.minZ]);
    const upper = transform([tile.bounds.maxX, tile.bounds.maxZ]);
    tile.bounds = { minX: lower[0], maxX: upper[0], minZ: lower[1], maxZ: upper[1] };
  });
  return {
    tiles,
    scale,
    ends: {
      left: { point: tiles[0].incoming, direction: negate(tiles[0].inDirection) },
      right: { point: tiles.at(-1).outgoing, direction: tiles.at(-1).outDirection },
    },
  };
}
