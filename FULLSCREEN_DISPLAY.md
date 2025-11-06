# Full-Screen Board Display Feature

## Overview

The Caribbean Domino Game CLI now features a full-screen, immersive board display that shows all game elements simultaneously. Players are positioned around a virtual table with the domino board in the center.

## Features

### Visual Layout

```
┌─────────────────────────────────────────────────────┐
│                   OPPONENT 1 (←)                    │
│                  [7 tiles remaining]                │
├─────────────────────────────────────────────────────┤
│          │                              │           │
│ ALLY (↑) │      DOMINO BOARD CENTER     │ OPP 2 (→) │
│          │                              │           │
│ 5 tiles  │   [3|5][5|2][2|6][6|4]      │  6 tiles  │
│          │   Left: 3 | Right: 4         │           │
│          │                              │           │
├─────────────────────────────────────────────────────┤
│                  YOUR HAND (You)                    │
│  [3|2]  [6|6]  [5|4]  [1|3]  [4|4]  [2|2]          │
│                                                     │
│  Valid Moves: 1. [3|2] Left  2. [5|4] Right        │
└─────────────────────────────────────────────────────┘
```

### Key Components

#### 1. **Game Header**
- Current round number
- Team scores with progress to target score
- Compact display at top of screen

#### 2. **Player Positions**
- **Top**: Opponent 1
- **Left**: Ally (your partner)
- **Right**: Opponent 2
- **Bottom**: You (human player)

#### 3. **Board Display**
- Centered domino chain
- Visual endpoints (left/right values)
- Highlighted last-played domino
- Color-coded dominoes

#### 4. **Player Information**

**For CPU Players:**
- Card-back symbols (🂠) representing tiles
- Tile count (e.g., "5 tiles remaining")
- Team affiliation
- Pass indicator if they passed last turn

**For Human Player:**
- Full hand display with actual tiles
- Tile values shown
- Numbered list of valid moves
- Move direction indicators (⬅️ Left, ➡️ Right, 🎯 First)

#### 5. **Turn Indicators**
- Heavy border around current player
- Green highlight for active player
- Status message in footer
- "PLAYING" indicator in title

#### 6. **Visual Effects**
- Last-played domino highlighted with arrows (►...◄)
- Smooth transitions with brief pauses
- Color-coded teams (Blue for Team 1, Red for Team 2)

## Technical Implementation

### Architecture

The full-screen display is implemented using three main classes:

1. **`BoardDisplay`** (`board_renderer.py`)
   - Renders the domino chain
   - Handles highlighting of last-played domino
   - Shows endpoint values

2. **`PlayerDisplay`** (`board_renderer.py`)
   - Renders CPU player info (tile counts, card backs)
   - Renders human player info (hand, valid moves)
   - Applies turn indicators and styling

3. **`GameRenderer`** (`board_renderer.py`)
   - Main rendering engine
   - Uses `Rich.Live` for live updates
   - Manages layout with `Rich.Layout`
   - Coordinates all display updates

### Integration

The `Game` class (`mvp.py`) has been updated to:
- Initialize the renderer at game start
- Stop/start live display for user input
- Update display after each game state change
- Maintain backward compatibility with legacy mode

### Backward Compatibility

The implementation includes fallback methods (`_play_turn_legacy`, `_play_round_legacy`) that preserve the original sequential display mode. You can toggle between modes using:

```python
game = Game()
game.use_full_screen = False  # Use legacy mode
```

## User Experience

### Gameplay Flow

1. **Round Start**
   - Display shows all players with 7 tiles each
   - Empty board in center
   - Starting player highlighted

2. **During Turns**
   - CPU players: "thinking" status shown, brief pause for realism
   - Human player: valid moves displayed, wait for input
   - After each play: board updates, last tile highlighted

3. **Passing**
   - "PASSED" indicator shown on player panel
   - Status message explains the pass

4. **Round End**
   - Live display stops
   - Results panel shown
   - Scores updated
   - Press Enter to continue

### Controls

- **Number keys**: Select your move (1, 2, 3, etc.)
- **Enter**: Confirm selections, continue between rounds
- **Ctrl+C**: Quit game

## Testing

Run the included test script to verify the renderer:

```bash
python test_renderer.py
```

This will cycle through different game states and demonstrate:
- All player positions
- Turn highlighting
- Last-played domino highlighting
- Board updates

## File Structure

```
domino-game-cli/
├── mvp.py                    # Main game logic (updated)
├── board_renderer.py         # New renderer classes
├── test_renderer.py          # Renderer test script
├── FULLSCREEN_DISPLAY.md     # This file
└── ...
```

## Future Enhancements

Potential improvements:
- Terminal size detection with automatic layout adjustments
- Animation for tile placement
- Sound effect hooks
- Color theme customization
- Accessibility options
- Statistics display between rounds

## Notes

- Minimum recommended terminal size: 80x24
- Works best with modern terminal emulators that support Rich formatting
- All colors and emojis are terminal-theme aware
- Layout automatically centers content
