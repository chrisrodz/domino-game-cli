#!/usr/bin/env python3
"""
Caribbean Domino Game - CLI POC
A 2v2 domino game following Caribbean (Puerto Rican) rules.
Player teams up with CPU ally against 2 CPU opponents.
"""

import random
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, IntPrompt
from rich import box
from rich.text import Text
from board_renderer import GameRenderer

# Initialize Rich console
console = Console()
app = typer.Typer(help="Caribbean Domino Game - 2v2 Domino Game CLI")


class PlayerType(Enum):
    HUMAN = "human"
    CPU = "cpu"


@dataclass
class Domino:
    """Represents a single domino tile."""
    left: int
    right: int

    def __str__(self) -> str:
        return f"[{self.left}|{self.right}]"

    def to_rich(self) -> str:
        """Return a rich-formatted representation."""
        colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'white']
        left_color = colors[self.left % len(colors)]
        right_color = colors[self.right % len(colors)]
        return f"[bold {left_color}]{self.left}[/]|[bold {right_color}]{self.right}[/]"

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


class Board:
    """Manages the domino line on the table."""

    def __init__(self):
        self.dominoes: List[Domino] = []

    def is_empty(self) -> bool:
        return len(self.dominoes) == 0

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
        if self.is_empty():
            return True

        left = self.left_value()
        right = self.right_value()

        return domino.has_value(left) or domino.has_value(right)

    def play_domino(self, domino: Domino, on_left: bool = False) -> bool:
        """
        Play a domino on the board.
        Returns True if successful, False otherwise.
        """
        if self.is_empty():
            self.dominoes.append(domino)
            return True

        left = self.left_value()
        right = self.right_value()

        if on_left:
            if domino.right == left:
                self.dominoes.insert(0, domino)
                return True
            elif domino.left == left:
                self.dominoes.insert(0, domino.flip())
                return True
        else:
            if domino.left == right:
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

    def to_rich(self) -> str:
        """Return a rich-formatted representation of the board."""
        if self.is_empty():
            return "[dim]Empty board[/dim]"
        return " ".join(f"[{d.to_rich()}]" for d in self.dominoes)


class Player:
    """Represents a player in the game."""

    def __init__(self, name: str, player_type: PlayerType, team: int):
        self.name = name
        self.player_type = player_type
        self.team = team  # 0 or 1
        self.hand: List[Domino] = []
        self.passed_last_turn = False

    def add_domino(self, domino: Domino):
        """Add a domino to the player's hand."""
        self.hand.append(domino)

    def remove_domino(self, domino: Domino):
        """Remove a domino from the player's hand."""
        self.hand.remove(domino)

    def has_domino(self, domino: Domino) -> bool:
        """Check if player has a specific domino."""
        return domino in self.hand

    def has_double_six(self) -> bool:
        """Check if player has the double-six."""
        return Domino(6, 6) in self.hand

    def hand_value(self) -> int:
        """Total value of all dominoes in hand."""
        return sum(d.value() for d in self.hand)

    def is_out(self) -> bool:
        """Check if player has played all dominoes."""
        return len(self.hand) == 0

    def get_valid_moves(self, board: Board) -> List[Tuple[Domino, str]]:
        """
        Get all valid moves for this player.
        Returns list of (domino, position) where position is 'left' or 'right'.
        """
        if board.is_empty():
            # First move must be double-six if available
            if self.has_double_six():
                return [(Domino(6, 6), 'first')]
            return [(self.hand[0], 'first')] if self.hand else []

        moves = []
        left = board.left_value()
        right = board.right_value()

        for domino in self.hand:
            if domino.has_value(left):
                moves.append((domino, 'left'))
            if domino.has_value(right) and left != right:
                moves.append((domino, 'right'))
            elif domino.has_value(right) and left == right:
                # Avoid duplicates when both ends are the same
                if not any(m[0] == domino and m[1] == 'left' for m in moves):
                    moves.append((domino, 'right'))

        return moves

    def __str__(self) -> str:
        hand_str = ", ".join(str(d) for d in sorted(self.hand, key=lambda d: d.value()))
        return f"{self.name} ({self.player_type.value}, Team {self.team + 1}): {hand_str}"


class Game:
    """Orchestrates the domino game."""

    def __init__(self):
        self.players: List[Player] = []
        self.board = Board()
        self.current_player_idx = 0
        self.team_scores = [0, 0]  # Team 0 and Team 1
        self.target_score = 200
        self.round_number = 1
        self.consecutive_passes = 0
        self.renderer: Optional[GameRenderer] = None
        self.use_full_screen = True  # Toggle for full-screen mode

    def setup_players(self):
        """Setup 4 players: Human, CPU Ally, 2 CPU Opponents."""
        self.players = [
            Player("You", PlayerType.HUMAN, 0),
            Player("Opponent 1", PlayerType.CPU, 1),
            Player("Ally", PlayerType.CPU, 0),
            Player("Opponent 2", PlayerType.CPU, 1)
        ]

    def create_deck(self) -> List[Domino]:
        """Create a full double-six domino set (28 tiles)."""
        deck = []
        for i in range(7):
            for j in range(i, 7):
                deck.append(Domino(i, j))
        return deck

    def deal_dominoes(self):
        """Deal 7 dominoes to each player."""
        deck = self.create_deck()
        random.shuffle(deck)

        for player in self.players:
            player.hand = []

        for i in range(7):
            for player in self.players:
                player.add_domino(deck.pop())

    def find_starting_player(self) -> int:
        """Find who should start (player with double-six in first round)."""
        if self.round_number == 1:
            for idx, player in enumerate(self.players):
                if player.has_double_six():
                    return idx
        # In subsequent rounds, this would be the previous winner
        # For now, just return 0
        return 0

    def play_turn(self, player: Player) -> bool:
        """
        Execute a player's turn.
        Returns True if the game should continue, False if round ended.
        """
        if not self.use_full_screen:
            # Fallback to old display mode
            return self._play_turn_legacy(player)

        # Get valid moves
        valid_moves = player.get_valid_moves(self.board)

        if not valid_moves:
            player.passed_last_turn = True
            self.consecutive_passes += 1

            # Update display to show pass
            status_msg = f"{player.name} has no valid moves and must PASS."
            if player.player_type == PlayerType.HUMAN:
                valid_moves_for_display = []
            else:
                valid_moves_for_display = None

            self.renderer.update_display(self, valid_moves_for_display, status_msg)
            self.renderer.refresh()

            if player.player_type == PlayerType.HUMAN:
                self.renderer.prompt_confirmation(self, "You must pass - no valid moves available.")

            import time
            time.sleep(1.0)  # Pause so CPU passes are visible

            # Check if game is blocked (all players passed)
            if self.consecutive_passes >= 4:
                return False
            return True

        player.passed_last_turn = False
        self.consecutive_passes = 0

        # Update display with valid moves
        if player.player_type == PlayerType.HUMAN:
            self.renderer.update_display(self, valid_moves, "Your turn - choose your move")
        else:
            self.renderer.update_display(self, None, f"{player.name} is thinking...")

        self.renderer.refresh()

        if player.player_type == PlayerType.HUMAN:
            chosen_move = self.get_human_move(player, valid_moves)
        else:
            chosen_move = self.get_cpu_move(player, valid_moves)

        if chosen_move:
            domino, position = chosen_move

            # Play the domino
            if position == 'first':
                self.board.play_domino(domino)
            elif position == 'left':
                self.board.play_domino(domino, on_left=True)
            else:  # right
                self.board.play_domino(domino, on_left=False)

            player.remove_domino(domino)

            # Mark the domino as last played for highlighting
            self.renderer.mark_last_played(domino)

            # Update display to show the played domino
            status_msg = f"✓ {player.name} played on {position}"
            self.renderer.update_display(self, None, status_msg)
            self.renderer.refresh()

            # Pause for visual effect
            self.renderer.pause_for_effect(0.8)

            # Clear the highlight
            self.renderer.clear_last_played()

            # Check if player went out
            if player.is_out():
                return False

        return True

    def _play_turn_legacy(self, player: Player) -> bool:
        """Legacy turn logic without full-screen renderer (fallback)."""
        # Display turn header
        console.print()
        console.rule(f"[bold cyan]{player.name}'s Turn (Team {player.team + 1})[/bold cyan]")
        console.print()

        # Display board state
        board_panel = Panel(
            self.board.to_rich(),
            title="[bold yellow]Board[/bold yellow]",
            subtitle=f"[dim]Left: [{self.board.left_value()}] | Right: [{self.board.right_value()}][/dim]",
            border_style="yellow"
        )
        console.print(board_panel)

        valid_moves = player.get_valid_moves(self.board)

        if not valid_moves:
            console.print(f"[red]{player.name} has no valid moves and must pass.[/red]")
            player.passed_last_turn = True
            self.consecutive_passes += 1

            if player.player_type == PlayerType.HUMAN:
                Confirm.ask("\nPress Enter to continue", default=True)

            # Check if game is blocked (all players passed)
            if self.consecutive_passes >= 4:
                return False
            return True

        player.passed_last_turn = False
        self.consecutive_passes = 0

        if player.player_type == PlayerType.HUMAN:
            chosen_move = self.get_human_move(player, valid_moves)
        else:
            chosen_move = self.get_cpu_move(player, valid_moves)

        if chosen_move:
            domino, position = chosen_move

            # Play the domino
            if position == 'first':
                self.board.play_domino(domino)
            elif position == 'left':
                self.board.play_domino(domino, on_left=True)
            else:  # right
                self.board.play_domino(domino, on_left=False)

            player.remove_domino(domino)
            console.print(f"\n[green]✓[/green] {player.name} played [{domino.to_rich()}] on the [bold]{position}[/bold]")

            # Check if player went out
            if player.is_out():
                return False

        if player.player_type == PlayerType.HUMAN:
            Confirm.ask("\nPress Enter to continue", default=True)

        return True

    def get_human_move(self, player: Player, valid_moves: List[Tuple[Domino, str]]) -> Optional[Tuple[Domino, str]]:
        """Get move from human player using numbered selection."""
        if not self.use_full_screen:
            # Legacy mode - display everything
            hand_table = Table(title="[bold green]Your Hand[/bold green]", box=box.ROUNDED)
            hand_table.add_column("Domino", style="cyan", justify="center")
            hand_table.add_column("Value", style="yellow", justify="center")

            sorted_hand = sorted(player.hand, key=lambda d: d.value())
            for domino in sorted_hand:
                hand_table.add_row(f"[{domino.to_rich()}]", str(domino.value()))

            hand_table.add_row("", "", end_section=True)
            hand_table.add_row("[bold]Total[/bold]", f"[bold]{player.hand_value()}[/bold]")

            console.print(hand_table)
            console.print()

            # Display numbered list of valid moves
            console.print("[bold cyan]Available moves:[/bold cyan]\n")
            for i, (domino, position) in enumerate(valid_moves, 1):
                position_text = {
                    'first': '🎯 First move',
                    'left': '⬅️  Play on left',
                    'right': '➡️  Play on right'
                }.get(position, position)

                console.print(f"  {i}. [{domino.to_rich()}] - {position_text} (value: {domino.value()})")

            console.print()

        # Get user selection
        if self.use_full_screen:
            # Use renderer's prompt method to keep display active
            valid_choices = [str(i) for i in range(1, len(valid_moves) + 1)]
            prompt_text = f"Choose your move (enter number 1-{len(valid_moves)})"
            choice_str = self.renderer.prompt_user_input(
                self,
                prompt_text,
                valid_moves=valid_moves,
                valid_choices=valid_choices
            )
            choice = int(choice_str)
        else:
            # Use IntPrompt for non-full-screen mode
            choice = IntPrompt.ask(
                "Choose your move (enter number)",
                choices=[str(i) for i in range(1, len(valid_moves) + 1)],
                show_choices=False
            )

        return valid_moves[choice - 1]

    def get_cpu_move(self, player: Player, valid_moves: List[Tuple[Domino, str]]) -> Optional[Tuple[Domino, str]]:
        """Simple CPU AI: prioritize high-value dominoes and doubles."""
        if not self.use_full_screen:
            console.print(f"\n[yellow]🤔 {player.name} is thinking...[/yellow]")
            console.print(f"[dim]{player.name}'s hand: {len(player.hand)} dominoes[/dim]")

        # Strategy: Play highest value domino, prefer doubles
        best_move = None
        best_score = -1

        for domino, position in valid_moves:
            score = domino.value()
            # Bonus for doubles (play them when possible)
            if domino.is_double():
                score += 5

            if score > best_score:
                best_score = score
                best_move = (domino, position)

        import time
        time.sleep(0.8)  # Brief pause for realism

        return best_move

    def calculate_round_scores(self) -> Tuple[int, int]:
        """
        Calculate scores for the round.
        Returns (winning_team, points_earned).
        """
        # Check if someone went out
        for player in self.players:
            if player.is_out():
                # Player went out - count all other players' points
                points = sum(p.hand_value() for p in self.players if p != player)
                return (player.team, points)

        # Game is blocked - find player with lowest hand value
        min_value = min(p.hand_value() for p in self.players)
        winner = next(p for p in self.players if p.hand_value() == min_value)

        # Winner gets sum of ALL other players' points
        points = sum(p.hand_value() for p in self.players if p != winner)

        console.print("\n[bold red]🚫 Game blocked![/bold red] Remaining hand values:")
        blocked_table = Table(box=box.SIMPLE)
        blocked_table.add_column("Player", style="cyan")
        blocked_table.add_column("Hand Value", style="yellow", justify="right")

        for player in self.players:
            style = "bold green" if player == winner else ""
            blocked_table.add_row(player.name, f"{player.hand_value()} points", style=style)

        console.print(blocked_table)

        return (winner.team, points)

    def play_round(self):
        """Play a single round of dominoes."""
        if not self.use_full_screen:
            return self._play_round_legacy()

        self.board = Board()
        self.deal_dominoes()
        self.consecutive_passes = 0

        # Find starting player
        self.current_player_idx = self.find_starting_player()
        starting_player = self.players[self.current_player_idx]

        # Initialize display for new round
        status_msg = f"🎲 Round {self.round_number} - {starting_player.name} starts"
        self.renderer.update_display(self, None, status_msg)
        self.renderer.refresh()

        # Brief pause to show starting player
        import time
        time.sleep(1.5)

        # Play turns until round ends
        game_continues = True
        while game_continues:
            player = self.players[self.current_player_idx]
            game_continues = self.play_turn(player)

            # Move to next player (counter-clockwise)
            self.current_player_idx = (self.current_player_idx + 1) % 4

        # Round ended - calculate scores
        winning_team, points = self.calculate_round_scores()
        self.team_scores[winning_team] += points

        # Show round results
        self.renderer.stop_live_display()
        console.print()
        console.rule("[bold green]🎉 ROUND COMPLETE 🎉[/bold green]", style="green")

        result_panel = Panel(
            f"[bold cyan]Team {winning_team + 1}[/bold cyan] wins [bold yellow]{points} points![/bold yellow]\n\n"
            f"[bold]Current Scores:[/bold]\n"
            f"  Team 1 (You & Ally): [yellow]{self.team_scores[0]}[/yellow] points\n"
            f"  Team 2 (Opponents): [yellow]{self.team_scores[1]}[/yellow] points",
            title=f"[bold]Round {self.round_number} Results[/bold]",
            border_style="green"
        )
        console.print(result_panel)

        Confirm.ask("\nPress Enter to continue to next round", default=True)

        self.round_number += 1
        self.renderer.start_live_display()

    def _play_round_legacy(self):
        """Legacy round logic without full-screen renderer."""
        console.print()
        console.rule(f"[bold magenta]⚡ ROUND {self.round_number} ⚡[/bold magenta]", style="magenta")

        # Score display
        score_table = Table(box=box.DOUBLE_EDGE, show_header=False)
        score_table.add_column("Team", style="cyan bold", justify="center")
        score_table.add_column("Score", style="yellow bold", justify="center")
        score_table.add_row(f"Team 1 (You & Ally)", f"{self.team_scores[0]} pts")
        score_table.add_row(f"Team 2 (Opponents)", f"{self.team_scores[1]} pts")
        console.print(score_table, justify="center")

        self.board = Board()
        self.deal_dominoes()
        self.consecutive_passes = 0

        # Find starting player
        self.current_player_idx = self.find_starting_player()
        starting_player = self.players[self.current_player_idx]
        console.print(f"\n[bold green]🎲 {starting_player.name} starts this round[/bold green]")

        if starting_player.player_type == PlayerType.HUMAN:
            Confirm.ask("\nPress Enter to start", default=True)

        # Play turns until round ends
        game_continues = True
        while game_continues:
            player = self.players[self.current_player_idx]
            game_continues = self.play_turn(player)

            # Move to next player (counter-clockwise)
            self.current_player_idx = (self.current_player_idx + 1) % 4

        # Round ended - calculate scores
        winning_team, points = self.calculate_round_scores()
        self.team_scores[winning_team] += points

        console.print()
        console.rule("[bold green]🎉 ROUND COMPLETE 🎉[/bold green]", style="green")

        result_panel = Panel(
            f"[bold cyan]Team {winning_team + 1}[/bold cyan] wins [bold yellow]{points} points![/bold yellow]\n\n"
            f"[bold]Current Scores:[/bold]\n"
            f"  Team 1 (You & Ally): [yellow]{self.team_scores[0]}[/yellow] points\n"
            f"  Team 2 (Opponents): [yellow]{self.team_scores[1]}[/yellow] points",
            title=f"[bold]Round {self.round_number} Results[/bold]",
            border_style="green"
        )
        console.print(result_panel)

        Confirm.ask("\nPress Enter to continue to next round", default=True)

        self.round_number += 1

    def play_game(self):
        """Play the full game until a team reaches target score."""
        # Welcome screen
        console.clear()
        welcome_text = Text()
        welcome_text.append("🎲 ", style="bold yellow")
        welcome_text.append("CARIBBEAN DOMINOES", style="bold cyan")
        welcome_text.append(" 🎲", style="bold yellow")

        welcome_panel = Panel(
            f"[bold yellow]Target Score:[/bold yellow] {self.target_score} points\n\n"
            f"[bold cyan]Teams:[/bold cyan]\n"
            f"  🟢 Team 1: You & Ally\n"
            f"  🔴 Team 2: Opponent 1 & Opponent 2\n\n"
            f"[bold magenta]Rules:[/bold magenta]\n"
            f"  • Each player gets 7 dominoes\n"
            f"  • Match numbers on either end of the line\n"
            f"  • Can't play? You must pass\n"
            f"  • Round ends when someone goes out or game is blocked\n"
            f"  • Winner gets points = sum of losers' remaining dominoes\n\n"
            f"[dim]Full-screen board display enabled - press Ctrl+C to quit[/dim]",
            title=welcome_text,
            border_style="cyan",
            box=box.DOUBLE
        )

        console.print(welcome_panel)
        Confirm.ask("\nReady to start", default=True)

        self.setup_players()

        # Initialize renderer for full-screen mode
        if self.use_full_screen:
            self.renderer = GameRenderer(console)
            self.renderer.start_live_display()

        try:
            while max(self.team_scores) < self.target_score:
                self.play_round()
        finally:
            # Clean up renderer
            if self.use_full_screen and self.renderer:
                self.renderer.stop_live_display()

        # Game over
        winning_team = 0 if self.team_scores[0] >= self.target_score else 1

        console.clear()
        console.print()
        console.rule("[bold yellow]🏆 GAME OVER 🏆[/bold yellow]", style="yellow")

        game_over_style = "bold green" if winning_team == 0 else "bold red"
        game_over_panel = Panel(
            f"[{game_over_style}]Team {winning_team + 1} WINS![/{game_over_style}]\n\n"
            f"[bold]Final Scores:[/bold]\n"
            f"  Team 1 (You & Ally): [yellow]{self.team_scores[0]}[/yellow] points\n"
            f"  Team 2 (Opponents): [yellow]{self.team_scores[1]}[/yellow] points\n\n"
            f"{'[green]Congratulations! 🎉[/green]' if winning_team == 0 else '[red]Better luck next time! 💪[/red]'}",
            title="[bold]Game Results[/bold]",
            border_style="yellow",
            box=box.DOUBLE
        )
        console.print(game_over_panel)


@app.command()
def play(
    target_score: int = typer.Option(200, "--target", "-t", help="Target score to win the game"),
    quick_mode: bool = typer.Option(False, "--quick", "-q", help="Quick mode: first to 100 points wins")
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
        box=box.DOUBLE
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
        box=box.DOUBLE
    )
    console.print(about_panel)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
