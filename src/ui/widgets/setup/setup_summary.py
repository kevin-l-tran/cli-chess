from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ui.models import SetupSelection


class SetupSummary(Widget):
    DEFAULT_CSS = """
    SetupSummary {
        width: 34;
        height: auto;
        padding: 1 2;
        margin: 0 4;
        border: round $border;
        background: $boost;
    }

    #summary_title {
        text-style: bold;
        margin-bottom: 1;
        height: auto;
    }

    #summary_body {
        height: auto;
    }
    """

    selection: reactive[SetupSelection | None] = reactive(None)

    # Compatibility with existing SetupScreen code that assigns .settings.
    settings: reactive[SetupSelection | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static("Summary", id="summary_title")
        yield Static("", id="summary_body")

    def watch_selection(self, selection: SetupSelection | None) -> None:
        self._update_summary(selection)

    def watch_settings(self, settings: SetupSelection | None) -> None:
        self.selection = settings

    def _update_summary(self, selection: SetupSelection | None) -> None:
        if selection is None:
            self.query_one("#summary_body", Static).update("")
            return

        opp = (
            "Local (2P)"
            if selection.opponent == "local"
            else f"Bot (Level {selection.bot_level})"
        )

        side = {
            "random": "Random",
            "white": "White",
            "black": "Black",
        }[selection.side_choice]

        if selection.time_control is None:
            time = "No Clock"
        else:
            mins = selection.time_control.initial_seconds // 60
            inc = selection.time_control.increment_seconds
            time = f"{mins}+{inc}"

        text = "\n".join(
            [
                f"Opponent: {opp}",
                f"Side:     {side}",
                f"Time:     {time}",
                "Start:    Standard",
            ]
        )
        self.query_one("#summary_body", Static).update(text)