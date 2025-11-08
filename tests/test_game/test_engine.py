"""Tests for game engine."""

from domino_game.game.engine import Game
from domino_game.models import PlayerType


def test_dealing():
    """Test dealing dominoes to players."""
    game = Game()
    game.setup_players()
    game.deal_dominoes()

    assert len(game.players) == 4

    total_dominoes = 0
    for player in game.players:
        assert len(player.hand) == 7
        total_dominoes += len(player.hand)

    assert total_dominoes == 28


def test_game_setup():
    """Test game setup."""
    game = Game()
    game.setup_players()

    assert len(game.players) == 4
    assert game.players[0].name == "You"
    assert game.players[0].player_type == PlayerType.HUMAN
    assert game.players[0].team == 0
    assert game.players[2].team == 0
    assert game.players[1].team == 1
    assert game.players[3].team == 1


def test_find_starting_player():
    """Test finding the starting player."""
    game = Game()
    game.setup_players()
    game.deal_dominoes()

    # In round 1, player with double-six should start
    starting_idx = game.find_starting_player()
    assert 0 <= starting_idx < 4

    # Verify that player has double-six
    if game.round_number == 1:
        has_double_six = False
        for player in game.players:
            if player.has_double_six():
                has_double_six = True
                break
        if has_double_six:
            assert game.players[starting_idx].has_double_six()
