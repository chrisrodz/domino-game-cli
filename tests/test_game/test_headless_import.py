"""The engine and the patio session must import without terminal dependencies.

El Patio (chrisrodz.io/elpatio) runs them in the browser through Pyodide, which
ships neither rich nor typer.
"""

import subprocess
import sys

BLOCK_TERMINAL_DEPS = """
import sys

class Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in ("rich", "typer"):
            raise ImportError(f"{name} is blocked to simulate a browser runtime")

sys.meta_path.insert(0, Block())
import random
from domino_game.game.simulate import simulate
from domino_game.patio.session import PatioSession

session = PatioSession(rng=random.Random(1))
while session.phase == "playing":
    if session.match.turn == 0:
        moves = session.match.legal_moves(0)
        if moves:
            tile, end = moves[0]
            session.play(f"{min(tile.left, tile.right)}-{max(tile.left, tile.right)}", end)
        else:
            session.pass_turn()
    else:
        session.step_cpu()
assert session.snapshot()["result"] is not None
assert simulate(matches=5, seed=1).violations == []
"""


def test_engine_and_session_run_without_rich_or_typer():
    result = subprocess.run([sys.executable, "-c", BLOCK_TERMINAL_DEPS], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
