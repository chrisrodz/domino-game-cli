"""Tests for AI strategies."""

from domino_game.game.ai import SimpleStrategy
from domino_game.models import Board, Domino, Player, PlayerType


def test_simple_strategy():
    """Test simple AI strategy."""
    strategy = SimpleStrategy()
    player = Player("CPU", PlayerType.CPU, 1)
    board = Board()

    # Add some dominoes to player's hand
    player.add_domino(Domino(3, 5))  # value 8
    player.add_domino(Domino(6, 6))  # value 12, double (bonus)
    player.add_domino(Domino(2, 2))  # value 4, double (bonus)

    # Empty board - first move
    valid_moves = player.get_valid_moves(board)
    best_move = strategy.get_best_move(player, valid_moves, board)

    assert best_move is not None
    assert best_move in valid_moves


def test_simple_strategy_prefers_doubles():
    """Test that simple strategy prefers doubles."""
    strategy = SimpleStrategy()
    player = Player("CPU", PlayerType.CPU, 1)
    board = Board()
    board.play_domino(Domino(3, 4))

    # Add dominoes where double has lower value but should still be preferred
    player.add_domino(Domino(3, 6))  # value 9, not double
    player.add_domino(Domino(3, 3))  # value 6, double (gets +5 bonus = 11)

    valid_moves = player.get_valid_moves(board)
    best_move = strategy.get_best_move(player, valid_moves, board)

    # With bonus, double should be preferred despite lower base value
    assert best_move[0].is_double() or best_move[0].value() >= 9


def test_simple_strategy_no_moves():
    """Test strategy with no valid moves."""
    strategy = SimpleStrategy()
    player = Player("CPU", PlayerType.CPU, 1)
    board = Board()

    valid_moves = []
    best_move = strategy.get_best_move(player, valid_moves, board)

    assert best_move is None
