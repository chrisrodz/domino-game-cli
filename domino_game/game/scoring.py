"""Scoring logic for domino games."""

from typing import Optional

from rich import box
from rich.console import Console
from rich.table import Table

console = Console()


def calculate_round_score(players: list, board, blocking_team: Optional[int] = None) -> tuple[int, int]:
    """
    Calculate scores for the round.

    Args:
        players: List of all players
        board: The game board
        blocking_team: Team index (0 or 1) that last played before the block

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
    hand_values = {player: player.hand_value() for player in players}
    min_value = min(hand_values.values())
    contenders = [player for player, value in hand_values.items() if value == min_value]

    if len(contenders) == 1:
        winner = contenders[0]
    else:
        # Prefer the team that blocked the game when there's a tie across teams
        winner = contenders[0]
        if blocking_team is not None:
            blocking_contenders = [player for player in contenders if player.team == blocking_team]
            if blocking_contenders:
                winner = blocking_contenders[0]

    # Winner gets sum of ALL unplayed points (including their own hand)
    points = sum(hand_values.values())

    console.print("\n[bold red]🚫 Game blocked![/bold red] Remaining hand values:")
    blocked_table = Table(box=box.SIMPLE)
    blocked_table.add_column("Player", style="cyan")
    blocked_table.add_column("Hand Value", style="yellow", justify="right")

    for player in players:
        style = "bold green" if player == winner else ""
        blocked_table.add_row(player.name, f"{player.hand_value()} points", style=style)

    console.print(blocked_table)

    return (winner.team, points)


def determine_winner(team_scores: list[int], target_score: int) -> int:
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
