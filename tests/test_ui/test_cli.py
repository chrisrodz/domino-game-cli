"""Difficulty configuration through flags and interactive setup."""

from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from domino_game.cli import app
from domino_game.models.player import AIDifficulty
from domino_game.ui.setup_menu import SetupMenu


def test_independent_flags_select_correct_seats_without_menu():
    with patch("domino_game.cli.Game") as game, patch("domino_game.cli.SetupMenu") as menu:
        result = CliRunner().invoke(app, ["play", "--ally", "hard", "--opponent-1", "medium", "--opponent-2", "simple"])
    assert result.exit_code == 0, result.exception
    menu.assert_not_called()
    settings = game.call_args.kwargs["cpu_settings"]
    assert settings.for_seat(1) == AIDifficulty.MEDIUM
    assert settings.for_seat(2) == AIDifficulty.HARD
    assert settings.for_seat(3) == AIDifficulty.SIMPLE


def test_invalid_difficulty_is_a_cli_error():
    result = CliRunner().invoke(app, ["play", "--ally", "expert"])
    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_missing_key_is_actionable_and_does_not_start_round(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with patch("domino_game.game.engine.Game.play_round") as round:
        result = CliRunner().invoke(app, ["play", "--single-round", "--ally", "hard"])
    assert result.exit_code == 1
    assert "TYPESAFE_API_KEY" in result.output
    round.assert_not_called()


@pytest.mark.parametrize(
    "choices, expected",
    [
        (["", "", ""], [AIDifficulty.SIMPLE] * 3),
        (["expert", "hard", "medium", "simple"], [AIDifficulty.HARD, AIDifficulty.MEDIUM, AIDifficulty.SIMPLE]),
    ],
)
def test_menu_sets_each_cpu_and_reprompts_invalid_choice(choices, expected):
    output = StringIO()
    console = Console(file=output, width=120)
    with patch.object(console, "input", side_effect=["2", *choices, ""]):
        config = SetupMenu(console).run()
    assert config.game_mode == "single_round"
    assert [config.cpu_settings.ally, config.cpu_settings.opponent_1, config.cpu_settings.opponent_2] == expected
    assert "Ally:" in output.getvalue()


def test_offline_default_still_plays_complete_round(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr("domino_game.game.engine.time.sleep", lambda _: None)
    result = CliRunner().invoke(app, ["play", "--single-round", "--skip-setup"], input="y\n1\n" * 100)
    assert result.exit_code == 0, result.exception
    assert "ROUND COMPLETE" in result.output
