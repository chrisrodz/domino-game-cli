#!/usr/bin/env python3
"""Tests for Domino model."""

from domino_game.models import Domino


def test_domino_basics():
    """Test basic domino functionality."""
    d1 = Domino(3, 5)
    assert d1.value() == 8, "Domino value should be 8"
    assert not d1.is_double(), "3-5 should not be a double"
    assert d1.has_value(3), "Should have value 3"
    assert d1.has_value(5), "Should have value 5"
    assert not d1.has_value(6), "Should not have value 6"

    d2 = Domino(6, 6)
    assert d2.is_double(), "6-6 should be a double"
    assert d2.value() == 12, "Double-six value should be 12"


def test_domino_flip():
    """Test domino flip functionality."""
    d1 = Domino(3, 5)
    d2 = d1.flip()
    assert d2.left == 5, "Flipped domino left should be 5"
    assert d2.right == 3, "Flipped domino right should be 3"


def test_domino_equality():
    """Test domino equality."""
    d1 = Domino(3, 5)
    d2 = Domino(5, 3)
    d3 = Domino(3, 5)

    assert d1 == d2, "Domino(3,5) should equal Domino(5,3)"
    assert d1 == d3, "Domino(3,5) should equal Domino(3,5)"


def test_domino_hash():
    """Test domino hashing for set operations."""
    d1 = Domino(3, 5)
    d2 = Domino(5, 3)

    domino_set = {d1}
    assert d2 in domino_set, "Flipped domino should have same hash"


if __name__ == "__main__":
    test_domino_basics()
    test_domino_flip()
    test_domino_equality()
    test_domino_hash()
    print("✓ All domino tests passed!")
