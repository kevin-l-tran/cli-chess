from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from ..widgets.setup.setup_actions import SetupActions
from ..widgets.setup.setup_form import SetupForm
from ..widgets.setup.setup_summary import SetupSummary
from .game import GameScreen


class SetupScreen(Screen):
    DEFAULT_CSS = (Path(__file__).parent / "css" / "setup.tcss").read_text()

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("New Game", id="title"),
            Static("Configure opponent, side, and clock.", id="subtitle"),
            Horizontal(
                VerticalScroll(SetupForm(), id="left"),
                SetupSummary(),
                id="content",
            ),
            SetupActions(),
            id="panel",
        )

    def on_mount(self) -> None:
        selection = self.query_one(SetupForm).settings()
        self.query_one(SetupSummary).selection = selection

    def on_setup_form_settings_changed(self, msg: SetupForm.SettingsChanged) -> None:
        self.query_one(SetupSummary).selection = msg.selection

    def on_setup_actions_start_pressed(self, msg: SetupActions.StartPressed) -> None:
        selection = self.query_one(SetupForm).settings()
        self.app.push_screen(GameScreen(selection))

    def on_setup_actions_back_pressed(self, msg: SetupActions.BackPressed) -> None:
        self.app.pop_screen()
