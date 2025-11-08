"""Main game renderer for full-screen display."""

import time
from typing import List, Tuple, Optional
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.box import ROUNDED

from domino_game.ui.renderer.board_display import BoardDisplay
from domino_game.ui.renderer.player_display import PlayerDisplay


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
