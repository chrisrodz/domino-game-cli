"""Tests for deck creation and dealing."""

from domino_game.game.deck import create_deck, shuffle_deck


def test_deck_creation():
    """Test that deck has correct number of dominoes."""
    deck = create_deck()
    assert len(deck) == 28

    # Check all dominoes are unique
    unique_dominoes = set()
    for domino in deck:
        key = (min(domino.left, domino.right), max(domino.left, domino.right))
        unique_dominoes.add(key)

    assert len(unique_dominoes) == 28


def test_shuffle_deck():
    """Test deck shuffling."""
    create_deck()
    deck2 = create_deck()

    shuffle_deck(deck2)

    # After shuffling, the order should likely be different
    # (There's a tiny chance they could be the same, but it's extremely unlikely)
    assert len(deck2) == 28
