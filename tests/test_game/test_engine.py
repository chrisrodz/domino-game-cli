"""Tests for game engine."""

from unittest.mock import Mock

import pytest

from domino_game.game.ai import CPUSettings
from domino_game.game.engine import Game, IllegalMoveError
from domino_game.game.jev import JevStrategy, JevUnavailableError
from domino_game.models import Domino, PlayerType
from domino_game.models.player import AIDifficulty
from tests.game_fixtures import complete_table


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


@pytest.mark.parametrize("full_screen", [True, False])
def test_actual_turns_record_plays_and_passes_in_both_displays(full_screen, monkeypatch):
    monkeypatch.setattr("domino_game.game.engine.time.sleep", lambda _: None)
    game = Game()
    game.setup_players()
    game.use_full_screen = full_screen
    game.renderer = Mock()
    game.board.play_domino(Domino(6, 2))
    player = game.players[1]
    player.hand = [Domino(2, 4), Domino(1, 1)]
    assert game.play_turn(player)
    played = game.turn_history[-1]
    assert (played.action, played.seat, played.tile, played.side) == ("play", 1, (2, 4), "right")
    assert played.ends_before == (6, 2)
    assert played.ends_after == (6, 4)
    assert played.tiles_remaining == 1
    assert game.play_turn(player)
    passed = game.turn_history[-1]
    assert passed.action == "pass"
    assert passed.ends_before == passed.ends_after == (6, 4)
    assert passed.tile is None


@pytest.mark.parametrize("move", [None, (Domino(5, 6), "right"), (Domino(0, 0), "left")])
def test_rejected_move_preserves_hand_board_and_history(move):
    game = Game()
    game.setup_players()
    game.board.play_domino(Domino(6, 2))
    player = game.players[1]
    player.hand = [Domino(5, 6)]
    with pytest.raises(IllegalMoveError):
        game.apply_move(player, move)
    assert player.hand == [Domino(5, 6)]
    assert game.board.dominoes == [Domino(6, 2)]
    assert game.turn_history == []


def test_pass_with_legal_move_is_rejected():
    game = Game()
    game.setup_players()
    game.players[1].hand = [Domino(6, 6)]
    with pytest.raises(IllegalMoveError, match="cannot pass"):
        game.record_pass(game.players[1])
    assert game.turn_history == []
    assert game.consecutive_passes == 0


@pytest.mark.parametrize("full_screen", [True, False])
def test_turn_rejects_missing_choice_with_legal_moves(full_screen, monkeypatch):
    game = Game()
    game.setup_players()
    game.use_full_screen = full_screen
    game.renderer = Mock()
    game.players[1].hand = [Domino(6, 6)]
    monkeypatch.setattr(game, "get_cpu_move", lambda player, moves: None)
    with pytest.raises(IllegalMoveError, match="Illegal move"):
        game.play_turn(game.players[1])
    assert game.turn_history == []
    assert game.players[1].hand == [Domino(6, 6)]


def test_redeal_clears_displayed_passes_but_preserves_public_history():
    game = Game()
    game.setup_players()
    game.record_pass(game.players[1])
    game.deal_dominoes()
    assert all(not player.passed_last_turn for player in game.players)
    assert len(game.turn_history) == 1


@pytest.mark.parametrize("full_screen", [True, False])
def test_fallback_is_visible_in_both_displays(full_screen, monkeypatch, capsys):
    monkeypatch.setattr("domino_game.game.engine.time.sleep", lambda _: None)
    game = Game(cpu_settings=CPUSettings(opponent_1=AIDifficulty.HARD))
    game.setup_players()
    game.use_full_screen = full_screen
    game.renderer = Mock()
    game.jev_strategy = Mock(spec=JevStrategy)
    game.jev_strategy.choose_move.side_effect = JevUnavailableError("Jev timed out")
    game.board.play_domino(Domino(6, 2))
    game.players[1].hand = [Domino(5, 6), Domino(2, 4)]
    complete_table(game)
    assert game.play_turn(game.players[1])
    assert game.turn_history[-1].tile == (5, 6)
    if full_screen:
        assert any("Simple fallback: Jev timed out" in call.args[2] for call in game.renderer.update_display.call_args_list)
    else:
        assert "Simple fallback: Jev timed out" in capsys.readouterr().out
