"""Deck creation and dealing utilities."""

import random
from typing import List
from domino_game.models.domino import Domino


def create_deck() -> List[Domino]:
    """Create a full double-six domino set (28 tiles)."""
    deck = []
    for i in range(7):
        for j in range(i, 7):
            deck.append(Domino(i, j))
    return deck


def shuffle_deck(deck: List[Domino]) -> None:
    """Shuffle a deck of dominoes in place."""
    random.shuffle(deck)
