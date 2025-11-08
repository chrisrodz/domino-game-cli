# 🎲 Caribbean Dominoes CLI

![CI](https://github.com/chrisrodz/domino-game-cli/workflows/CI/badge.svg)

A beautiful, interactive CLI application to play Caribbean dominoes and learn how to get better so you can beat your friends IRL!

## ✨ Features

- **🎨 Beautiful Interface**: Rich, colorful terminal output with panels, tables, and emojis
- **⌨️ Arrow Key Navigation**: Navigate menus using ↑↓ arrow keys or Vim-style j/k keys
- **🤖 Smart CPU Opponents**: Play against intelligent CPU players
- **👥 Team-Based Gameplay**: 2v2 teams (You + Ally vs 2 Opponents)
- **📊 Real-Time Scoring**: Track scores and progress throughout the game
- **🎯 Multiple Game Modes**: Standard and quick play modes
- **📖 Built-in Rules**: Access game rules and help anytime

## 🚀 Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd domino-game-cli
```

2. Install the package:
```bash
pip install -e .
```

Or using uv:
```bash
uv sync
```

3. Activate the virtual environment (if using uv):
```bash
# On macOS/Linux
source .venv/bin/activate

# On Windows
.venv\Scripts\activate
```

**Or** skip activation and use `uv run` to run commands (see Usage below).

## 🎮 Usage

### Start a Game

**Option A - With activated virtual environment:**
```bash
# Play with default settings (first to 200 points)
domino play

# Quick mode (first to 100 points)
domino play --quick

# Custom target score
domino play --target 150

# Or use the main.py entry point
python main.py play
```

**Option B - Without activating (using uv run):**

```bash
# Play with default settings
uv run domino play

# Or using main.py
uv run python main.py play
```

### View Commands

```bash
# Show all available commands
domino --help

# View game rules
domino rules

# About the game
domino about
```

## 🎯 Game Controls

- **↑/↓ or j/k**: Navigate menu options
- **Enter**: Select/Confirm choice
- **Vim-style navigation**: Supports j (down) and k (up) for Vim users

## 📖 Game Rules

### Setup
- 4 players in 2 teams (You + Ally vs 2 Opponents)
- Each player gets 7 dominoes from a double-six set
- First round starts with the [6|6] domino

### Gameplay
- Players take turns counter-clockwise
- Match your domino to either end of the line
- If you can't play, you must pass
- Round ends when someone plays all dominoes or all players pass

### Scoring
- Winner scores the sum of all remaining dominoes in other players' hands
- If game is blocked, player with lowest hand value wins
- First team to reach target score (default: 200) wins!

## 🛠️ Technology Stack

- **Python 3.9+**: Core language
- **Typer**: CLI framework with rich help formatting
- **Rich**: Beautiful terminal output with colors and formatting

## 📁 Project Structure

```
domino-game-cli/
├── domino_game/              # Main package
│   ├── models/               # Domain models (Domino, Board, Player)
│   ├── game/                 # Game engine & logic (AI, scoring, deck)
│   ├── ui/                   # User interface components
│   │   └── renderer/         # Full-screen rendering
│   └── cli.py               # CLI commands
├── tests/                    # Organized test suite
│   ├── test_models/
│   ├── test_game/
│   └── test_ui/
├── main.py                   # Entry point
└── pyproject.toml           # Project configuration
```

## 🧪 Testing

Run all tests using the test runner:

```bash
python run_tests.py
```

Or run individual test modules:

```bash
# Test models
python tests/test_models/test_domino.py
python tests/test_models/test_board.py
python tests/test_models/test_player.py

# Test game logic
python tests/test_game/test_deck.py
python tests/test_game/test_ai.py
python tests/test_game/test_engine.py
python tests/test_game/test_scoring.py

# Test UI
python tests/test_ui/test_renderer.py
```

Continuous Integration runs automatically on:
- Pull requests to `main`
- Pushes to `main` branch

The CI tests the package on Python 3.9, 3.10, 3.11, and 3.12.

## 📝 Commands Reference

| Command | Options | Description |
|---------|---------|-------------|
| `play` | `--target/-t`, `--quick/-q` | Start a new game |
| `rules` | - | Display game rules |
| `about` | - | About the application |

## 🎨 Screenshots

The game features:
- Colorful domino representations with unique colors for each number
- Beautiful panels and borders for game states
- Real-time score tracking in tables
- Visual feedback for moves and game events
- Clean, organized layout for easy gameplay

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues and enhancement requests.

## 📜 License

See LICENSE file for details.

---

**Version 2.0 - Enhanced Edition** 🚀
