"""Tests for scoring logic."""

from domino_game.game.engine import Game
from domino_game.game.scoring import calculate_round_score, determine_winner
from domino_game.models import Domino


def test_scoring():
    """Test scoring when a player goes out."""
    game = Game()
    game.setup_players()

    # Simulate a player going out (empty hand)
    game.players[0].hand = []  # 0 points (went out - winner)
    game.players[1].hand = [Domino(3, 5), Domino(2, 2)]  # 12 points
    game.players[2].hand = [Domino(1, 6)]  # 7 points
    game.players[3].hand = [Domino(4, 4)]  # 8 points

    winning_team, points = calculate_round_score(game.players, game.board)
    assert winning_team == 0
    # All remaining tiles (winner has 0): 0 + 12 + 7 + 8 = 27
    assert points == 27


def test_blocked_game():
    """Test blocked game with clear winner (no draw)."""
    game = Game()
    game.setup_players()

    # Simulate a blocked game with clear winner (lowest hand value)
    game.players[0].hand = [Domino(3, 5)]  # 8 points
    game.players[1].hand = [Domino(2, 2), Domino(1, 1)]  # 6 points (winner - lowest)
    game.players[2].hand = [Domino(4, 5)]  # 9 points
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    winning_team, points = calculate_round_score(game.players, game.board)
    assert winning_team == 1
    # Winner has tiles but doesn't count them: 8 + 9 + 12 = 29 (excludes winner's 6)
    assert points == 29


def test_blocked_game_draw_same_team():
    """Test blocked game with draw between players on the same team.

    When multiple players tie for lowest hand value, it's a draw.
    In a draw, the winner gets ALL tiles including their own.
    """
    game = Game()
    game.setup_players()

    # Simulate a draw between Team 0 players (0 and 2)
    game.players[0].hand = [Domino(3, 3)]  # 6 points (tied - has tiles)
    game.players[1].hand = [Domino(4, 5)]  # 9 points
    game.players[2].hand = [Domino(2, 4)]  # 6 points (tied - has tiles)
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    winning_team, points = calculate_round_score(game.players, game.board)
    assert winning_team == 0  # Team with tied lowest hands wins
    # In a draw, winner's tiles ARE included: 6 + 9 + 6 + 12 = 33
    assert points == 33


def test_blocked_game_draw_opposing_teams_team0_blocked():
    """Test blocked game with draw between opposing teams - Team 0 blocked.

    When players from opposing teams tie for lowest hand value, the team that
    blocked the game (made the last move) wins. As a draw, winner gets ALL tiles.
    """
    game = Game()
    game.setup_players()

    # Simulate a draw between opposing teams: Players 0 (Team 0) and 1 (Team 1)
    game.players[0].hand = [Domino(3, 3)]  # 6 points (tied - has tiles)
    game.players[1].hand = [Domino(2, 4)]  # 6 points (tied - has tiles)
    game.players[2].hand = [Domino(4, 5)]  # 9 points
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    # Team 0 made the last move (blocked the game)
    game.last_player_to_move = game.players[2]  # Team 0 player

    winning_team, points = calculate_round_score(game.players, game.board, game.last_player_to_move)
    assert winning_team == 0  # Team 0 wins (blocked the game)
    # In a draw, winner's tiles ARE included: 6 + 6 + 9 + 12 = 33
    assert points == 33


def test_blocked_game_draw_opposing_teams_team1_blocked():
    """Test blocked game with draw between opposing teams - Team 1 blocked.

    When players from opposing teams tie for lowest hand value, the team that
    blocked the game (made the last move) wins. As a draw, winner gets ALL tiles.
    """
    game = Game()
    game.setup_players()

    # Simulate a draw between opposing teams: Players 0 (Team 0) and 1 (Team 1)
    game.players[0].hand = [Domino(3, 3)]  # 6 points (tied - has tiles)
    game.players[1].hand = [Domino(2, 4)]  # 6 points (tied - has tiles)
    game.players[2].hand = [Domino(4, 5)]  # 9 points
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    # Team 1 made the last move (blocked the game)
    game.last_player_to_move = game.players[3]  # Team 1 player

    winning_team, points = calculate_round_score(game.players, game.board, game.last_player_to_move)
    assert winning_team == 1  # Team 1 wins (blocked the game)
    # In a draw, winner's tiles ARE included: 6 + 6 + 9 + 12 = 33
    assert points == 33


def test_blocked_game_no_draw_excludes_winner_tiles():
    """Test that non-draw blocked game excludes winner's tiles from points.

    In a blocked game with a clear winner (no draw), the winner still has tiles
    in their hand, but those tiles don't count toward the points awarded.
    """
    game = Game()
    game.setup_players()

    # Single winner with clear lowest hand value
    game.players[0].hand = [Domino(3, 5)]  # 8 points
    game.players[1].hand = [Domino(2, 2), Domino(1, 1)]  # 6 points (clear winner - has tiles)
    game.players[2].hand = [Domino(4, 5)]  # 9 points
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    winning_team, points = calculate_round_score(game.players, game.board)
    assert winning_team == 1
    # Winner still has 6 points worth of tiles, but they're excluded: 8 + 9 + 12 = 29
    assert points == 29


def test_determine_winner():
    """Test winner determination."""
    team_scores = [150, 100]
    assert determine_winner(team_scores, 200) == -1

    team_scores = [200, 150]
    assert determine_winner(team_scores, 200) == 0

    team_scores = [180, 210]
    assert determine_winner(team_scores, 200) == 1
