"""Browser gameplay and HTTP boundary regression coverage."""

import json
import random
import threading
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

import pytest

from domino_game.game.referee import audit
from domino_game.models import Board, Domino
from domino_game.models import Domino as D
from domino_game.patio.server import PatioServer
from domino_game.patio.session import MoveError, PatioSession, tile_data


@pytest.fixture
def session():
    return PatioSession(rng=random.Random(66))


def reach_human(session):
    while session.phase == "playing" and session.match.turn != 0:
        session.step_cpu()


def set_table(session, board, hands, turn=0):
    match = session.match
    match.board = Board()
    for tile in board:
        match.board.play_domino(tile, on_left=False)
    match.hands = [list(hand) for hand in hands]
    match.turn = turn


def test_deal_preserves_engine_and_hides_cpu_hands(session):
    snapshot = session.snapshot()
    assert [player["count"] for player in snapshot["players"]] == [7, 7, 7, 7]
    assert len({tile_data(tile)["id"] for hand in session.match.hands for tile in hand}) == 28
    assert all(player["hand"] is None and player["value"] is None for player in snapshot["players"][1:])
    assert Domino(6, 6) in session.match.hands[snapshot["leader"]]
    assert snapshot["turn"] == snapshot["leader"]


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


def test_opening_anchor_survives_left_placements_and_history_truncation(session):
    assert session.snapshot()["opening"] is None
    set_table(session, [], [[D(6, 6), D(1, 6), D(0, 0)], [D(1, 1)], [D(2, 2)], [D(3, 3)]])
    session.play("6-6", "first")
    session.match.turn = 0
    session.play("1-6", "left")
    snapshot = session.snapshot()
    assert snapshot["opening"] == "6-6"
    assert snapshot["board"][0]["id"] == "1-6"


@pytest.mark.parametrize("ends,tile", [(D(6, 6), D(1, 6)), (D(2, 6), D(2, 6)), (D(3, 3), D(3, 3))])
@pytest.mark.parametrize("position", ["left", "right"])
def test_tile_matching_both_ends_can_be_played_on_either_side(session, ends, tile, position):
    set_table(session, [ends], [[tile, D(0, 0)], [D(0, 1)], [D(0, 2)], [D(0, 3)]])
    moves = session.snapshot()["moves"]
    assert {move["position"] for move in moves if move["tile"] == tile_data(tile)["id"]} == {"left", "right"}
    session.play(tile_data(tile)["id"], position)
    board = session.match.board.dominoes
    assert len(board) == 2
    assert board[0].right == board[1].left


def test_pass_is_allowed_only_without_moves(session):
    set_table(session, [D(6, 6)], [[D(0, 1)], [D(6, 1)], [D(0, 2)], [D(0, 3)]])
    session.pass_turn()
    assert session.snapshot()["players"][0]["passed"]
    assert session.match.turn == 1


def test_tranque_scores_once_reveals_hands_and_winner_leads_next_round(session):
    set_table(session, [D(6, 6)], [[D(0, 5)], [D(6, 4), D(0, 1)], [D(0, 3)], [D(0, 2)]], turn=1)
    session.step_cpu()
    assert session.phase == "round_over"
    snapshot = session.snapshot()
    # Team 1 holds 1 + 2 pips against team 0's 5 + 3; seat 1 closed and holds fewer than seat 3.
    assert snapshot["result"] == {"team": 1, "points": 11, "blocked": True, "nextLeader": 1}
    assert snapshot["scores"] == [0, 11]
    book = snapshot["rounds"]
    assert len(book) == 1
    assert book[0]["winner"] is None and book[0]["nextLeader"] == "Opponent 1"
    assert book[0]["teamPips"] == [8, 3]
    assert sum(hand["value"] for hand in book[0]["unplayed"]) == book[0]["points"]
    assert all(player["hand"] is not None for player in snapshot["players"])
    with pytest.raises(MoveError, match="ended"):
        session.step_cpu()
    session.next_round()
    after = session.snapshot()
    assert (after["round"], after["leader"], after["turn"]) == (2, 1, 1)
    assert after["scores"] == [0, 11]
    assert after["board"] == [] and after["opening"] is None
    assert all(player["count"] == 7 for player in after["players"])
    assert after["rounds"] == book


def test_round_winner_may_open_with_any_tile(session):
    set_table(session, [D(6, 6)], [[D(6, 5)], [D(0, 1)], [D(0, 2)], [D(0, 3)]])
    session.play("5-6", "right")
    session.next_round()
    snapshot = session.snapshot()
    assert snapshot["turn"] == snapshot["leader"] == 0
    assert {move["tile"] for move in snapshot["moves"]} == {tile["id"] for tile in snapshot["players"][0]["hand"]}
    assert {move["position"] for move in snapshot["moves"]} == {"first"}


def test_going_out_finishes_single_round():
    session = PatioSession(game_mode="single_round")
    set_table(session, [D(6, 6)], [[D(1, 6)], [D(2, 2)], [D(3, 3)], [D(4, 4)]])
    session.play("1-6", "left")
    assert session.match.scores == [18, 0]
    assert session.phase == "match_over"
    assert session.snapshot()["rounds"][0]["winner"] == "You"
    assert session.snapshot()["rounds"][0]["points"] == 18
    with pytest.raises(MoveError, match="next round"):
        session.next_round()


def test_autoplay_lets_the_cpu_take_the_human_seat(session):
    session.set_autoplay(True)
    snapshot = session.snapshot()
    assert snapshot["autoplay"] is True and snapshot["moves"] == []
    with pytest.raises(MoveError, match="Autoplay"):
        session.play(snapshot["players"][0]["hand"][0]["id"], "first")
    for _ in range(2000):
        if session.phase == "match_over":
            break
        if session.phase == "round_over":
            session.next_round()
        else:
            session.step_cpu()
    assert session.phase == "match_over"
    assert any(turn.seat == 0 for log in session.match.rounds for turn in log.turns)
    assert audit(session.match) == []
    with pytest.raises(MoveError, match="true or false"):
        session.set_autoplay("yes")


@pytest.mark.parametrize("seed", range(12))
def test_complete_matches_conserve_tiles_and_keep_chain_connected(seed):
    session = PatioSession(target_score=100, rng=random.Random(seed))
    for _ in range(1000):
        if session.phase == "match_over":
            assert max(session.match.scores) >= 100
            totals = [0, 0]
            for number, hand in enumerate(session.snapshot()["rounds"], 1):
                assert hand["round"] == number
                assert sum(player["value"] for player in hand["unplayed"]) == hand["points"]
                totals[hand["team"]] += hand["points"]
                assert hand["scores"] == totals
            assert totals == session.match.scores
            assert audit(session.match) == []
            return
        if session.phase == "round_over":
            session.next_round()
        elif session.match.turn:
            session.step_cpu()
        else:
            moves = session.snapshot()["moves"]
            if moves:
                session.play(moves[0]["tile"], moves[0]["position"])
            else:
                session.pass_turn()
        match = session.match
        tiles = match.board.dominoes + [tile for hand in match.hands for tile in hand]
        assert len(tiles) == len(set(tiles)) == 28
        assert all(left.right == right.left for left, right in zip(match.board.dominoes, match.board.dominoes[1:]))
    pytest.fail(f"Match with seed {seed} did not finish within 1000 actions.")


@pytest.mark.parametrize(
    "config",
    [{"target_score": 0}, {"target_score": True}, {"target_score": 1001}, {"game_mode": "unknown"}, {"autoplay": 1}],
)
def test_invalid_settings_fail_at_boundary(config):
    with pytest.raises(MoveError):
        PatioSession(**config)


@pytest.fixture
def http_game():
    server = PatioServer(0, {"target_score": 200, "game_mode": "target_score", "autoplay": False})
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


def test_scorebook_survives_http_refresh_and_resets_with_new_match(http_game):
    client, url = http_game
    with client.open(url + "/api/state") as response:
        state = json.load(response)
    for _ in range(100):
        if state["phase"] != "playing":
            break
        payload = {"revision": state["revision"]}
        if state["turn"]:
            path = "step"
        elif state["moves"]:
            path = "move"
            payload.update(state["moves"][0])
        else:
            path = "pass"
        with post(client, url, f"/api/{path}", payload) as response:
            state = json.load(response)
    assert len(state["rounds"]) == 1
    with client.open(url + "/api/state") as response:
        assert json.load(response)["rounds"] == state["rounds"]
    with post(client, url, "/api/game", {"target": 200}) as response:
        replacement = json.load(response)
    assert replacement["rounds"] == []
    assert replacement["scores"] == [0, 0]


def test_autoplay_endpoint_and_new_game_option(http_game):
    client, url = http_game
    with client.open(url + "/api/state") as response:
        state = json.load(response)
    with post(client, url, "/api/autoplay", {"enabled": True, "revision": state["revision"]}) as response:
        state = json.load(response)
    assert state["autoplay"] is True
    for _ in range(40):
        if state["phase"] != "playing":
            break
        with post(client, url, "/api/step", {"revision": state["revision"]}) as response:
            state = json.load(response)
    assert any(event["player"] == 0 for event in state["history"]) or state["phase"] != "playing"
    with pytest.raises(HTTPError) as error:
        post(client, url, "/api/autoplay", {"enabled": "on", "revision": state["revision"]})
    assert error.value.code == 400
    with post(client, url, "/api/game", {"target": 100, "autoplay": False}) as response:
        assert json.load(response)["autoplay"] is False
