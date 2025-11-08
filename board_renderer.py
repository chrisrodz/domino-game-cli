"""
Full-screen board renderer for the Caribbean Domino Game.
Displays a constant game board with players positioned around a table.
"""

from typing import List, Optional, Tuple
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.box import ROUNDED, DOUBLE, HEAVY
import time


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
            return Panel(
                Align.center(content),
                title="🎲 DOMINO BOARD 🎲",
                border_style="cyan",
                box=ROUNDED,
                padding=(1, 2)
            )

        # Build the domino chain
        domino_chain = Text()
        for i, domino in enumerate(board.dominoes):
            # Check if this is the last played domino
            is_last_played = (last_played_domino and
                            domino.left == last_played_domino.left and
                            domino.right == last_played_domino.right)

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
            Align.center(full_display),
            title="🎲 DOMINO BOARD 🎲",
            border_style="cyan bold",
            box=DOUBLE,
            padding=(1, 2)
        )


class PlayerDisplay:
    """Renders player information around the table."""

    @staticmethod
    def render_cpu_player(
        player,
        is_current: bool = False,
        position: str = "top"
    ) -> Panel:
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
        tile_text.append(f"\n{tile_count} tile{'s' if tile_count != 1 else ''} remaining",
                        style="bold yellow" if is_current else "dim")

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

        return Panel(
            Align.center(content),
            title=title,
            border_style=border_style,
            box=box,
            padding=(0, 1)
        )

    @staticmethod
    def render_human_player(
        player,
        valid_moves: List[Tuple],
        is_current: bool = False
    ) -> Panel:
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
            hand_table.add_row(
                domino.to_rich(),
                str(domino.value())
            )

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
        from rich.console import Group
        content_group = Group(*content_parts)

        # Choose styling
        if is_current:
            border_style = "bold green"
            box = HEAVY
            title = f"▶ YOUR TURN ◀"
        else:
            border_style = "blue"
            box = ROUNDED
            title = f"{player.name} (Team {player.team + 1})"

        return Panel(
            content_group,
            title=title,
            border_style=border_style,
            box=box,
            padding=(1, 2)
        )


class GameRenderer:
    """Main rendering engine for the full-screen domino game display."""

    def __init__(self, console: Console = None):
        """Initialize the game renderer."""
        self.console = console or Console()
        self.layout = None
        self.live = None
        self.last_played_domino = None

    def create_layout(self) -> Layout:
        """Create the full-screen layout structure."""
        layout = Layout()

        # Split into main sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="input_area", size=3),
            Layout(name="footer", size=1)
        )

        # Split main section into three rows
        layout["main"].split_column(
            Layout(name="top_player", size=7),
            Layout(name="middle", ratio=1),
            Layout(name="human_player", size=12)
        )

        # Split middle section into three columns
        layout["middle"].split_row(
            Layout(name="left_player", ratio=1),
            Layout(name="board", ratio=2),
            Layout(name="right_player", ratio=1)
        )

        return layout

    def render_header(self, round_number: int, team_scores: List[int], target_score: int) -> Panel:
        """Render the game header with scores and round info."""
        header_text = Text()

        # Round info
        header_text.append(f"Round {round_number}", style="bold cyan")
        header_text.append("  |  ", style="dim")

        # Team scores
        header_text.append("Team 1: ", style="bold blue")
        header_text.append(f"{team_scores[0]}", style="bold white")
        header_text.append(f"/{target_score}", style="dim")
        header_text.append("  vs  ", style="dim")
        header_text.append("Team 2: ", style="bold red")
        header_text.append(f"{team_scores[1]}", style="bold white")
        header_text.append(f"/{target_score}", style="dim")

        return Panel(Align.center(header_text), border_style="cyan", box=ROUNDED)

    def render_input_area(self, prompt_text: str = "") -> Panel:
        """Render the input area for user prompts."""
        if prompt_text:
            content = Text(prompt_text, style="bold yellow", justify="left")
        else:
            content = Text("", style="dim")

        return Panel(
            content,
            border_style="yellow" if prompt_text else "dim",
            box=ROUNDED,
            padding=(0, 1)
        )

    def render_footer(self, message: str = "") -> Text:
        """Render the footer with status messages."""
        if message:
            return Text(message, style="dim italic", justify="center")
        return Text("Caribbean Dominoes - Press Ctrl+C to quit", style="dim", justify="center")

    def update_display(
        self,
        game,
        valid_moves: Optional[List[Tuple]] = None,
        status_message: str = "",
        prompt_text: str = ""
    ):
        """
        Update the entire display with current game state.

        Args:
            game: The Game object with current state
            valid_moves: Valid moves for human player (if their turn)
            status_message: Status message for footer
            prompt_text: Text to display in input area
        """
        if not self.layout:
            self.layout = self.create_layout()

        # Update header
        self.layout["header"].update(
            self.render_header(game.round_number, game.team_scores, game.target_score)
        )

        # Update board
        self.layout["board"].update(
            BoardDisplay.render_board(game.board, self.last_played_domino)
        )

        # Update players - Counter-clockwise layout with alternating teams
        # Player 0: Human (bottom) - Team 0
        # Player 1: Opponent 1 (right) - Team 1
        # Player 2: Ally (top) - Team 0
        # Player 3: Opponent 2 (left) - Team 1

        current_idx = game.current_player_idx
        players = game.players

        # Top player (Ally - index 2)
        self.layout["top_player"].update(
            PlayerDisplay.render_cpu_player(
                players[2],
                is_current=(current_idx == 2),
                position="top"
            )
        )

        # Left player (Opponent 2 - index 3)
        self.layout["left_player"].update(
            PlayerDisplay.render_cpu_player(
                players[3],
                is_current=(current_idx == 3),
                position="left"
            )
        )

        # Right player (Opponent 1 - index 1)
        self.layout["right_player"].update(
            PlayerDisplay.render_cpu_player(
                players[1],
                is_current=(current_idx == 1),
                position="right"
            )
        )

        # Bottom player (Human - index 0)
        self.layout["human_player"].update(
            PlayerDisplay.render_human_player(
                players[0],
                valid_moves or [],
                is_current=(current_idx == 0)
            )
        )

        # Update input area
        self.layout["input_area"].update(self.render_input_area(prompt_text))

        # Update footer
        self.layout["footer"].update(self.render_footer(status_message))

    def start_live_display(self):
        """Start the live display mode."""
        if not self.layout:
            self.layout = self.create_layout()

        self.live = Live(
            self.layout,
            console=self.console,
            screen=True,
            auto_refresh=False
        )
        self.live.start()

    def stop_live_display(self):
        """Stop the live display mode."""
        if self.live:
            self.live.stop()
            self.live = None

    def refresh(self):
        """Refresh the display."""
        if self.live:
            self.live.refresh()

    def mark_last_played(self, domino):
        """Mark a domino as the last played for highlighting."""
        self.last_played_domino = domino

    def clear_last_played(self):
        """Clear the last played domino highlight."""
        self.last_played_domino = None

    def pause_for_effect(self, seconds: float = 0.8):
        """Pause briefly for visual effect after tile placement."""
        time.sleep(seconds)

    def prompt_user_input(
        self,
        game,
        prompt_text: str,
        valid_moves: Optional[List[Tuple]] = None,
        valid_choices: Optional[List[str]] = None
    ) -> str:
        """
        Prompt user for input while keeping the live display running.

        Args:
            game: The Game object
            prompt_text: Text to show in the prompt area
            valid_moves: Valid moves to display (if applicable)
            valid_choices: List of valid input choices (e.g., ["1", "2", "3"])

        Returns:
            The user's input as a string
        """
        # Update display with prompt
        self.update_display(game, valid_moves=valid_moves, prompt_text=prompt_text)
        self.refresh()

        # Get input using console.input which works with Live display
        while True:
            try:
                user_input = self.console.input("> ").strip()

                # Validate input if choices provided
                if valid_choices and user_input not in valid_choices:
                    error_prompt = f"{prompt_text}\n[red]Invalid choice. Please enter one of: {', '.join(valid_choices)}[/red]"
                    self.update_display(game, valid_moves=valid_moves, prompt_text=error_prompt)
                    self.refresh()
                    continue

                # Clear the prompt after successful input
                self.update_display(game, valid_moves=valid_moves, prompt_text="")
                self.refresh()

                return user_input

            except (KeyboardInterrupt, EOFError):
                raise

    def prompt_confirmation(self, game, message: str) -> bool:
        """
        Prompt user for confirmation while keeping display running.

        Args:
            game: The Game object
            message: Message to display

        Returns:
            True (always, since we just need them to press Enter)
        """
        prompt_text = f"{message} [Press Enter to continue]"
        self.update_display(game, prompt_text=prompt_text)
        self.refresh()

        try:
            self.console.input()
        except (KeyboardInterrupt, EOFError):
            raise

        # Clear prompt
        self.update_display(game, prompt_text="")
        self.refresh()

        return True
