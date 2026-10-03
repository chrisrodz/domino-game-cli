"""Headless game engine and business logic.

The terminal `Game` lives in `domino_game.game.engine`; it is not re-exported so
the engine imports without terminal dependencies such as rich.
"""

from domino_game.game.ai import CPUStrategy, SimpleStrategy
from domino_game.game.deck import create_deck, shuffle_deck
from domino_game.game.match import Match
from domino_game.game.rules import RuleError, legal_moves, score_round
from domino_game.game.scoring import determine_winner

__all__ = [
    "CPUStrategy",
    "Match",
    "RuleError",
    "SimpleStrategy",
    "create_deck",
    "determine_winner",
    "legal_moves",
    "score_round",
    "shuffle_deck",
]
