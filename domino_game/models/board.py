"""Board model for managing the domino line."""

from typing import Optional

from rich.text import Text

from domino_game.models.domino import Domino


class Board:
    """Manages the domino line on the table."""

    def __init__(self):
        self.dominoes: list[Domino] = []

    def is_empty(self) -> bool:
        return len(self.dominoes) == 0

    def left_value(self) -> Optional[int]:
        """Get the value on the left end of the line."""
        if self.is_empty():
            return None
        return self.dominoes[0].left

    def right_value(self) -> Optional[int]:
        """Get the value on the right end of the line."""
        if self.is_empty():
            return None
        return self.dominoes[-1].right

    def can_play(self, domino: Domino) -> bool:
        """Check if a domino can be played."""
        if self.is_empty():
            return True

        left = self.left_value()
        right = self.right_value()

        return domino.has_value(left) or domino.has_value(right)

    def play_domino(self, domino: Domino, on_left: bool = False) -> bool:
        """
        Play a domino on the board.
        Returns True if successful, False otherwise.
        """
        if self.is_empty():
            self.dominoes.append(domino)
            return True

        left = self.left_value()
        right = self.right_value()

        if on_left:
            if domino.right == left:
                self.dominoes.insert(0, domino)
                return True
            elif domino.left == left:
                self.dominoes.insert(0, domino.flip())
                return True
        else:
            if domino.left == right:
                self.dominoes.append(domino)
                return True
            elif domino.right == right:
                self.dominoes.append(domino.flip())
                return True

        return False

    def __str__(self) -> str:
        if self.is_empty():
            return "Empty board"
        return " ".join(str(d) for d in self.dominoes)

    def to_rich(self) -> Text:
        """Return a rich-formatted representation of the board."""
        if self.is_empty():
            return Text("Empty board", style="dim")

        text = Text()
        for i, d in enumerate(self.dominoes):
            if i > 0:
                text.append(" ")
            text.append(d.to_rich())
        return text
