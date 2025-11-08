#!/usr/bin/env python3
"""Tests for Board model."""

from domino_game.models import Board, Domino


def test_board():
    """Test board functionality."""
    board = Board()
    assert board.is_empty(), "New board should be empty"
    assert board.left_value() is None, "Empty board should have no left value"
    assert board.right_value() is None, "Empty board should have no right value"

    # Play first domino
    d1 = Domino(3, 5)
    board.play_domino(d1)
    assert not board.is_empty(), "Board should not be empty after playing"
    assert board.left_value() == 3, "Left value should be 3"
    assert board.right_value() == 5, "Right value should be 5"

    # Play on right end
    d2 = Domino(5, 2)
    assert board.can_play(d2), "Should be able to play 5-2"
    board.play_domino(d2, on_left=False)
    assert board.left_value() == 3, "Left value should still be 3"
    assert board.right_value() == 2, "Right value should now be 2"

    # Play on left end
    d3 = Domino(6, 3)
    assert board.can_play(d3), "Should be able to play 6-3"
    board.play_domino(d3, on_left=True)
    assert board.left_value() == 6, "Left value should now be 6"
    assert board.right_value() == 2, "Right value should still be 2"

    # Try invalid domino
    d4 = Domino(4, 4)
    assert not board.can_play(d4), "Should not be able to play 4-4"


def test_board_string_representation():
    """Test board string representation."""
    board = Board()
    assert str(board) == "Empty board", "Empty board string should be 'Empty board'"

    board.play_domino(Domino(3, 5))
    board_str = str(board)
    assert "[3|5]" in board_str, "Board string should contain domino"


if __name__ == "__main__":
    test_board()
    test_board_string_representation()
    print("✓ All board tests passed!")
