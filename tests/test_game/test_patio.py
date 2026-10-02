"""Browser gameplay and HTTP boundary regression coverage."""

import json
import random
import threading
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

import pytest

from domino_game.models import Board, Domino
from domino_game.patio.server import PatioServer
from domino_game.patio.session import MoveError, PatioSession, tile_data


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setattr("domino_game.game.engine.shuffle_deck", random.Random(66).shuffle)
    return PatioSession()


def reach_human(session):
    while session.phase == "playing" and session.game.current_player_idx != 0:
        session.step_cpu()


def test_deal_preserves_engine_and_hides_cpu_hands(session):
    snapshot = session.snapshot()
    assert [player["count"] for player in snapshot["players"]] == [7, 7, 7, 7]
    assert len({tile_data(tile)["id"] for player in session.game.players for tile in player.hand}) == 28
    assert all(player["hand"] is None and player["value"] is None for player in snapshot["players"][1:])
    opener = session.game.players[session.game.current_player_idx]
    assert opener.has_double_six()


def test_illegal_move_and_illegal_pass_leave_state_unchanged(session):
    reach_human(session)
    before = session.snapshot()
    with pytest.raises(MoveError, match="cannot be played"):
        session.play("9-9", "left")
    with pytest.raises(MoveError, match="legal move"):
        session.pass_turn()
    assert session.snapshot() == before


def test_valid_move_consumes_one_tile_and_rotates_turn(session):
    reach_human(session)
    before = session.snapshot()
    move = before["moves"][0]
    session.play(move["tile"], move["position"])
    after = session.snapshot()
    assert len(after["board"]) == len(before["board"]) + 1
    assert after["players"][0]["count"] == before["players"][0]["count"] - 1
    assert after["turn"] == 1
    assert after["revision"] == before["revision"] + 1


def test_pass_is_allowed_only_without_moves(session):
    game = session.game
    game.current_player_idx = 0
    game.board.play_domino(Domino(6, 6))
    game.players[0].hand = [Domino(0, 1)]
    session.pass_turn()
    assert game.players[0].passed_last_turn
    assert game.consecutive_passes == 1
    assert game.current_player_idx == 1


def test_four_passes_score_block_once_and_reveal_hands(session):
    game = session.game
    game.current_player_idx = 0
    game.board = Board()
    game.board.play_domino(Domino(6, 6))
    game.last_played_team = 1
    for player, tile in zip(game.players, [Domino(0, 1), Domino(0, 2), Domino(0, 3), Domino(0, 4)]):
        player.hand = [tile]
    session.pass_turn()
    for _ in range(3):
        session.step_cpu()
    assert session.result == {"team": 0, "points": 10, "blocked": True}
    assert game.team_scores == [10, 0]
    assert all(player["hand"] is not None for player in session.snapshot()["players"])
    with pytest.raises(MoveError, match="ended"):
        session.step_cpu()
    assert game.team_scores == [10, 0]
    session.next_round()
    assert session.game.round_number == 2
    assert session.game.team_scores == [10, 0]
    assert session.game.board.is_empty()
    assert all(len(player.hand) == 7 for player in session.game.players)


def test_going_out_uses_existing_scorer_and_finishes_single_round():
    session = PatioSession(game_mode="single_round")
    game = session.game
    game.current_player_idx = 0
    game.board.play_domino(Domino(6, 6))
    for player, tile in zip(game.players, [Domino(1, 6), Domino(2, 2), Domino(3, 3), Domino(4, 4)]):
        player.hand = [tile]
    session.play("1-6", "left")
    assert game.team_scores == [18, 0]
    assert session.phase == "match_over"
    with pytest.raises(MoveError, match="next round"):
        session.next_round()


@pytest.mark.parametrize("seed", range(12))
def test_complete_matches_conserve_tiles_and_keep_chain_connected(monkeypatch, seed):
    monkeypatch.setattr("domino_game.game.engine.shuffle_deck", random.Random(seed).shuffle)
    session = PatioSession(target_score=100)
    for _ in range(1000):
        if session.phase == "match_over":
            assert max(session.game.team_scores) >= 100
            return
        if session.phase == "round_over":
            session.next_round()
        elif session.game.current_player_idx:
            session.step_cpu()
        else:
            moves = session.snapshot()["moves"]
            if moves:
                session.play(moves[0]["tile"], moves[0]["position"])
            else:
                session.pass_turn()
        game = session.game
        tiles = game.board.dominoes + [tile for player in game.players for tile in player.hand]
        assert len(tiles) == len(set(tiles)) == 28
        assert all(left.right == right.left for left, right in zip(game.board.dominoes, game.board.dominoes[1:]))
    pytest.fail(f"Match with seed {seed} did not finish within 1000 actions.")


@pytest.mark.parametrize(
    "config", [{"target_score": 0}, {"target_score": True}, {"target_score": 1001}, {"game_mode": "unknown"}]
)
def test_invalid_settings_fail_at_boundary(config):
    with pytest.raises(MoveError):
        PatioSession(**config)


@pytest.fixture
def http_game():
    server = PatioServer(0, {"target_score": 200, "game_mode": "target_score"})
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}"
    client = build_opener(HTTPCookieProcessor(CookieJar()))
    yield client, url
    server.shutdown()
    server.server_close()
    worker.join()


def post(client, url, path, payload, **headers):
    request = Request(url + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers})
    return client.open(request)


def test_browser_refresh_retains_session_and_clients_are_isolated(http_game):
    client, url = http_game
    with client.open(url + "/api/state") as response:
        first = json.load(response)
        assert "HttpOnly" in response.headers["Set-Cookie"]
    with post(client, url, "/api/game", {"target": 100, "mode": "single_round"}) as response:
        new = json.load(response)
    with client.open(url + "/api/state") as response:
        assert json.load(response) == new
    with build_opener().open(url + "/api/state") as response:
        other = json.load(response)
    assert other["target"] == 200
    assert other["mode"] == "target_score"
    assert new["revision"] > first["revision"]


def test_stale_actions_and_cross_origin_requests_are_rejected(http_game):
    client, url = http_game
    with client.open(url + "/api/state") as response:
        state = json.load(response)
    with pytest.raises(HTTPError) as error:
        post(client, url, "/api/step", {"revision": -1})
    assert error.value.code == 409
    assert json.load(error.value)["state"] == state
    with pytest.raises(HTTPError) as error:
        post(client, url, "/api/game", {"target": 100}, Origin="https://example.com")
    assert error.value.code == 403
    with pytest.raises(HTTPError) as error:
        client.open(Request(url + "/api/state", headers={"Host": "example.com"}))
    assert error.value.code == 403


def test_invalid_http_payload_does_not_replace_match(http_game):
    client, url = http_game
    with client.open(url + "/api/state") as response:
        before = json.load(response)
    with pytest.raises(HTTPError) as error:
        post(client, url, "/api/game", {"target": "two hundred"})
    assert error.value.code == 400
    with pytest.raises(HTTPError) as error:
        post(client, url, "/api/game", [])
    assert error.value.code == 400
    with client.open(url + "/api/state") as response:
        assert json.load(response) == before
