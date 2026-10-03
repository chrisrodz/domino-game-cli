/** One double-six domino, held or placed with `left` and `right` in that order. */
export interface Tile {
  readonly left: number;
  readonly right: number;
}

export const MAX_PIPS = 6;

const isHalf = (value: number) => Number.isInteger(value) && value >= 0 && value <= MAX_PIPS;

export function tile(left: number, right: number): Tile {
  if (!isHalf(left) || !isHalf(right)) {
    throw new RangeError(`A double-six tile needs halves from 0 to ${MAX_PIPS}, got [${left}|${right}].`);
  }
  return Object.freeze({ left, right });
}

/** Orientation-free id with the low half first: [6|1] and [1|6] are both "1-6". */
export function tileId(t: Tile): string {
  return `${Math.min(t.left, t.right)}-${Math.max(t.left, t.right)}`;
}

export function parseTileId(id: unknown): Tile {
  const match = typeof id === 'string' ? /^([0-6])-([0-6])$/.exec(id) : null;
  if (!match) throw new RangeError(`Expected a tile id such as "1-6", got ${JSON.stringify(id)}.`);
  return tile(Number(match[1]), Number(match[2]));
}

export const sameTile = (a: Tile, b: Tile): boolean => tileId(a) === tileId(b);
export const pipsOf = (t: Tile): number => t.left + t.right;
export const isDouble = (t: Tile): boolean => t.left === t.right;
export const hasValue = (t: Tile, value: number): boolean => t.left === value || t.right === value;
export const flip = (t: Tile): Tile => tile(t.right, t.left);
export const formatTile = (t: Tile): string => `[${t.left}|${t.right}]`;

/** The 28 tiles of a double-six set, each with its low half on the left, in a fixed order. */
export function createDeck(): Tile[] {
  const deck: Tile[] = [];
  for (let low = 0; low <= MAX_PIPS; low++) {
    for (let high = low; high <= MAX_PIPS; high++) deck.push(tile(low, high));
  }
  return deck;
}
