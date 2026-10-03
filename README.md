# 🎲 Caribbean Dominoes CLI

![CI](https://github.com/chrisrodz/domino-game-cli/workflows/CI/badge.svg)

A beautiful, interactive CLI application to play Caribbean dominoes and learn how to get better so you can beat your friends IRL!

## ✨ Features

- **🎨 Beautiful Interface**: Rich, colorful terminal output with panels, tables, and emojis
- **⌨️ Arrow Key Navigation**: Navigate menus using ↑↓ arrow keys or Vim-style j/k keys
- **🤖 Smart CPU Opponents**: Play against intelligent CPU players
- **CPU Difficulty per Player**: Simple local play, Medium Jev decisions, or Hard Jev decisions with public turn history
- **👥 Team-Based Gameplay**: 2v2 teams (You + Ally vs 2 Opponents)
- **📊 Real-Time Scoring**: Track scores and progress throughout the game
- **🎯 Multiple Game Modes**: Standard and quick play modes
- **📖 Built-in Rules**: Access game rules and help anytime

## 🚀 Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd domino-game-cli
```

2. Install dependencies (uv uses the Python 3.14.8 pin in `.python-version`):
```bash
uv sync
```

That's it! Use `uv run python main.py` to start playing (see Usage below).

## 🎮 Usage

### Start a Game

```bash
# Play with default settings (first to 200 points)
uv run python main.py play

# Quick mode (first to 100 points)
uv run python main.py play --quick

# Custom target score
uv run python main.py play --target 150
```

### CPU Difficulty

Choose a difficulty separately for your ally and each opponent in the setup menu, or use flags:

```bash
uv run python main.py play --single-round --ally hard --opponent-1 medium --opponent-2 simple
```

All CPUs default to `simple`. Any explicit game or CPU flag skips the setup menu; unspecified CPUs remain `simple`.

| Difficulty | Decision method | Available information |
|------------|-----------------|-----------------------|
| `simple` | Local greedy strategy: highest pip value, with a bonus for doubles | Own hand and legal moves |
| `medium` | Jev scores hand connections, suit control, and double management | Own hand, current board, public tile counts, team scores, and rules |
| `hard` | Medium's tactics plus partner support, opponent pressure, and blocking | Medium's information plus all public turns and round results so far |

Medium receives no remembered passes, ordered move history, or history-derived features. Hard remembers who played or
passed and the board ends at each turn. Pass deductions apply only to the current deal. Previous rounds stay in its
history, but their missing-number deductions expire when tiles are redealt. Neither Jev level receives another player's
hidden tiles or unrevealed hand value. Public blocked-round hand totals are recorded only after they are displayed.

Medium and Hard require internet access and `TYPESAFE_API_KEY` in your environment. Create a key at the
[TypeSafe console](https://console.typesafe.ai/keys). The integration uses the official Python SDK and its model default;
`TYPESAFE_DEFAULT_MODEL` can override the model. Credentials stay in the environment, outside the repository.

The engine computes legal moves, suit counts, hand connectivity, possible unseen holdings, and pip bounds in Python.
Jev evaluates independent tactical questions for each candidate in one request. Python combines the scores using explicit
weights; Hard shifts priorities when a partner or opponent has few tiles, or a favorable block becomes plausible. Public
suit signals count only when observed alternatives establish a voluntary choice. Uncertain judgments shrink toward neutral;
proven passes and finishes retain their full effect. Forced moves, proven wins, and passes make no API request.
HTTP operations use a two-second timeout without retries. A timeout,
service failure, or invalid answer uses Simple for that turn, with a visible fallback message. Credential or request
configuration errors stop the game with an actionable message. Difficulty labels describe tactical scope and available
information; a small benchmark does not establish comparative playing strength.

See [Jev decision design](docs/JEV_AI.md) for the questions, weighting policies, privacy boundary, and live comparison command.

AI follows the engine's current rules: later rounds start at seat 0; an empty board offers double-six if held, otherwise
the first tile in the starting hand. Blocked rounds award all remaining pips, including the winner's, with ties favoring
the last-playing team. This AI change preserves those behaviors.

### View Commands

```bash
# Show all available commands
uv run python main.py --help

# View game rules
uv run python main.py rules

# About the game
uv run python main.py about
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

- **Python 3.14+**: Core language
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

Install dev dependencies first:

```bash
uv sync --extra dev
```

Run all tests with pytest:

```bash
uv run pytest                    # Run all tests
uv run pytest -v                 # Verbose output
uv run pytest -m "not slow"      # Skip slow tests
```

Run specific tests:

```bash
# Test specific directory
uv run pytest tests/test_game/

# Test specific file
uv run pytest tests/test_models/test_domino.py

# Test specific function
uv run pytest tests/test_game/test_ai.py::test_simple_strategy
```

Run with coverage:

```bash
uv run pytest --cov=domino_game --cov-report=term-missing
```

Continuous Integration runs automatically on:
- Pull requests to `main`
- Pushes to `main` branch

CI runs tests and lint checks on Python 3.14.8, using the same `.python-version` pin as local development.

## 📝 Commands Reference

| Command | Options | Description |
|---------|---------|-------------|
| `play` | `--target/-t`, `--quick/-q`, `--single-round/-s`, `--skip-setup`, `--ally`, `--opponent-1`, `--opponent-2` | Start a new game with independent CPU difficulties |
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
