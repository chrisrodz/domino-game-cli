"""Tests for Player model."""

from domino_game.models import Board, Domino, Player, PlayerType


def test_player():
    """Test player functionality."""
    player = Player("Test Player", PlayerType.HUMAN, 0)

    # Add dominoes
    player.add_domino(Domino(3, 5))
    player.add_domino(Domino(6, 6))
    player.add_domino(Domino(2, 4))

    assert len(player.hand) == 3
    assert player.hand_value() == 26
    assert player.has_double_six()

    # Valid moves
    board = Board()
    board.play_domino(Domino(5, 1))
    valid_moves = player.get_valid_moves(board)

    # Should be able to play 3-5 on either end
    assert len(valid_moves) >= 1

    # Remove domino
    player.remove_domino(Domino(3, 5))
    assert len(player.hand) == 2


def test_player_is_out():
    """Test player is_out functionality."""
    player = Player("Test", PlayerType.CPU, 1)
    assert player.is_out()

    player.add_domino(Domino(3, 5))
    assert not player.is_out()


def test_player_valid_moves_first_round():
    """Test valid moves for first round (double-six)."""
    player = Player("Test", PlayerType.HUMAN, 0)
    player.add_domino(Domino(6, 6))
    player.add_domino(Domino(3, 5))

    board = Board()
    valid_moves = player.get_valid_moves(board)

    # First move should be double-six if player has it
    assert len(valid_moves) == 1
    assert valid_moves[0][0] == Domino(6, 6)
    assert valid_moves[0][1] == "first"
