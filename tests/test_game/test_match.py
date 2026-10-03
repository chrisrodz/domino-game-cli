"""Headless match engine, referee, and all-CPU simulation."""

import random
from dataclasses import replace

import pytest
from typer.testing import CliRunner

from domino_game.cli import app
from domino_game.game.match import Match, Turn
from domino_game.game.referee import audit
from domino_game.game.rules import OPENING_TILE, RuleError
from domino_game.game.simulate import play_out, simulate
from domino_game.models import Board
from domino_game.models import Domino as D


def finish_round(match):
    while match.phase == "playing":
        match.auto_turn(match.turn)


def test_first_round_is_led_by_the_double_six_holder_with_the_double_six():
    for seed in range(20):
        match = Match(rng=random.Random(seed))
        assert OPENING_TILE in match.hands[match.turn]
        assert match.legal_moves(match.turn) == [(OPENING_TILE, "first")]
        assert all(not match.legal_moves(seat) for seat in range(4) if seat != match.turn)


def test_later_rounds_are_led_by_the_previous_winner_with_any_tile():
    leaders = set()
    for seed in range(40):
        match = Match(rng=random.Random(seed))
        finish_round(match)
        winner = match.outcome.next_leader
        match.next_round()
        assert match.round_number == 2
        assert match.turn == match.round.leader == winner
        assert [tile for tile, _ in match.legal_moves(winner)] == match.hands[winner]
        assert {end for _, end in match.legal_moves(winner)} == {"first"}
        leaders.add(winner)
    assert len(leaders) > 1, "different seats should win across seeds"


def test_tranque_ends_the_round_on_the_closing_tile_without_waiting_for_passes():
    match = Match(rng=random.Random(0))
    match.board = Board()
    match.board.play_domino(D(6, 6))
    match.hands = [[D(1, 6), D(2, 2)], [D(0, 2)], [D(0, 3)], [D(0, 4)]]
    match.turn = 0
    match.play(0, D(6, 1), "left")
    assert match.phase == "round_over"
    assert match.round.turns == [Turn(0, D(6, 1), "left")]
    outcome = match.outcome
    assert outcome.blocked and outcome.closer == 0
    assert outcome.team_pips == (4 + 3, 2 + 4)
    assert (outcome.team, outcome.points, outcome.next_leader) == (1, 13, 1)
    assert match.scores == [0, 13]


def test_going_out_wins_even_when_the_line_is_also_closed():
    match = Match(rng=random.Random(0))
    match.board = Board()
    match.board.play_domino(D(6, 6))
    match.hands = [[D(1, 6)], [D(0, 2)], [D(0, 3)], [D(0, 4)]]
    match.turn = 0
    match.play(0, D(1, 6), "right")
    assert (match.outcome.blocked, match.outcome.team, match.outcome.points) == (False, 0, 9)


def test_invalid_actions_raise_and_leave_the_match_unchanged():
    match = Match(rng=random.Random(3))
    leader = match.turn
    other = (leader + 1) % 4
    before = ([hand.copy() for hand in match.hands], match.turn, list(match.round.turns))
    with pytest.raises(RuleError, match="turn"):
        match.play(other, match.hands[other][0], "first")
    with pytest.raises(RuleError, match="cannot play"):
        match.play(leader, next(tile for tile in match.hands[leader] if tile != OPENING_TILE), "first")
    with pytest.raises(RuleError, match="cannot pass"):
        match.pass_turn(leader)
    with pytest.raises(RuleError, match="next round"):
        match.next_round()
    assert ([hand.copy() for hand in match.hands], match.turn, list(match.round.turns)) == before


def test_single_round_mode_ends_after_one_round():
    match = Match(mode="single_round", rng=random.Random(5))
    finish_round(match)
    assert match.phase == "match_over"
    assert match.winner == match.outcome.team
    with pytest.raises(RuleError):
        match.next_round()


@pytest.mark.parametrize("config", [{"target": 0}, {"target": True}, {"target": 1001}, {"mode": "chiva"}])
def test_invalid_match_settings_fail_fast(config):
    with pytest.raises(RuleError):
        Match(**config)


def test_matches_are_reproducible_from_a_seed():
    first = play_out(Match(rng=random.Random(42)))
    second = play_out(Match(rng=random.Random(42)))
    assert [log.turns for log in first.rounds] == [log.turns for log in second.rounds]
    assert first.scores == second.scores


def test_all_cpu_matches_pass_the_referee():
    report = simulate(matches=300, target=200, seed=7)
    assert report.violations == []
    assert report.matches == 300
    assert sum(report.team_wins) == 300
    assert 0 < report.blocked < report.rounds


@pytest.mark.parametrize("target", [1, 50, 500])
def test_match_ends_on_the_round_that_reaches_the_target(target):
    report = simulate(matches=40, target=target, seed=target)
    assert report.violations == []


def test_simulate_command_reports_a_clean_audit():
    result = CliRunner().invoke(app, ["simulate", "--matches", "25", "--seed", "3"])
    assert result.exit_code == 0, result.output
    assert "25 matches" in result.output
    assert "no rule violations" in result.output


@pytest.fixture
def played():
    return play_out(Match(target=150, rng=random.Random(11)))


def test_referee_accepts_a_clean_match(played):
    assert len(played.rounds) > 1
    assert audit(played) == []


def test_referee_flags_wrong_round_leader(played):
    played.rounds[1].leader = (played.rounds[1].leader + 1) % 4
    assert any("previous winner" in problem for problem in audit(played))


def test_referee_flags_pass_while_holding_a_legal_tile(played):
    log = played.rounds[0]
    index = next(i for i, turn in enumerate(log.turns) if turn.tile is not None and i > 0)
    log.turns[index] = Turn(log.turns[index].seat, None, None)
    assert any("passed while holding" in problem for problem in audit(played))


def test_referee_flags_wrong_points_and_totals(played):
    log = played.rounds[0]
    log.outcome = replace(log.outcome, points=log.outcome.points + 1)
    problems = audit(played)
    assert any("awarded" in problem for problem in problems)
    assert any("totals" in problem for problem in problems)


def test_referee_flags_wrong_tranque_winner():
    match = Match(target=1000, rng=random.Random(0))
    for _ in range(400):
        if match.phase == "playing":
            match.auto_turn(match.turn)
        elif match.outcome.blocked and match.outcome.team_pips[0] != match.outcome.team_pips[1]:
            break
        else:
            match.next_round()
    else:
        pytest.fail("No decisive tranque within 400 actions.")
    match.round.outcome = replace(match.outcome, team=1 - match.outcome.team)
    assert any("expected" in problem for problem in audit(match))


def test_referee_flags_a_match_that_ends_early_or_runs_long(played):
    played.target = played.scores[played.winner] + 1
    assert any("ended before" in problem for problem in audit(played))


def test_referee_flags_out_of_turn_and_illegal_opening(played):
    log = played.rounds[0]
    first = log.turns[0]
    other = next(tile for tile in log.deal[first.seat] if tile != OPENING_TILE)
    log.turns[0] = Turn(first.seat, other, "first")
    log.turns[1] = replace(log.turns[1], seat=(log.turns[1].seat + 1) % 4)
    problems = audit(played)
    assert any("instead of [6|6]" in problem for problem in problems)
    assert any("out of order" in problem for problem in problems)
