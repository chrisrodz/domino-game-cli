import type { Board } from './board.ts';
import type { Move } from './rules.ts';
import { isDouble, pipsOf, type Tile } from './tile.ts';

export interface CpuStrategy {
  readonly name: string;
  /**
   * Choose one of `moves`, or null when there are none.
   * `hand` is every tile the seat still holds, including ones it cannot play now.
   */
  chooseMove(hand: readonly Tile[], moves: readonly Move[], board: Board): Move | null;
}

/** Greedy: play the highest-value tile, with a bonus for doubles; ignores the rest of the hand and the board. */
export const simpleStrategy: CpuStrategy = {
  name: 'simple',
  chooseMove(_hand, moves) {
    let best: Move | null = null;
    let bestScore = -1;
    for (const move of moves) {
      const score = pipsOf(move.tile) + (isDouble(move.tile) ? 5 : 0);
      // Strictly greater keeps the first of equal moves, matching the Python strategy.
      if (score > bestScore) {
        bestScore = score;
        best = move;
      }
    }
    return best;
  },
};
