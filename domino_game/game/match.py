"""Headless match state machine: deal, turns, rounds, and scores with no I/O.

Every action is validated against `rules`; invalid actions raise `RuleError`
and leave the match unchanged. Each round keeps its deal and turn log so a
referee can replay and audit the match independently.
"""

import random
from dataclasses import dataclass, field
from typing import Literal, Optional

from domino_game.game.ai import CPUStrategy, SimpleStrategy
from domino_game.game.deck import create_deck
from domino_game.game.rules import (
    HAND_SIZE,
    OPENING_TILE,
    SEATS,
    End,
    Move,
    RoundOutcome,
    RuleError,
    is_blocked,
    legal_moves,
    next_seat,
    score_round,
)
from domino_game.models import Board, Domino

Phase = Literal["playing", "round_over", "match_over"]
Mode = Literal["target_score", "single_round"]
MAX_TARGET = 1000


@dataclass(frozen=True)
class Turn:
    seat: int
    tile: Optional[Domino]
    """None when the seat passed."""
    end: Optional[End]


@dataclass
class RoundLog:
    number: int
    leader: int
    deal: tuple[tuple[Domino, ...], ...]
    turns: list[Turn] = field(default_factory=list)
    outcome: Optional[RoundOutcome] = None
    scores: Optional[tuple[int, int]] = None
    """Team totals after this round was scored."""


class Match:
    """One partnership match played to a target score or for a single round."""

    def __init__(self, *, target: int = 200, mode: Mode = "target_score", rng: Optional[random.Random] = None):
        if type(target) is not int or not 1 <= target <= MAX_TARGET:
            raise RuleError(f"Target score must be an integer from 1 to {MAX_TARGET}, got {target!r}.")
        if mode not in ("target_score", "single_round"):
            raise RuleError(f"Unknown game mode: {mode!r}.")
        self.target = target
        self.mode: Mode = mode
        self.rng = rng or random.Random()
        self.scores = [0, 0]
        self.rounds: list[RoundLog] = []
        self.hands: list[list[Domino]] = [[] for _ in range(SEATS)]
        self.board = Board()
        self.passed = [False] * SEATS
        self.turn = 0
        self.phase: Phase = "playing"
        self._deal(leader=None)

    @property
    def round(self) -> RoundLog:
        return self.rounds[-1]

    @property
    def round_number(self) -> int:
        return self.round.number

    @property
    def outcome(self) -> Optional[RoundOutcome]:
        return self.round.outcome

    def _deal(self, *, leader: Optional[int]) -> None:
        deck = create_deck()
        self.rng.shuffle(deck)
        self.hands = [deck[seat * HAND_SIZE : (seat + 1) * HAND_SIZE] for seat in range(SEATS)]
        if leader is None:
            leader = next(seat for seat, hand in enumerate(self.hands) if OPENING_TILE in hand)
        self.board = Board()
        self.passed = [False] * SEATS
        self.turn = leader
        self.phase = "playing"
        self.rounds.append(RoundLog(len(self.rounds) + 1, leader, tuple(tuple(hand) for hand in self.hands)))

    def legal_moves(self, seat: int) -> list[Move]:
        if self.phase != "playing" or seat != self.turn:
            return []
        must_open = OPENING_TILE if self.round_number == 1 else None
        return legal_moves(self.hands[seat], self.board, must_open_with=must_open)

    def _require_turn(self, seat: int) -> None:
        if self.phase != "playing":
            raise RuleError(f"Round {self.round_number} has ended; seat {seat} cannot act.")
        if seat != self.turn:
            raise RuleError(f"It is seat {self.turn}'s turn, not seat {seat}'s.")

    def play(self, seat: int, tile: Domino, end: End) -> None:
        self._require_turn(seat)
        if (tile, end) not in self.legal_moves(seat):
            raise RuleError(
                f"Seat {seat} cannot play {tile} on {end!r} with ends {self.board.left_value()}/{self.board.right_value()}."
            )
        if not self.board.play_domino(tile, on_left=end == "left"):
            raise RuleError(f"Board rejected {tile} on {end!r}; no turn was consumed.")
        self.hands[seat].remove(tile)
        self.passed[seat] = False
        self.round.turns.append(Turn(seat, tile, end))
        if not self.hands[seat] or is_blocked(self.hands, self.board):
            self._finish_round(closer=seat)
        else:
            self.turn = next_seat(seat)

    def pass_turn(self, seat: int) -> None:
        self._require_turn(seat)
        if self.legal_moves(seat):
            raise RuleError(f"Seat {seat} holds a legal tile and cannot pass.")
        self.passed[seat] = True
        self.round.turns.append(Turn(seat, None, None))
        self.turn = next_seat(seat)

    def auto_turn(self, seat: int, strategy: CPUStrategy = SimpleStrategy()) -> Turn:
        """Play the strategy's move for `seat`, or pass when it has none."""
        moves = self.legal_moves(seat)
        if not moves:
            self.pass_turn(seat)
        else:
            choice = strategy.get_best_move(None, moves, self.board)
            if choice is None:
                raise RuleError(f"{type(strategy).__name__} returned no move for seat {seat} despite legal moves.")
            self.play(seat, *choice)
        return self.round.turns[-1]

    def _finish_round(self, *, closer: int) -> None:
        outcome = score_round(self.hands, closer=closer)
        self.scores[outcome.team] += outcome.points
        self.round.outcome = outcome
        self.round.scores = (self.scores[0], self.scores[1])
        over = self.mode == "single_round" or max(self.scores) >= self.target
        self.phase = "match_over" if over else "round_over"

    def next_round(self) -> None:
        if self.phase != "round_over":
            raise RuleError(
                f"Round {self.round_number} is {self.phase!r}; deal the next round only after a round ends mid-match."
            )
        self._deal(leader=self.round.outcome.next_leader)

    @property
    def winner(self) -> Optional[int]:
        """Winning team once the match is over; only a round's winners score, so they crossed the target."""
        return self.round.outcome.team if self.phase == "match_over" else None
