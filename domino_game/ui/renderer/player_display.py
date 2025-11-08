"""Player display rendering."""

from rich.align import Align
from rich.box import HEAVY, ROUNDED
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class PlayerDisplay:
    """Renders player information around the table."""

    @staticmethod
    def render_cpu_player(player, is_current: bool = False, position: str = "top") -> Panel:
        """
        Render a CPU player with tile count indicator.

        Args:
            player: The player object
            is_current: Whether this player is currently playing
            position: Position around table (top, left, right)

        Returns:
            Rich Panel with player info
        """
        tile_count = len(player.hand)

        # Create tile count visualization with card backs
        card_backs = "🂠 " * tile_count

        # Player name and team
        name_text = Text()
        name_text.append(player.name, style="bold white")
        name_text.append(f" (Team {player.team + 1})", style="dim")

        # Tile information
        tile_text = Text()
        tile_text.append(card_backs, style="")
        tile_text.append(
            f"\n{tile_count} tile{'s' if tile_count != 1 else ''} remaining", style="bold yellow" if is_current else "dim"
        )

        # Add pass indicator if they passed last turn
        if player.passed_last_turn:
            tile_text.append("\n[PASSED]", style="red italic")

        # Combine content
        content = Text()
        content.append(name_text)
        content.append("\n")
        content.append(tile_text)

        # Choose border style based on current player and team
        if is_current:
            border_style = "bold green"
            box = HEAVY
            title = f"▶ {player.name.upper()} (PLAYING) ◀"
        else:
            border_style = "blue" if player.team == 0 else "red"
            box = ROUNDED
            title = player.name

        return Panel(Align.center(content), title=title, border_style=border_style, box=box, padding=(0, 1))

    @staticmethod
    def render_human_player(player, valid_moves: list[tuple], is_current: bool = False) -> Panel:
        """
        Render the human player with their actual hand visible.

        Args:
            player: The player object (human)
            valid_moves: List of (domino, position) tuples for valid moves
            is_current: Whether it's the player's turn

        Returns:
            Rich Panel with player's hand and move options
        """
        # Create hand display table
        hand_table = Table(show_header=True, box=None, padding=(0, 1))
        hand_table.add_column("Domino", justify="center", style="cyan")
        hand_table.add_column("Value", justify="center", style="yellow")

        for domino in player.hand:
            hand_table.add_row(domino.to_rich(), str(domino.value()))

        # Create content
        content_parts = [hand_table]

        # Add valid moves if it's their turn
        if is_current and valid_moves:
            moves_text = Text("\n\n")
            moves_text.append("Valid Moves:", style="bold green")

            for idx, (domino, position) in enumerate(valid_moves, 1):
                moves_text.append(f"\n{idx}. ", style="bold white")
                moves_text.append(domino.to_rich())

                if position == "left":
                    moves_text.append(" ⬅️  Play on LEFT", style="cyan")
                elif position == "right":
                    moves_text.append(" ➡️  Play on RIGHT", style="cyan")
                else:  # first move
                    moves_text.append(" 🎯 First move", style="yellow")

                moves_text.append(f" (value: {domino.value()})", style="dim")

            content_parts.append(moves_text)
        elif is_current and not valid_moves:
            no_moves = Text("\n\n", style="")
            no_moves.append("No valid moves available - You must PASS", style="bold red")
            content_parts.append(no_moves)

        # Combine all content
        content_group = Group(*content_parts)

        # Choose styling
        if is_current:
            border_style = "bold green"
            box = HEAVY
            title = "▶ YOUR TURN ◀"
        else:
            border_style = "blue"
            box = ROUNDED
            title = f"{player.name} (Team {player.team + 1})"

        return Panel(content_group, title=title, border_style=border_style, box=box, padding=(1, 2))
