from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static

from ui.widgets.setup_actions import SetupActions
from ui.widgets.setup_form import SetupForm
from ui.widgets.setup_summary import SetupSummary


class SetupScreen(Screen):
    CSS = """
    SetupScreen { align: center middle; }

    #panel {
        width: auto;
        height: auto;
        max-width: 120;
        max-height: 35;
        padding: 2 4;
        border: round $border;
        background: $panel;
    }

    #title {
        content-align: center middle;
        text-style: bold;
        height: auto;
    }

    #subtitle {
        content-align: center middle;
        color: $text-muted;
        margin-bottom: 1;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("New Game", id="title"),
            Static("Configure opponent, side, and clock.", id="subtitle"),
            Horizontal(
                Vertical(SetupForm(), id="left"),
                SetupSummary(),
                id="content",
            ),
            SetupActions(),
            id="panel",
        )

    def on_mount(self) -> None:
        settings = self.query_one(SetupForm).settings()
        self.query_one(SetupSummary).settings = settings

    def on_setup_form_settings_changed(self, msg: SetupForm.SettingsChanged) -> None:
        self.query_one(SetupSummary).settings = msg.settings

    def on_setup_actions_start_pressed(self, msg: SetupActions.StartPressed) -> None:
        # TODO: start game using settings
        pass

    def on_setup_actions_back_pressed(self, msg: SetupActions.BackPressed) -> None:
        # TODO: return to previous screen
        pass
