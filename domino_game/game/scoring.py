"""Scoring logic for domino games."""

from rich import box
from rich.console import Console
from rich.table import Table

console = Console()


def calculate_round_score(players: list, board, last_player_to_move=None) -> tuple[int, int]:
    """
    Calculate scores for the round.

    Args:
        players: List of all players
        board: The game board
        last_player_to_move: The player who made the last non-pass move (for blocked games)

    Returns:
        Tuple of (winning_team, points_earned)
    """
    # Check if someone went out
    for player in players:
        if player.is_out():
            # Player went out - count all other players' points
            points = sum(p.hand_value() for p in players if p != player)
            return (player.team, points)

    # Game is blocked - find all players with lowest hand value
    min_value = min(p.hand_value() for p in players)
    tied_players = [p for p in players if p.hand_value() == min_value]

    # Determine winner based on draw rules
    if len(tied_players) == 1:
        # Single winner with lowest hand
        winner = tied_players[0]
        is_draw = False
    else:
        # Multiple players tied - check if they're on opposing teams
        tied_teams = set(p.team for p in tied_players)

        if len(tied_teams) == 1:
            # All tied players are on same team - that team wins
            # Pick any player from the tied group
            winner = tied_players[0]
            is_draw = True
        else:
            # Tied players on opposing teams - team who blocked wins
            if last_player_to_move:
                blocking_team = last_player_to_move.team
                # Find a tied player from the blocking team
                winner = next((p for p in tied_players if p.team == blocking_team), tied_players[0])
            else:
                # Fallback if no last_player_to_move tracked
                winner = tied_players[0]
            is_draw = True

    # Point calculation: In draw scenarios, include ALL tiles (including winner's)
    # When someone goes out normally, exclude their tiles (handled above)
    if is_draw:
        points = sum(p.hand_value() for p in players)
    else:
        points = sum(p.hand_value() for p in players if p != winner)

    # Display blocked game message
    if is_draw and len(tied_players) > 1:
        console.print(f"\n[bold yellow]⚖️  DRAW GAME![/bold yellow] {len(tied_players)} players tied at {min_value} points")
        if len(tied_teams) > 1 and last_player_to_move:
            console.print(f"[bold cyan]Team {winner.team + 1}[/bold cyan] wins (blocked the game)")
    else:
        console.print("\n[bold red]🚫 Game blocked![/bold red]")

    console.print("Remaining hand values:")
    blocked_table = Table(box=box.SIMPLE)
    blocked_table.add_column("Player", style="cyan")
    blocked_table.add_column("Hand Value", style="yellow", justify="right")

    for player in players:
        style = "bold green" if player == winner else ""
        is_tied = player in tied_players
        value_display = f"{player.hand_value()} points"
        if is_tied and len(tied_players) > 1:
            value_display += " 🔗"
        blocked_table.add_row(player.name, value_display, style=style)

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
