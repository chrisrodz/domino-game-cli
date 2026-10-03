"""The committed TypeScript conformance fixture must match the Python engine."""

import json

from domino_game.game.conformance import FIXTURE, build_fixture


def test_conformance_fixture_is_current():
    assert FIXTURE.read_text() == build_fixture(), (
        "js/test/fixtures/conformance.json is stale. Run: uv run python -m domino_game.game.conformance"
    )


def test_conformance_fixture_covers_every_kind_of_round_end():
    matches = json.loads(FIXTURE.read_text())["matches"]
    outcomes = [outcome for entry in matches for outcome in entry["outcomes"]]
    turns = [turn for entry in matches for log in entry["record"]["rounds"] for turn in log["turns"]]
    assert any(not outcome["blocked"] for outcome in outcomes)
    assert any(outcome["blocked"] and outcome["teamPips"][0] != outcome["teamPips"][1] for outcome in outcomes)
    assert any(outcome["blocked"] and outcome["teamPips"][0] == outcome["teamPips"][1] for outcome in outcomes)
    assert {outcome["team"] for outcome in outcomes} == {0, 1}
    assert any(turn[1] is None for turn in turns), "no seat ever passed"
