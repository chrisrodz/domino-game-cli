#!/usr/bin/env python3
"""
Unit tests for the Caribbean Domino Game
"""

from mvp import Domino, Board, Player, Game, PlayerType


def test_domino_basics():
    """Test basic domino functionality."""
    print("Testing Domino class...")

    d1 = Domino(3, 5)
    assert d1.value() == 8, "Domino value should be 8"
    assert not d1.is_double(), "3-5 should not be a double"
    assert d1.has_value(3), "Should have value 3"
    assert d1.has_value(5), "Should have value 5"
    assert not d1.has_value(6), "Should not have value 6"

    d2 = Domino(6, 6)
    assert d2.is_double(), "6-6 should be a double"
    assert d2.value() == 12, "Double-six value should be 12"

    print("  ✓ Domino class works correctly")


def test_board():
    """Test board functionality."""
    print("Testing Board class...")

    board = Board()
    assert board.is_empty(), "New board should be empty"
    assert board.left_value() is None, "Empty board should have no left value"
    assert board.right_value() is None, "Empty board should have no right value"

    # Play first domino
    d1 = Domino(3, 5)
    board.play_domino(d1)
    assert not board.is_empty(), "Board should not be empty after playing"
    assert board.left_value() == 3, "Left value should be 3"
    assert board.right_value() == 5, "Right value should be 5"

    # Play on right end
    d2 = Domino(5, 2)
    assert board.can_play(d2), "Should be able to play 5-2"
    board.play_domino(d2, on_left=False)
    assert board.left_value() == 3, "Left value should still be 3"
    assert board.right_value() == 2, "Right value should now be 2"

    # Play on left end
    d3 = Domino(6, 3)
    assert board.can_play(d3), "Should be able to play 6-3"
    board.play_domino(d3, on_left=True)
    assert board.left_value() == 6, "Left value should now be 6"
    assert board.right_value() == 2, "Right value should still be 2"

    # Try invalid domino
    d4 = Domino(4, 4)
    assert not board.can_play(d4), "Should not be able to play 4-4"

    print("  ✓ Board class works correctly")


def test_player():
    """Test player functionality."""
    print("Testing Player class...")

    player = Player("Test Player", PlayerType.HUMAN, 0)

    # Add dominoes
    player.add_domino(Domino(3, 5))
    player.add_domino(Domino(6, 6))
    player.add_domino(Domino(2, 4))

    assert len(player.hand) == 3, "Player should have 3 dominoes"
    assert player.hand_value() == 26, "Hand value should be 8+12+6=26"
    assert player.has_double_six(), "Player should have double-six"

    # Valid moves
    board = Board()
    board.play_domino(Domino(5, 1))
    valid_moves = player.get_valid_moves(board)

    # Should be able to play 3-5 on either end
    assert len(valid_moves) >= 1, "Should have at least one valid move"

    # Remove domino
    player.remove_domino(Domino(3, 5))
    assert len(player.hand) == 2, "Player should have 2 dominoes left"

    print("  ✓ Player class works correctly")


def test_deck_creation():
    """Test that deck has correct number of dominoes."""
    print("Testing deck creation...")

    game = Game()
    deck = game.create_deck()

    assert len(deck) == 28, "Double-six set should have 28 dominoes"

    # Check all dominoes are unique
    unique_dominoes = set()
    for domino in deck:
        key = (min(domino.left, domino.right), max(domino.left, domino.right))
        unique_dominoes.add(key)

    assert len(unique_dominoes) == 28, "All dominoes should be unique"

    print("  ✓ Deck creation works correctly")


def test_dealing():
    """Test dealing dominoes to players."""
    print("Testing dealing...")

    game = Game()
    game.setup_players()
    game.deal_dominoes()

    assert len(game.players) == 4, "Should have 4 players"

    total_dominoes = 0
    for player in game.players:
        assert len(player.hand) == 7, f"{player.name} should have 7 dominoes"
        total_dominoes += len(player.hand)

    assert total_dominoes == 28, "All 28 dominoes should be dealt"

    print("  ✓ Dealing works correctly")


def test_game_setup():
    """Test game setup."""
    print("Testing game setup...")

    game = Game()
    game.setup_players()

    assert len(game.players) == 4, "Should have 4 players"
    assert game.players[0].name == "You", "First player should be human"
    assert game.players[0].player_type == PlayerType.HUMAN, "First player should be human type"
    assert game.players[0].team == 0, "Player should be on team 0"
    assert game.players[2].team == 0, "Ally should be on team 0"
    assert game.players[1].team == 1, "Opponent 1 should be on team 1"
    assert game.players[3].team == 1, "Opponent 2 should be on team 1"

    print("  ✓ Game setup works correctly")


def test_scoring():
    """Test scoring calculation."""
    print("Testing scoring...")

    game = Game()
    game.setup_players()

    # Simulate a player going out
    game.players[0].hand = []  # Player went out
    game.players[1].hand = [Domino(3, 5), Domino(2, 2)]  # 8 + 4 = 12
    game.players[2].hand = [Domino(1, 6)]  # 7
    game.players[3].hand = [Domino(4, 4)]  # 8

    winning_team, points = game.calculate_round_scores()
    assert winning_team == 0, "Team 0 should win (player went out)"
    assert points == 27, "Should score 12+7+8=27 points"

    print("  ✓ Scoring works correctly")


def test_blocked_game():
    """Test blocked game scenario."""
    print("Testing blocked game...")

    game = Game()
    game.setup_players()

    # Simulate a blocked game with different hand values
    game.players[0].hand = [Domino(3, 5)]  # 8 points
    game.players[1].hand = [Domino(2, 2), Domino(1, 1)]  # 6 points (winner)
    game.players[2].hand = [Domino(4, 5)]  # 9 points
    game.players[3].hand = [Domino(6, 6)]  # 12 points

    winning_team, points = game.calculate_round_scores()
    assert winning_team == 1, "Team 1 should win (lowest hand value)"
    assert points == 29, "Should score 8+9+12=29 points"

    print("  ✓ Blocked game handling works correctly")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("Running Caribbean Domino Game Tests")
    print("="*60 + "\n")

    try:
        test_domino_basics()
        test_board()
        test_player()
        test_deck_creation()
        test_dealing()
        test_game_setup()
        test_scoring()
        test_blocked_game()

        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60 + "\n")
        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
