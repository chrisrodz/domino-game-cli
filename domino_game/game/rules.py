"""Puerto Rican partnership dominoes (Doscientos) rules as pure functions.

Four seats in fixed partnerships: seats 0 and 2 are team 0, seats 1 and 3 are
team 1. Turns advance seat + 1 (counter-clockwise at the table). All 28 tiles
are dealt, so there is no boneyard: a player without a legal tile passes.

- Round 1: the holder of [6|6] leads and must open with it.
- Later rounds: the winner of the previous round leads with any tile.
- A round ends when a player empties their hand ("domino") or when no seat
  can play ("tranque"). With every tile dealt, the tranque is known the moment
  the closing tile is played.
- Domino: the player's team scores every pip still held by all four seats.
- Tranque: the team with fewer pips wins and scores every pip on the table.
  Its member with fewer pips leads next; partners tied on pips resolve to the
  one nearest the closer in turn order. When team totals tie, the closer's team
  wins and the closer leads next.
"""

from dataclasses import dataclass
from typing import Literal, Optional

from domino_game.models import Board, Domino

SEATS = 4
HAND_SIZE = 7
OPENING_TILE = Domino(6, 6)

End = Literal["first", "left", "right"]
Move = tuple[Domino, End]


class RuleError(ValueError):
    """A requested action breaks the rules for the current game state."""


def team_of(seat: int) -> int:
    return seat % 2


def next_seat(seat: int) -> int:
    return (seat + 1) % SEATS


def pips(hand: list[Domino]) -> int:
    return sum(tile.value() for tile in hand)


def legal_moves(hand: list[Domino], board: Board, *, must_open_with: Optional[Domino] = None) -> list[Move]:
    """Every (tile, end) the hand may play; a tile matching both ends is listed for each end."""
    ends = board.ends()
    if ends is None:
        if must_open_with is not None:
            return [(must_open_with, "first")] if must_open_with in hand else []
        return [(tile, "first") for tile in hand]
    left, right = ends
    moves: list[Move] = []
    for tile in hand:
        if tile.has_value(left):
            moves.append((tile, "left"))
        if tile.has_value(right):
            moves.append((tile, "right"))
    return moves


def is_blocked(hands: list[list[Domino]], board: Board) -> bool:
    """True when the line is open and no seat holds a tile matching either end."""
    return not board.is_empty() and not any(legal_moves(hand, board) for hand in hands)


@dataclass(frozen=True)
class RoundOutcome:
    team: int
    points: int
    blocked: bool
    next_leader: int
    """Seat that leads the following round."""
    closer: int
    """Seat that played the last tile."""
    hand_pips: tuple[int, ...]
    team_pips: tuple[int, int]


def score_round(hands: list[list[Domino]], *, closer: int) -> RoundOutcome:
    """Score a finished round. `closer` is the seat that played the final tile."""
    if len(hands) != SEATS:
        raise RuleError(f"Scoring needs {SEATS} hands, got {len(hands)}.")
    hand_pips = tuple(pips(hand) for hand in hands)
    team_pips = (hand_pips[0] + hand_pips[2], hand_pips[1] + hand_pips[3])
    points = sum(hand_pips)
    if not hands[closer]:
        return RoundOutcome(
            team_of(closer), points, blocked=False, next_leader=closer, closer=closer, hand_pips=hand_pips, team_pips=team_pips
        )
    if any(not hand for hand in hands):
        raise RuleError(f"Seat {closer} closed the round, but a different seat has an empty hand.")
    if team_pips[0] == team_pips[1]:
        return RoundOutcome(
            team_of(closer), points, blocked=True, next_leader=closer, closer=closer, hand_pips=hand_pips, team_pips=team_pips
        )
    team = 0 if team_pips[0] < team_pips[1] else 1
    order = [(closer + step) % SEATS for step in range(SEATS)]
    members = [seat for seat in order if team_of(seat) == team]
    leader = min(members, key=lambda seat: hand_pips[seat])
    return RoundOutcome(
        team, points, blocked=True, next_leader=leader, closer=closer, hand_pips=hand_pips, team_pips=team_pips
    )
