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
        print(f"\n{'='*60}")
        print(f"{player.name}'s Turn (Team {player.team + 1})")
        print(f"{'='*60}")
        print(f"Board: {self.board}")
        print(f"Board ends: Left=[{self.board.left_value()}] Right=[{self.board.right_value()}]")

        valid_moves = player.get_valid_moves(self.board)

        if not valid_moves:
            print(f"{player.name} has no valid moves and must pass.")
            player.passed_last_turn = True
            self.consecutive_passes += 1
            input("Press Enter to continue...")

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
            print(f"\n{player.name} played {domino} on the {position}")

            # Check if player went out
            if player.is_out():
                return False

        if player.player_type == PlayerType.HUMAN:
            input("\nPress Enter to continue...")

        return True

    def get_human_move(self, player: Player, valid_moves: List[Tuple[Domino, str]]) -> Optional[Tuple[Domino, str]]:
        """Get move from human player."""
        print(f"\nYour hand: {', '.join(str(d) for d in player.hand)}")
        print(f"Your hand value: {player.hand_value()} points")
        print("\nValid moves:")

        for idx, (domino, position) in enumerate(valid_moves, 1):
            print(f"  {idx}. Play {domino} on {position}")

        while True:
            try:
                choice = input(f"\nChoose move (1-{len(valid_moves)}): ").strip()
                choice_idx = int(choice) - 1

                if 0 <= choice_idx < len(valid_moves):
                    return valid_moves[choice_idx]
                else:
                    print(f"Invalid choice. Please enter 1-{len(valid_moves)}")
            except (ValueError, KeyboardInterrupt):
                print("Invalid input. Please enter a number.")

    def get_cpu_move(self, player: Player, valid_moves: List[Tuple[Domino, str]]) -> Optional[Tuple[Domino, str]]:
        """Simple CPU AI: prioritize high-value dominoes and doubles."""
        print(f"\n{player.name} is thinking...")
        print(f"{player.name}'s hand size: {len(player.hand)} dominoes")

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

        print(f"\nGame blocked! Remaining hand values:")
        for player in self.players:
            print(f"  {player.name}: {player.hand_value()} points")

        return (winner.team, points)

    def play_round(self):
        """Play a single round of dominoes."""
        print(f"\n{'#'*60}")
        print(f"# ROUND {self.round_number}")
        print(f"# Team 1: {self.team_scores[0]} points | Team 2: {self.team_scores[1]} points")
        print(f"{'#'*60}")

        self.board = Board()
        self.deal_dominoes()
        self.consecutive_passes = 0

        # Find starting player
        self.current_player_idx = self.find_starting_player()
        starting_player = self.players[self.current_player_idx]
        print(f"\n{starting_player.name} starts this round")

        if starting_player.player_type == PlayerType.HUMAN:
            input("\nPress Enter to start...")

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

        print(f"\n{'='*60}")
        print(f"ROUND {self.round_number} COMPLETE!")
        print(f"Team {winning_team + 1} wins {points} points!")
        print(f"{'='*60}")
        print(f"Team 1 (You & Ally): {self.team_scores[0]} points")
        print(f"Team 2 (Opponents): {self.team_scores[1]} points")
        print(f"{'='*60}")

        input("\nPress Enter to continue to next round...")

        self.round_number += 1

    def play_game(self):
        """Play the full game until a team reaches target score."""
        print("\n" + "="*60)
        print("CARIBBEAN DOMINOES - 2v2")
        print("="*60)
        print(f"Target Score: {self.target_score} points")
        print("\nTeams:")
        print("  Team 1: You & Ally")
        print("  Team 2: Opponent 1 & Opponent 2")
        print("\nRules:")
        print("  - Each player gets 7 dominoes")
        print("  - Match numbers on either end of the line")
        print("  - Can't play? You must pass")
        print("  - Round ends when someone goes out or game is blocked")
        print("  - Winner gets points = sum of losers' remaining dominoes")
        print("="*60)

        input("\nPress Enter to start the game...")

        self.setup_players()

        while max(self.team_scores) < self.target_score:
            self.play_round()

        # Game over
        winning_team = 0 if self.team_scores[0] >= self.target_score else 1

        print("\n" + "="*60)
        print("GAME OVER!")
        print("="*60)
        print(f"Team {winning_team + 1} WINS!")
        print(f"Final Scores:")
        print(f"  Team 1 (You & Ally): {self.team_scores[0]} points")
        print(f"  Team 2 (Opponents): {self.team_scores[1]} points")
        print("="*60)


def main():
    """Main entry point."""
    game = Game()
    game.play_game()


if __name__ == "__main__":
    main()
