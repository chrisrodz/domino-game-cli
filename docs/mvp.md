# Caribbean Dominoes CLI Game - POC

A command-line implementation of Caribbean-style dominoes (Puerto Rican rules) for 2v2 play.

## Overview

This is a proof-of-concept CLI application where you play Caribbean dominoes with a CPU ally against 2 CPU opponents. The game follows traditional Puerto Rican "Doscientos" (200 points) rules.

## Features

### Game Mechanics

- **Full Double-Six Set**: 28 dominoes (0-0 through 6-6)
- **2v2 Teams**: You + CPU Ally vs 2 CPU Opponents
- **Caribbean Rules**:
  - 7 dominoes per player
  - Counter-clockwise play
  - First game starts with double-six
  - Must pass if no valid moves
  - Round ends when someone goes out or game is blocked
  - First team to 200 points wins

### Scoring

- **Player Goes Out**: Winner gets sum of all other players' remaining dominoes
- **Blocked Game**: Player with lowest hand value wins, gets sum of ALL other players' dominoes
- **Target Score**: 200 points (traditional Doscientos)

### CPU AI

Simple but effective AI that:

- Plays valid moves intelligently
- Prioritizes high-value dominoes to reduce hand value
- Plays doubles when advantageous
- Works for both your ally and opponents

## Installation & Running

### Requirements

- Python 3.7 or higher

### Running the Game

```bash
# Make executable (first time only)
chmod +x domino_game.py

# Run the game
python3 domino_game.py

# Or directly
./domino_game.py
```

### Running Tests

```bash
python3 test_domino_game.py
```

## How to Play

### Game Start

1. Launch the game
2. You'll be dealt 7 random dominoes
3. The player with double-six [6|6] starts the first round

### Your Turn

1. You'll see:

   - Current board state
   - Board ends (left and right values)
   - Your hand
   - Valid moves available

2. Choose a move by entering the number (e.g., `1`, `2`, etc.)

3. The game will play your domino and move to the next player

### Example Turn

```
============================================================
You's Turn (Team 1)
============================================================
Board: [6|6] [6|3] [3|2]
Board ends: Left=[6] Right=[2]
Your hand: [0|2], [1|5], [2|4], [4|6], [5|5], [5|6]
Your hand value: 27 points
Valid moves:
  1. Play [0|2] on right
  2. Play [2|4] on right
  3. Play [4|6] on left
  4. Play [5|6] on left
Choose move (1-4):
```

### Game Flow

1. Players take turns counter-clockwise
2. CPU players automatically make their moves
3. If you can't play, you must pass
4. Round ends when:

   - Someone plays all their dominoes (goes out)
   - All players pass (game blocked)

5. Scores are calculated and added to team totals
6. Next round begins
7. First team to 200 points wins!

## Game Rules Summary

### Valid Moves

- Must match the number on either end of the domino line
- Example: If board ends are [3] and [5], you can play any domino with 3 or 5

### Scoring

- **Normal Win**: Sum of all other players' dominoes
- **Blocked Game**: Player with lowest hand wins, scores everyone's dominoes
- **Example**: You go out, opponents have 45 points remaining → you score 45

### Team Strategy

- You're on Team 1 with your Ally (CPU)
- Opponents 1 & 2 are Team 2
- Team scores accumulate across rounds
- First team to 200 wins the match

## Code Structure

### Main Components

```python
# Core Classes
Domino          # Represents a single domino tile [left|right]
Board           # Manages the domino line/train on the table
Player          # Represents a player (human or CPU)
Game            # Orchestrates the entire game flow

# Key Methods
- Board.can_play(domino)          # Check if domino is playable
- Player.get_valid_moves(board)   # Find all valid moves
- Game.play_turn(player)          # Execute a player's turn
- Game.calculate_round_scores()   # Determine round winner and points
```

### Architecture

```
domino_game.py
├── Domino class          # Tile representation
├── Board class           # Game board management
├── Player class          # Player logic
├── Game class            # Game orchestration
└── main()                # Entry point
test_domino_game.py       # Unit tests
```

## Testing

The test suite covers:

- ✓ Domino basic functionality (value, doubles, matching)
- ✓ Board operations (playing, valid moves, both ends)
- ✓ Player hand management
- ✓ Deck creation (28 unique dominoes)
- ✓ Dealing (7 per player, 28 total)
- ✓ Game setup (4 players, correct teams)
- ✓ Scoring (going out scenario)
- ✓ Blocked games (lowest hand wins)

## Future Enhancements

Potential improvements for a full version:

- [ ] More sophisticated CPU AI (strategic blocking, team coordination)
- [ ] Boneyard support for 2-3 player games
- [ ] Bonus scoring (double-out, shutouts, etc.)
- [ ] Game history and statistics
- [ ] Save/load game state
- [ ] Multiple scoring modes (100, 200, 500 points)
- [ ] Chiva variation (4 consecutive wins)
- [ ] Replay functionality
- [ ] Colorized terminal output
- [ ] Sound effects

## Caribbean Domino Rules Reference

For complete rules, see:

- `/docs/DOMINO_RULES.md` - Comprehensive rule documentation
- `/docs/DOMINO_GAME_FLOW.md` - Visual game flow diagram

## License

This is a proof-of-concept implementation for the DobleSeis project.

## Credits

Based on traditional Caribbean domino rules, primarily Puerto Rican "Doscientos" style.
