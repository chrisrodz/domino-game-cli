"""Game orchestration engine."""

import time

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt
from rich.text import Text

from domino_game.game.ai import CPUSettings, SimpleStrategy
from domino_game.game.deck import create_deck, shuffle_deck
from domino_game.game.jev import JevStrategy, JevUnavailableError
from domino_game.game.observation import RoundRecord, TurnRecord, board_ends, build_observation
from domino_game.game.scoring import calculate_round_score
from domino_game.models import Board, Domino, Player, PlayerType
from domino_game.models.player import AIDifficulty
from domino_game.ui.legacy_display import LegacyDisplay

console = Console()


class IllegalMoveError(ValueError):
    """A move or pass does not match the current hand and board."""


class Game:
    """Orchestrates the domino game."""

    def __init__(self, game_mode: str = "target_score", target_score: int = 200, cpu_settings: CPUSettings | None = None):
        self.players: list[Player] = []
        self.board = Board()
        self.current_player_idx = 0
        self.team_scores = [0, 0]  # Team 0 and Team 1
        self.game_mode = game_mode  # "target_score" or "single_round"
        self.target_score = target_score
        self.round_number = 1
        self.consecutive_passes = 0
        self.renderer = None
        self.use_full_screen = True  # Toggle for full-screen mode
        self.cpu_settings = cpu_settings or CPUSettings()
        self.cpu_strategy = SimpleStrategy()
        self.jev_strategy: JevStrategy | None = None
        self.cpu_warning: str | None = None
        self.turn_history: list[TurnRecord] = []
        self.round_results: list[RoundRecord] = []
        self.last_played_team: int | None = None

    def setup_players(self):
        """Setup 4 players: Human, CPU Ally, 2 CPU Opponents."""
        self.players = [
            Player("You", PlayerType.HUMAN, 0),
            Player("Opponent 1", PlayerType.CPU, 1, self.cpu_settings.for_seat(1)),
            Player("Ally", PlayerType.CPU, 0, self.cpu_settings.for_seat(2)),
            Player("Opponent 2", PlayerType.CPU, 1, self.cpu_settings.for_seat(3)),
        ]

    def deal_dominoes(self):
        """Deal 7 dominoes to each player."""
        deck = create_deck()
        shuffle_deck(deck)

        for player in self.players:
            player.hand = []
            player.passed_last_turn = False

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
        self.cpu_warning = None
        if not self.use_full_screen:
            # Fallback to old display mode
            return self._play_turn_legacy(player)

        # Get valid moves
        valid_moves = player.get_valid_moves(self.board)

        if not valid_moves:
            self.record_pass(player)

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

        # Update display with valid moves
        if player.player_type == PlayerType.HUMAN:
            self.renderer.update_display(self, valid_moves, "Your turn - choose your move")
        else:
            self.renderer.update_display(self, None, f"{player.name} ({player.ai_difficulty.value}) is thinking...")

        self.renderer.refresh()

        if player.player_type == PlayerType.HUMAN:
            chosen_move = self.get_human_move(player, valid_moves)
        else:
            chosen_move = self.get_cpu_move(player, valid_moves)

        self.apply_move(player, chosen_move)
        domino, position = chosen_move

        # Mark the domino as last played for highlighting
        self.renderer.mark_last_played(domino)

        # Update display to show the played domino
        status_msg = f"✓ {player.name} played on {position}"
        if self.cpu_warning:
            status_msg += f" | Simple fallback: {self.cpu_warning}"
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
        """Use the same move validation and history with the legacy display."""
        LegacyDisplay.display_turn_header(player)
        LegacyDisplay.display_board_state(self.board)
        valid_moves = player.get_valid_moves(self.board)
        if not valid_moves:
            self.record_pass(player)
            LegacyDisplay.display_pass(player)
            if player.player_type == PlayerType.HUMAN:
                Confirm.ask("\nPress Enter to continue", default=True)
            return self.consecutive_passes < 4
        chosen_move = (
            self.get_human_move(player, valid_moves)
            if player.player_type == PlayerType.HUMAN
            else self.get_cpu_move(player, valid_moves)
        )
        self.apply_move(player, chosen_move)
        LegacyDisplay.display_play_result(player, *chosen_move)
        if self.cpu_warning:
            console.print(f"[yellow]Simple fallback: {self.cpu_warning}[/yellow]")
        if player.is_out():
            return False
        if player.player_type == PlayerType.HUMAN:
            Confirm.ask("\nPress Enter to continue", default=True)
        return True

    def get_human_move(self, player: Player, valid_moves: list[tuple[Domino, str]]) -> tuple[Domino, str] | None:
        """Get move from human player using numbered selection."""
        if not self.use_full_screen:
            LegacyDisplay.display_hand(player)
            LegacyDisplay.display_valid_moves(valid_moves)

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

    def prepare_ai(self) -> None:
        if self.cpu_settings.requires_jev() and self.jev_strategy is None:
            self.jev_strategy = JevStrategy.from_environment()

    def close(self) -> None:
        if self.jev_strategy is not None:
            self.jev_strategy.close()
            self.jev_strategy = None

    def record_pass(self, player: Player) -> None:
        if player.get_valid_moves(self.board):
            raise IllegalMoveError(f"{player.name} cannot pass while a legal move exists")
        ends = board_ends(self.board)
        self.turn_history.append(
            TurnRecord(
                round_number=self.round_number,
                seat=self.players.index(player),
                action="pass",
                tile=None,
                side=None,
                ends_before=ends,
                ends_after=ends,
                tiles_remaining=len(player.hand),
            )
        )
        player.passed_last_turn = True
        self.consecutive_passes += 1

    def apply_move(self, player: Player, move: tuple[Domino, str] | None) -> None:
        if move is None or move not in player.get_valid_moves(self.board):
            raise IllegalMoveError(f"Illegal move for {player.name}: {move}; board ends {board_ends(self.board)}")
        tile, side = move
        ends_before = board_ends(self.board)
        if not self.board.play_domino(tile, on_left=side == "left"):
            raise IllegalMoveError(f"Board rejected {tile} on {side} for {player.name}; ends {ends_before}")
        player.remove_domino(tile)
        player.passed_last_turn = False
        self.consecutive_passes = 0
        self.last_played_team = player.team
        self.turn_history.append(
            TurnRecord(
                round_number=self.round_number,
                seat=self.players.index(player),
                action="play",
                tile=(tile.left, tile.right),
                side=side,
                ends_before=ends_before,
                ends_after=board_ends(self.board),
                tiles_remaining=len(player.hand),
            )
        )

    def get_cpu_move(self, player: Player, valid_moves: list[tuple[Domino, str]]) -> tuple[Domino, str] | None:
        """Only Jev decisions receive a copied, player-specific observation."""
        self.cpu_warning = None
        if not valid_moves:
            return None
        if len(valid_moves) == 1:
            return valid_moves[0]
        if not self.use_full_screen:
            LegacyDisplay.display_cpu_thinking(player)
        started = time.monotonic()
        if player.ai_difficulty == AIDifficulty.SIMPLE:
            move = self.cpu_strategy.get_best_move(player, valid_moves, self.board)
        else:
            if self.jev_strategy is None:
                self.jev_strategy = JevStrategy.from_environment()
            observation = build_observation(self, player, valid_moves)
            try:
                move_id = self.jev_strategy.choose_move(observation)
                move = next(
                    valid_moves[index]
                    for index, candidate in enumerate(observation.candidates)
                    if candidate.move_id == move_id
                )
            except JevUnavailableError as error:
                self.cpu_warning = str(error)
                move = self.cpu_strategy.get_best_move(player, valid_moves, self.board)
        time.sleep(max(0.0, 0.8 - (time.monotonic() - started)))
        return move

    def play_round(self):
        """Record the public round in either display mode."""
        if not self.use_full_screen:
            LegacyDisplay.display_round_header(self.round_number, self.team_scores)
        self.board = Board()
        self.last_played_team = None
        self.deal_dominoes()
        self.consecutive_passes = 0
        self.current_player_idx = self.find_starting_player()
        starting_player = self.players[self.current_player_idx]
        if self.use_full_screen:
            self.renderer.update_display(self, None, f"Round {self.round_number} - {starting_player.name} starts")
            self.renderer.refresh()
            time.sleep(1.5)
        else:
            LegacyDisplay.display_starting_player(starting_player)
            if starting_player.player_type == PlayerType.HUMAN:
                Confirm.ask("\nPress Enter to start", default=True)
        game_continues = True
        while game_continues:
            game_continues = self.play_turn(self.players[self.current_player_idx])
            self.current_player_idx = (self.current_player_idx + 1) % 4
        winning_team, points = calculate_round_score(self.players, self.board, self.last_played_team)
        self.team_scores[winning_team] += points
        # Blocked-round totals are revealed by the scoring display; other hands remain private.
        revealed_pips = (
            tuple(player.hand_value() for player in self.players) if not any(p.is_out() for p in self.players) else None
        )
        self.round_results.append(
            RoundRecord(
                round_number=self.round_number, winning_team=winning_team, points=points, revealed_hand_pips=revealed_pips
            )
        )
        if self.use_full_screen:
            self.renderer.stop_live_display()
        console.print()
        console.rule("[bold green]ROUND COMPLETE[/bold green]", style="green")
        console.print(
            Panel(
                f"[bold cyan]Team {winning_team + 1}[/bold cyan] wins [bold yellow]{points} points![/bold yellow]\n\n"
                f"[bold]Current Scores:[/bold]\n"
                f"  Team 1 (You & Ally): [yellow]{self.team_scores[0]}[/yellow] points\n"
                f"  Team 2 (Opponents): [yellow]{self.team_scores[1]}[/yellow] points",
                title=f"[bold]Round {self.round_number} Results[/bold]",
                border_style="green",
            )
        )
        Confirm.ask("\nPress Enter to continue", default=True)
        self.round_number += 1
        if self.use_full_screen:
            self.renderer.start_live_display()

    def play_game(self):
        """Play the full game until a team reaches target score or complete single round."""
        self.prepare_ai()
        # Welcome screen
        console.clear()
        welcome_text = Text()
        welcome_text.append("🎲 ", style="bold yellow")
        welcome_text.append("CARIBBEAN DOMINOES", style="bold cyan")
        welcome_text.append(" 🎲", style="bold yellow")

        # Build mode-specific welcome message
        if self.game_mode == "single_round":
            mode_info = "[bold yellow]Mode:[/bold yellow] Single Round\n\n"
        else:
            mode_info = f"[bold yellow]Target Score:[/bold yellow] {self.target_score} points\n\n"

        welcome_panel = Panel(
            f"{mode_info}"
            f"[bold]CPU difficulty:[/bold] Ally: {self.cpu_settings.ally.value}; "
            f"Opponent 1: {self.cpu_settings.opponent_1.value}; Opponent 2: {self.cpu_settings.opponent_2.value}\n\n"
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
            if self.game_mode == "single_round":
                # Play exactly one round
                self.play_round()
            else:
                # Play until target score reached
                while max(self.team_scores) < self.target_score:
                    self.play_round()
        finally:
            # Clean up renderer
            if self.use_full_screen and self.renderer:
                self.renderer.stop_live_display()
            self.close()

        # Game over
        console.clear()
        console.print()

        if self.game_mode == "single_round":
            # Single round result
            if self.team_scores[0] == self.team_scores[1]:
                console.rule("[bold yellow]🏆 ROUND COMPLETE 🏆[/bold yellow]", style="yellow")
                game_over_panel = Panel(
                    f"[bold magenta]The round ended in a tie![/bold magenta]\n\n"
                    f"[bold]Round Scores:[/bold]\n"
                    f"  Team 1 (You & Ally): [yellow]{self.team_scores[0]}[/yellow] points\n"
                    f"  Team 2 (Opponents): [yellow]{self.team_scores[1]}[/yellow] points\n\n"
                    f"[cyan]It was a close game! 🤝[/cyan]",
                    title="[bold]Round Results[/bold]",
                    border_style="yellow",
                    box=box.DOUBLE,
                )
                console.print(game_over_panel)
            else:
                winning_team = 0 if self.team_scores[0] > self.team_scores[1] else 1
                console.rule("[bold yellow]🏆 ROUND COMPLETE 🏆[/bold yellow]", style="yellow")

                game_over_style = "bold green" if winning_team == 0 else "bold red"
                game_over_panel = Panel(
                    f"[{game_over_style}]Team {winning_team + 1} WINS THE ROUND![/{game_over_style}]\n\n"
                    f"[bold]Round Scores:[/bold]\n"
                    f"  Team 1 (You & Ally): [yellow]{self.team_scores[0]}[/yellow] points\n"
                    f"  Team 2 (Opponents): [yellow]{self.team_scores[1]}[/yellow] points\n\n"
                    f"{'[green]Well played! 🎉[/green]' if winning_team == 0 else '[red]Better luck next time! 💪[/red]'}",
                    title="[bold]Round Results[/bold]",
                    border_style="yellow",
                    box=box.DOUBLE,
                )
                console.print(game_over_panel)
        else:
            # Full game result
            winning_team = 0 if self.team_scores[0] >= self.target_score else 1
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
