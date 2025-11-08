"""Scoring logic for domino games."""

from typing import Tuple, List
from rich.console import Console
from rich.table import Table
from rich import box


console = Console()


def calculate_round_score(players: List, board) -> Tuple[int, int]:
    """
    Calculate scores for the round.

    Args:
        players: List of all players
        board: The game board

    Returns:
        Tuple of (winning_team, points_earned)
    """
    # Check if someone went out
    for player in players:
        if player.is_out():
            # Player went out - count all other players' points
            points = sum(p.hand_value() for p in players if p != player)
            return (player.team, points)

    # Game is blocked - find player with lowest hand value
    min_value = min(p.hand_value() for p in players)
    winner = next(p for p in players if p.hand_value() == min_value)

    # Winner gets sum of ALL other players' points
    points = sum(p.hand_value() for p in players if p != winner)

    console.print("\n[bold red]🚫 Game blocked![/bold red] Remaining hand values:")
    blocked_table = Table(box=box.SIMPLE)
    blocked_table.add_column("Player", style="cyan")
    blocked_table.add_column("Hand Value", style="yellow", justify="right")

    for player in players:
        style = "bold green" if player == winner else ""
        blocked_table.add_row(player.name, f"{player.hand_value()} points", style=style)

    console.print(blocked_table)

    return (winner.team, points)


def determine_winner(team_scores: List[int], target_score: int) -> int:
    """
    Determine which team has won the game.

    Args:
        team_scores: List of team scores
        target_score: The target score to win

    Returns:
        Winning team index (0 or 1)
    """
    if team_scores[0] >= target_score:
        return 0
    elif team_scores[1] >= target_score:
        return 1
    return -1  # No winner yet
