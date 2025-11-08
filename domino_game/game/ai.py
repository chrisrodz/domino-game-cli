"""CPU AI strategies for domino gameplay."""

from typing import List, Tuple, Optional
from abc import ABC, abstractmethod
from domino_game.models.domino import Domino


class CPUStrategy(ABC):
    """Abstract base class for CPU strategies."""

    @abstractmethod
    def get_best_move(
        self,
        player,
        valid_moves: List[Tuple[Domino, str]],
        board
    ) -> Optional[Tuple[Domino, str]]:
        """
        Get the best move for the CPU player.

        Args:
            player: The CPU player
            valid_moves: List of valid (domino, position) tuples
            board: The current board state

        Returns:
            The chosen (domino, position) tuple or None
        """
        pass


class SimpleStrategy(CPUStrategy):
    """Simple greedy strategy: play highest value dominoes, prefer doubles."""

    def get_best_move(
        self,
        player,
        valid_moves: List[Tuple[Domino, str]],
        board
    ) -> Optional[Tuple[Domino, str]]:
        """
        Simple CPU AI: prioritize high-value dominoes and doubles.

        Strategy: Play highest value domino, prefer doubles.
        """
        if not valid_moves:
            return None

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
