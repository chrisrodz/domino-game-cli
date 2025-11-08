"""Tests for the board renderer."""

import time

import pytest
from rich.console import Console

from domino_game.game.engine import Game
from domino_game.models import Domino
from domino_game.ui.renderer.game_renderer import GameRenderer


@pytest.mark.slow
def test_renderer():
    """Test the full-screen renderer with a sample game state."""
    console = Console()
    game = Game()
    game.setup_players()
    game.deal_dominoes()
    game.current_player_idx = 0

    # Play a few dominoes for testing
    game.board.play_domino(Domino(3, 5))
    game.board.play_domino(Domino(5, 2))
    game.board.play_domino(Domino(2, 6))

    # Remove those dominoes from players' hands (just for display testing)
    for player in game.players:
        if Domino(3, 5) in player.hand:
            player.remove_domino(Domino(3, 5))
            break

    # Create and test renderer
    renderer = GameRenderer(console)
    renderer.start_live_display()

    try:
        # Test different game states
        for i in range(4):
            game.current_player_idx = i
            valid_moves = game.players[0].get_valid_moves(game.board) if i == 0 else None

            status = f"Testing player {i} - {game.players[i].name}"
            renderer.update_display(game, valid_moves, status)
            renderer.refresh()
            time.sleep(0.5)  # Reduced from 2s for faster tests

        # Test with last played highlighting
        last_domino = Domino(6, 4)
        game.board.play_domino(last_domino)
        renderer.mark_last_played(last_domino)
        renderer.update_display(game, None, "Highlighting last played domino")
        renderer.refresh()
        time.sleep(0.5)

        renderer.clear_last_played()
        renderer.update_display(game, None, "Test complete!")
        renderer.refresh()
        time.sleep(0.5)

    finally:
        renderer.stop_live_display()

    console.print("[green]✓ Renderer test completed successfully![/green]")


def test_renderer_creation():
    """Test basic renderer creation."""
    console = Console()
    renderer = GameRenderer(console)
    assert renderer.console == console
    assert renderer.layout is None
    assert renderer.live is None
    assert renderer.last_played_domino is None
