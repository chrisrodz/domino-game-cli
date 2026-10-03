import { flip, type Tile } from './tile.ts';

/** Where a tile goes: `first` opens an empty line; `left` and `right` extend an open end. */
export type End = 'first' | 'left' | 'right';

export type Ends = readonly [left: number, right: number];

/** The line of tiles on the table, oriented so neighbouring halves match. */
export class Board {
  readonly tiles: Tile[] = [];

  isEmpty(): boolean {
    return this.tiles.length === 0;
  }

  /** Open (left, right) values, or null before the first tile. */
  ends(): Ends | null {
    const first = this.tiles[0];
    const last = this.tiles.at(-1);
    return first && last ? [first.left, last.right] : null;
  }

  /** Place `t` on `end`, flipping it to match. Returns false, leaving the line unchanged, when it does not fit. */
  place(t: Tile, end: End): boolean {
    const ends = this.ends();
    if (ends === null) {
      this.tiles.push(t);
      return true;
    }
    const [left, right] = ends;
    if (end === 'left') {
      if (t.right === left) this.tiles.unshift(t);
      else if (t.left === left) this.tiles.unshift(flip(t));
      else return false;
      return true;
    }
    if (t.left === right) this.tiles.push(t);
    else if (t.right === right) this.tiles.push(flip(t));
    else return false;
    return true;
  }
}
