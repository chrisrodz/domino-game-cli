"""Tests for scoring logic."""

from domino_game.game.engine import Game
from domino_game.game.scoring import calculate_round_score, determine_winner
from domino_game.models import Domino


def test_scoring():
    """Test scoring calculation."""
    game = Game()
    game.setup_players()

    # Simulate a player going out
    game.players[0].hand = []  # Player went out
    game.players[1].hand = [Domino(3, 5), Domino(2, 2)]  # 8 + 4 = 12
    game.players[2].hand = [Domino(1, 6)]  # 7
    game.players[3].hand = [Domino(4, 4)]  # 8

    winning_team, points = calculate_round_score(game.players, game.board)
    assert winning_team == 0
    assert points == 27


def test_blocked_game():
    """Test blocked game scenario."""
    game = Game()
    game.setup_players()

    # Simulate a blocked game with different hand values
    game.players[0].hand = [Domino(3, 5)]  # 8 points
    game.players[1].hand = [Domino(2, 2), Domino(1, 1)]  # 6 points (winner)
    game.players[2].hand = [Domino(4, 5)]  # 9 points
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    winning_team, points = calculate_round_score(game.players, game.board)
    assert winning_team == 1
    assert points == 29


def test_blocked_game_draw_same_team():
    """Test blocked game with draw between players on the same team."""
    game = Game()
    game.setup_players()

    # Simulate a draw between Team 0 players (0 and 2)
    game.players[0].hand = [Domino(3, 3)]  # 6 points (tied winner)
    game.players[1].hand = [Domino(4, 5)]  # 9 points
    game.players[2].hand = [Domino(2, 4)]  # 6 points (tied winner)
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    winning_team, points = calculate_round_score(game.players, game.board)
    assert winning_team == 0  # Team with tied lowest hands wins
    # In a draw, points include ALL tiles: 6 + 9 + 6 + 12 = 33
    assert points == 33


def test_blocked_game_draw_opposing_teams_team0_blocked():
    """Test blocked game with draw between opposing teams - Team 0 blocked."""
    game = Game()
    game.setup_players()

    # Simulate a draw between opposing teams: Players 0 (Team 0) and 1 (Team 1)
    game.players[0].hand = [Domino(3, 3)]  # 6 points (tied)
    game.players[1].hand = [Domino(2, 4)]  # 6 points (tied)
    game.players[2].hand = [Domino(4, 5)]  # 9 points
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    # Team 0 made the last move (blocked the game)
    game.last_player_to_move = game.players[2]  # Team 0 player

    winning_team, points = calculate_round_score(game.players, game.board, game.last_player_to_move)
    assert winning_team == 0  # Team 0 wins (blocked the game)
    # In a draw, points include ALL tiles: 6 + 6 + 9 + 12 = 33
    assert points == 33


def test_blocked_game_draw_opposing_teams_team1_blocked():
    """Test blocked game with draw between opposing teams - Team 1 blocked."""
    game = Game()
    game.setup_players()

    # Simulate a draw between opposing teams: Players 0 (Team 0) and 1 (Team 1)
    game.players[0].hand = [Domino(3, 3)]  # 6 points (tied)
    game.players[1].hand = [Domino(2, 4)]  # 6 points (tied)
    game.players[2].hand = [Domino(4, 5)]  # 9 points
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    # Team 1 made the last move (blocked the game)
    game.last_player_to_move = game.players[3]  # Team 1 player

    winning_team, points = calculate_round_score(game.players, game.board, game.last_player_to_move)
    assert winning_team == 1  # Team 1 wins (blocked the game)
    # In a draw, points include ALL tiles: 6 + 6 + 9 + 12 = 33
    assert points == 33


def test_blocked_game_no_draw_excludes_winner_tiles():
    """Test that non-draw blocked game excludes winner's tiles from points."""
    game = Game()
    game.setup_players()

    # Single winner with clear lowest hand value
    game.players[0].hand = [Domino(3, 5)]  # 8 points
    game.players[1].hand = [Domino(2, 2), Domino(1, 1)]  # 6 points (clear winner)
    game.players[2].hand = [Domino(4, 5)]  # 9 points
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    winning_team, points = calculate_round_score(game.players, game.board)
    assert winning_team == 1
    # Winner's tiles excluded: 8 + 9 + 12 = 29
    assert points == 29


def test_determine_winner():
    """Test winner determination."""
    team_scores = [150, 100]
    assert determine_winner(team_scores, 200) == -1

    team_scores = [200, 150]
    assert determine_winner(team_scores, 200) == 0

    team_scores = [180, 210]
    assert determine_winner(team_scores, 200) == 1
