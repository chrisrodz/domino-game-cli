"""Player-visible snapshots and public history for Jev decisions."""

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Literal

from domino_game.game.knowledge import (
    Ends,
    JSONValue,
    KnowledgeInput,
    ObservationError,
    TableKnowledge,
    Tile,
    derive_knowledge,
    hand_connections,
    suit_counts,
)
from domino_game.models import Board, Domino, Player
from domino_game.models.player import AIDifficulty

if TYPE_CHECKING:
    from domino_game.game.engine import Game


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
    facts: dict[str, JSONValue]

    def to_option(self) -> dict[str, JSONValue]:
        option: dict[str, JSONValue] = {
            "tile": list(self.tile),
            "side": self.side,
            "resulting_ends": list(self.ends_after),
            "remaining_hand_pips": self.remaining_pips,
            "remaining_hand": [list(tile) for tile in self.remaining_tiles],
            "own_playable_tiles_on_resulting_board": self.playable_tiles_after,
            **self.facts,
        }
        if self.forced_pass_seats is not None:
            option["seats_known_to_be_unable_to_play_on_resulting_board"] = list(self.forced_pass_seats)
        return option


@dataclass(frozen=True)
class TurnContext:
    seat: int
    difficulty: AIDifficulty
    tile_counts: tuple[int, ...]
    own_team: int
    team_scores: tuple[int, ...]
    target_score: int


@dataclass(frozen=True)
class TurnObservation:
    state: dict[str, JSONValue]
    candidates: tuple[MoveCandidate, ...]
    context: TurnContext
    knowledge: TableKnowledge


def board_ends(board: Board) -> Ends:
    return board.left_value(), board.right_value()


def signal_evidence(turns: list[TurnRecord]) -> list[dict[str, JSONValue]]:
    """Later observed plays can prove an earlier alternative existed; hidden hands cannot."""
    evidence = []
    for index, turn in enumerate(turns):
        if turn.action != "play":
            continue
        alternatives = [
            later.tile
            for later in turns[index + 1 :]
            if later.seat == turn.seat and later.tile is not None and any(end in later.tile for end in turn.ends_before)
        ]
        if turn.ends_before == (None, None):
            choice = "compulsory_opening"
        elif turn.tiles_remaining == 0:
            choice = "last_tile"
        elif alternatives or (
            turn.ends_before[0] != turn.ends_before[1] and tuple(sorted(turn.ends_before)) == tuple(sorted(turn.tile))
        ):
            choice = "demonstrated_alternative"
        else:
            choice = "unknown_whether_forced"
        evidence.append(
            {
                **turn.to_state(),
                "choice_evidence": choice,
                "later_observed_alternative_tiles": [list(tile) for tile in alternatives],
                "introduced_suit": turn.ends_after[0 if turn.side == "left" else 1],
            }
        )
    return evidence


def candidate_facts(tiles: tuple[Tile, ...], ends: Ends, observation: TurnObservation) -> dict[str, JSONValue]:
    knowledge, context = observation.knowledge, observation.context
    unseen_playable = sum(any(end in tile for end in ends) for tile in knowledge.unseen_tiles)
    own_playable = sum(any(end in tile for end in ends) for tile in tiles)
    facts: dict[str, JSONValue] = {
        "connections": hand_connections(tiles, ends),
        "unseen_tiles_matching_resulting_ends": unseen_playable,
        "unseen_suit_counts": suit_counts(knowledge.unseen_tiles),
        "remaining_doubles": [
            {
                "tile": list(tile),
                "playable_on_resulting_board": tile[0] in ends,
                "other_unplayed_tiles_in_suit": sum(
                    tile[0] in other and other != tile for other in (*tiles, *knowledge.unseen_tiles)
                ),
                "permanently_stranded": tile[0] not in ends
                and not any(tile[0] in other and other != tile for other in (*tiles, *knowledge.unseen_tiles)),
            }
            for tile in tiles
            if tile[0] == tile[1]
        ],
        "blocks_round": bool(tiles) and own_playable == 0 and unseen_playable == 0,
        "blocked_points": sum(sum(tile) for tile in (*tiles, *knowledge.unseen_tiles)),
    }
    partner = (context.seat + 2) % 4
    opponents = ((context.seat + 1) % 4, (context.seat + 3) % 4)
    own_pips = sum(sum(tile) for tile in tiles)
    opponent_min = min(knowledge.pip_bounds[seat][0] for seat in opponents)
    if own_pips <= opponent_min or knowledge.pip_bounds[partner][1] <= opponent_min:
        block_outcome = "team_win"
    elif any(knowledge.pip_bounds[seat][1] < min(own_pips, knowledge.pip_bounds[partner][0]) for seat in opponents):
        block_outcome = "team_loss"
    else:
        block_outcome = "uncertain"
    facts["blocking_outcome_from_bounds"] = block_outcome
    if context.difficulty == AIDifficulty.HARD:
        compatible = {
            seat: sum(any(end in tile for end in ends) for tile in possible)
            for seat, possible in knowledge.possible_tiles.items()
        }
        next_opponent = opponents[0]
        facts["possible_matching_tiles_by_seat"] = {str(seat): count for seat, count in compatible.items()}
        facts["next_opponent_forced_pass"] = compatible[next_opponent] == 0
        facts["next_opponent_possible_exit"] = context.tile_counts[next_opponent] == 1 and compatible[next_opponent] > 0
        facts["next_opponent_guaranteed_exit"] = context.tile_counts[next_opponent] == 1 and compatible[next_opponent] == len(
            knowledge.possible_tiles[next_opponent]
        )
        facts["partner_cannot_play_on_unchanged_ends"] = compatible[partner] == 0
        facts["partner_exit_after_next_pass"] = (
            compatible[next_opponent] == 0
            and context.tile_counts[partner] == 1
            and compatible[partner] == len(knowledge.possible_tiles[partner])
        )
        facts["blocking_pressure"] = unseen_playable <= 2 or sum(count == 0 for count in compatible.values()) >= 2
        facts["turn_order_caution"] = (
            "Only the next opponent acts immediately on these ends; later seats may face changed ends"
        )
    return facts


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
        state["public_signal_evidence_this_round"] = signal_evidence(
            [turn for turn in game.turn_history if turn.round_number == game.round_number]
        )

    knowledge = derive_knowledge(
        KnowledgeInput(
            own_tiles=tuple((tile.left, tile.right) for tile in player.hand),
            board_tiles=tuple((tile.left, tile.right) for tile in game.board.dominoes),
            other_counts={index: len(other.hand) for index, other in enumerate(game.players) if index != seat},
            missing_numbers=missing,
        )
    )
    context = TurnContext(
        seat=seat,
        difficulty=player.ai_difficulty,
        tile_counts=tuple(len(other.hand) for other in game.players),
        own_team=player.team,
        team_scores=tuple(game.team_scores),
        target_score=game.target_score,
    )
    state["public_knowledge"] = knowledge.to_state()
    state["own_suit_counts"] = suit_counts(tuple((tile.left, tile.right) for tile in player.hand))
    state["roles"] = {
        "self": seat,
        "next_opponent": (seat + 1) % 4,
        "partner": (seat + 2) % 4,
        "other_opponent": (seat + 3) % 4,
    }
    view = TurnObservation(state=state, candidates=(), context=context, knowledge=knowledge)

    candidates = []
    for index, (tile, side) in enumerate(valid_moves):
        projected = Board()
        projected.dominoes = [Domino(item.left, item.right) for item in game.board.dominoes]
        if not projected.play_domino(Domino(tile.left, tile.right), on_left=side == "left"):
            raise ObservationError(f"Cannot project legal move {tile} on {side}")
        remaining = list(player.hand)
        remaining.remove(tile)
        ends = board_ends(projected)
        forced_passes = None
        if hard:
            forced_passes = tuple(
                index
                for index, possible in knowledge.possible_tiles.items()
                if not any(any(end in item for end in ends) for item in possible)
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
                facts=candidate_facts(tuple((item.left, item.right) for item in remaining), ends, view),
            )
        )
    state["candidates"] = {candidate.move_id: candidate.to_option() for candidate in candidates}
    return TurnObservation(state=state, candidates=tuple(candidates), context=context, knowledge=knowledge)
