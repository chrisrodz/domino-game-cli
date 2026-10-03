"""CPU AI strategies for domino gameplay."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Optional

from domino_game.game.rules import Move
from domino_game.models import Board, Domino


class CPUStrategy(ABC):
    """Abstract base class for CPU strategies."""

    @abstractmethod
    def get_best_move(self, hand: Sequence[Domino], valid_moves: Sequence[Move], board: Board) -> Optional[Move]:
        """
        Choose a move for a CPU seat.

        Args:
            hand: Every tile the CPU still holds, including ones it cannot play now
            valid_moves: The legal (domino, end) moves for this turn
            board: The current board state

        Returns:
            One of `valid_moves`, or None when there are none
        """


class SimpleStrategy(CPUStrategy):
    """Simple greedy strategy: play highest value dominoes, prefer doubles."""

    # The greedy strategy ignores `hand` and `board`; the interface supplies them for smarter strategies.
    def get_best_move(self, hand: Sequence[Domino], valid_moves: Sequence[Move], board: Board) -> Optional[Move]:  # noqa: ARG002
        """Play the highest-value tile, with a bonus for doubles; ignores the rest of the hand and the board."""
        best_move = None
        best_score = -1

        for domino, position in valid_moves:
            score = domino.value()
            # Bonus for doubles (play them when possible)
            if domino.is_double():
                score += 5

            if score > best_score:
                best_score = score
                best_move = (domino, position)

        return best_move
