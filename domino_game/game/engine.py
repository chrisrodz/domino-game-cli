"""Game orchestration engine."""

import time
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt
from rich.table import Table
from rich.text import Text

from domino_game.game.ai import SimpleStrategy
from domino_game.game.deck import create_deck, shuffle_deck
from domino_game.game.scoring import calculate_round_score
from domino_game.models import Board, Domino, Player, PlayerType

console = Console()


class Game:
    """Orchestrates the domino game."""

    def __init__(self):
        self.players: list[Player] = []
        self.board = Board()
        self.current_player_idx = 0
        self.team_scores = [0, 0]  # Team 0 and Team 1
        self.target_score = 200
        self.round_number = 1
        self.consecutive_passes = 0
        self.renderer = None
        self.use_full_screen = True  # Toggle for full-screen mode
        self.cpu_strategy = SimpleStrategy()
        self.last_played_team: Optional[int] = None

    def setup_players(self):
        """Setup 4 players: Human, CPU Ally, 2 CPU Opponents."""
        self.players = [
            Player("You", PlayerType.HUMAN, 0),
            Player("Opponent 1", PlayerType.CPU, 1),
            Player("Ally", PlayerType.CPU, 0),
            Player("Opponent 2", PlayerType.CPU, 1),
        ]

    def deal_dominoes(self):
        """Deal 7 dominoes to each player."""
        deck = create_deck()
        shuffle_deck(deck)

        for player in self.players:
            player.hand = []

        for _i in range(7):
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
            if position == "first":
                self.board.play_domino(domino)
            elif position == "left":
                self.board.play_domino(domino, on_left=True)
            else:  # right
                self.board.play_domino(domino, on_left=False)

            player.remove_domino(domino)
            self.last_played_team = player.team

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
            border_style="yellow",
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
            if position == "first":
                self.board.play_domino(domino)
            elif position == "left":
                self.board.play_domino(domino, on_left=True)
            else:  # right
                self.board.play_domino(domino, on_left=False)

            player.remove_domino(domino)
            self.last_played_team = player.team
            msg = Text("\n")
            msg.append("✓", style="green")
            msg.append(f" {player.name} played ")
            msg.append(domino.to_rich())
            msg.append(" on the ")
            msg.append(position, style="bold")
            console.print(msg)

            # Check if player went out
            if player.is_out():
                return False

        if player.player_type == PlayerType.HUMAN:
            Confirm.ask("\nPress Enter to continue", default=True)

        return True

    def get_human_move(self, player: Player, valid_moves: list[tuple[Domino, str]]) -> Optional[tuple[Domino, str]]:
        """Get move from human player using numbered selection."""
        if not self.use_full_screen:
            # Legacy mode - display everything
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

            # Display numbered list of valid moves
            console.print("[bold cyan]Available moves:[/bold cyan]\n")
            for i, (domino, position) in enumerate(valid_moves, 1):
                position_text = {"first": "🎯 First move", "left": "⬅️  Play on left", "right": "➡️  Play on right"}.get(
                    position, position
                )

                move_text = Text(f"  {i}. ")
                move_text.append(domino.to_rich())
                move_text.append(f" - {position_text} (value: {domino.value()})")
                console.print(move_text)

            console.print()

        # Get user selection
        if self.use_full_screen:
            # Use renderer's prompt method to keep display active
            valid_choices = [str(i) for i in range(1, len(valid_moves) + 1)]
            prompt_text = f"Choose your move (enter number 1-{len(valid_moves)})"
            choice_str = self.renderer.prompt_user_input(
                self, prompt_text, valid_moves=valid_moves, valid_choices=valid_choices
            )
            choice = int(choice_str)
        else:
            # Use IntPrompt for non-full-screen mode
            choice = IntPrompt.ask(
                "Choose your move (enter number)", choices=[str(i) for i in range(1, len(valid_moves) + 1)], show_choices=False
            )

        return valid_moves[choice - 1]

    def get_cpu_move(self, player: Player, valid_moves: list[tuple[Domino, str]]) -> Optional[tuple[Domino, str]]:
        """Get CPU move using the configured strategy."""
        if not self.use_full_screen:
            console.print(f"\n[yellow]🤔 {player.name} is thinking...[/yellow]")
            console.print(f"[dim]{player.name}'s hand: {len(player.hand)} dominoes[/dim]")

        # Use strategy to get best move
        best_move = self.cpu_strategy.get_best_move(player, valid_moves, self.board)

        time.sleep(0.8)  # Brief pause for realism

        return best_move

    def play_round(self):
        """Play a single round of dominoes."""
        if not self.use_full_screen:
            return self._play_round_legacy()

        self.board = Board()
        self.last_played_team = None
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
        time.sleep(1.5)

        # Play turns until round ends
        game_continues = True
        while game_continues:
            player = self.players[self.current_player_idx]
            game_continues = self.play_turn(player)

            # Move to next player (counter-clockwise)
            self.current_player_idx = (self.current_player_idx + 1) % 4

        # Round ended - calculate scores
        winning_team, points = calculate_round_score(self.players, self.board, self.last_played_team)
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
            border_style="green",
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
        score_table.add_row("Team 1 (You & Ally)", f"{self.team_scores[0]} pts")
        score_table.add_row("Team 2 (Opponents)", f"{self.team_scores[1]} pts")
        console.print(score_table, justify="center")

        self.board = Board()
        self.last_played_team = None
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
        winning_team, points = calculate_round_score(self.players, self.board, self.last_played_team)
        self.team_scores[winning_team] += points

        console.print()
        console.rule("[bold green]🎉 ROUND COMPLETE 🎉[/bold green]", style="green")

        result_panel = Panel(
            f"[bold cyan]Team {winning_team + 1}[/bold cyan] wins [bold yellow]{points} points![/bold yellow]\n\n"
            f"[bold]Current Scores:[/bold]\n"
            f"  Team 1 (You & Ally): [yellow]{self.team_scores[0]}[/yellow] points\n"
            f"  Team 2 (Opponents): [yellow]{self.team_scores[1]}[/yellow] points",
            title=f"[bold]Round {self.round_number} Results[/bold]",
            border_style="green",
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
            box=box.DOUBLE,
        )

        console.print(welcome_panel)
        Confirm.ask("\nReady to start", default=True)

        self.setup_players()

        # Initialize renderer for full-screen mode
        if self.use_full_screen:
            from domino_game.ui.renderer.game_renderer import GameRenderer

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
            box=box.DOUBLE,
        )
        console.print(game_over_panel)
