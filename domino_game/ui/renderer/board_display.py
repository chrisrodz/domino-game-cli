"""Board rendering for domino game."""

from typing import Optional

from rich.align import Align
from rich.box import DOUBLE, ROUNDED
from rich.panel import Panel
from rich.text import Text


class BoardDisplay:
    """Renders the domino chain in the center of the table."""

    @staticmethod
    def render_board(board, last_played_domino: Optional[object] = None) -> Panel:
        """
        Create a visual representation of the domino board.

        Args:
            board: The game board with dominoes
            last_played_domino: The most recently played domino to highlight

        Returns:
            Rich Panel with the board display
        """
        if board.is_empty():
            content = Text("Empty Board - Waiting for first move", style="dim italic", justify="center")
            return Panel(Align.center(content), title="🎲 DOMINO BOARD 🎲", border_style="cyan", box=ROUNDED, padding=(1, 2))

        # Build the domino chain
        domino_chain = Text()
        for i, domino in enumerate(board.dominoes):
            # Check if this is the last played domino
            is_last_played = (
                last_played_domino and domino.left == last_played_domino.left and domino.right == last_played_domino.right
            )

            # Add spacing between dominoes
            if i > 0:
                domino_chain.append(" ")

            # Render the domino with highlighting if it's the last played
            if is_last_played:
                domino_chain.append("►", style="bold yellow")

            domino_chain.append(domino.to_rich())

            if is_last_played:
                domino_chain.append("◄", style="bold yellow")

        # Add endpoint information
        endpoints = Text()
        endpoints.append("\n\n")
        endpoints.append("◄ Left: ", style="bold cyan")
        endpoints.append(f"[{board.left_value()}]", style="bold yellow")
        endpoints.append("  |  ", style="dim")
        endpoints.append("Right: ", style="bold cyan")
        endpoints.append(f"[{board.right_value()}]", style="bold yellow")
        endpoints.append(" ►", style="bold cyan")

        # Combine everything
        full_display = Text()
        full_display.append(domino_chain)
        full_display.append(endpoints)

        return Panel(
            Align.center(full_display), title="🎲 DOMINO BOARD 🎲", border_style="cyan bold", box=DOUBLE, padding=(1, 2)
        )
