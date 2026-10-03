/** All-CPU matches for fast, audited rule verification. */
import { Match, roundResult, type Mode } from './match.ts';
import { seededRandom, shuffleWith } from './random.ts';
import { audit } from './referee.ts';
import { RuleError } from './rules.ts';
import { simpleStrategy, type CpuStrategy } from './strategy.ts';

// A round lasts at most 28 plays plus passes; a 1000-point match ends long before this.
export const MAX_ACTIONS = 20_000;

export interface SimulationReport {
  matches: number;
  rounds: number;
  blocked: number;
  tiedBlocks: number;
  teamWins: [number, number];
  violations: string[];
}

/** Let `strategy` play every seat until the match ends. */
export function playOut(match: Match, strategy: CpuStrategy = simpleStrategy, maxActions = MAX_ACTIONS): Match {
  for (let action = 0; action < maxActions; action++) {
    if (match.phase === 'match_over') return match;
    if (match.phase === 'round_over') match.nextRound();
    else match.autoTurn(match.turn, strategy);
  }
  throw new RuleError(
    `Match did not finish within ${maxActions} actions (round ${match.roundNumber}, scores ${match.scores.join('-')}).`
  );
}

export interface SimulationOptions {
  readonly matches: number;
  readonly target?: number;
  readonly mode?: Mode;
  /** Match N is dealt from `seededRandom(seed + N)`. Defaults to a random seed. */
  readonly seed?: number;
}

/** Play and audit `matches` all-CPU matches. */
export function simulate({ matches, target = 200, mode = 'target_score', seed }: SimulationOptions): SimulationReport {
  const report: SimulationReport = { matches: 0, rounds: 0, blocked: 0, tiedBlocks: 0, teamWins: [0, 0], violations: [] };
  const base = seed ?? Math.floor(Math.random() * 2 ** 32);
  for (let index = 0; index < matches; index++) {
    const match = playOut(new Match({ target, mode, shuffle: shuffleWith(seededRandom(base + index)) }));
    const outcomes = match.rounds.map(roundResult);
    report.matches += 1;
    report.rounds += outcomes.length;
    report.blocked += outcomes.filter((outcome) => outcome.blocked).length;
    report.tiedBlocks += outcomes.filter((o) => o.blocked && o.teamPips[0] === o.teamPips[1]).length;
    const last = outcomes.at(-1);
    if (last) report.teamWins[last.team] += 1;
    report.violations.push(...audit(match).map((problem) => `match seed ${base + index}: ${problem}`));
  }
  return report;
}
