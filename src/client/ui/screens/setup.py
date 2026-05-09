from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Static

from src.application.authoritative_helpers.authoritative_session_types import (
    TimeControl,
)
from src.application.local_draft_controller import LocalDraftController
from src.application.local_game_client import LocalGameClient
from src.client.ui.models.setup_models import SetupTimeControl

from ..widgets.setup.actions import SetupActions
from ..widgets.setup.form import SetupForm
from ..widgets.setup.summary import SetupSummary
from .game.game import GameScreen


class SetupScreen(Screen):
    DEFAULT_CSS = (Path(__file__).parent / "css" / "setup.tcss").read_text()

    BINDINGS = [
        Binding("ctrl+g", "back", "Back", show=True),
        Binding("escape", "back", "Back", show=False),
        Binding("ctrl+s", "start", "Start", show=True),
        Binding("ctrl+o", "cycle_opponent", "Opponent", show=True),
        Binding("ctrl+l", "increment_level", "Level", show=True),
        Binding("ctrl+t", "cycle_time", "Time", show=True),
    ]

    def compose(self) -> ComposeResult:
        panel = Vertical(id="panel")
        panel.border_title = "New Game"

        with panel:
            yield Static(
                "Configure opponent, side, and clock.",
                id="subtitle",
                markup=False,
            )

            with VerticalScroll(id="setup-scroll"):
                with Vertical(id="setup-stack"):
                    yield SetupForm()
                    yield SetupSummary()

            yield SetupActions()

        yield Footer()

    def on_mount(self) -> None:
        selection = self.query_one(SetupForm).settings()
        self.query_one(SetupSummary).selection = selection

    def on_setup_form_settings_changed(self, msg: SetupForm.SettingsChanged) -> None:
        self.query_one(SetupSummary).selection = msg.selection

    def on_setup_actions_start_pressed(self, msg: SetupActions.StartPressed) -> None:
        self.action_start()

    def on_setup_actions_back_pressed(self, msg: SetupActions.BackPressed) -> None:
        self.action_back()

    def action_start(self) -> None:
        form = self.query_one(SetupForm)
        if not form.is_valid:
            self.app.notify("Fix the setup form before starting.", severity="warning")
            return

        selection = form.settings().with_resolved_player_side()

        client = LocalGameClient.local(
            time_control=_time_control(selection.time_control),
        )
        draft = LocalDraftController()

        self.app.push_screen(
            GameScreen(
                client=client,
                draft=draft,
                selection=selection,
            )
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_cycle_opponent(self) -> None:
        self.query_one(SetupForm).cycle_opponent()

    def action_increment_level(self) -> None:
        self.query_one(SetupForm).increment_bot_level()

    def action_cycle_time(self) -> None:
        self.query_one(SetupForm).cycle_time()


def _time_control(
    time_control: SetupTimeControl | None,
) -> TimeControl | None:
    if time_control is None:
        return None

    return TimeControl(
        initial_seconds=time_control.initial_seconds,
        increment_seconds=time_control.increment_seconds,
    )
