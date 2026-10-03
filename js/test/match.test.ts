import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  Board,
  Match,
  OPENING_TILE,
  RuleError,
  audit,
  playOut,
  roundResult,
  sameTile,
  seededRandom,
  shuffleWith,
  simulate,
  tile,
  tileId,
  type CpuStrategy,
  type MatchOptions,
  type RoundOutcome,
  type Tile,
} from '../src/index.ts';

const seeded = (seed: number, options: MatchOptions = {}) =>
  new Match({ ...options, shuffle: shuffleWith(seededRandom(seed)) });

const ids = (tiles: readonly Tile[]) => tiles.map(tileId);

function finishRound(match: Match): void {
  while (match.phase === 'playing') match.autoTurn(match.turn);
}

function position(match: Match, hands: Tile[][], opening: Tile): void {
  match.board = new Board();
  match.board.place(opening, 'first');
  match.hands = hands;
  match.turn = 0;
}

test('round 1 is led by the double-six holder, with the double-six', () => {
  for (let seed = 0; seed < 20; seed++) {
    const match = seeded(seed);
    const moves = match.legalMoves(match.turn);
    assert.ok(match.hands[match.turn]?.some((t) => sameTile(t, OPENING_TILE)));
    assert.equal(moves.length, 1);
    assert.equal(tileId(moves[0]!.tile), '6-6');
    assert.equal(moves[0]!.end, 'first');
    for (let seat = 0; seat < 4; seat++) if (seat !== match.turn) assert.deepEqual(match.legalMoves(seat), []);
  }
});

test('later rounds are led by the previous winner, with any tile', () => {
  const leaders = new Set<number>();
  for (let seed = 0; seed < 40; seed++) {
    const match = seeded(seed);
    finishRound(match);
    const winner = roundResult(match.round).nextLeader;
    match.nextRound();
    assert.equal(match.roundNumber, 2);
    assert.equal(match.turn, winner);
    assert.equal(match.round.leader, winner);
    const moves = match.legalMoves(winner);
    assert.deepEqual(ids(moves.map((move) => move.tile)), ids(match.hands[winner]!));
    assert.ok(moves.every((move) => move.end === 'first'));
    leaders.add(winner);
  }
  assert.ok(leaders.size > 1, 'different seats should win across seeds');
});

test('a tranque ends the round on the closing tile without waiting for passes', () => {
  const match = seeded(0);
  position(match, [[tile(1, 6), tile(2, 2)], [tile(0, 2)], [tile(0, 3)], [tile(0, 4)]], tile(6, 6));
  match.play(0, tile(6, 1), 'left');
  assert.equal(match.phase, 'round_over');
  assert.equal(match.round.turns.length, 1);
  const outcome = roundResult(match.round);
  assert.equal(outcome.blocked, true);
  assert.equal(outcome.closer, 0);
  assert.deepEqual(outcome.teamPips, [4 + 3, 2 + 4]);
  assert.deepEqual([outcome.team, outcome.points, outcome.nextLeader], [1, 13, 1]);
  assert.deepEqual(match.scores, [0, 13]);
});

test('going out wins even when the line is also closed', () => {
  const match = seeded(0);
  position(match, [[tile(1, 6)], [tile(0, 2)], [tile(0, 3)], [tile(0, 4)]], tile(6, 6));
  match.play(0, tile(1, 6), 'right');
  const outcome = roundResult(match.round);
  assert.deepEqual([outcome.blocked, outcome.team, outcome.points], [false, 0, 9]);
});

test('a tile matching both ends can be played on either side', () => {
  for (const end of ['left', 'right'] as const) {
    const match = seeded(0);
    position(match, [[tile(6, 6), tile(1, 2)], [tile(0, 2)], [tile(0, 3)], [tile(0, 4)]], tile(6, 6));
    match.play(0, tile(6, 6), end);
    assert.deepEqual(ids(match.board.tiles), ['6-6', '6-6']);
  }
});

test('invalid actions throw and leave the match unchanged', () => {
  const match = seeded(3);
  const leader = match.turn;
  const other = (leader + 1) % 4;
  const before = JSON.stringify([match.hands, match.turn, match.round.turns]);
  assert.throws(() => match.play(other, match.hands[other]![0]!, 'first'), /turn/);
  const notOpener = match.hands[leader]!.find((t) => !sameTile(t, OPENING_TILE))!;
  assert.throws(() => match.play(leader, notOpener, 'first'), /cannot play/);
  assert.throws(() => match.pass(leader), /cannot pass/);
  assert.throws(() => match.nextRound(), /next round/);
  assert.equal(JSON.stringify([match.hands, match.turn, match.round.turns]), before);
});

test('single-round mode ends after one round', () => {
  const match = seeded(5, { mode: 'single_round' });
  finishRound(match);
  assert.equal(match.phase, 'match_over');
  assert.equal(match.winner, roundResult(match.round).team);
  assert.throws(() => match.nextRound(), RuleError);
});

test('invalid settings fail fast', () => {
  for (const options of [{ target: 0 }, { target: 1.5 }, { target: 1001 }, { mode: 'chiva' }]) {
    assert.throws(() => new Match(options as MatchOptions), RuleError);
  }
});

test('a shuffle that is not one double-six set is rejected', () => {
  assert.throws(() => new Match({ shuffle: (deck) => [...deck.slice(1), deck[1]!] }), /one double-six set/);
});

test('matches reproduce from a seed', () => {
  const first = playOut(seeded(42));
  const second = playOut(seeded(42));
  assert.deepEqual(first.toRecord(), second.toRecord());
  assert.deepEqual(first.scores, second.scores);
});

test('autoTurn hands the strategy the seat hand', () => {
  const seen: [string[], boolean][] = [];
  const lastMove: CpuStrategy = {
    name: 'last',
    chooseMove(hand, moves, board) {
      seen.push([ids(hand), board.isEmpty()]);
      return moves.at(-1) ?? null;
    },
  };
  const match = seeded(9);
  const leader = match.turn;
  const dealt = ids(match.round.deal[leader]!);
  match.autoTurn(leader, lastMove);
  assert.deepEqual(seen, [[dealt, true]]);
  assert.deepEqual(audit(match), []);
});

test('fromRecord restores an in-progress match and rejects tampered ones', () => {
  const match = seeded(13);
  for (let step = 0; step < 9; step++) match.autoTurn(match.turn);
  const record = match.toRecord();
  const restored = Match.fromRecord(JSON.parse(JSON.stringify(record)));
  assert.deepEqual(restored.toRecord(), record);
  assert.equal(restored.turn, match.turn);
  assert.deepEqual(ids(restored.hands.flat()), ids(match.hands.flat()));
  assert.deepEqual(ids(restored.board.tiles), ids(match.board.tiles));

  const swapped = structuredClone(record) as unknown as { rounds: { turns: unknown[][] }[] };
  const firstTurn = swapped.rounds[0]!.turns[0]!;
  swapped.rounds[0]!.turns[0] = [(Number(firstTurn[0]) + 1) % 4, firstTurn[1], firstTurn[2]];
  assert.throws(() => Match.fromRecord(swapped), RuleError);
  assert.throws(() => Match.fromRecord({ ...record, version: 2 }), /version/);
  assert.throws(() => Match.fromRecord({ ...record, rounds: [] }), /at least one round/);
  assert.throws(() => Match.fromRecord('nope'), /expected an object/);
});

test('all-CPU matches pass the referee', () => {
  const report = simulate({ matches: 300, target: 200, seed: 7 });
  assert.deepEqual(report.violations, []);
  assert.equal(report.matches, 300);
  assert.equal(report.teamWins[0] + report.teamWins[1], 300);
  assert.ok(report.blocked > 0 && report.blocked < report.rounds);
});

test('matches end on the round that reaches the target', () => {
  for (const target of [1, 50, 500]) assert.deepEqual(simulate({ matches: 40, target, seed: target }).violations, []);
});

const played = () => playOut(seeded(11, { target: 150 }));
const withOutcome = (match: Match, index: number, change: Partial<RoundOutcome>) => {
  const log = match.rounds[index]!;
  log.outcome = { ...roundResult(log), ...change };
};

test('the referee accepts a clean match', () => {
  const match = played();
  assert.ok(match.rounds.length > 1);
  assert.deepEqual(audit(match), []);
});

test('the referee flags a wrong round leader', () => {
  const match = played();
  match.rounds[1]!.leader = (match.rounds[1]!.leader + 1) % 4;
  assert.ok(audit(match).some((problem) => problem.includes('previous winner')));
});

test('the referee flags a pass while holding a legal tile', () => {
  const match = played();
  const log = match.rounds[0]!;
  const index = log.turns.findIndex((turn, i) => turn.tile !== null && i > 0);
  log.turns[index] = { seat: log.turns[index]!.seat, tile: null, end: null };
  assert.ok(audit(match).some((problem) => problem.includes('passed while holding')));
});

test('the referee flags wrong points, totals, and pip breakdowns', () => {
  const match = played();
  withOutcome(match, 0, { points: roundResult(match.rounds[0]!).points + 1 });
  const problems = audit(match);
  assert.ok(problems.some((problem) => problem.includes('awarded')));
  assert.ok(problems.some((problem) => problem.includes('totals')));

  const other = played();
  const outcome = roundResult(other.rounds[0]!);
  withOutcome(other, 0, { teamPips: [outcome.teamPips[1], outcome.teamPips[0]], handPips: [0, 0, 0, outcome.points] });
  assert.ok(audit(other).some((problem) => problem.includes('recorded pips')));
});

test('the referee flags a wrong tranque winner', () => {
  const match = seeded(0, { target: 1000 });
  for (let action = 0; ; action++) {
    assert.ok(action < 400, 'No decisive tranque within 400 actions.');
    if (match.phase === 'playing') match.autoTurn(match.turn);
    else {
      const outcome = roundResult(match.round);
      if (outcome.blocked && outcome.teamPips[0] !== outcome.teamPips[1]) break;
      match.nextRound();
    }
  }
  withOutcome(match, match.rounds.length - 1, { team: roundResult(match.round).team === 0 ? 1 : 0 });
  assert.ok(audit(match).some((problem) => problem.includes('expected')));
});

test('the referee flags a match that ends early', () => {
  const match = played();
  const scored = match.scores[match.winner ?? 0] + 1;
  Object.defineProperty(match, 'target', { value: scored });
  assert.ok(audit(match).some((problem) => problem.includes('ended before')));
});

test('the referee flags out-of-turn play and an illegal opening', () => {
  const match = played();
  const log = match.rounds[0]!;
  const first = log.turns[0]!;
  const other = log.deal[first.seat]!.find((t) => !sameTile(t, OPENING_TILE))!;
  log.turns[0] = { seat: first.seat, tile: other, end: 'first' };
  log.turns[1] = { ...log.turns[1]!, seat: (log.turns[1]!.seat + 1) % 4 };
  const problems = audit(match);
  assert.ok(problems.some((problem) => problem.includes('instead of [6|6]')));
  assert.ok(problems.some((problem) => problem.includes('out of order')));
});
