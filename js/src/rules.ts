/**
 * Puerto Rican partnership dominoes (Doscientos) rules as pure functions.
 *
 * Four seats in fixed partnerships: seats 0 and 2 are team 0, seats 1 and 3 are
 * team 1. Turns advance seat + 1 (counter-clockwise at the table). All 28 tiles
 * are dealt, so there is no boneyard: a player without a legal tile passes.
 *
 * - Round 1: the holder of [6|6] leads and must open with it.
 * - Later rounds: the winner of the previous round leads with any tile.
 * - A round ends when a player empties their hand ("domino") or when no seat
 *   can play ("tranque"). With every tile dealt, the tranque is known the moment
 *   the closing tile is played.
 * - Domino: the player's team scores every pip still held by all four seats.
 * - Tranque: the team with fewer pips wins and scores every pip on the table.
 *   Its member with fewer pips leads next; partners tied on pips resolve to the
 *   one nearest the closer in turn order. When team totals tie, the closer's team
 *   wins and the closer leads next.
 *
 * This mirrors `domino_game/game/rules.py`; `test/conformance.test.ts` replays
 * matches recorded by the Python engine to keep the two in step.
 */
import type { Board, End } from './board.ts';
import { hasValue, pipsOf, sameTile, tile, type Tile } from './tile.ts';

export const SEATS = 4;
export const HAND_SIZE = 7;
export const OPENING_TILE: Tile = tile(6, 6);

export interface Move {
  readonly tile: Tile;
  readonly end: End;
}

/** A requested action breaks the rules for the current game state. */
export class RuleError extends Error {
  override name = 'RuleError';
}

/** Seats 0 and 2 are team 0; seats 1 and 3 are team 1. */
export type Team = 0 | 1;

export const teamOf = (seat: number): Team => (seat % 2 === 0 ? 0 : 1);
export const nextSeat = (seat: number): number => (seat + 1) % SEATS;
export const pips = (hand: readonly Tile[]): number => hand.reduce((sum, t) => sum + pipsOf(t), 0);

/** Every (tile, end) the hand may play; a tile matching both ends is listed for each end. */
export function legalMoves(hand: readonly Tile[], board: Board, mustOpenWith: Tile | null = null): Move[] {
  const ends = board.ends();
  if (ends === null) {
    if (mustOpenWith === null) return hand.map((t) => ({ tile: t, end: 'first' }));
    const opener = hand.find((t) => sameTile(t, mustOpenWith));
    return opener ? [{ tile: opener, end: 'first' }] : [];
  }
  const [left, right] = ends;
  const moves: Move[] = [];
  for (const t of hand) {
    if (hasValue(t, left)) moves.push({ tile: t, end: 'left' });
    if (hasValue(t, right)) moves.push({ tile: t, end: 'right' });
  }
  return moves;
}

/** True when the line is open and no seat holds a tile matching either end. */
export function isBlocked(hands: readonly (readonly Tile[])[], board: Board): boolean {
  return !board.isEmpty() && !hands.some((hand) => legalMoves(hand, board).length > 0);
}

export interface RoundOutcome {
  readonly team: Team;
  readonly points: number;
  readonly blocked: boolean;
  /** Seat that leads the following round. */
  readonly nextLeader: number;
  /** Seat that played the last tile. */
  readonly closer: number;
  readonly handPips: readonly number[];
  readonly teamPips: readonly [number, number];
}

/** Score a finished round. `closer` is the seat that played the final tile. */
export function scoreRound(hands: readonly (readonly Tile[])[], closer: number): RoundOutcome {
  if (hands.length !== SEATS) throw new RuleError(`Scoring needs ${SEATS} hands, got ${hands.length}.`);
  const handPips = hands.map(pips);
  const [p0 = 0, p1 = 0, p2 = 0, p3 = 0] = handPips;
  const teamPips: [number, number] = [p0 + p2, p1 + p3];
  const points = p0 + p1 + p2 + p3;
  const base = { points, closer, handPips, teamPips };
  if (hands[closer]?.length === 0) {
    return { ...base, team: teamOf(closer), blocked: false, nextLeader: closer };
  }
  if (hands.some((hand) => hand.length === 0)) {
    throw new RuleError(`Seat ${closer} closed the round, but a different seat has an empty hand.`);
  }
  if (teamPips[0] === teamPips[1]) {
    return { ...base, team: teamOf(closer), blocked: true, nextLeader: closer };
  }
  const team = teamPips[0] < teamPips[1] ? 0 : 1;
  // Seats in turn order from the closer, so a tie between partners goes to the nearer one.
  const members = [0, 1, 2, 3].map((step) => (closer + step) % SEATS).filter((seat) => teamOf(seat) === team);
  const nextLeader = members.reduce((best, seat) => ((handPips[seat] ?? 0) < (handPips[best] ?? 0) ? seat : best));
  return { ...base, team, blocked: true, nextLeader };
}
