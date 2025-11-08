#!/usr/bin/env python3
"""Tests for game engine."""

from domino_game.game.engine import Game
from domino_game.models import PlayerType, Domino


def test_dealing():
    """Test dealing dominoes to players."""
    game = Game()
    game.setup_players()
    game.deal_dominoes()

    assert len(game.players) == 4, "Should have 4 players"

    total_dominoes = 0
    for player in game.players:
        assert len(player.hand) == 7, f"{player.name} should have 7 dominoes"
        total_dominoes += len(player.hand)

    assert total_dominoes == 28, "All 28 dominoes should be dealt"


def test_game_setup():
    """Test game setup."""
    game = Game()
    game.setup_players()

    assert len(game.players) == 4, "Should have 4 players"
    assert game.players[0].name == "You", "First player should be human"
    assert game.players[0].player_type == PlayerType.HUMAN, "First player should be human type"
    assert game.players[0].team == 0, "Player should be on team 0"
    assert game.players[2].team == 0, "Ally should be on team 0"
    assert game.players[1].team == 1, "Opponent 1 should be on team 1"
    assert game.players[3].team == 1, "Opponent 2 should be on team 1"


def test_find_starting_player():
    """Test finding the starting player."""
    game = Game()
    game.setup_players()
    game.deal_dominoes()

    # In round 1, player with double-six should start
    starting_idx = game.find_starting_player()
    assert 0 <= starting_idx < 4, "Starting player index should be valid"

    # Verify that player has double-six
    if game.round_number == 1:
        has_double_six = False
        for player in game.players:
            if player.has_double_six():
                has_double_six = True
                break
        if has_double_six:
            assert game.players[starting_idx].has_double_six(), "Starting player should have double-six"


if __name__ == "__main__":
    test_dealing()
    test_game_setup()
    test_find_starting_player()
    print("✓ All game engine tests passed!")
