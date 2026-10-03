"""Seeded all-CPU matches recorded for the TypeScript engine's conformance tests.

The TypeScript package (`js/`) replays each recorded deal with its own rules
and CPU strategy and must produce the same turns, outcomes, and scores. Regenerate
after any rule or strategy change, and commit the result:

    uv run python -m domino_game.game.conformance
"""

import json
import random
from pathlib import Path
from typing import Any

from domino_game.game.match import Match, Mode, RoundLog
from domino_game.game.simulate import play_out
from domino_game.models import Domino

FIXTURE = Path(__file__).resolve().parents[2] / "js" / "test" / "fixtures" / "conformance.json"
CASES: tuple[tuple[Mode, int, range], ...] = (
    ("target_score", 200, range(12)),
    ("target_score", 50, range(100, 106)),
    ("single_round", 200, range(200, 210)),
)


def tile_id(tile: Domino) -> str:
    return f"{min(tile.left, tile.right)}-{max(tile.left, tile.right)}"


def round_record(log: RoundLog) -> dict[str, Any]:
    return {
        "deal": [[tile_id(tile) for tile in hand] for hand in log.deal],
        "turns": [[turn.seat, turn.tile and tile_id(turn.tile), turn.end] for turn in log.turns],
    }


def match_record(match: Match) -> dict[str, Any]:
    """The same JSON shape as the TypeScript `Match.toRecord()`."""
    return {
        "version": 1,
        "target": match.target,
        "mode": match.mode,
        "rounds": [round_record(log) for log in match.rounds],
    }


def outcome_record(log: RoundLog) -> dict[str, Any]:
    outcome = log.result()
    return {
        "team": outcome.team,
        "points": outcome.points,
        "blocked": outcome.blocked,
        "nextLeader": outcome.next_leader,
        "closer": outcome.closer,
        "handPips": list(outcome.hand_pips),
        "teamPips": list(outcome.team_pips),
        "scores": list(log.scores or ()),
    }


def build_fixture() -> str:
    matches = []
    for mode, target, seeds in CASES:
        for seed in seeds:
            match = play_out(Match(target=target, mode=mode, rng=random.Random(seed)))
            matches.append(
                {
                    "seed": seed,
                    "record": match_record(match),
                    "outcomes": [outcome_record(log) for log in match.rounds],
                }
            )
    # One match per line keeps diffs readable when a rule change moves a few turns.
    lines = ",\n".join(json.dumps(entry, separators=(",", ":")) for entry in matches)
    return f'{{"generator":"uv run python -m domino_game.game.conformance","matches":[\n{lines}\n]}}\n'


if __name__ == "__main__":
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(build_fixture())
    print(f"Wrote {FIXTURE}")
