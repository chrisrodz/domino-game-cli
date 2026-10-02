"""Information available to each CPU, independent of the engine's hidden state."""

import pytest

from domino_game.game.engine import Game
from domino_game.game.observation import RoundRecord, TurnRecord, build_observation
from domino_game.models import Domino
from domino_game.models.player import AIDifficulty


@pytest.fixture
def game():
    game = Game()
    game.setup_players()
    game.board.play_domino(Domino(6, 2))
    game.players[0].hand = [Domino(0, 0), Domino(1, 1)]
    game.players[1].hand = [Domino(2, 4), Domino(5, 6), Domino(3, 3)]
    game.players[2].hand = [Domino(0, 1), Domino(1, 3)]
    game.players[3].hand = [Domino(0, 3), Domino(1, 4)]
    return game


def observation(game, seat=1, difficulty=AIDifficulty.MEDIUM):
    player = game.players[seat]
    player.ai_difficulty = difficulty
    return build_observation(game, player, player.get_valid_moves(game.board))


def passed(round_number=1, seat=2):
    return TurnRecord(
        round_number=round_number,
        seat=seat,
        action="pass",
        tile=None,
        side=None,
        ends_before=(6, 4),
        ends_after=(6, 4),
        tiles_remaining=2,
    )


@pytest.mark.parametrize("difficulty", [AIDifficulty.MEDIUM, AIDifficulty.HARD])
def test_redistributing_hidden_tiles_does_not_change_request(game, difficulty):
    before = observation(game, difficulty=difficulty)
    game.players[0].hand, game.players[2].hand = game.players[2].hand, game.players[0].hand
    assert observation(game, difficulty=difficulty) == before


@pytest.mark.parametrize("seat", [1, 2, 3])
def test_each_seat_receives_only_its_own_hand(game, seat):
    view = observation(game, seat)
    assert view.state["acting_seat"] == seat
    assert view.state["own_hand"] == [[tile.left, tile.right] for tile in game.players[seat].hand]
    assert all(set(other) == {"seat", "team", "tiles_remaining"} for other in view.state["players"])


def test_medium_ignores_all_history_derived_information(game):
    before = observation(game)
    game.turn_history.append(passed())
    game.round_results.append(RoundRecord(round_number=0, winning_team=0, points=25))
    game.players[2].passed_last_turn = True
    game.last_played_team = 1
    game.consecutive_passes = 3
    assert observation(game) == before
    assert "public_turn_history" not in before.state
    assert all(candidate.forced_pass_seats is None for candidate in before.candidates)


def test_hard_preserves_full_history_but_resets_pass_deductions(game):
    game.turn_history = [passed(), passed(round_number=2, seat=3)]
    game.round_results = [RoundRecord(round_number=1, winning_team=0, points=25)]
    game.round_number = 2
    view = observation(game, difficulty=AIDifficulty.HARD)
    assert len(view.state["public_turn_history"]) == 2
    assert view.state["public_round_results"] == [{"round_number": 1, "winning_team": 0, "points": 25}]
    assert view.state["known_missing_numbers_this_round"]["2"] == []
    assert view.state["known_missing_numbers_this_round"]["3"] == [4, 6]
    blocking = next(candidate for candidate in view.candidates if candidate.tile == (2, 4))
    assert blocking.ends_after == (6, 4)
    assert blocking.forced_pass_seats == (3,)


def test_projection_is_exact_and_does_not_mutate_game(game):
    board_before = list(game.board.dominoes)
    hand_before = list(game.players[1].hand)
    view = observation(game)
    by_tile = {candidate.tile: candidate for candidate in view.candidates}
    assert by_tile[(2, 4)].ends_after == (6, 4)
    assert by_tile[(2, 4)].remaining_pips == 17
    assert by_tile[(2, 4)].playable_tiles_after == 1
    assert by_tile[(5, 6)].ends_after == (5, 2)
    assert game.board.dominoes == board_before
    assert game.players[1].hand == hand_before


def test_snapshot_does_not_share_mutable_game_data(game):
    view = observation(game)
    game.players[1].hand[0].left = 0
    game.board.dominoes[0].left = 0
    game.team_scores[0] = 100
    assert view.state["own_hand"][0] == [2, 4]
    assert view.state["board"] == [[6, 2]]
    assert view.state["team_scores"] == [0, 0]
