from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from src.ui.models.setup_models import SetupSelection


class SetupSummary(Vertical):
    DEFAULT_CSS = (Path(__file__).parent / "css" / "summary.tcss").read_text()

    selection: reactive[SetupSelection | None] = reactive(None)

    # Compatibility with existing SetupScreen code that assigns .settings.
    settings: reactive[SetupSelection | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static(self._section_title("Summary"), id="summary_title", markup=False)
        yield Static("", id="summary_body", markup=False)

    def watch_selection(self, selection: SetupSelection | None) -> None:
        self._update_summary(selection)

    def watch_settings(self, settings: SetupSelection | None) -> None:
        self.selection = settings

    def _section_title(self, label: str) -> str:
        width = 76
        prefix = f"-- {label} "
        return prefix + "-" * max(0, width - len(prefix))

    def _update_summary(self, selection: SetupSelection | None) -> None:
        if selection is None:
            self.query_one("#summary_body", Static).update("")
            return

        opponent = (
            "Local (2P)"
            if selection.opponent == "local"
            else f"Bot (Level {selection.bot_level})"
        )

        side = {
            "random": "Random side",
            "white": "White",
            "black": "Black",
        }[selection.side_choice]

        if selection.time_control is None:
            time = "No Clock"
        else:
            mins = selection.time_control.initial_seconds // 60
            inc = selection.time_control.increment_seconds
            time = f"{mins}+{inc}"

        self.query_one("#summary_body", Static).update(
            f"Ready: {opponent} | {side} | {time} | Standard"
        )
