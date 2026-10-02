"""Non-blocking turns around the CLI's game, models, AI, and scoring."""

from typing import Any

from domino_game.game.engine import Game
from domino_game.game.scoring import calculate_round_score
from domino_game.models import Board, Domino


class MoveError(ValueError):
    """A requested action is invalid for this game state."""


def tile_data(tile: Domino) -> dict[str, Any]:
    return {"id": f"{min(tile.left, tile.right)}-{max(tile.left, tile.right)}", "left": tile.left, "right": tile.right}


class PatioSession:
    """Keep terminal I/O outside browser turns; retain engine behavior."""

    def __init__(self, *, target_score: int = 200, game_mode: str = "target_score"):
        if type(target_score) is not int or not 1 <= target_score <= 1000:
            raise MoveError("Target score must be an integer from 1 to 1000.")
        if game_mode not in ("target_score", "single_round"):
            raise MoveError(f"Unknown game mode: {game_mode!r}.")
        self.game = Game(game_mode=game_mode, target_score=target_score)
        self.game.setup_players()
        self.phase = "playing"
        self.result = None
        self.history: list[dict[str, Any]] = []
        self.revision = 0
        self._deal()

    def _deal(self) -> None:
        game = self.game
        game.board = Board()
        game.last_played_team = None
        game.consecutive_passes = 0
        game.deal_dominoes()
        for player in game.players:
            player.passed_last_turn = False
        game.current_player_idx = game.find_starting_player()
        self.phase = "playing"
        self.result = None
        self.history = []
        self.opening = None
        self.revision += 1

    def _require_turn(self, *, human: bool) -> None:
        if self.phase != "playing":
            raise MoveError("This round has ended. Start the next round or a new game.")
        is_human_turn = self.game.current_player_idx == 0
        if is_human_turn != human:
            raise MoveError("Wait for your turn." if human else "The current turn belongs to you.")

    def play(self, tile_id: str, position: str) -> None:
        self._require_turn(human=True)
        player = self.game.players[0]
        valid = player.get_valid_moves(self.game.board)
        chosen = next((move for move in valid if tile_data(move[0])["id"] == tile_id and move[1] == position), None)
        if chosen is None:
            raise MoveError(f"Tile {tile_id!r} cannot be played on {position!r}. Choose a highlighted tile and end.")
        self._take_turn(chosen)

    def pass_turn(self) -> None:
        self._require_turn(human=True)
        if self.game.players[0].get_valid_moves(self.game.board):
            raise MoveError("You have a legal move. Play a highlighted tile before passing.")
        self._take_turn(None)

    def step_cpu(self) -> None:
        self._require_turn(human=False)
        game = self.game
        player = game.players[game.current_player_idx]
        moves = player.get_valid_moves(game.board)
        self._take_turn(game.cpu_strategy.get_best_move(player, moves, game.board))

    def _take_turn(self, chosen) -> None:
        game = self.game
        player = game.players[game.current_player_idx]
        event: dict[str, Any] = {"player": game.current_player_idx, "name": player.name, "type": "pass"}
        if chosen:
            tile, position = chosen
            if not game.board.play_domino(tile, on_left=position == "left"):
                raise MoveError(f"Board rejected tile {tile} on {position}; no turn was consumed.")
            player.remove_domino(tile)
            if position == "first":
                self.opening = tile_data(tile)["id"]
            player.passed_last_turn = False
            game.consecutive_passes = 0
            game.last_played_team = player.team
            event.update(type="play", tile=tile_data(tile), position=position)
        else:
            player.passed_last_turn = True
            game.consecutive_passes += 1
        self.history.append(event)
        self.revision += 1
        if player.is_out() or game.consecutive_passes >= 4:
            team, points = calculate_round_score(game.players, game.board, game.last_played_team)
            game.team_scores[team] += points
            match_over = game.game_mode == "single_round" or max(game.team_scores) >= game.target_score
            self.phase = "match_over" if match_over else "round_over"
            self.result = {"team": team, "points": points, "blocked": game.consecutive_passes >= 4}
        else:
            game.current_player_idx = (game.current_player_idx + 1) % 4

    def next_round(self) -> None:
        if self.phase != "round_over":
            raise MoveError("A next round is available only after an unfinished match's round ends.")
        self.game.round_number += 1
        self._deal()

    def snapshot(self) -> dict[str, Any]:
        game = self.game
        moves = game.players[0].get_valid_moves(game.board) if self.phase == "playing" and game.current_player_idx == 0 else []
        return {
            "revision": self.revision,
            "phase": self.phase,
            "round": game.round_number,
            "target": game.target_score,
            "mode": game.game_mode,
            "turn": game.current_player_idx,
            "scores": game.team_scores.copy(),
            "board": [tile_data(tile) for tile in game.board.dominoes],
            "opening": self.opening,
            "ends": {"left": game.board.left_value(), "right": game.board.right_value()},
            "players": [
                {
                    "name": player.name,
                    "team": player.team,
                    "count": len(player.hand),
                    "passed": player.passed_last_turn,
                    "hand": [tile_data(tile) for tile in player.hand] if index == 0 or self.phase != "playing" else None,
                    "value": player.hand_value() if index == 0 or self.phase != "playing" else None,
                }
                for index, player in enumerate(game.players)
            ],
            "moves": [{"tile": tile_data(tile)["id"], "position": position} for tile, position in moves],
            "history": self.history[-12:],
            "result": self.result,
        }
