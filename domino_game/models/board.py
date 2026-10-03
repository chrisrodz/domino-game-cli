"""Board model for managing the domino line."""

from typing import Optional

from rich.text import Text

from domino_game.models.domino import Domino


class Board:
    """Manages the domino line on the table."""

    def __init__(self) -> None:
        self.dominoes: list[Domino] = []

    def is_empty(self) -> bool:
        return len(self.dominoes) == 0

    def ends(self) -> Optional[tuple[int, int]]:
        """Open (left, right) values, or None before the first tile."""
        if not self.dominoes:
            return None
        return self.dominoes[0].left, self.dominoes[-1].right

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
        ends = self.ends()
        if ends is None:
            return True
        return domino.has_value(ends[0]) or domino.has_value(ends[1])

    def play_domino(self, domino: Domino, *, on_left: bool = False) -> bool:
        """Play `domino` on one end, flipping it to match. Returns False when it does not fit."""
        ends = self.ends()
        if ends is None:
            self.dominoes.append(domino)
            return True
        left, right = ends
        if on_left:
            if domino.right == left:
                self.dominoes.insert(0, domino)
                return True
            if domino.left == left:
                self.dominoes.insert(0, domino.flip())
                return True
        elif domino.left == right:
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
