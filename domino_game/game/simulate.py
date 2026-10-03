"""All-CPU matches for fast, audited rule verification."""

import random
from dataclasses import dataclass, field
from typing import Optional

from domino_game.game.match import Match, Mode
from domino_game.game.referee import audit
from domino_game.game.rules import RuleError

# A round lasts at most 28 plays plus passes; a 1000-point match ends long before this.
MAX_ACTIONS = 20_000


@dataclass
class SimulationReport:
    matches: int = 0
    rounds: int = 0
    blocked: int = 0
    tied_blocks: int = 0
    team_wins: list[int] = field(default_factory=lambda: [0, 0])
    violations: list[str] = field(default_factory=list)


def play_out(match: Match, *, max_actions: int = MAX_ACTIONS) -> Match:
    """Let the CPU strategy play every seat until the match ends."""
    for _ in range(max_actions):
        if match.phase == "match_over":
            return match
        if match.phase == "round_over":
            match.next_round()
        else:
            match.auto_turn(match.turn)
    raise RuleError(f"Match did not finish within {max_actions} actions (round {match.round_number}, scores {match.scores}).")


def simulate(*, matches: int, target: int = 200, mode: Mode = "target_score", seed: Optional[int] = None) -> SimulationReport:
    """Play and audit `matches` matches; seed N reproduces match N as `Random(seed + N)`."""
    report = SimulationReport()
    base = random.randrange(2**32) if seed is None else seed
    for index in range(matches):
        match = play_out(Match(target=target, mode=mode, rng=random.Random(base + index)))
        outcomes = [log.result() for log in match.rounds]
        report.matches += 1
        report.rounds += len(outcomes)
        report.blocked += sum(outcome.blocked for outcome in outcomes)
        report.tied_blocks += sum(outcome.blocked and outcome.team_pips[0] == outcome.team_pips[1] for outcome in outcomes)
        report.team_wins[outcomes[-1].team] += 1
        report.violations += [f"match seed {base + index}: {problem}" for problem in audit(match)]
    return report
