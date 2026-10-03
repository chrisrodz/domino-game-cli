"""Exact deductions from an actor's hand, visible tiles, counts, and public passes."""

from dataclasses import dataclass
from functools import cache

type Tile = tuple[int, int]
type Ends = tuple[int | None, int | None]
type JSONValue = str | int | float | bool | None | list[JSONValue] | dict[str, JSONValue]


class ObservationError(ValueError):
    """Visible game facts cannot describe a consistent double-six deal."""


@dataclass(frozen=True)
class KnowledgeInput:
    own_tiles: tuple[Tile, ...]
    board_tiles: tuple[Tile, ...]
    other_counts: dict[int, int]
    missing_numbers: dict[int, set[int]]


@dataclass(frozen=True)
class TableKnowledge:
    unseen_tiles: tuple[Tile, ...]
    possible_tiles: dict[int, tuple[Tile, ...]]
    pip_bounds: dict[int, tuple[int, int]]

    def to_state(self) -> dict[str, JSONValue]:
        return {
            "unseen_tiles": [list(tile) for tile in self.unseen_tiles],
            "unseen_suit_counts": suit_counts(self.unseen_tiles),
            "possible_holdings_by_seat": {
                str(seat): {
                    "possible_tiles": [list(tile) for tile in tiles],
                    "hand_pips_min": self.pip_bounds[seat][0],
                    "hand_pips_max": self.pip_bounds[seat][1],
                }
                for seat, tiles in self.possible_tiles.items()
            },
            "interpretation": "Possible holdings and bounds, not revealed hands or ownership probabilities",
        }


def suit_counts(tiles: tuple[Tile, ...]) -> dict[str, int]:
    # A double belongs to its suit once; this is a tile count, not a pip count.
    return {str(number): sum(number in tile for tile in tiles) for number in range(7)}


def derive_knowledge(facts: KnowledgeInput) -> TableKnowledge:
    visible = [tuple(sorted(tile)) for tile in (*facts.own_tiles, *facts.board_tiles)]
    deck = {(left, right) for left in range(7) for right in range(left, 7)}
    if len(set(visible)) != len(visible) or any(tile not in deck for tile in visible):
        raise ObservationError("Own hand and board must contain distinct double-six tiles")
    unseen = tuple(sorted(deck - set(visible)))
    seats = tuple(sorted(facts.other_counts))
    capacities = tuple(facts.other_counts[seat] for seat in seats)
    if sum(capacities) != len(unseen) or any(count < 0 or count > 7 for count in capacities):
        raise ObservationError(f"Public hand counts {facts.other_counts} do not match {len(unseen)} unseen tiles")
    domains = tuple(
        tuple(index for index, seat in enumerate(seats) if not set(tile) & facts.missing_numbers.get(seat, set()))
        for tile in unseen
    )

    @cache
    def bounds(index: int, remaining: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
        if index == len(unseen):
            return ((0,) * len(seats), (0,) * len(seats)) if not any(remaining) else None
        branches = []
        for owner in domains[index]:
            if remaining[owner] == 0:
                continue
            after = tuple(count - (position == owner) for position, count in enumerate(remaining))
            child = bounds(index + 1, after)
            if child is not None:
                value = sum(unseen[index])
                branches.append(
                    tuple(
                        tuple(pips + (value if position == owner else 0) for position, pips in enumerate(row)) for row in child
                    )
                )
        if not branches:
            return None
        return (
            tuple(min(branch[0][owner] for branch in branches) for owner in range(len(seats))),
            tuple(max(branch[1][owner] for branch in branches) for owner in range(len(seats))),
        )

    totals = bounds(0, capacities)
    if totals is None:
        raise ObservationError("Public passes and hand counts admit no consistent allocation of the unseen tiles")
    possible: dict[int, list[Tile]] = {seat: [] for seat in seats}
    frontier = {capacities}
    for index, tile in enumerate(unseen):
        next_frontier = set()
        owners = set()
        for remaining in frontier:
            for owner in domains[index]:
                if remaining[owner] == 0:
                    continue
                after = tuple(count - (position == owner) for position, count in enumerate(remaining))
                if bounds(index + 1, after) is not None:
                    owners.add(owner)
                    next_frontier.add(after)
        for owner in owners:
            possible[seats[owner]].append(tile)
        frontier = next_frontier
    return TableKnowledge(
        unseen_tiles=unseen,
        possible_tiles={seat: tuple(tiles) for seat, tiles in possible.items()},
        pip_bounds={seat: (totals[0][index], totals[1][index]) for index, seat in enumerate(seats)},
    )


def hand_connections(tiles: tuple[Tile, ...], ends: Ends) -> dict[str, JSONValue]:
    reachable = {number for number in ends if number is not None}
    while True:
        extended = reachable | {number for tile in tiles if set(tile) & reachable for number in tile}
        if extended == reachable:
            break
        reachable = extended
    return {
        "suit_counts": suit_counts(tiles),
        "distinct_suits": len({number for tile in tiles for number in tile}),
        "tiles_reachable_through_own_connections": sum(bool(set(tile) & reachable) for tile in tiles),
        "disconnected_tiles": [list(tile) for tile in tiles if not set(tile) & reachable],
        "interpretation": "Own-hand connectivity on these ends; other players may change the board before the next turn",
    }
