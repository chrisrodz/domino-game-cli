"""CLI interface for Caribbean Domino Game."""

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel

from domino_game.game.engine import Game

console = Console()
app = typer.Typer(help="Caribbean Domino Game - 2v2 Domino Game CLI")


@app.command()
def play(
    target_score: int = typer.Option(200, "--target", "-t", help="Target score to win the game"),
    quick_mode: bool = typer.Option(False, "--quick", "-q", help="Quick mode: first to 100 points wins"),
):
    """
    🎲 Start a new game of Caribbean Dominoes!

    Play a 2v2 domino game with arrow key navigation and beautiful interface.
    """
    game = Game()
    if quick_mode:
        game.target_score = 100
        console.print("[yellow]⚡ Quick mode enabled! First to 100 points wins![/yellow]\n")
    else:
        game.target_score = target_score
    game.play_game()


@app.command()
def rules():
    """
    📖 Display the game rules and instructions
    """
    rules_panel = Panel(
        "[bold cyan]Caribbean Dominoes Rules[/bold cyan]\n\n"
        "[bold]Setup:[/bold]\n"
        "  • 4 players in 2 teams (You + Ally vs 2 Opponents)\n"
        "  • Each player gets 7 dominoes from a double-six set\n"
        "  • First round starts with the [6|6] domino\n\n"
        "[bold]Gameplay:[/bold]\n"
        "  • Players take turns counter-clockwise\n"
        "  • Match your domino to either end of the line\n"
        "  • If you can't play, you must pass\n"
        "  • Round ends when someone plays all dominoes or all players pass\n\n"
        "[bold]Scoring:[/bold]\n"
        "  • Winner scores the sum of all remaining dominoes in other players' hands\n"
        "  • If game is blocked, player with lowest hand value wins\n"
        "  • First team to reach target score (default: 200) wins!\n\n"
        "[bold]Controls:[/bold]\n"
        "  • Use ↑↓ arrow keys to navigate menus\n"
        "  • Press Enter to select\n"
        "  • Also supports j/k for up/down (Vim-style)\n\n"
        "[dim]Tip: Play high-value dominoes and doubles strategically![/dim]",
        title="[bold yellow]🎲 How to Play 🎲[/bold yellow]",
        border_style="cyan",
        box=box.DOUBLE,
    )
    console.print(rules_panel)


@app.command()
def about():
    """
    ℹ️  About Caribbean Dominoes CLI
    """
    about_panel = Panel(
        "[bold cyan]Caribbean Dominoes CLI[/bold cyan]\n\n"
        "A beautiful command-line interface for playing Caribbean-style dominoes.\n\n"
        "[bold]Features:[/bold]\n"
        "  ✨ Interactive arrow key navigation\n"
        "  🎨 Colorful, rich terminal interface\n"
        "  🤖 Smart CPU opponents\n"
        "  👥 2v2 team-based gameplay\n"
        "  📊 Real-time score tracking\n\n"
        "[bold]Technology:[/bold]\n"
        "  • Built with Python 3\n"
        "  • Typer for CLI framework\n"
        "  • Rich for formatting and prompts\n\n"
        "[dim]Version 2.0 - Enhanced Edition[/dim]",
        title="[bold magenta]About[/bold magenta]",
        border_style="magenta",
        box=box.DOUBLE,
    )
    console.print(about_panel)


def main():
    """Main entry point for the CLI."""
    app()
