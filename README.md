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
uv run python main.py patio --autoplay   # watch four CPUs play
uv run python main.py patio --port 8001 --no-browser
```

El Patio opens at `http://127.0.0.1:8000`. Play the existing 2v2 game at a
sunlit backyard table, with white plastic chairs and banana plants inspired by
the setting of Bad Bunny's *Debi Tirar Mas Fotos* cover. All scene geometry is
original, created in Blender; no album artwork or music is included.

Every action happens on the table or the keyboard. Your seven tiles stand at
your edge of the table, numbered 1-7 from your left; playable ones glow. Click a
tile, then a glowing end (`L` or `R`). Click the selected tile again to play it
when only one end fits. A tile matching both ends can go on either side, even
when the open values are equal. When you open a round, a **Lead** button
appears at the center. Hover or focus an end to preview the exact placement.
CPU turns play automatically. Drag the patio to orbit, scroll or pinch to zoom,
or choose **Table view** for an overhead camera.

| Key | Action |
| --- | --- |
| `1`-`7` | Select a tile |
| `Left` / `Right` | Step through playable tiles |
| `L` / `R` | Play the selected tile on the left / right end |
| `Enter` | Play or lead when only one end fits |
| `P` | Pass (only when nothing fits) |
| `N` | Next round, or a new game after the match |
| `Esc` | Clear the selection |
| `A` | Autoplay: CPUs play every seat, yours included |
| `Z` | Zen mode: hide everything but the table |
| `T` / `B` / `S` | Table view / La libreta / sound |
| `?` | Show all shortcuts |

**Autoplay** (`A`, the setup dialog, or `--autoplay`) hands your seat to the CPU
and deals each next round on its own, so you can watch whole matches quickly.
**Zen mode** (`Z`) keeps only the table, a score and round chip, and the Zen
toggle; the browser remembers it.
**New game** offers a single round or a target score from 1 to 1000.
After a round, **View board** reveals the completed snake and remaining
hands. **Round score** brings the result back.
**La libreta** records each finished hand, its points, and running team totals.
The notebook stays with the match across rounds and browser refreshes.
**Table sounds** enables short tile slaps and a cue for your turn. Sound starts
off; your preference is remembered by the browser. Tile motion follows the
playing seat, and respects the browser's reduced-motion preference.

The browser and the simulator run the same headless match engine
(`domino_game/game/match.py`). The terminal `play` command keeps its own turn
loop but uses the same rule functions (`domino_game/game/rules.py`), so all
three follow the Puerto Rican Doscientos rules below. Refreshing retains the
game while the server runs.
Stopping the server clears games. Each browser session gets a separate match.

Requires a browser with WebGL 2. The Python server binds only to loopback;
it is intended for local play. All browser dependencies and assets are included,
so playing requires no internet connection or Node.js tooling.

The courtyard uses handmade terracotta pavers, a limewashed garden wall,
veined banana foliage, glazed espresso cups, and a mahogany table with brass
joinery and woven green baize. Ivory dominoes have recessed pips, brass spinners,
and green backs. The hand controls share their ivory and brass finish.

Albedo, roughness, and normal maps are authored by the Blender build scripts
and packed into the assets; no texture downloads are needed. Desktop rendering
adds contact shading and 4096-pixel sun shadows. Touch devices skip the contact
shading pass and use 2048-pixel shadows to reduce GPU work.

The editable scene is `domino_game/patio/web/assets/el-patio.blend`.
Its collections separate the courtyard, all 28 master tiles, and a staged
presentation arrangement. Presentation tiles stay out of the playable exports.
To rebuild the two GLB files with Blender 4.5 or later:

```bash
blender --background --python tools/build_patio.py
```

The Blender meshes and UI faces share `assets/domino-spec.json` for tile
proportions and pip positions. The board anchors the opening tile, places
doubles across the chain, and bends using the matching half of each tile.
Tiles touch without overlapping; long snakes scale together to fit the table.

The browser renderer is Three.js 0.186.1 (MIT), vendored with its license in
`domino_game/patio/web/vendor/`. The existing terminal commands remain available.

### Audit the rules with all-CPU matches

```bash
uv run python main.py simulate --matches 1000 --seed 1
```

Plays complete matches with every seat on the CPU, with no rendering or delays
(about 7 seconds per 1,000 matches). An independent referee
(`domino_game/game/referee.py`) replays each round from its deal and checks
every turn, pass, round result, next leader, and running score. The command
reports tranque and win rates, and exits non-zero on any violation. CI runs
500 matches on every push.

### Use the engine from JavaScript or TypeScript

The repository is also `@chrisrodz/dominoes`, a zero-dependency TypeScript port
of the headless engine for browsers and Node: tiles, board, rules, the `Match`
state machine, the greedy CPU strategy, the referee, and the simulator. It is
not on npm yet; install it from GitHub, pinned to a commit:

```bash
npm install "github:chrisrodz/domino-game-cli#<commit>"
```

```ts
import { Match, audit, playOut, simulate } from '@chrisrodz/dominoes';

const match = new Match({ target: 200 });
match.legalMoves(match.turn); // [{ tile, end }]
match.autoTurn(match.turn); // CPU move or pass
const saved = match.toRecord(); // plain JSON: settings, deals, turns
Match.fromRecord(saved); // replays through the rules; corrupt saves throw RuleError
audit(playOut(match)); // [] when every turn and score is legal
simulate({ matches: 500, seed: 1 }).violations; // []
```

Installing builds `dist/` through the `prepare` script. Sources live in
`js/src/`; the Python engine stays the reference. The TypeScript suite replays
seeded matches recorded by Python (`js/test/fixtures/conformance.json`) and must
reproduce every turn, outcome, and score. After changing the rules or the CPU
strategy, regenerate the fixture and run both suites:

```bash
uv run python -m domino_game.game.conformance
npm install
npm run typecheck && npm test
```

The engine tests run TypeScript directly, so they need Node 22.18 or later.
[El Patio](https://chrisrodz.io/elpatio) runs the browser game on this package.

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

Puerto Rican partnership dominoes, *Doscientos*:

### Setup
- 4 players in 2 teams (You + Ally vs 2 Opponents), partners sit across
- All 28 tiles of a double-six set are dealt, 7 each; there is no boneyard
- Round 1: whoever holds [6|6] opens with it
- Later rounds: the winner of the previous round opens with any tile

### Gameplay
- Players take turns counter-clockwise
- Match a tile to either end of the line; if nothing fits, pass
- A round ends when a player empties their hand (*domino*) or when no one can
  play (*tranque*), which is known as soon as the closing tile lands

### Scoring
- Domino: the winner's team scores every pip still held by all four players
- Tranque: the team holding fewer pips scores every pip on the table, and its
  player with fewer pips opens next; if the teams tie, the team that closed the
  game wins and the closer opens next
- First team to reach the target score (default: 200) wins

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
├── js/                       # TypeScript engine package (@chrisrodz/dominoes)
│   ├── src/
│   └── test/                 # Includes Python conformance fixtures
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

Lint and type-check (both run in CI):

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy                      # strict; covers domino_game/, tests/, main.py
```

The Blender build scripts in `tools/` run inside Blender's untyped `bpy` API and
are linted but not type-checked.

The 3D board geometry uses Node's built-in test runner, with no npm dependencies:

```bash
node --test tests/test_patio_layout.mjs
```

Continuous Integration runs automatically on:
- Pull requests to `main`
- Pushes to `main` branch

The CI tests the package on Python 3.9, 3.10, 3.11, and 3.12.

## 📝 Commands Reference

| Command | Options | Description |
|---------|---------|-------------|
| `play` | `--target/-t`, `--quick/-q` | Start a new game |
| `patio` | `--target`, `--single-round`, `--autoplay`, `--port`, `--no-browser` | Play in the 3D browser patio |
| `simulate` | `--matches/-n`, `--target`, `--single-round`, `--seed` | Audit all-CPU matches against the rules |
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
