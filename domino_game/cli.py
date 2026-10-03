"""CLI interface for Caribbean Domino Game."""

from typing import TYPE_CHECKING, Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel

from domino_game.game.engine import Game
from domino_game.ui.setup_menu import SetupMenu

if TYPE_CHECKING:
    from domino_game.game.match import Mode

console = Console()
app = typer.Typer(help="Caribbean Domino Game - 2v2 Domino Game CLI")


@app.command()
def patio(
    port: int = typer.Option(8000, min=1, max=65535, help="Local browser port"),
    target: int = typer.Option(200, min=1, max=1000, help="Target score"),
    single_round: bool = typer.Option(False, "--single-round", help="Play one round"),
    autoplay: bool = typer.Option(False, "--autoplay", help="Watch CPUs play every seat, including yours"),
    browser: bool = typer.Option(True, "--browser/--no-browser", help="Open the browser automatically"),
) -> None:
    """Play the existing 2v2 game at a Blender-built 3D patio table."""
    from domino_game.patio.server import serve
    from domino_game.patio.session import MoveError

    try:
        serve(
            port=port,
            target_score=target,
            game_mode="single_round" if single_round else "target_score",
            autoplay=autoplay,
            open_browser=browser,
        )
    except MoveError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(1) from error


@app.command()
def simulate(
    matches: int = typer.Option(200, "--matches", "-n", min=1, max=100_000, help="Matches to play"),
    target: int = typer.Option(200, min=1, max=1000, help="Target score"),
    single_round: bool = typer.Option(False, "--single-round", help="Each match is one round"),
    seed: Optional[int] = typer.Option(None, help="Base seed; match N uses seed + N"),
) -> None:
    """Play all-CPU matches headlessly and audit every turn against the rules."""
    from domino_game.game.simulate import simulate as run

    report = run(matches=matches, target=target, mode="single_round" if single_round else "target_score", seed=seed)
    blocked_share = report.blocked / report.rounds if report.rounds else 0
    console.print(
        f"{report.matches} matches, {report.rounds} rounds "
        f"({report.rounds / report.matches:.1f} per match), "
        f"{report.blocked} tranques ({blocked_share:.0%}, {report.tied_blocks} tied).\n"
        f"Match wins: You & Ally {report.team_wins[0]}, Opponents {report.team_wins[1]}."
    )
    if report.violations:
        for problem in report.violations[:20]:
            console.print(f"[red]{problem}[/red]")
        console.print(f"[red]{len(report.violations)} rule violations.[/red]")
        raise typer.Exit(1)
    console.print("[green]Referee: no rule violations.[/green]")


@app.command()
def play(
    target_score: Optional[int] = typer.Option(None, "--target", "-t", help="Target score to win the game"),
    quick_mode: bool = typer.Option(False, "--quick", "-q", help="Quick mode: first to 100 points wins"),
    single_round: bool = typer.Option(False, "--single-round", "-s", help="Play a single round only"),
    skip_setup: bool = typer.Option(False, "--skip-setup", help="Skip setup menu (use with other flags)"),
) -> None:
    """
    🎲 Start a new game of Caribbean Dominoes!

    Play a 2v2 domino game with arrow key navigation and beautiful interface.
    """
    # Determine if we should show setup menu
    has_cli_config = quick_mode or single_round or target_score is not None

    if skip_setup or has_cli_config:
        # Use CLI flags directly
        game_mode: Mode
        if single_round:
            game_mode = "single_round"
            final_target = 0  # Not used in single round
        else:
            game_mode = "target_score"
            if quick_mode:
                final_target = 100
                console.print("[yellow]⚡ Quick mode enabled! First to 100 points wins![/yellow]\n")
            else:
                final_target = target_score if target_score is not None else 200

        game = Game(game_mode=game_mode, target_score=final_target)
    else:
        # Show interactive setup menu
        setup_menu = SetupMenu(console)
        config = setup_menu.run()
        game = Game(game_mode=config.game_mode, target_score=config.target_score)

    game.play_game()


@app.command()
def rules() -> None:
    """
    📖 Display the game rules and instructions
    """
    rules_panel = Panel(
        "[bold cyan]Caribbean Dominoes Rules[/bold cyan]\n\n"
        "[bold]Setup:[/bold]\n"
        "  • 4 players in 2 teams (You + Ally vs 2 Opponents)\n"
        "  • Each player gets 7 dominoes from a double-six set\n"
        "  • Round 1: the [6|6] holder opens with it\n"
        "  • Later rounds: the previous round's winner opens with any tile\n\n"
        "[bold]Gameplay:[/bold]\n"
        "  • Players take turns counter-clockwise\n"
        "  • Match your domino to either end of the line\n"
        "  • If you can't play, you must pass\n"
        "  • Round ends when someone plays all dominoes or no one can play (tranque)\n\n"
        "[bold]Scoring:[/bold]\n"
        "  • Domino: the winner's team scores every pip left in all hands\n"
        "  • Tranque: the team with fewer pips scores them all; ties go to the closer\n"
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
def about() -> None:
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


def main() -> None:
    """Main entry point for the CLI."""
    app()
