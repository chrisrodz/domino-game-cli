"""Setup menu for game configuration."""

from dataclasses import dataclass
from typing import Literal, Optional

from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


@dataclass
class SetupConfig:
    """Configuration from setup menu."""

    game_mode: Literal["target_score", "single_round"]
    target_score: int


class SetupMenu:
    """Interactive setup menu for game configuration."""

    PRESET_SCORES = [100, 200, 300, 500]

    def __init__(self, console: Optional[Console] = None):
        """Initialize the setup menu."""
        self.console = console or Console()
        self.game_mode = "target_score"
        self.target_score = 200

    def run(self) -> SetupConfig:
        """Run the setup menu and return configuration."""
        self.console.clear()

        # Show title
        title = Panel(
            Align.center(Text("CARIBBEAN DOMINOES", style="bold cyan")),
            border_style="cyan",
            box=ROUNDED
        )
        self.console.print(title)
        self.console.print()

        # Get game mode
        self.console.print("[bold yellow]Game Mode[/bold yellow]")
        self.console.print("  1. Play to Target Score (multiple rounds)")
        self.console.print("  2. Single Round Only")
        self.console.print()

        while True:
            choice = self.console.input("[yellow]Select game mode (1 or 2):[/yellow] ").strip()
            if choice == "1":
                self.game_mode = "target_score"
                break
            elif choice == "2":
                self.game_mode = "single_round"
                break
            else:
                self.console.print("[red]Invalid choice. Please enter 1 or 2.[/red]")

        self.console.print()

        # Get target score only if playing to target score
        if self.game_mode == "target_score":
            self.console.print("[bold yellow]Target Score[/bold yellow]")
            for i, score in enumerate(self.PRESET_SCORES, 1):
                self.console.print(f"  {i}. {score} points")
            self.console.print(f"  {len(self.PRESET_SCORES) + 1}. Custom")
            self.console.print()

            while True:
                choice = self.console.input(f"[yellow]Select target score (1-{len(self.PRESET_SCORES) + 1}):[/yellow] ").strip()
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(self.PRESET_SCORES):
                        self.target_score = self.PRESET_SCORES[choice_num - 1]
                        break
                    elif choice_num == len(self.PRESET_SCORES) + 1:
                        # Custom input
                        while True:
                            custom = self.console.input("[yellow]Enter custom target score (50-1000):[/yellow] ").strip()
                            try:
                                custom_score = int(custom)
                                if 50 <= custom_score <= 1000:
                                    self.target_score = custom_score
                                    break
                                else:
                                    self.console.print("[red]Please enter a value between 50 and 1000.[/red]")
                            except ValueError:
                                self.console.print("[red]Please enter a valid number.[/red]")
                        break
                    else:
                        self.console.print(f"[red]Invalid choice. Please enter 1-{len(self.PRESET_SCORES) + 1}.[/red]")
                except ValueError:
                    self.console.print(f"[red]Invalid choice. Please enter 1-{len(self.PRESET_SCORES) + 1}.[/red]")
        else:
            # For single round, target_score doesn't matter but set to 0 for clarity
            self.target_score = 0

        self.console.print()

        # Show configuration summary
        summary = Panel(
            self._render_config_summary(),
            title="Configuration",
            border_style="green",
            box=ROUNDED
        )
        self.console.print(summary)
        self.console.print()

        self.console.input("[dim]Press Enter to start the game...[/dim]")
        self.console.clear()

        return SetupConfig(game_mode=self.game_mode, target_score=self.target_score)

    def _render_config_summary(self) -> Text:
        """Render configuration summary."""
        summary = Text()

        if self.game_mode == "target_score":
            summary.append("Game Mode: ", style="bold")
            summary.append("Play to Target Score\n", style="cyan")
            summary.append("Target Score: ", style="bold")
            summary.append(f"{self.target_score} points", style="cyan")
        else:
            summary.append("Game Mode: ", style="bold")
            summary.append("Single Round", style="cyan")

        return summary
