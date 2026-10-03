"""Independent audit of a finished or in-progress match log.

The referee replays each round from its recorded deal using its own end
tracking, not `Board` or `rules.legal_moves`, so an engine bug cannot hide
behind the code that produced it. It returns human-readable violations; an
empty list means every turn, round result, and score followed the rules.
"""

from domino_game.game.match import Match
from domino_game.game.rules import HAND_SIZE, OPENING_TILE, SEATS, RoundOutcome
from domino_game.models import Domino

FULL_SET = {Domino(low, high) for low in range(7) for high in range(low, 7)}


def _fits(tile: Domino, ends: tuple[int, int]) -> bool:
    return ends[0] in (tile.left, tile.right) or ends[1] in (tile.left, tile.right)


def audit(match: Match) -> list[str]:
    violations: list[str] = []
    scores = [0, 0]
    expected_leader = None
    for log in match.rounds:
        tag = f"round {log.number}"
        violations += _audit_deal(log.deal, tag)
        hands = [list(hand) for hand in log.deal]
        if log.number == 1:
            holder = next((seat for seat, hand in enumerate(hands) if OPENING_TILE in hand), None)
            if log.leader != holder:
                violations.append(f"{tag}: seat {log.leader} led, but seat {holder} holds [6|6].")
        elif log.leader != expected_leader:
            violations.append(f"{tag}: seat {log.leader} led, but the previous winner is seat {expected_leader}.")
        ends = None
        seat = log.leader
        finished = False
        closer = None
        for index, turn in enumerate(log.turns):
            where = f"{tag} turn {index + 1}"
            if finished:
                violations.append(f"{where}: seat {turn.seat} acted after the round ended.")
                break
            if turn.seat != seat:
                violations.append(f"{where}: seat {turn.seat} acted out of order; expected seat {seat}.")
            hand = hands[turn.seat]
            if turn.tile is None:
                playable = [tile for tile in hand if ends is None or _fits(tile, ends)]
                if ends is None or playable:
                    violations.append(f"{where}: seat {turn.seat} passed while holding {playable or hand}.")
            else:
                tile = turn.tile
                if tile not in hand:
                    violations.append(f"{where}: seat {turn.seat} played {tile}, which is not in its hand.")
                    break
                if ends is None:
                    if turn.end != "first":
                        violations.append(f"{where}: the opening tile was placed on {turn.end!r}.")
                    if log.number == 1 and tile != OPENING_TILE:
                        violations.append(f"{where}: round 1 opened with {tile} instead of [6|6].")
                    ends = (tile.left, tile.right)
                elif turn.end == "left" and ends[0] in (tile.left, tile.right):
                    ends = (tile.left if tile.right == ends[0] else tile.right, ends[1])
                elif turn.end == "right" and ends[1] in (tile.left, tile.right):
                    ends = (ends[0], tile.right if tile.left == ends[1] else tile.left)
                else:
                    violations.append(f"{where}: {tile} does not match the {turn.end} end of {ends}.")
                    break
                hand.remove(tile)
                closer = turn.seat
                finished = not hand or not any(_fits(other, ends) for held in hands for other in held)
            seat = (turn.seat + 1) % SEATS
        if log.outcome is None:
            if finished:
                violations.append(f"{tag}: the round should have ended but has no result.")
            if log is not match.round:
                violations.append(f"{tag}: an earlier round was never scored.")
            continue
        # A round only finishes on a play, so a finished round always has a closer.
        if not finished or closer is None:
            violations.append(f"{tag}: scored while a seat could still play.")
            continue
        violations += _audit_outcome(log.outcome, hands, closer, tag)
        scores[log.outcome.team] += log.outcome.points
        if log.scores != tuple(scores):
            violations.append(f"{tag}: recorded totals {log.scores}, expected {tuple(scores)}.")
        decided = match.mode == "single_round" or max(scores) >= match.target
        if decided and log is not match.round:
            violations.append(f"{tag}: the match was decided, yet round {log.number + 1} was dealt.")
        expected_leader = log.outcome.next_leader
    if match.scores != scores:
        violations.append(f"match: totals {match.scores}, expected {scores}.")
    decided = match.mode == "single_round" or max(scores) >= match.target
    if match.phase == "match_over" and not decided:
        violations.append(f"match: ended before a team reached {match.target} (scores {scores}).")
    if match.phase == "round_over" and decided:
        violations.append(f"match: scores {scores} reached {match.target}, but the match continues.")
    return violations


def _audit_deal(deal: tuple[tuple[Domino, ...], ...], tag: str) -> list[str]:
    tiles = [tile for hand in deal for tile in hand]
    problems = []
    if len(deal) != SEATS or any(len(hand) != HAND_SIZE for hand in deal):
        problems.append(f"{tag}: deal sizes {[len(hand) for hand in deal]}, expected {SEATS} x {HAND_SIZE}.")
    if len(tiles) != len(set(tiles)) or set(tiles) != FULL_SET:
        problems.append(f"{tag}: the deal is not exactly one double-six set.")
    return problems


def _audit_outcome(outcome: RoundOutcome, hands: list[list[Domino]], closer: int, tag: str) -> list[str]:
    hand_pips = [sum(tile.value() for tile in hand) for hand in hands]
    team_pips = (hand_pips[0] + hand_pips[2], hand_pips[1] + hand_pips[3])
    problems = []
    if outcome.hand_pips != tuple(hand_pips) or outcome.team_pips != team_pips:
        problems.append(
            f"{tag}: recorded pips {outcome.hand_pips} / teams {outcome.team_pips}, "
            f"but replay leaves {tuple(hand_pips)} / teams {team_pips}."
        )
    if outcome.points != sum(hand_pips):
        problems.append(f"{tag}: awarded {outcome.points} points, but {sum(hand_pips)} pips remain.")
    if outcome.closer != closer:
        problems.append(f"{tag}: closer recorded as seat {outcome.closer}, but seat {closer} played last.")
    if not hands[closer]:
        expected = (closer % 2, False, closer)
    else:
        if team_pips[0] == team_pips[1]:
            team, leader = closer % 2, closer
        else:
            team = 0 if team_pips[0] < team_pips[1] else 1
            members = [seat for seat in ((closer + step) % SEATS for step in range(SEATS)) if seat % 2 == team]
            leader = members[0] if hand_pips[members[0]] <= hand_pips[members[1]] else members[1]
        expected = (team, True, leader)
    actual = (outcome.team, outcome.blocked, outcome.next_leader)
    if actual != expected:
        problems.append(f"{tag}: result (team, blocked, next leader) = {actual}, expected {expected}.")
    return problems
