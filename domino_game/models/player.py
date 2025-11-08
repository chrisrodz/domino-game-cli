"""Player model and player type enum."""

from enum import Enum

from domino_game.models.domino import Domino


class PlayerType(Enum):
    HUMAN = "human"
    CPU = "cpu"


class Player:
    """Represents a player in the game."""

    def __init__(self, name: str, player_type: PlayerType, team: int):
        self.name = name
        self.player_type = player_type
        self.team = team  # 0 or 1
        self.hand: list[Domino] = []
        self.passed_last_turn = False

    def add_domino(self, domino: Domino):
        """Add a domino to the player's hand."""
        self.hand.append(domino)

    def remove_domino(self, domino: Domino):
        """Remove a domino from the player's hand."""
        self.hand.remove(domino)

    def has_domino(self, domino: Domino) -> bool:
        """Check if player has a specific domino."""
        return domino in self.hand

    def has_double_six(self) -> bool:
        """Check if player has the double-six."""
        return Domino(6, 6) in self.hand

    def hand_value(self) -> int:
        """Total value of all dominoes in hand."""
        return sum(d.value() for d in self.hand)

    def is_out(self) -> bool:
        """Check if player has played all dominoes."""
        return len(self.hand) == 0

    def get_valid_moves(self, board) -> list[tuple[Domino, str]]:
        """
        Get all valid moves for this player.
        Returns list of (domino, position) where position is 'left' or 'right'.
        """
        if board.is_empty():
            # First move must be double-six if available
            if self.has_double_six():
                return [(Domino(6, 6), "first")]
            return [(self.hand[0], "first")] if self.hand else []

        moves = []
        left = board.left_value()
        right = board.right_value()

        for domino in self.hand:
            if domino.has_value(left):
                moves.append((domino, "left"))
            if domino.has_value(right) and left != right:
                moves.append((domino, "right"))
            elif domino.has_value(right) and left == right:
                # Avoid duplicates when both ends are the same
                if not any(m[0] == domino and m[1] == "left" for m in moves):
                    moves.append((domino, "right"))

        return moves

    def __str__(self) -> str:
        hand_str = ", ".join(str(d) for d in sorted(self.hand, key=lambda d: d.value()))
        return f"{self.name} ({self.player_type.value}, Team {self.team + 1}): {hand_str}"
