import type { Tile } from './tile.ts';

/** Reorders a fresh deck into dealt order. */
export type Shuffle = (deck: Tile[]) => Tile[];

/** Fisher-Yates over `random`, which returns floats in [0, 1) like `Math.random`. */
export function shuffleWith(random: () => number): Shuffle {
  return (deck) => {
    const shuffled = [...deck];
    for (let index = shuffled.length - 1; index > 0; index--) {
      const swap = Math.floor(random() * (index + 1));
      [shuffled[index], shuffled[swap]] = [shuffled[swap] as Tile, shuffled[index] as Tile];
    }
    return shuffled;
  };
}

/** Small deterministic generator (mulberry32) so simulations and tests reproduce from a seed. */
export function seededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}
