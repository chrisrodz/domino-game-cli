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


def test_determine_winner():
    """Test winner determination."""
    team_scores = [150, 100]
    assert determine_winner(team_scores, 200) == -1

    team_scores = [200, 150]
    assert determine_winner(team_scores, 200) == 0

    team_scores = [180, 210]
    assert determine_winner(team_scores, 200) == 1
