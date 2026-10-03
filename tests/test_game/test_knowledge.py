"""Check public deductions against exhaustive allocations, never actual hidden hands."""

from itertools import combinations

import pytest

from domino_game.game.knowledge import KnowledgeInput, ObservationError, derive_knowledge, hand_connections, suit_counts


def table_facts(unseen, counts, missing):
    own = ((6, 6),)
    board = tuple((left, right) for left in range(7) for right in range(left, 7) if (left, right) not in (*own, *unseen))
    return KnowledgeInput(own, board, counts, missing)


def test_counts_and_passes_can_prove_tile_ownership():
    unseen = ((0, 0), (0, 1), (1, 1), (2, 2))
    facts = table_facts(unseen, {1: 2, 2: 1, 3: 1}, {2: {0, 1}})
    result = derive_knowledge(facts)
    assert result.possible_tiles[2] == ((2, 2),)
    assert result.pip_bounds[2] == (4, 4)
    assert result.pip_bounds[1] == (1, 3)
    assert result.pip_bounds[3] == (0, 2)
    assert all((2, 2) not in result.possible_tiles[seat] for seat in (1, 3))


def test_possible_owners_and_pip_bounds_match_exhaustive_deals():
    unseen = ((0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3))
    missing = {1: {3}, 2: {0}, 3: {2}}
    valid = []
    for first in combinations(unseen, 2):
        remainder = tuple(tile for tile in unseen if tile not in first)
        for second in combinations(remainder, 2):
            third = tuple(tile for tile in remainder if tile not in second)
            hands = {1: first, 2: second, 3: third}
            if all(not set(tile) & missing[seat] for seat, hand in hands.items() for tile in hand):
                valid.append(hands)
    assert valid
    actual = derive_knowledge(table_facts(unseen, {1: 2, 2: 2, 3: 2}, missing))
    for seat in (1, 2, 3):
        expected_tiles = {tile for hands in valid for tile in hands[seat]}
        values = [sum(map(sum, hands[seat])) for hands in valid]
        assert set(actual.possible_tiles[seat]) == expected_tiles
        assert actual.pip_bounds[seat] == (min(values), max(values))


def test_impossible_public_evidence_fails_at_source():
    with pytest.raises(ObservationError, match="no consistent allocation"):
        derive_knowledge(table_facts(((0, 0),), {1: 1, 2: 0, 3: 0}, {1: {0}}))
    with pytest.raises(ObservationError, match="hand counts"):
        derive_knowledge(table_facts(((0, 0),), {1: 2, 2: 0, 3: 0}, {}))
    with pytest.raises(ObservationError, match="distinct"):
        derive_knowledge(KnowledgeInput(((6, 6),), ((6, 6),), {1: 7, 2: 7, 3: 7}, {}))


def test_double_counts_once_and_connectivity_does_not_promise_future_turns():
    tiles = ((2, 4), (4, 4), (4, 1), (0, 0))
    assert suit_counts(tiles)["4"] == 3
    facts = hand_connections(tiles, (6, 2))
    assert facts["tiles_reachable_through_own_connections"] == 3
    assert facts["disconnected_tiles"] == [[0, 0]]
    assert "may change" in facts["interpretation"]
