"""Exercise the real SDK against deterministic HTTP responses."""

import json
from random import Random

import httpx2
import pytest
from typesafe_sdk import RetryPolicy, TypeSafeClient

from domino_game.game.ai import CPUSettings
from domino_game.game.engine import Game
from domino_game.game.jev import AIConfigurationError, JevStrategy, JevUnavailableError
from domino_game.game.observation import build_observation
from domino_game.models import Domino
from domino_game.models.player import AIDifficulty
from tests.game_fixtures import complete_table


@pytest.fixture
def game(monkeypatch):
    monkeypatch.setattr("domino_game.game.engine.time.sleep", lambda _: None)
    game = Game(cpu_settings=CPUSettings(opponent_1=AIDifficulty.MEDIUM))
    game.setup_players()
    game.players[1].hand = [Domino(2, 4), Domino(5, 6), Domino(3, 3)]
    complete_table(game)
    return game


def client_for(handler):
    return TypeSafeClient(
        api_key="test-key", transport=httpx2.MockTransport(handler), retry=RetryPolicy(max_retries=0), timeout=2.0
    )


def answer(payload, confidence=0.1):
    answers = {}
    for identifier, question in payload["questions"].items():
        if question["type"] == "noul":
            answers[identifier] = {"type": "noul", "noul": 0.5}
        else:
            level = 4 if identifier.startswith("move_0") else 0
            answers[identifier] = {
                "type": "score",
                "score": float(level),
                "confidence": confidence,
                "legend": {str(index): description for index, description in enumerate(question["criteria"])},
                "probabilities": {str(index): float(index == level) for index in range(5)},
            }
    return httpx2.Response(
        200,
        json={
            "model": "jev-test",
            "usage": {"input_tokens": 100, "output_tokens": 10},
            "answers": answers,
        },
    )


def test_sdk_sends_complete_options_and_accepts_low_confidence(game):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return answer(requests[-1])

    with client_for(handler) as client:
        game.jev_strategy = JevStrategy(client)
        moves = game.players[1].get_valid_moves(game.board)
        assert game.get_cpu_move(game.players[1], moves) == (Domino(2, 4), "right")
    assert len(requests) == 1
    assert len(requests[0]["questions"]) == 6
    assert all(question["type"] == "score" for question in requests[0]["questions"].values())
    assert requests[0]["state"]["candidates"]["move_0"]["side"] == "right"
    assert requests[0]["state"]["own_hand"] == [[2, 4], [5, 6], [3, 3]]
    assert game.cpu_warning is None


@pytest.mark.parametrize("status", [429, 500, 503])
def test_service_failure_falls_back_once_without_retry(game, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx2.Response(status, json={"error": "unavailable"})

    with client_for(handler) as client:
        game.jev_strategy = JevStrategy(client)
        moves = game.players[1].get_valid_moves(game.board)
        assert game.get_cpu_move(game.players[1], moves) == (Domino(5, 6), "left")
    assert len(calls) == 1
    assert str(status) in game.cpu_warning


def test_timeout_falls_back_without_exposing_exception_text(game):
    def handler(request):
        raise httpx2.ReadTimeout("sensitive transport details", request=request)

    with client_for(handler) as client:
        game.jev_strategy = JevStrategy(client)
        assert game.get_cpu_move(game.players[1], game.players[1].get_valid_moves(game.board))[0] == Domino(5, 6)
    assert "timed out" in game.cpu_warning
    assert "sensitive" not in game.cpu_warning


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_configuration_errors_stop_instead_of_silently_switching_ai(game, status):
    with client_for(lambda request: httpx2.Response(status, json={"error": "sensitive server details"})) as client:
        strategy = JevStrategy(client)
        view = build_observation(game, game.players[1], game.players[1].get_valid_moves(game.board))
        with pytest.raises(AIConfigurationError, match=f"HTTP {status}") as raised:
            strategy.choose_move(view)
        assert "sensitive" not in str(raised.value)


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(200, json={"model": "jev-test", "usage": {}, "answers": {"move": {"type": "noul", "noul": 1.0}}}),
        httpx2.Response(200, json={}),
        httpx2.Response(200, json={"model": "jev-test", "usage": {}, "answers": {}}),
    ],
)
def test_invalid_answers_are_rejected(game, response):
    with client_for(lambda request: response) as client:
        view = build_observation(game, game.players[1], game.players[1].get_valid_moves(game.board))
        with pytest.raises(JevUnavailableError):
            JevStrategy(client).choose_move(view)


def test_forced_move_and_pass_need_no_key_or_network(game, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    player = game.players[1]
    player.hand = [Domino(2, 4)]
    assert game.get_cpu_move(player, player.get_valid_moves(game.board)) == (Domino(2, 4), "right")
    player.hand = [Domino(3, 3)]
    assert game.get_cpu_move(player, []) is None
    assert game.jev_strategy is None


def test_missing_key_fails_before_starting_game(game, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(AIConfigurationError, match="TYPESAFE_API_KEY"):
        game.prepare_ai()


@pytest.mark.parametrize("full_screen", [True, False])
def test_two_rounds_record_all_turns_without_leaking_future_history(full_screen, monkeypatch):
    from unittest.mock import Mock

    monkeypatch.setattr("domino_game.game.engine.time.sleep", lambda _: None)
    monkeypatch.setattr("domino_game.game.engine.Confirm.ask", lambda *args, **kwargs: True)
    monkeypatch.setattr("domino_game.game.deck.random.shuffle", Random(17).shuffle)
    game = Game(cpu_settings=CPUSettings(ally=AIDifficulty.HARD, opponent_1=AIDifficulty.MEDIUM))
    game.setup_players()
    game.use_full_screen = full_screen
    game.renderer = Mock()
    monkeypatch.setattr(game, "get_human_move", lambda player, moves: moves[0])
    captured = []

    def handler(request):
        payload = json.loads(request.content)
        state = payload["state"]
        captured.append(state)
        if state["acting_seat"] == 2:
            assert state["public_turn_history"] == [turn.to_state() for turn in game.turn_history]
            assert state["public_round_results"] == [result.to_state() for result in game.round_results]
        else:
            assert "public_turn_history" not in state
            assert "known_missing_numbers_this_round" not in state
        return answer(payload, confidence=1.0)

    with client_for(handler) as client:
        game.jev_strategy = JevStrategy(client)
        for round_number in (1, 2):
            game.play_round()
            turns = [turn for turn in game.turn_history if turn.round_number == round_number]
            assert sum(turn.action == "play" for turn in turns) == len(game.board.dominoes)
            assert len(game.board.dominoes) + sum(len(player.hand) for player in game.players) == 28
            assert game.round_results[-1].round_number == round_number
            blocked = not any(player.is_out() for player in game.players)
            assert (game.round_results[-1].revealed_hand_pips is not None) == blocked
    assert {state["round_number"] for state in captured} == {1, 2}
    assert {state["acting_seat"] for state in captured} == {1, 2}
