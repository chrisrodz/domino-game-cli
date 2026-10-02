"""Player-visible snapshots and public history for Jev decisions."""

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Literal

from domino_game.models import Board, Domino, Player
from domino_game.models.player import AIDifficulty

if TYPE_CHECKING:
    from domino_game.game.engine import Game

type Tile = tuple[int, int]
type Ends = tuple[int | None, int | None]
type JSONValue = str | int | float | bool | None | list[JSONValue] | dict[str, JSONValue]


@dataclass(frozen=True)
class TurnRecord:
    round_number: int
    seat: int
    action: Literal["play", "pass"]
    tile: Tile | None
    side: str | None
    ends_before: Ends
    ends_after: Ends
    tiles_remaining: int

    def to_state(self) -> dict[str, JSONValue]:
        return {
            **asdict(self),
            "tile": list(self.tile) if self.tile else None,
            "ends_before": list(self.ends_before),
            "ends_after": list(self.ends_after),
        }


@dataclass(frozen=True)
class RoundRecord:
    round_number: int
    winning_team: int
    points: int
    revealed_hand_pips: tuple[int, ...] | None = None

    def to_state(self) -> dict[str, JSONValue]:
        result: dict[str, JSONValue] = {
            "round_number": self.round_number,
            "winning_team": self.winning_team,
            "points": self.points,
        }
        if self.revealed_hand_pips is not None:
            result["revealed_hand_pips_by_seat"] = list(self.revealed_hand_pips)
        return result


@dataclass(frozen=True)
class MoveCandidate:
    move_id: str
    tile: Tile
    side: str
    ends_after: Ends
    remaining_pips: int
    remaining_tiles: tuple[Tile, ...]
    playable_tiles_after: int
    forced_pass_seats: tuple[int, ...] | None

    def to_option(self) -> dict[str, JSONValue]:
        option: dict[str, JSONValue] = {
            "tile": list(self.tile),
            "side": self.side,
            "resulting_ends": list(self.ends_after),
            "remaining_hand_pips": self.remaining_pips,
            "remaining_hand": [list(tile) for tile in self.remaining_tiles],
            "own_playable_tiles_on_resulting_board": self.playable_tiles_after,
        }
        if self.forced_pass_seats is not None:
            option["seats_known_to_be_unable_to_play_on_resulting_board"] = list(self.forced_pass_seats)
        return option


@dataclass(frozen=True)
class TurnObservation:
    state: dict[str, JSONValue]
    candidates: tuple[MoveCandidate, ...]


def board_ends(board: Board) -> Ends:
    return board.left_value(), board.right_value()


def build_observation(game: Game, player: Player, valid_moves: list[tuple[Domino, str]]) -> TurnObservation:
    """Copy only the acting player's hand and public facts; never serialize Game or Player."""
    seat = game.players.index(player)
    hard = player.ai_difficulty == AIDifficulty.HARD
    state: dict[str, JSONValue] = {
        "acting_seat": seat,
        "own_team": player.team,
        "own_hand": [[tile.left, tile.right] for tile in player.hand],
        "own_hand_pips": player.hand_value(),
        "board": [[tile.left, tile.right] for tile in game.board.dominoes],
        "board_ends": list(board_ends(game.board)),
        "players": [
            {"seat": index, "team": other.team, "tiles_remaining": len(other.hand)} for index, other in enumerate(game.players)
        ],
        "team_scores": list(game.team_scores),
        "round_number": game.round_number,
        "game_mode": game.game_mode,
        "target_score": game.target_score,
        "rules": {
            "set": "double-six; 28 tiles; seven per player; no drawing",
            "turn_order": "next seat is (acting_seat + 1) modulo 4; partners sit opposite",
            "passing": "must play if a legal move exists; four consecutive passes end the round",
            "going_out": "first empty hand wins for its team; points are pips in all other hands, including partner",
            "blocked": "lowest individual hand wins; tie prefers last-playing team; points include all remaining hands",
            "opening": "first round starts with double-six; later rounds start at seat 0; use supplied legal options",
        },
    }
    missing: dict[int, set[int]] = {index: set() for index in range(len(game.players))}
    if hard:
        state["public_turn_history"] = [turn.to_state() for turn in game.turn_history]
        state["public_round_results"] = [result.to_state() for result in game.round_results]
        for turn in game.turn_history:
            if turn.round_number == game.round_number and turn.action == "pass":
                missing[turn.seat].update(value for value in turn.ends_before if value is not None)
        state["known_missing_numbers_this_round"] = {str(index): sorted(numbers) for index, numbers in missing.items()}

    candidates = []
    for index, (tile, side) in enumerate(valid_moves):
        projected = Board()
        projected.dominoes = [Domino(item.left, item.right) for item in game.board.dominoes]
        if not projected.play_domino(Domino(tile.left, tile.right), on_left=side == "left"):
            raise ValueError(f"Cannot project legal move {tile} on {side}")
        remaining = list(player.hand)
        remaining.remove(tile)
        ends = board_ends(projected)
        forced_passes = None
        if hard:
            forced_passes = tuple(
                index for index, numbers in missing.items() if index != seat and all(end in numbers for end in ends)
            )
        candidates.append(
            MoveCandidate(
                move_id=f"move_{index}",
                tile=(tile.left, tile.right),
                side=side,
                ends_after=ends,
                remaining_pips=sum(item.value() for item in remaining),
                remaining_tiles=tuple((item.left, item.right) for item in remaining),
                playable_tiles_after=sum(projected.can_play(item) for item in remaining),
                forced_pass_seats=forced_passes,
            )
        )
    return TurnObservation(state=state, candidates=tuple(candidates))
