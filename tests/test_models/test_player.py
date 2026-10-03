"""Tests for Player model."""

from domino_game.models import Domino, Player, PlayerType


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

    # Remove domino
    player.remove_domino(Domino(3, 5))
    assert len(player.hand) == 2


def test_player_is_out():
    """Test player is_out functionality."""
    player = Player("Test", PlayerType.CPU, 1)
    assert player.is_out()

    player.add_domino(Domino(3, 5))
    assert not player.is_out()
