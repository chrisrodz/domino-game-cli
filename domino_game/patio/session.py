"""Browser view of a headless `Match`: seat names, hidden hands, and autoplay."""

import random
from typing import Any, Optional

from domino_game.game.match import Match
from domino_game.game.rules import RuleError
from domino_game.models import Domino

NAMES = ("You", "Opponent 1", "Ally", "Opponent 2")
HUMAN = 0


class MoveError(RuleError):
    """A browser action is invalid for this game state."""


def tile_data(tile: Domino) -> dict[str, Any]:
    return {"id": f"{min(tile.left, tile.right)}-{max(tile.left, tile.right)}", "left": tile.left, "right": tile.right}


class PatioSession:
    """One browser match. With autoplay on, the CPU strategy also plays the human seat."""

    def __init__(
        self,
        *,
        target_score: int = 200,
        game_mode: str = "target_score",
        autoplay: bool = False,
        rng: Optional[random.Random] = None,
    ):
        if type(autoplay) is not bool:
            raise MoveError(f"Autoplay must be true or false, got {autoplay!r}.")
        try:
            self.match = Match(target=target_score, mode=game_mode, rng=rng)
        except RuleError as error:
            raise MoveError(str(error)) from error
        self.autoplay = autoplay
        self.revision = 0

    @property
    def phase(self) -> str:
        return self.match.phase

    def _require_human_turn(self) -> None:
        if self.match.phase != "playing":
            raise MoveError("This round has ended. Start the next round or a new game.")
        if self.autoplay:
            raise MoveError("Autoplay is on. Turn it off to take your seat.")
        if self.match.turn != HUMAN:
            raise MoveError("Wait for your turn.")

    def play(self, tile_id: Any, position: Any) -> None:
        self._require_human_turn()
        chosen = next(
            (move for move in self.match.legal_moves(HUMAN) if tile_data(move[0])["id"] == tile_id and move[1] == position),
            None,
        )
        if chosen is None:
            raise MoveError(f"Tile {tile_id!r} cannot be played on {position!r}. Choose a highlighted tile and end.")
        self.match.play(HUMAN, *chosen)
        self.revision += 1

    def pass_turn(self) -> None:
        self._require_human_turn()
        if self.match.legal_moves(HUMAN):
            raise MoveError("You have a legal move. Play a highlighted tile before passing.")
        self.match.pass_turn(HUMAN)
        self.revision += 1

    def step_cpu(self) -> None:
        if self.match.phase != "playing":
            raise MoveError("This round has ended. Start the next round or a new game.")
        if self.match.turn == HUMAN and not self.autoplay:
            raise MoveError("The current turn belongs to you.")
        self.match.auto_turn(self.match.turn)
        self.revision += 1

    def next_round(self) -> None:
        if self.match.phase != "round_over":
            raise MoveError("A next round is available only after an unfinished match's round ends.")
        self.match.next_round()
        self.revision += 1

    def set_autoplay(self, enabled: Any) -> None:
        if type(enabled) is not bool:
            raise MoveError(f"Autoplay must be true or false, got {enabled!r}.")
        self.autoplay = enabled
        self.revision += 1

    def _round_entry(self, log) -> dict[str, Any]:
        outcome = log.outcome
        return {
            "round": log.number,
            "team": outcome.team,
            "points": outcome.points,
            "blocked": outcome.blocked,
            "scores": list(log.scores),
            "winner": None if outcome.blocked else NAMES[outcome.closer],
            "leader": NAMES[log.leader],
            "nextLeader": NAMES[outcome.next_leader],
            "teamPips": list(outcome.team_pips),
            "unplayed": [{"name": name, "value": value} for name, value in zip(NAMES, outcome.hand_pips)],
        }

    def snapshot(self) -> dict[str, Any]:
        match = self.match
        log = match.round
        playing = match.phase == "playing"
        moves = match.legal_moves(HUMAN) if playing and not self.autoplay else []
        opening = next((turn.tile for turn in log.turns if turn.tile is not None), None)
        history = [
            {"player": turn.seat, "name": NAMES[turn.seat], "type": "pass"}
            if turn.tile is None
            else {
                "player": turn.seat,
                "name": NAMES[turn.seat],
                "type": "play",
                "tile": tile_data(turn.tile),
                "position": turn.end,
            }
            for turn in log.turns[-12:]
        ]
        outcome = log.outcome
        return {
            "revision": self.revision,
            "phase": match.phase,
            "round": log.number,
            "leader": log.leader,
            "target": match.target,
            "mode": match.mode,
            "autoplay": self.autoplay,
            "turn": match.turn,
            "scores": match.scores.copy(),
            "board": [tile_data(tile) for tile in match.board.dominoes],
            "opening": tile_data(opening)["id"] if opening else None,
            "ends": {"left": match.board.left_value(), "right": match.board.right_value()},
            "players": [
                {
                    "name": name,
                    "team": seat % 2,
                    "count": len(hand),
                    "passed": match.passed[seat],
                    "hand": [tile_data(tile) for tile in hand] if seat == HUMAN or not playing else None,
                    "value": sum(tile.value() for tile in hand) if seat == HUMAN or not playing else None,
                }
                for seat, (name, hand) in enumerate(zip(NAMES, match.hands))
            ],
            "moves": [{"tile": tile_data(tile)["id"], "position": position} for tile, position in moves],
            "history": history,
            "result": None
            if outcome is None
            else {
                "team": outcome.team,
                "points": outcome.points,
                "blocked": outcome.blocked,
                "nextLeader": outcome.next_leader,
            },
            "rounds": [self._round_entry(entry) for entry in match.rounds if entry.outcome is not None],
        }
