"""Match-level scoring helpers."""


def determine_winner(team_scores: list[int], target_score: int) -> int:
    """
    Determine which team has won the game.

    Args:
        team_scores: List of team scores
        target_score: The target score to win

    Returns:
        Winning team index (0 or 1), or -1 when no team has reached the target
    """
    if team_scores[0] >= target_score:
        return 0
    if team_scores[1] >= target_score:
        return 1
    return -1  # No winner yet
