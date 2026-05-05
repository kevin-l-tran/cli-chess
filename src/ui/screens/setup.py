from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
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
        config = selection.to_session_config()  # noqa: F841

        # TODO: start game using config.
        #
        # Local:
        # client = InProcessGameClient.local(
        #     time_control=config.time_control,
        # )
        #
        # Bot:
        # bot = StockfishBotAdapter(level=selection.bot_level)
        # client = InProcessGameClient.bot(
        #     human_side=config.player_side,
        #     bot=bot,
        #     time_control=config.time_control,
        # )
        pass

    def on_setup_actions_back_pressed(self, msg: SetupActions.BackPressed) -> None:
        # TODO: return to previous screen
        self.dismiss()