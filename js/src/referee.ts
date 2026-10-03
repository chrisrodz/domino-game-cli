/**
 * Independent audit of a finished or in-progress match log.
 *
 * The referee replays each round from its recorded deal using its own end
 * tracking, not `Board` or `legalMoves`, so an engine bug cannot hide behind the
 * code that produced it. It returns human-readable violations; an empty list
 * means every turn, round result, and score followed the rules.
 */
import type { Match } from './match.ts';
import { HAND_SIZE, OPENING_TILE, SEATS, type RoundOutcome } from './rules.ts';
import { createDeck, formatTile, sameTile, tileId, type Tile } from './tile.ts';

type Ends = readonly [number, number];

const FULL_SET = new Set(createDeck().map(tileId));
const fits = (t: Tile, ends: Ends) => [t.left, t.right].includes(ends[0]) || [t.left, t.right].includes(ends[1]);
const sum = (values: readonly number[]) => values.reduce((total, value) => total + value, 0);
const show = (value: unknown) => JSON.stringify(value);

export function audit(match: Match): string[] {
  const violations: string[] = [];
  const scores: [number, number] = [0, 0];
  let expectedLeader: number | null = null;
  for (const log of match.rounds) {
    const tag = `round ${log.number}`;
    violations.push(...auditDeal(log.deal, tag));
    const hands = log.deal.map((hand) => [...hand]);
    if (log.number === 1) {
      const holder = hands.findIndex((hand) => hand.some((t) => sameTile(t, OPENING_TILE)));
      if (log.leader !== holder) violations.push(`${tag}: seat ${log.leader} led, but seat ${holder} holds [6|6].`);
    } else if (log.leader !== expectedLeader) {
      violations.push(`${tag}: seat ${log.leader} led, but the previous winner is seat ${expectedLeader}.`);
    }
    let ends: Ends | null = null;
    let seat = log.leader;
    let finished = false;
    let closer: number | null = null;
    for (const [index, turn] of log.turns.entries()) {
      const where = `${tag} turn ${index + 1}`;
      if (finished) {
        violations.push(`${where}: seat ${turn.seat} acted after the round ended.`);
        break;
      }
      if (turn.seat !== seat) violations.push(`${where}: seat ${turn.seat} acted out of order; expected seat ${seat}.`);
      const hand = hands[turn.seat] ?? [];
      if (turn.tile === null) {
        const open = ends;
        const playable = hand.filter((t) => open === null || fits(t, open));
        if (open === null || playable.length > 0) {
          const held = (playable.length > 0 ? playable : hand).map(formatTile).join(' ');
          violations.push(`${where}: seat ${turn.seat} passed while holding ${held}.`);
        }
      } else {
        const t = turn.tile;
        const at = hand.findIndex((held) => sameTile(held, t));
        if (at < 0) {
          violations.push(`${where}: seat ${turn.seat} played ${formatTile(t)}, which is not in its hand.`);
          break;
        }
        if (ends === null) {
          if (turn.end !== 'first') violations.push(`${where}: the opening tile was placed on ${show(turn.end)}.`);
          if (log.number === 1 && !sameTile(t, OPENING_TILE)) {
            violations.push(`${where}: round 1 opened with ${formatTile(t)} instead of [6|6].`);
          }
          ends = [t.left, t.right];
        } else if (turn.end === 'left' && [t.left, t.right].includes(ends[0])) {
          ends = [t.right === ends[0] ? t.left : t.right, ends[1]];
        } else if (turn.end === 'right' && [t.left, t.right].includes(ends[1])) {
          ends = [ends[0], t.left === ends[1] ? t.right : t.left];
        } else {
          violations.push(`${where}: ${formatTile(t)} does not match the ${turn.end} end of ${ends.join('/')}.`);
          break;
        }
        hand.splice(at, 1);
        closer = turn.seat;
        const open = ends;
        finished = hand.length === 0 || !hands.some((held) => held.some((other) => fits(other, open)));
      }
      seat = (turn.seat + 1) % SEATS;
    }
    if (log.outcome === null) {
      if (finished) violations.push(`${tag}: the round should have ended but has no result.`);
      if (log !== match.round) violations.push(`${tag}: an earlier round was never scored.`);
      continue;
    }
    // A round only finishes on a play, so a finished round always has a closer.
    if (!finished || closer === null) {
      violations.push(`${tag}: scored while a seat could still play.`);
      continue;
    }
    violations.push(...auditOutcome(log.outcome, hands, closer, tag));
    scores[log.outcome.team] += log.outcome.points;
    if (show(log.scores) !== show(scores)) {
      violations.push(`${tag}: recorded totals ${show(log.scores)}, expected ${show(scores)}.`);
    }
    const decided = match.mode === 'single_round' || Math.max(...scores) >= match.target;
    if (decided && log !== match.round) {
      violations.push(`${tag}: the match was decided, yet round ${log.number + 1} was dealt.`);
    }
    expectedLeader = log.outcome.nextLeader;
  }
  if (show(match.scores) !== show(scores)) {
    violations.push(`match: totals ${show(match.scores)}, expected ${show(scores)}.`);
  }
  const decided = match.mode === 'single_round' || Math.max(...scores) >= match.target;
  if (match.phase === 'match_over' && !decided) {
    violations.push(`match: ended before a team reached ${match.target} (scores ${show(scores)}).`);
  }
  if (match.phase === 'round_over' && decided) {
    violations.push(`match: scores ${show(scores)} reached ${match.target}, but the match continues.`);
  }
  return violations;
}

function auditDeal(deal: readonly (readonly Tile[])[], tag: string): string[] {
  const ids = deal.flat().map(tileId);
  const problems: string[] = [];
  if (deal.length !== SEATS || deal.some((hand) => hand.length !== HAND_SIZE)) {
    problems.push(`${tag}: deal sizes ${show(deal.map((hand) => hand.length))}, expected ${SEATS} x ${HAND_SIZE}.`);
  }
  if (new Set(ids).size !== ids.length || ids.length !== FULL_SET.size || !ids.every((id) => FULL_SET.has(id))) {
    problems.push(`${tag}: the deal is not exactly one double-six set.`);
  }
  return problems;
}

function auditOutcome(outcome: RoundOutcome, hands: readonly Tile[][], closer: number, tag: string): string[] {
  const handPips = hands.map((hand) => sum(hand.map((t) => t.left + t.right)));
  const pipsAt = (seat: number) => handPips[seat] ?? 0;
  const teamPips = [pipsAt(0) + pipsAt(2), pipsAt(1) + pipsAt(3)];
  const problems: string[] = [];
  if (show(outcome.handPips) !== show(handPips) || show(outcome.teamPips) !== show(teamPips)) {
    problems.push(
      `${tag}: recorded pips ${show(outcome.handPips)} / teams ${show(outcome.teamPips)}, ` +
        `but replay leaves ${show(handPips)} / teams ${show(teamPips)}.`
    );
  }
  if (outcome.points !== sum(handPips)) {
    problems.push(`${tag}: awarded ${outcome.points} points, but ${sum(handPips)} pips remain.`);
  }
  if (outcome.closer !== closer) {
    problems.push(`${tag}: closer recorded as seat ${outcome.closer}, but seat ${closer} played last.`);
  }
  let expected: [team: number, blocked: boolean, leader: number];
  if ((hands[closer] ?? []).length === 0) {
    expected = [closer % 2, false, closer];
  } else if (teamPips[0] === teamPips[1]) {
    expected = [closer % 2, true, closer];
  } else {
    const team = (teamPips[0] ?? 0) < (teamPips[1] ?? 0) ? 0 : 1;
    const [near = closer, far = closer] = [0, 1, 2, 3].map((step) => (closer + step) % SEATS).filter((s) => s % 2 === team);
    expected = [team, true, pipsAt(near) <= pipsAt(far) ? near : far];
  }
  const actual = [outcome.team, outcome.blocked, outcome.nextLeader];
  if (show(actual) !== show(expected)) {
    problems.push(`${tag}: result (team, blocked, next leader) = ${show(actual)}, expected ${show(expected)}.`);
  }
  return problems;
}
