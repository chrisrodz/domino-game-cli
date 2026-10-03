"""Complete double-six tables for tests that infer unseen holdings."""

from domino_game.game.deck import create_deck
from domino_game.game.engine import Game
from domino_game.models import Domino


def complete_table(game: Game, acting_seat: int = 1) -> None:
    game.board.dominoes = [Domino(6, 0), Domino(0, 5), Domino(5, 1), Domino(1, 6), Domino(6, 2)]
    visible = [*game.board.dominoes, *game.players[acting_seat].hand]
    remaining = [tile for tile in create_deck() if tile not in visible]
    seats = [seat for seat in range(4) if seat != acting_seat]
    for index, seat in enumerate(seats):
        count = len(remaining) // (len(seats) - index)
        game.players[seat].hand = remaining[:count]
        remaining = remaining[count:]
