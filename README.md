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

## 🚀 Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd domino-game-cli
```

2. Install dependencies:
```bash
uv sync
```

That's it! Use `uv run python main.py` to start playing (see Usage below).

## 🎮 Usage

### Play in 3D with Blender-built assets

```bash
uv run python main.py patio

# Optional: custom score, single round, or another local port
uv run python main.py patio --target 100
uv run python main.py patio --single-round
uv run python main.py patio --port 8001 --no-browser
```

El Patio opens at `http://127.0.0.1:8000`. Play the existing 2v2 game at a
sunlit backyard table, with white plastic chairs and banana plants inspired by
the setting of Bad Bunny's *Debi Tirar Mas Fotos* cover. All scene geometry is
original, created in Blender; no album artwork or music is included.

Select a highlighted tile in your hand (or on the 3D table), then choose an
available end. Keys 1-7 select tiles. CPU turns play automatically. Drag to
orbit, scroll or pinch to zoom, or choose **Table view** for an overhead camera.
**New game** offers a single round or a target score from 1 to 1000.

The browser uses the Python game's dealing, valid moves, CPU strategy, and
scoring. Blocked rounds award all unplayed pips, including the winning hand;
ties favor the team that last played. Later rounds use the CLI's current opener
behavior (You start). Refreshing retains the game while the server runs.
Stopping the server clears games. Each browser session gets a separate match.

Requires a browser with WebGL 2. The Python server binds only to loopback;
it is intended for local play. All browser dependencies and assets are included,
so playing requires no internet connection or Node.js tooling.

The editable scene is `domino_game/patio/web/assets/el-patio.blend`.
To rebuild the two GLB files with Blender 4.5 or later:

```bash
blender --background --python tools/build_patio.py
```

The browser renderer is Three.js 0.186.1 (MIT), vendored with its license in
`domino_game/patio/web/vendor/`. The existing terminal commands remain available.

### Start a Game

```bash
# Play with default settings (first to 200 points)
uv run python main.py play

# Quick mode (first to 100 points)
uv run python main.py play --quick

# Custom target score
uv run python main.py play --target 150
```

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
