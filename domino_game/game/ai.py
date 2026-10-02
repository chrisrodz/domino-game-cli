"""CPU AI strategies for domino gameplay."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from domino_game.models.domino import Domino
from domino_game.models.player import AIDifficulty


@dataclass(frozen=True)
class CPUSettings:
    ally: AIDifficulty = AIDifficulty.SIMPLE
    opponent_1: AIDifficulty = AIDifficulty.SIMPLE
    opponent_2: AIDifficulty = AIDifficulty.SIMPLE

    def for_seat(self, seat: int) -> AIDifficulty:
        return {1: self.opponent_1, 2: self.ally, 3: self.opponent_2}[seat]

    def requires_jev(self) -> bool:
        return any(level != AIDifficulty.SIMPLE for level in (self.ally, self.opponent_1, self.opponent_2))


class CPUStrategy(ABC):
    """Abstract base class for CPU strategies."""

    @abstractmethod
    def get_best_move(self, player, valid_moves: list[tuple[Domino, str]], board) -> tuple[Domino, str] | None:
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

    def get_best_move(self, player, valid_moves: list[tuple[Domino, str]], board) -> tuple[Domino, str] | None:
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
