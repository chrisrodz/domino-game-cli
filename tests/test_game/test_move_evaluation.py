"""Tactical questions, uncertainty, exact overrides, and order-independent composition."""

from dataclasses import replace

import pytest
from typesafe_sdk import NoulAnswer, Score, ScoreAnswer, SystemOneResponse

from domino_game.game.engine import Game
from domino_game.game.move_evaluation import (
    RUBRICS,
    JudgmentError,
    build_questions,
    certain_move,
    decision_policy,
    eligible_candidates,
    select_move,
    validated_score,
)
from domino_game.game.observation import TurnRecord, build_observation, signal_evidence
from domino_game.models import Domino
from domino_game.models.player import AIDifficulty
from tests.game_fixtures import complete_table


@pytest.fixture
def view():
    game = Game()
    game.setup_players()
    player = game.players[1]
    player.hand = [Domino(2, 4), Domino(5, 6), Domino(3, 3)]
    player.ai_difficulty = AIDifficulty.MEDIUM
    complete_table(game)
    return build_observation(game, player, player.get_valid_moves(game.board))


def response_for(plan, levels=None, confidence=1.0):
    levels = levels or {}
    answers = {}
    for (move_id, dimension), identifier in plan.scores.items():
        level = levels.get((move_id, dimension), 2)
        answers[identifier] = ScoreAnswer(
            score=float(level),
            confidence=confidence,
            legend=dict(enumerate(RUBRICS[dimension])),
            probabilities={index: float(index == level) for index in range(5)},
        )
    for identifier in plan.signals.values():
        answers[identifier] = NoulAnswer(noul=0.5)
    return SystemOneResponse(model="jev-test", usage={"input_tokens": 200, "output_tokens": 30}, answers=answers)


def hard_view(view):
    candidates = tuple(
        replace(
            candidate,
            facts={
                **candidate.facts,
                "blocking_pressure": False,
                "next_opponent_forced_pass": False,
                "next_opponent_possible_exit": False,
                "next_opponent_guaranteed_exit": False,
                "partner_cannot_play_on_unchanged_ends": False,
            },
        )
        for candidate in view.candidates
    )
    return replace(
        view,
        context=replace(view.context, difficulty=AIDifficulty.HARD),
        candidates=candidates,
        state={**view.state, "public_signal_evidence_this_round": []},
    )


def test_medium_has_three_independent_dimensions_per_move(view):
    plan = build_questions(view)
    assert len(plan.questions) == len(view.candidates) * 3
    assert not plan.signals
    assert all(isinstance(question, Score) for question in plan.questions.values())
    assert {dimension for _, dimension in plan.scores} == {"continuation", "control", "doubles"}
    for (move_id, _), identifier in plan.scores.items():
        assert f"`candidates.{move_id}`" == plan.questions[identifier].instructions["candidate"]


def test_continuation_can_outweigh_discarding_more_pips(view):
    plan = build_questions(view)
    levels = {(view.candidates[0].move_id, dimension): 4 for dimension in ("continuation", "control", "doubles")}
    levels.update({(view.candidates[1].move_id, dimension): 0 for dimension in ("continuation", "control", "doubles")})
    decision = select_move(view, plan, response_for(plan, levels))
    assert decision.move_id == view.candidates[0].move_id
    assert decision.evaluations[0].components["pip_relief"] < decision.evaluations[1].components["pip_relief"]


def test_low_confidence_remains_a_valid_decision(view):
    plan = build_questions(view)
    decision = select_move(view, plan, response_for(plan, confidence=0.0))
    assert decision.move_id in {candidate.move_id for candidate in view.candidates}
    assert all(evaluation.components["continuation"] == 0.5 for evaluation in decision.evaluations)


def test_independently_rounded_live_score_is_valid():
    answer = ScoreAnswer(
        score=2.82,
        confidence=0.58,
        legend=dict(enumerate(RUBRICS["control"])),
        probabilities={0: 0.0, 1: 0.06, 2: 0.2, 3: 0.58, 4: 0.16},
    )
    assert validated_score(answer) == pytest.approx(0.5 + (2.82 / 4 - 0.5) * 0.58)
    rounded = answer.model_copy(update={"probabilities": {0: 0.0, 1: 0.06, 2: 0.19, 3: 0.57, 4: 0.16}})
    assert validated_score(rounded) == pytest.approx(validated_score(answer))


def test_reordering_candidates_does_not_change_the_chosen_tile(view):
    plan = build_questions(view)
    decision = select_move(view, plan, response_for(plan))
    reordered = replace(view, candidates=tuple(reversed(view.candidates)))
    other_plan = build_questions(reordered)
    other = select_move(reordered, other_plan, response_for(other_plan))
    assert decision.move_id == other.move_id


@pytest.mark.parametrize("mode, counts", [("defend", (6, 3, 1, 7)), ("support", (6, 3, 7, 1))])
def test_hard_changes_priorities_with_public_hand_counts(view, mode, counts):
    hard = hard_view(view)
    hard = replace(hard, context=replace(hard.context, tile_counts=counts))
    policy = decision_policy(hard)
    assert policy.name == mode
    assert policy.weights["pressure" if mode == "defend" else "partner"] == max(policy.weights.values())
    assert sum(policy.weights.values()) == pytest.approx(1.0)


def test_hard_pass_deduction_is_not_discounted_by_model_uncertainty(view):
    hard = hard_view(view)
    first = replace(hard.candidates[0], facts={**hard.candidates[0].facts, "next_opponent_forced_pass": True})
    hard = replace(hard, candidates=(first, hard.candidates[1]))
    plan = build_questions(hard)
    decision = select_move(hard, plan, response_for(plan, confidence=0.0))
    assert decision.move_id == first.move_id
    assert decision.evaluations[0].components["pressure"] == 1.0


def test_proved_loss_is_excluded_but_a_move_always_remains(view):
    bad = replace(
        view.candidates[0],
        facts={**view.candidates[0].facts, "blocks_round": True, "blocking_outcome_from_bounds": "team_loss"},
    )
    changed = replace(view, candidates=(bad, view.candidates[1]))
    assert eligible_candidates(changed) == (view.candidates[1],)
    assert eligible_candidates(replace(view, candidates=(bad,))) == (bad,)


def test_immediate_exit_and_proved_winning_block_bypass_judgment(view):
    winner = replace(view.candidates[0], remaining_tiles=())
    assert certain_move(replace(view, candidates=(winner, view.candidates[1]))) == winner.move_id
    block = replace(
        view.candidates[0],
        facts={**view.candidates[0].facts, "blocks_round": True, "blocking_outcome_from_bounds": "team_win"},
    )
    assert certain_move(replace(view, candidates=(block, view.candidates[1]))) == block.move_id


@pytest.mark.parametrize("corruption", ["missing", "wrong_type", "nan", "range", "distribution"])
def test_bad_tactical_answers_fail_at_the_boundary(view, corruption):
    plan = build_questions(view)
    response = response_for(plan)
    identifier = next(iter(response.answers))
    if corruption == "missing":
        del response.answers[identifier]
    elif corruption == "wrong_type":
        response.answers[identifier] = NoulAnswer(noul=1.0)
    elif corruption == "nan":
        response.answers[identifier] = response.answers[identifier].model_copy(update={"score": float("nan")})
    elif corruption == "range":
        response.answers[identifier] = response.answers[identifier].model_copy(update={"confidence": 2.0})
    else:
        response.answers[identifier] = response.answers[identifier].model_copy(update={"probabilities": {0: 1.0}})
    with pytest.raises(JudgmentError):
        select_move(view, plan, response)


def test_only_observed_alternatives_establish_voluntary_play():
    turns = [
        TurnRecord(1, 2, "play", (6, 6), "first", (None, None), (6, 6), 6),
        TurnRecord(1, 2, "play", (6, 4), "right", (2, 6), (2, 4), 5),
        TurnRecord(1, 2, "play", (6, 3), "right", (1, 6), (1, 3), 4),
        TurnRecord(1, 2, "play", (3, 3), "right", (3, 3), (3, 3), 3),
        TurnRecord(1, 2, "play", (2, 2), "right", (4, 2), (4, 2), 0),
    ]
    evidence = signal_evidence(turns)
    assert [play["choice_evidence"] for play in evidence] == [
        "compulsory_opening",
        "demonstrated_alternative",
        "unknown_whether_forced",
        "unknown_whether_forced",
        "last_tile",
    ]
    assert evidence[1]["later_observed_alternative_tiles"] == [[6, 3], [2, 2]]
    # An alternative observed after the decision cannot be used before it happened.
    assert signal_evidence(turns[:2])[1]["choice_evidence"] == "unknown_whether_forced"


def test_partner_signal_is_gated_and_cannot_override_missing_suit(view):
    hard = hard_view(view)
    partner = (hard.context.seat + 2) % 4
    hard.state["public_signal_evidence_this_round"] = [
        {"seat": partner, "introduced_suit": 4, "choice_evidence": "demonstrated_alternative"},
    ]
    plan = build_questions(hard)
    assert (partner, 4) in plan.signals
    levels = {(candidate.move_id, "partner"): 4 for candidate in hard.candidates}
    neutral = select_move(hard, plan, response_for(plan, levels))
    assert all(evaluation.components["partner"] == 0.5 for evaluation in neutral.evaluations)
    response = response_for(plan, levels)
    response.answers[plan.signals[(partner, 4)]] = NoulAnswer(noul=1.0)
    supported = select_move(hard, plan, response)
    assert supported.evaluations[0].components["partner"] == 1.0
    assert supported.evaluations[1].components["partner"] == 0.5
    holdings = {
        **hard.knowledge.possible_tiles,
        partner: tuple(tile for tile in hard.knowledge.possible_tiles[partner] if 4 not in tile),
    }
    impossible = replace(hard, knowledge=replace(hard.knowledge, possible_tiles=holdings))
    assert (partner, 4) not in build_questions(impossible).signals


def test_partner_pass_is_not_assumed_after_an_opponent_can_change_the_ends(view):
    hard = hard_view(view)
    first = replace(hard.candidates[0], facts={**hard.candidates[0].facts, "partner_cannot_play_on_unchanged_ends": True})
    hard = replace(hard, candidates=(first, hard.candidates[1]))
    plan = build_questions(hard)
    decision = select_move(hard, plan, response_for(plan, confidence=0.0))
    assert decision.evaluations[0].components["partner"] == 0.5


def test_proved_partner_exit_needs_no_model_judgment(view):
    winner = replace(view.candidates[0], facts={**view.candidates[0].facts, "partner_exit_after_next_pass": True})
    assert certain_move(replace(view, candidates=(winner, view.candidates[1]))) == winner.move_id


def test_match_loss_exposure_counts_own_pips_and_ignores_single_round_target(view):
    target = sum(map(sum, view.knowledge.unseen_tiles)) + 1
    match = replace(view, context=replace(view.context, target_score=target))
    assert decision_policy(match).weights["pip_relief"] > 0.15
    round_only = replace(match, state={**match.state, "game_mode": "single_round"})
    assert decision_policy(round_only).weights["pip_relief"] == 0.15
