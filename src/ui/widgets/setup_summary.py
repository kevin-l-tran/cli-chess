from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ui.models import GameSettings


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

    settings: reactive[GameSettings | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static("Summary", id="summary_title")
        yield Static("", id="summary_body")

    def watch_settings(self, settings: GameSettings | None) -> None:
        if settings is None:
            self.query_one("#summary_body", Static).update("")
            return

        opp = (
            "Local (2P)"
            if settings.opponent == "local"
            else f"Bot (Level {settings.bot_level})"
        )
        side = {"random": "Random", "white": "White", "black": "Black"}.get(
            settings.side, settings.side
        )
        time = (
            "No Clock"
            if settings.time == (0, 0)
            else f"{settings.time[0]}+{settings.time[1]}"
        )

        text = "\n".join(
            [
                f"Opponent: {opp}",
                f"Side:     {side}",
                f"Time:     {time}",
                "Start:    Standard",
            ]
        )
        self.query_one("#summary_body", Static).update(text)
