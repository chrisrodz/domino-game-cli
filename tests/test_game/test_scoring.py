"""Round scoring under Puerto Rican Doscientos rules."""

import pytest

from domino_game.game.rules import RuleError, score_round
from domino_game.game.scoring import determine_winner
from domino_game.models import Domino as D


def test_domino_scores_every_remaining_pip_including_partner():
    hands = [[], [D(3, 5), D(2, 2)], [D(1, 6)], [D(4, 4)]]
    outcome = score_round(hands, closer=0)
    assert (outcome.team, outcome.points, outcome.blocked, outcome.next_leader) == (0, 27, False, 0)


def test_tranque_goes_to_lower_team_total_not_lowest_single_hand():
    # Seat 1 holds the lowest hand (6), but team 0 holds fewer pips (8 + 9 < 6 + 12).
    hands = [[D(3, 5)], [D(2, 2), D(1, 1)], [D(4, 5)], [D(6, 6)]]
    outcome = score_round(hands, closer=1)
    assert outcome.team_pips == (17, 18)
    assert (outcome.team, outcome.points, outcome.blocked) == (0, 35, True)
    assert outcome.next_leader == 0, "the winning team's member with fewer pips leads next"


def test_tranque_partners_tied_on_pips_resolve_nearest_the_closer():
    hands = [[D(1, 4)], [D(5, 5)], [D(2, 3)], [D(6, 4)]]
    assert score_round(hands, closer=1).next_leader == 2
    assert score_round(hands, closer=3).next_leader == 0


def test_tranque_tied_teams_go_to_the_closer_who_leads_next():
    hands = [[D(1, 4)], [D(2, 3)], [D(5, 5)], [D(6, 4)]]
    for closer in range(4):
        outcome = score_round(hands, closer=closer)
        assert outcome.team_pips == (15, 15)
        assert (outcome.team, outcome.points, outcome.next_leader) == (closer % 2, 30, closer)


def test_scoring_rejects_inconsistent_closer():
    with pytest.raises(RuleError, match="different seat"):
        score_round([[D(1, 1)], [], [D(2, 2)], [D(3, 3)]], closer=0)


def test_determine_winner():
    assert determine_winner([150, 100], 200) == -1
    assert determine_winner([200, 150], 200) == 0
    assert determine_winner([180, 210], 200) == 1
