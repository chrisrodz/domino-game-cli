"""Batched System One judgments composed with exact domino facts and explicit priorities."""

from dataclasses import dataclass
from math import isclose, isfinite

from typesafe_sdk import Noul, NoulAnswer, Score, ScoreAnswer, SystemOneResponse

from domino_game.game.observation import MoveCandidate, TurnObservation
from domino_game.models.player import AIDifficulty


class JudgmentError(ValueError):
    """A response lacks a valid answer to a requested tactical question."""


RUBRICS: dict[str, tuple[str, ...]] = {
    "continuation": (
        "The remaining hand loses access to its connecting routes and depends on others rescuing it.",
        "Only one fragile continuation remains, with other tiles disconnected from it.",
        "Usable connections remain, with neither a clear improvement nor a serious structural loss.",
        "Several useful continuations remain through connected tiles.",
        "The remaining hand has a well-connected route and alternative connections if one end changes.",
    ),
    "control": (
        "The move abandons the hand's sustainable suits and gives away its useful control tiles.",
        "The move weakens access to a supported suit or spends its last useful connector prematurely.",
        "The move preserves ordinary suit access without a clear control advantage.",
        "The move maintains a well-supported suit while retaining a useful spare connection.",
        "The move establishes strong sustainable suit control while preserving alternative access.",
    ),
    "doubles": (
        "The move strands a remaining double with no future route into its suit.",
        "The move leaves vulnerable doubles while consuming their scarce access tiles.",
        "No vulnerable doubles remain, or the move does not materially change their access.",
        "The move releases a vulnerable double or preserves a usable route for the remaining doubles.",
        "The move resolves the hand's urgent double liability while retaining reliable suit access.",
    ),
    "partner": (
        "On unchanged ends, the move contradicts the partner's known exclusions and cuts their supported route.",
        "The move weakens access to suits the partner's demonstrated choices support.",
        "Evidence is insufficient or the move is neutral toward the partner's supported suits.",
        "The move preserves an end compatible with a suit the partner's demonstrated choices support.",
        "The move strongly maintains the partner's supported route when their short hand makes it urgent.",
    ),
    "pressure": (
        "The move sustains the next opponent's supported route when their short hand makes it dangerous.",
        "The move leaves a useful route through suits the next opponent appears to prefer.",
        "Evidence is insufficient or the move has no clear effect on the next opponent's supported routes.",
        "The move cuts a supported route and makes the next opponent depend on less-supported suits.",
        "The move closes the next opponent's supported routes at an urgent point in their short hand.",
    ),
    "blocking": (
        "Steering toward closure exposes the team to an unfavorable count and abandons a usable exit route.",
        "Closure is poorly supported by the supplied count ranges compared with continuing play.",
        "The count evidence is inconclusive, or this move produces no useful pressure toward closure.",
        "Closure is a useful tactical alternative given the count ranges and limited continuation routes.",
        "Closure is strongly supported by the count evidence and is the team's most promising available route.",
    ),
}

FOCUS = {
    "continuation": "How well does this move preserve usable connections through our remaining hand?",
    "control": "How well does this move maintain access to suits our remaining hand can sustain?",
    "doubles": "How well does this move manage vulnerable doubles and preserve access to their suits?",
    "partner": "How compatible are the resulting ends with the partner's demonstrated voluntary suit signals?",
    "pressure": "How effectively does this move close the next opponent's supported routes?",
    "blocking": "How desirable is steering toward closure on these ends given the supplied count ranges and exit pressure?",
}


@dataclass(frozen=True)
class DecisionPolicy:
    name: str
    weights: dict[str, float]


@dataclass(frozen=True)
class QuestionPlan:
    questions: dict[str, Score | Noul]
    scores: dict[tuple[str, str], str]
    signals: dict[tuple[int, int], str]
    candidates: tuple[MoveCandidate, ...]
    policy: DecisionPolicy


@dataclass(frozen=True)
class MoveEvaluation:
    move_id: str
    total: float
    components: dict[str, float]


@dataclass(frozen=True)
class MoveDecision:
    move_id: str
    policy: DecisionPolicy
    evaluations: tuple[MoveEvaluation, ...]
    model: str
    input_tokens: int


def certain_move(observation: TurnObservation) -> str | None:
    winners = [candidate for candidate in observation.candidates if not candidate.remaining_tiles]
    if not winners:
        winners = [
            candidate
            for candidate in observation.candidates
            if candidate.facts["blocks_round"] and candidate.facts["blocking_outcome_from_bounds"] == "team_win"
        ]
    if winners:
        return max(winners, key=lambda candidate: (candidate.facts["blocked_points"], tie_break(candidate))).move_id
    partner_winners = [
        candidate for candidate in observation.candidates if candidate.facts.get("partner_exit_after_next_pass")
    ]
    if partner_winners:
        return max(partner_winners, key=tie_break).move_id
    eligible = eligible_candidates(observation)
    if len(eligible) == 1:
        return eligible[0].move_id
    return None


def eligible_candidates(observation: TurnObservation) -> tuple[MoveCandidate, ...]:
    safe = tuple(
        candidate
        for candidate in observation.candidates
        if not (candidate.facts["blocks_round"] and candidate.facts["blocking_outcome_from_bounds"] == "team_loss")
        and not candidate.facts.get("next_opponent_guaranteed_exit", False)
    )
    return safe or observation.candidates


def decision_policy(observation: TurnObservation) -> DecisionPolicy:
    context = observation.context
    weights = {"continuation": 0.42, "control": 0.25, "doubles": 0.18, "pip_relief": 0.15}
    name = "balanced"
    if context.difficulty == AIDifficulty.HARD:
        weights = {
            "continuation": 0.25,
            "control": 0.15,
            "doubles": 0.10,
            "pip_relief": 0.10,
            "partner": 0.15,
            "pressure": 0.15,
            "blocking": 0.10,
        }
        if context.tile_counts[(context.seat + 1) % 4] <= 2:
            name = "defend"
            weights.update(continuation=0.15, partner=0.10, pressure=0.40, blocking=0.05)
        elif context.tile_counts[(context.seat + 2) % 4] <= 2:
            name = "support"
            weights.update(continuation=0.15, partner=0.40, pressure=0.10, blocking=0.05)
        elif any(
            candidate.facts["blocking_pressure"] and candidate.facts["blocking_outcome_from_bounds"] == "team_win"
            for candidate in observation.candidates
        ):
            name = "close"
            weights.update(continuation=0.20, doubles=0.05, partner=0.10, pressure=0.10, blocking=0.30)
    own_score = context.team_scores[context.own_team]
    if (
        observation.state["game_mode"] == "target_score"
        and own_score
        < context.target_score
        <= context.team_scores[1 - context.own_team]
        + sum(map(sum, observation.knowledge.unseen_tiles))
        + observation.state["own_hand_pips"]
    ):
        # Keep the match from ending on a large loss when a safer discard remains.
        weights["pip_relief"] += 0.10
    total = sum(weights.values())
    return DecisionPolicy(name=name, weights={dimension: weight / total for dimension, weight in weights.items()})


def build_questions(observation: TurnObservation) -> QuestionPlan:
    questions: dict[str, Score | Noul] = {}
    scores = {}
    signals = {}
    candidates = eligible_candidates(observation)
    hard = observation.context.difficulty == AIDifficulty.HARD
    for candidate in candidates:
        dimensions = ["continuation", "control", "doubles"]
        if hard:
            dimensions.extend(("partner", "pressure"))
            if candidate.facts["blocking_pressure"]:
                dimensions.append("blocking")
        for dimension in dimensions:
            identifier = f"{candidate.move_id}_{dimension}"
            scores[(candidate.move_id, dimension)] = identifier
            instructions = {
                "question": FOCUS[dimension],
                "candidate": f"`candidates.{candidate.move_id}`",
                "evidence": ["`own_hand`", "`own_suit_counts`", "`public_knowledge`", "`roles`", "`players`", "`rules`"],
                "boundaries": (
                    "Judge this dimension alone using the supplied computed facts. Other hands are unknown. "
                    "Possible holdings are alternatives, not actual hands or equally likely outcomes. "
                    "Only the next opponent acts immediately on the resulting ends. Later seats may face changed ends. "
                    "Connections describe the immediate hand structure, not a promised future sequence. "
                    "Pip bounds follow the stated lowest-individual-hand blocking rule. No capicu or pass bonuses apply."
                ),
            }
            if dimension in ("partner", "pressure"):
                instructions["history"] = (
                    "Use `public_signal_evidence_this_round`; only demonstrated alternatives establish choice."
                )
            questions[identifier] = Score(
                instructions=instructions,
                criteria=list(RUBRICS[dimension]),
            )
    if hard:
        for seat in ((observation.context.seat + 2) % 4, (observation.context.seat + 1) % 4):
            evidence = observation.state["public_signal_evidence_this_round"]
            suits = {
                play["introduced_suit"]
                for play in evidence
                if play["seat"] == seat and play["choice_evidence"] == "demonstrated_alternative"
            }
            for number in sorted(suits):
                if not any(number in tile for tile in observation.knowledge.possible_tiles[seat]):
                    continue
                identifier = f"seat_{seat}_promotes_{number}"
                signals[(seat, number)] = identifier
                questions[identifier] = Noul(
                    instructions={
                        "question": f"Does seat {seat}'s demonstrated voluntary play sequence provide credible evidence of deliberately maintaining suit {number}?",
                        "evidence": "`public_signal_evidence_this_round`",
                        "boundaries": "Use this deal only. Exclude compulsory openings, last-tile plays, and choices marked unknown. A single appearance proves possession then, not preference or possession now.",
                    },
                    criteria={
                        "true": "Demonstrated choices credibly favor maintaining this suit.",
                        "false": "Choices do not support that preference, or evidence is insufficient.",
                    },
                )
    return QuestionPlan(
        questions=questions, scores=scores, signals=signals, candidates=candidates, policy=decision_policy(observation)
    )


def validated_score(answer: object) -> float:
    if not isinstance(answer, ScoreAnswer):
        raise JudgmentError("Missing tactical score")
    probabilities = answer.probabilities
    # Live responses round each probability and the mean independently to two decimals.
    # Accumulated rounding must not turn a valid distribution into a service fallback.
    rounding = 0.005 + 1e-9
    if (
        set(probabilities) != set(range(5))
        or not all(isfinite(value) and 0 <= value <= 1 for value in probabilities.values())
        or not isclose(sum(probabilities.values()), 1.0, abs_tol=5 * rounding)
        or not isfinite(answer.score)
        or not 0 <= answer.score <= 4
        or not isfinite(answer.confidence)
        or not 0 <= answer.confidence <= 1
        or not isclose(
            answer.score,
            sum(level * value for level, value in probabilities.items()),
            abs_tol=(1 + sum(range(5))) * rounding,
        )
    ):
        raise JudgmentError("Invalid tactical score distribution")
    # Uncertain semantic judgments shrink toward neutral; exact game facts never do.
    return 0.5 + (answer.score / 4 - 0.5) * answer.confidence


def select_move(observation: TurnObservation, plan: QuestionPlan, response: SystemOneResponse) -> MoveDecision:
    values = {key: validated_score(response.answers.get(identifier)) for key, identifier in plan.scores.items()}
    signals = {}
    for key, identifier in plan.signals.items():
        answer = response.answers.get(identifier)
        if not isinstance(answer, NoulAnswer) or not isfinite(answer.noul) or not 0 <= answer.noul <= 1:
            raise JudgmentError("Missing or invalid suit signal")
        signals[key] = max(0.0, 2 * answer.noul - 1)
    own_pips = sum(map(sum, observation.state["own_hand"]))
    evaluations = []
    for candidate in plan.candidates:
        components = {dimension: values.get((candidate.move_id, dimension), 0.5) for dimension in plan.policy.weights}
        components["pip_relief"] = (own_pips - candidate.remaining_pips) / max(own_pips, 1)
        if observation.context.difficulty == AIDifficulty.HARD:
            partner = (observation.context.seat + 2) % 4
            opponent = (observation.context.seat + 1) % 4
            for dimension, seat in (("partner", partner), ("pressure", opponent)):
                affected_suits = set(observation.state["board_ends"]) | set(candidate.ends_after)
                strength = max(
                    (value for (owner, number), value in signals.items() if owner == seat and number in affected_suits),
                    default=0.0,
                )
                components[dimension] = 0.5 + (components[dimension] - 0.5) * strength
            # These facts are guaranteed on unchanged ends, independently of model certainty.
            if candidate.facts["next_opponent_forced_pass"]:
                components["pressure"] = 1.0
                if candidate.facts["partner_cannot_play_on_unchanged_ends"]:
                    components["partner"] = 0.0
            elif candidate.facts["next_opponent_possible_exit"]:
                components["pressure"] = min(components["pressure"], 0.25)
        total = sum(plan.policy.weights[dimension] * value for dimension, value in components.items())
        evaluations.append(MoveEvaluation(candidate.move_id, total, components))
    if not evaluations:
        raise JudgmentError("No legal candidates to rank")
    candidates = {candidate.move_id: candidate for candidate in plan.candidates}
    winner = max(evaluations, key=lambda evaluation: (evaluation.total, tie_break(candidates[evaluation.move_id])))
    return MoveDecision(winner.move_id, plan.policy, tuple(evaluations), response.model, response.usage.input_tokens)


def tie_break(candidate: MoveCandidate) -> tuple[int, int, int, int, str]:
    left, right = sorted(candidate.tile)
    return -candidate.remaining_pips, candidate.playable_tiles_after, -left, -right, candidate.side
