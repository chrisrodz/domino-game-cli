"""Legacy turn-by-turn display functions (non-full-screen mode)."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box


console = Console()


class LegacyDisplay:
    """Legacy display methods for turn-by-turn gameplay."""

    @staticmethod
    def display_turn_header(player):
        """Display the turn header for a player."""
        console.print()
        console.rule(f"[bold cyan]{player.name}'s Turn (Team {player.team + 1})[/bold cyan]")
        console.print()

    @staticmethod
    def display_board_state(board):
        """Display the current board state."""
        board_panel = Panel(
            board.to_rich(),
            title="[bold yellow]Board[/bold yellow]",
            subtitle=f"[dim]Left: [{board.left_value()}] | Right: [{board.right_value()}][/dim]",
            border_style="yellow"
        )
        console.print(board_panel)

    @staticmethod
    def display_hand(player):
        """Display a player's hand."""
        hand_table = Table(title="[bold green]Your Hand[/bold green]", box=box.ROUNDED)
        hand_table.add_column("Domino", style="cyan", justify="center")
        hand_table.add_column("Value", style="yellow", justify="center")

        sorted_hand = sorted(player.hand, key=lambda d: d.value())
        for domino in sorted_hand:
            hand_table.add_row(domino.to_rich(), str(domino.value()))

        hand_table.add_row("", "", end_section=True)
        hand_table.add_row("[bold]Total[/bold]", f"[bold]{player.hand_value()}[/bold]")

        console.print(hand_table)
        console.print()

    @staticmethod
    def display_valid_moves(valid_moves):
        """Display numbered list of valid moves."""
        console.print("[bold cyan]Available moves:[/bold cyan]\n")
        for i, (domino, position) in enumerate(valid_moves, 1):
            position_text = {
                'first': '🎯 First move',
                'left': '⬅️  Play on left',
                'right': '➡️  Play on right'
            }.get(position, position)

            move_text = Text(f"  {i}. ")
            move_text.append(domino.to_rich())
            move_text.append(f" - {position_text} (value: {domino.value()})")
            console.print(move_text)

        console.print()

    @staticmethod
    def display_cpu_thinking(player):
        """Display CPU thinking message."""
        console.print(f"\n[yellow]🤔 {player.name} is thinking...[/yellow]")
        console.print(f"[dim]{player.name}'s hand: {len(player.hand)} dominoes[/dim]")

    @staticmethod
    def display_play_result(player, domino, position):
        """Display the result of a domino play."""
        msg = Text("\n")
        msg.append("✓", style="green")
        msg.append(f" {player.name} played ")
        msg.append(domino.to_rich())
        msg.append(" on the ")
        msg.append(position, style="bold")
        console.print(msg)

    @staticmethod
    def display_pass(player):
        """Display a pass message."""
        console.print(f"[red]{player.name} has no valid moves and must pass.[/red]")

    @staticmethod
    def display_round_header(round_number, team_scores):
        """Display round header with scores."""
        console.print()
        console.rule(f"[bold magenta]⚡ ROUND {round_number} ⚡[/bold magenta]", style="magenta")

        # Score display
        score_table = Table(box=box.DOUBLE_EDGE, show_header=False)
        score_table.add_column("Team", style="cyan bold", justify="center")
        score_table.add_column("Score", style="yellow bold", justify="center")
        score_table.add_row(f"Team 1 (You & Ally)", f"{team_scores[0]} pts")
        score_table.add_row(f"Team 2 (Opponents)", f"{team_scores[1]} pts")
        console.print(score_table, justify="center")

    @staticmethod
    def display_starting_player(player):
        """Display who starts the round."""
        console.print(f"\n[bold green]🎲 {player.name} starts this round[/bold green]")
