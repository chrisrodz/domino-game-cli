"""Domino tile model."""

from dataclasses import dataclass
from rich.text import Text


@dataclass
class Domino:
    """Represents a single domino tile."""
    left: int
    right: int

    def __str__(self) -> str:
        return f"[{self.left}|{self.right}]"

    def to_rich(self) -> Text:
        """Return a rich-formatted representation with brackets."""
        colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'white']
        left_color = colors[self.left % len(colors)]
        right_color = colors[self.right % len(colors)]

        text = Text("[")
        text.append(str(self.left), style=f"bold {left_color}")
        text.append("|")
        text.append(str(self.right), style=f"bold {right_color}")
        text.append("]")
        return text

    def value(self) -> int:
        """Total value (sum of both sides)."""
        return self.left + self.right

    def is_double(self) -> bool:
        """Check if this is a double domino."""
        return self.left == self.right

    def has_value(self, value: int) -> bool:
        """Check if either side matches the given value."""
        return self.left == value or self.right == value

    def flip(self) -> 'Domino':
        """Return a flipped version of this domino."""
        return Domino(self.right, self.left)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Domino):
            return False
        return (self.left == other.left and self.right == other.right) or \
               (self.left == other.right and self.right == other.left)

    def __hash__(self) -> int:
        return hash((min(self.left, self.right), max(self.left, self.right)))
