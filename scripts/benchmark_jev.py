"""Compare tactical Jev against the original broad Choice on rotated, identical deals.

Run with TYPESAFE_API_KEY set: uv run python -m scripts.benchmark_jev --seeds 17 42
No fallback is allowed: failures must remain visible in the benchmark.
"""

import argparse
import json
import random
import statistics
import time
from dataclasses import dataclass, field
from io import StringIO
from unittest.mock import patch

from rich.console import Console
from typesafe_sdk import Choice, RetryPolicy, TypeSafeClient, TypeSafeError

from domino_game.game.deck import create_deck
from domino_game.game.engine import Game
from domino_game.game.jev import JevStrategy, JevUnavailableError
from domino_game.game.observation import TurnObservation, build_observation
from domino_game.game.scoring import calculate_round_score
from domino_game.models.player import AIDifficulty

BASELINE_INSTRUCTIONS = (
    "Which supplied legal move best advances the acting player's team toward winning this round "
    "and match under `rules`? Weigh going out, partner support, opponent pressure, remaining "
    "hand connections and pip exposure. Use the exact resulting ends and hand facts in each "
    "option. Other players' tiles are unknown. If public history is supplied, use it as evidence; "
    "pass deductions apply only in the current round. Playable tiles after this move describe "
    "the immediate board, not a guarantee about the player's next turn. Select one option."
)
BASELINE_STATE_KEYS = {
    "acting_seat",
    "own_team",
    "own_hand",
    "own_hand_pips",
    "board",
    "board_ends",
    "players",
    "team_scores",
    "round_number",
    "game_mode",
    "target_score",
    "rules",
    "public_turn_history",
    "public_round_results",
    "known_missing_numbers_this_round",
}
BASELINE_OPTION_KEYS = {
    "tile",
    "side",
    "resulting_ends",
    "remaining_hand_pips",
    "remaining_hand",
    "own_playable_tiles_on_resulting_board",
}


@dataclass(frozen=True)
class Deal:
    seed: int
    rotation: int
    difficulty: AIDifficulty


@dataclass
class Metrics:
    calls: int = 0
    input_tokens: int = 0
    code_decisions: int = 0
    latencies: list[float] = field(default_factory=list)
    models: set[str] = field(default_factory=set)

    def report(self) -> dict:
        ordered = sorted(self.latencies)
        return {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "code_decisions": self.code_decisions,
            "mean_decision_seconds": round(statistics.mean(ordered), 4) if ordered else 0,
            "p95_decision_seconds": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 4) if ordered else 0,
            "models": sorted(self.models),
        }


def baseline_choice(client: TypeSafeClient, view: TurnObservation, metrics: Metrics) -> str:
    state = {key: value for key, value in view.state.items() if key in BASELINE_STATE_KEYS}
    options = {}
    for candidate in view.candidates:
        option = {key: value for key, value in candidate.to_option().items() if key in BASELINE_OPTION_KEYS}
        if view.context.difficulty == AIDifficulty.HARD:
            missing = state["known_missing_numbers_this_round"]
            option["seats_known_to_be_unable_to_play_on_resulting_board"] = [
                int(seat)
                for seat, numbers in missing.items()
                if int(seat) != view.context.seat and set(candidate.ends_after) <= set(numbers)
            ]
        options[candidate.move_id] = option
    response = client.system_one(state=state, questions={"move": Choice(instructions=BASELINE_INSTRUCTIONS, criteria=options)})
    metrics.calls += 1
    metrics.input_tokens += response.usage.input_tokens
    metrics.models.add(response.model)
    answer = response.choices.get("move")
    if answer is None or answer.choice not in options:
        raise JevUnavailableError("Baseline returned an invalid move")
    return answer.choice


def play_deal(deal: Deal, strategy: JevStrategy, metrics: tuple[Metrics, Metrics]) -> dict:
    game = Game(game_mode="single_round", target_score=0)
    game.setup_players()
    deck = create_deck()
    random.Random(deal.seed).shuffle(deck)
    for _ in range(7):
        for index in range(4):
            game.players[(index + deal.rotation) % 4].hand.append(deck.pop())
    for player in game.players:
        player.ai_difficulty = deal.difficulty
    seat = game.find_starting_player()
    while len(game.turn_history) < 128:
        player = game.players[seat]
        legal = player.get_valid_moves(game.board)
        current_metrics = metrics[player.team]
        if not legal:
            game.record_pass(player)
            if game.consecutive_passes == 4:
                break
        else:
            if len(legal) == 1:
                move = legal[0]
                current_metrics.code_decisions += 1
            else:
                started = time.monotonic()
                view = build_observation(game, player, legal)
                if player.team == 0:
                    move_id = strategy.choose_move(view)
                    decision = strategy.last_decision
                    if decision is None:
                        current_metrics.code_decisions += 1
                    else:
                        current_metrics.calls += 1
                        current_metrics.input_tokens += decision.input_tokens
                        current_metrics.models.add(decision.model)
                else:
                    move_id = baseline_choice(strategy.client, view, current_metrics)
                current_metrics.latencies.append(time.monotonic() - started)
                move = next(legal[index] for index, candidate in enumerate(view.candidates) if candidate.move_id == move_id)
            game.apply_move(player, move)
            if player.is_out():
                break
        tiles = [*game.board.dominoes, *(tile for other in game.players for tile in other.hand)]
        assert len(tiles) == len(set(tiles)) == 28, "Tile conservation failed"
        seat = (seat + 1) % 4
    else:
        raise RuntimeError("Benchmark round failed to terminate within 128 turns")
    with patch("domino_game.game.scoring.console", Console(file=StringIO())):
        team, points = calculate_round_score(game.players, game.board, game.last_played_team)
    return {
        "seed": deal.seed,
        "rotation": deal.rotation,
        "difficulty": deal.difficulty.value,
        "winner": "tactical" if team == 0 else "broad_choice",
        "points": points,
        "turns": len(game.turn_history),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=[17])
    parser.add_argument("--levels", choices=["medium", "hard"], nargs="+", default=["medium", "hard"])
    args = parser.parse_args()
    try:
        with TypeSafeClient(timeout=2.0, retry=RetryPolicy(max_retries=0, timeout=2.0)) as client:
            strategy = JevStrategy(client)
            for level in args.levels:
                metrics = (Metrics(), Metrics())
                results = []
                for seed in args.seeds:
                    for rotation in range(4):
                        result = play_deal(Deal(seed, rotation, AIDifficulty(level)), strategy, metrics)
                        results.append(result)
                        print(json.dumps(result), flush=True)
                print(
                    json.dumps(
                        {
                            "difficulty": level,
                            "rounds": len(results),
                            "tactical_wins": sum(result["winner"] == "tactical" for result in results),
                            "tactical_points": sum(result["points"] for result in results if result["winner"] == "tactical"),
                            "broad_choice_points": sum(
                                result["points"] for result in results if result["winner"] == "broad_choice"
                            ),
                            "tactical": metrics[0].report(),
                            "broad_choice": metrics[1].report(),
                        }
                    ),
                    flush=True,
                )
    except (TypeSafeError, JevUnavailableError) as error:
        status = getattr(error, "status", None)
        detail = str(error) if isinstance(error, JevUnavailableError) else type(error).__name__
        raise SystemExit(f"Benchmark stopped: {detail} (HTTP {status}); no fallback is permitted.") from None


if __name__ == "__main__":
    main()
