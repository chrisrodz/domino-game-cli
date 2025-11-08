"""Tests for Board model."""

from domino_game.models import Board, Domino


def test_board():
    """Test board functionality."""
    board = Board()
    assert board.is_empty()
    assert board.left_value() is None
    assert board.right_value() is None

    # Play first domino
    d1 = Domino(3, 5)
    board.play_domino(d1)
    assert not board.is_empty()
    assert board.left_value() == 3
    assert board.right_value() == 5

    # Play on right end
    d2 = Domino(5, 2)
    assert board.can_play(d2)
    board.play_domino(d2, on_left=False)
    assert board.left_value() == 3
    assert board.right_value() == 2

    # Play on left end
    d3 = Domino(6, 3)
    assert board.can_play(d3)
    board.play_domino(d3, on_left=True)
    assert board.left_value() == 6
    assert board.right_value() == 2

    # Try invalid domino
    d4 = Domino(4, 4)
    assert not board.can_play(d4)


def test_board_string_representation():
    """Test board string representation."""
    board = Board()
    assert str(board) == "Empty board"

    board.play_domino(Domino(3, 5))
    board_str = str(board)
    assert "[3|5]" in board_str
