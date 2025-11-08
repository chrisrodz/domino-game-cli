"""Tests for Domino model."""

from domino_game.models import Domino


def test_domino_basics():
    """Test basic domino functionality."""
    d1 = Domino(3, 5)
    assert d1.value() == 8
    assert not d1.is_double()
    assert d1.has_value(3)
    assert d1.has_value(5)
    assert not d1.has_value(6)

    d2 = Domino(6, 6)
    assert d2.is_double()
    assert d2.value() == 12


def test_domino_flip():
    """Test domino flip functionality."""
    d1 = Domino(3, 5)
    d2 = d1.flip()
    assert d2.left == 5
    assert d2.right == 3


def test_domino_equality():
    """Test domino equality."""
    d1 = Domino(3, 5)
    d2 = Domino(5, 3)
    d3 = Domino(3, 5)

    assert d1 == d2
    assert d1 == d3


def test_domino_hash():
    """Test domino hashing for set operations."""
    d1 = Domino(3, 5)
    d2 = Domino(5, 3)

    domino_set = {d1}
    assert d2 in domino_set
