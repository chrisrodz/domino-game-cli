/**
 * Headless match state machine: deal, turns, rounds, and scores with no I/O.
 *
 * Every action is validated against `rules`; invalid actions throw `RuleError`
 * and leave the match unchanged. Each round keeps its deal and turn log so a
 * referee can replay and audit the match, and so `toRecord()` / `fromRecord()`
 * can save and restore it.
 */
import { Board, type End } from './board.ts';
import {
  HAND_SIZE,
  OPENING_TILE,
  RuleError,
  SEATS,
  isBlocked,
  legalMoves,
  nextSeat,
  scoreRound,
  type Move,
  type RoundOutcome,
  type Team,
} from './rules.ts';
import { shuffleWith, type Shuffle } from './random.ts';
import { simpleStrategy, type CpuStrategy } from './strategy.ts';
import { createDeck, formatTile, parseTileId, sameTile, tileId, type Tile } from './tile.ts';

export type Phase = 'playing' | 'round_over' | 'match_over';
export const MODES = ['target_score', 'single_round'] as const;
export type Mode = (typeof MODES)[number];
export const MAX_TARGET = 1000;

/** Validate an untrusted game mode, such as one from a form or saved game. */
export function parseMode(value: unknown): Mode {
  const mode = MODES.find((candidate) => candidate === value);
  if (mode === undefined) {
    throw new RuleError(`Unknown game mode: ${JSON.stringify(value)}; expected one of ${MODES.join(', ')}.`);
  }
  return mode;
}

export interface Turn {
  readonly seat: number;
  /** null when the seat passed. */
  readonly tile: Tile | null;
  readonly end: End | null;
}

export interface RoundLog {
  readonly number: number;
  leader: number;
  readonly deal: readonly (readonly Tile[])[];
  turns: Turn[];
  outcome: RoundOutcome | null;
  /** Team totals after this round was scored. */
  scores: readonly [number, number] | null;
}

/** The scored outcome; fails loudly for a round still in play. */
export function roundResult(log: RoundLog): RoundOutcome {
  if (log.outcome === null) throw new RuleError(`Round ${log.number} has not been scored yet.`);
  return log.outcome;
}

/** A finished or in-progress match as plain JSON: settings, each round's deal, and every turn. */
export interface MatchRecord {
  readonly version: 1;
  readonly target: number;
  readonly mode: Mode;
  readonly rounds: readonly RoundRecord[];
}

export interface RoundRecord {
  /** Four hands of tile ids, in the order they were dealt. */
  readonly deal: readonly (readonly string[])[];
  readonly turns: readonly TurnRecord[];
}

/** `[seat, tileId, end]`, or `[seat, null, null]` for a pass. */
export type TurnRecord = readonly [seat: number, tile: string | null, end: End | null];

export interface MatchOptions {
  /** Points that win the match, from 1 to 1000. Ignored by `single_round` except for display. */
  readonly target?: number;
  readonly mode?: Mode;
  /** Returns the deck in dealt order; seat N receives tiles 7N to 7N+6. Defaults to `Math.random`. */
  readonly shuffle?: Shuffle;
}

/** One partnership match played to a target score or for a single round. */
export class Match {
  readonly target: number;
  readonly mode: Mode;
  readonly scores: [number, number] = [0, 0];
  readonly rounds: RoundLog[] = [];
  hands: Tile[][] = [];
  board = new Board();
  passed: boolean[] = [];
  turn = 0;
  phase: Phase = 'playing';
  readonly #shuffle: Shuffle;

  constructor({ target = 200, mode = 'target_score', shuffle = shuffleWith(Math.random) }: MatchOptions = {}) {
    if (!Number.isInteger(target) || target < 1 || target > MAX_TARGET) {
      throw new RuleError(`Target score must be an integer from 1 to ${MAX_TARGET}, got ${JSON.stringify(target)}.`);
    }
    this.target = target;
    this.mode = parseMode(mode);
    this.#shuffle = shuffle;
    this.#deal(null);
  }

  get round(): RoundLog {
    const current = this.rounds.at(-1);
    if (current === undefined) throw new RuleError('The match has not dealt a round.');
    return current;
  }

  get roundNumber(): number {
    return this.round.number;
  }

  /** Winning team once the match is over; only a round's winners score, so they crossed the target. */
  get winner(): Team | null {
    return this.phase === 'match_over' ? roundResult(this.round).team : null;
  }

  #deal(leader: number | null): void {
    const deck = this.#shuffle(createDeck());
    const ids = deck.map(tileId);
    if (deck.length !== SEATS * HAND_SIZE || new Set(ids).size !== deck.length) {
      throw new RuleError(`The shuffle must return one double-six set; got ${deck.map(formatTile).join(' ')}.`);
    }
    this.hands = Array.from({ length: SEATS }, (_, seat) => deck.slice(seat * HAND_SIZE, (seat + 1) * HAND_SIZE));
    const opener = leader ?? this.hands.findIndex((hand) => hand.some((t) => sameTile(t, OPENING_TILE)));
    this.board = new Board();
    this.passed = Array<boolean>(SEATS).fill(false);
    this.turn = opener;
    this.phase = 'playing';
    this.rounds.push({
      number: this.rounds.length + 1,
      leader: opener,
      deal: this.hands.map((hand) => [...hand]),
      turns: [],
      outcome: null,
      scores: null,
    });
  }

  legalMoves(seat: number): Move[] {
    if (this.phase !== 'playing' || seat !== this.turn) return [];
    const mustOpen = this.roundNumber === 1 ? OPENING_TILE : null;
    return legalMoves(this.hands[seat] ?? [], this.board, mustOpen);
  }

  #requireTurn(seat: number): void {
    if (this.phase !== 'playing') {
      throw new RuleError(`Round ${this.roundNumber} has ended; seat ${seat} cannot act.`);
    }
    if (seat !== this.turn) throw new RuleError(`It is seat ${this.turn}'s turn, not seat ${seat}'s.`);
  }

  /** Play `t` (either orientation) from `seat`'s hand on `end`. */
  play(seat: number, t: Tile, end: End): void {
    this.#requireTurn(seat);
    const move = this.legalMoves(seat).find((candidate) => candidate.end === end && sameTile(candidate.tile, t));
    if (move === undefined) {
      const ends = this.board.ends();
      throw new RuleError(
        `Seat ${seat} cannot play ${formatTile(t)} on "${end}" with ends ${ends ? ends.join('/') : 'none'}.`
      );
    }
    if (!this.board.place(move.tile, end)) {
      throw new RuleError(`Board rejected ${formatTile(t)} on "${end}"; no turn was consumed.`);
    }
    const hand = this.hands[seat] ?? [];
    hand.splice(hand.indexOf(move.tile), 1);
    this.passed[seat] = false;
    this.round.turns.push({ seat, tile: move.tile, end });
    if (hand.length === 0 || isBlocked(this.hands, this.board)) this.#finishRound(seat);
    else this.turn = nextSeat(seat);
  }

  pass(seat: number): void {
    this.#requireTurn(seat);
    if (this.legalMoves(seat).length > 0) throw new RuleError(`Seat ${seat} holds a legal tile and cannot pass.`);
    this.passed[seat] = true;
    this.round.turns.push({ seat, tile: null, end: null });
    this.turn = nextSeat(seat);
  }

  /** Play the strategy's move for `seat`, or pass when it has none. */
  autoTurn(seat: number, strategy: CpuStrategy = simpleStrategy): Turn {
    const moves = this.legalMoves(seat);
    if (moves.length === 0) {
      this.pass(seat);
    } else {
      const choice = strategy.chooseMove(this.hands[seat] ?? [], moves, this.board);
      if (choice === null) {
        throw new RuleError(`Strategy "${strategy.name}" returned no move for seat ${seat} despite legal moves.`);
      }
      this.play(seat, choice.tile, choice.end);
    }
    const last = this.round.turns.at(-1);
    if (last === undefined) throw new RuleError(`Seat ${seat}'s turn was not recorded.`);
    return last;
  }

  #finishRound(closer: number): void {
    const outcome = scoreRound(this.hands, closer);
    this.scores[outcome.team] += outcome.points;
    this.round.outcome = outcome;
    this.round.scores = [this.scores[0], this.scores[1]];
    const over = this.mode === 'single_round' || Math.max(...this.scores) >= this.target;
    this.phase = over ? 'match_over' : 'round_over';
  }

  nextRound(): void {
    if (this.phase !== 'round_over') {
      throw new RuleError(
        `Round ${this.roundNumber} is "${this.phase}"; deal the next round only after a round ends mid-match.`
      );
    }
    this.#deal(roundResult(this.round).nextLeader);
  }

  toRecord(): MatchRecord {
    return {
      version: 1,
      target: this.target,
      mode: this.mode,
      rounds: this.rounds.map((log) => ({
        deal: log.deal.map((hand) => hand.map(tileId)),
        turns: log.turns.map((turn): TurnRecord => [turn.seat, turn.tile && tileId(turn.tile), turn.end]),
      })),
    };
  }

  /**
   * Rebuild a match by replaying a record through the rules, so a tampered or
   * corrupt record fails with a `RuleError` instead of producing an illegal game.
   */
  static fromRecord(input: unknown): Match {
    const record = parseRecord(input);
    const deals = record.rounds.map((round) => round.deal.flat().map(parseTileId));
    let dealt = 0;
    const replayDeal: Shuffle = () => {
      const deck = deals[dealt++];
      if (deck === undefined) throw new RuleError(`The record has no deal for round ${dealt}.`);
      return deck;
    };
    const match = new Match({ target: record.target, mode: record.mode, shuffle: replayDeal });
    record.rounds.forEach((round, index) => {
      if (index > 0) match.nextRound();
      for (const [seat, id, end] of round.turns) {
        if (id === null) match.pass(seat);
        else match.play(seat, parseTileId(id), end ?? 'first');
      }
    });
    return match;
  }
}

const isRecordObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

function parseRecord(input: unknown): MatchRecord {
  const fail = (problem: string): never => {
    throw new RuleError(`Invalid match record: ${problem}.`);
  };
  if (!isRecordObject(input)) return fail('expected an object');
  if (input.version !== 1) fail(`unsupported version ${JSON.stringify(input.version)}`);
  if (typeof input.target !== 'number') fail('target must be a number');
  const mode = parseMode(input.mode);
  if (!Array.isArray(input.rounds) || input.rounds.length === 0) return fail('expected at least one round');
  const rounds = input.rounds.map((round: unknown, index): RoundRecord => {
    if (!isRecordObject(round) || !Array.isArray(round.deal) || !Array.isArray(round.turns)) {
      return fail(`round ${index + 1} needs a deal and turns`);
    }
    const deal = round.deal.map((hand: unknown) =>
      Array.isArray(hand) && hand.every((id) => typeof id === 'string')
        ? (hand as string[])
        : fail(`round ${index + 1} has a malformed hand`)
    );
    const turns = round.turns.map((turn: unknown): TurnRecord => {
      if (!Array.isArray(turn) || turn.length !== 3) return fail(`round ${index + 1} has a malformed turn`);
      const [seat, id, end] = turn as unknown[];
      const validSeat = Number.isInteger(seat) && (seat as number) >= 0 && (seat as number) < SEATS;
      const validPlay = typeof id === 'string' && (end === 'first' || end === 'left' || end === 'right');
      if (!validSeat || !(validPlay || (id === null && end === null))) {
        fail(`round ${index + 1} has an invalid turn ${JSON.stringify(turn)}`);
      }
      return turn as unknown as TurnRecord;
    });
    return { deal, turns };
  });
  return { version: 1, target: input.target as number, mode, rounds };
}
