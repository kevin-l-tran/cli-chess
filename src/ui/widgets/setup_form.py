from typing import cast

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Input,
    RadioButton,
    RadioSet,
    Static,
    Select,
)
from textual_slider import Slider

from application.session_types import OpponentType, TimeControl
from ui.models import SetupSelection, SideChoice


class BotLevelSlider(Horizontal):
    DEFAULT_CSS = """
    #bot-level-slider {
        width: 32;
        height: 3;
    }

    #bot-level-display {
        margin-left: 1;
        content-align: left middle;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Slider(min=1, max=10, value=4, id="bot-level-slider")
        yield Static("", id="bot-level-display")

    def on_mount(self) -> None:
        self._sync_display()

    def on_slider_changed(self, _: Slider.Changed) -> None:
        self._sync_display()

    def _sync_display(self) -> None:
        bot_level = int(self.query_one("#bot-level-slider", Slider).value)
        self.query_one("#bot-level-display", Static).update(
            self._format_bot_level(bot_level)
        )

    def _format_bot_level(self, v: int) -> str:
        if v <= 2:
            tag = "easy"
        elif v <= 5:
            tag = "medium"
        elif v <= 8:
            tag = "hard"
        else:
            tag = "expert"
        return f"{v} ({tag})"


class CustomTimeInput(Widget):
    DEFAULT_CSS = """
    CustomTimeInput {
        layout: vertical;
        height: auto;
    }

    CustomTimeInput Horizontal {
        height: auto;
    }

    CustomTimeInput #mins {
        width: 10;
    }

    CustomTimeInput #plus {
        width: 3;
        height: 100%;
        content-align: center middle;
    }

    CustomTimeInput #inc {
        width: 10;
    }

    CustomTimeInput #error {
        height: auto;
        color: $error;
    }
    """

    value: reactive[tuple[int, int] | None] = reactive(None)

    class Changed(Message):
        bubble = True

        def __init__(self, value: tuple[int, int] | None) -> None:
            super().__init__()
            self.value = value

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Input(placeholder="MM", id="mins", restrict=r"[0-9]*"),
            Static("+", id="plus"),
            Input(placeholder="SS", id="inc", restrict=r"[0-9]*"),
        )
        yield Static("", id="error")

    def on_mount(self) -> None:
        self.query_one("#mins", Input).value = "5"
        self.query_one("#inc", Input).value = "0"
        self._recompute()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id in {"mins", "inc"}:
            self._recompute()

    def _recompute(self) -> None:
        mins_s = self.query_one("#mins", Input).value.strip()
        inc_s = self.query_one("#inc", Input).value.strip()
        err = self.query_one("#error", Static)

        if not mins_s or not inc_s:
            self.value = None
            err.update("Enter minutes and increment.")
            self.post_message(self.Changed(self.value))
            return

        mins = int(mins_s)
        inc = int(inc_s)

        if not (0 < mins <= 59):
            self.value = None
            err.update("Start time must be 1-59 minutes.")
        elif not (0 <= inc <= 59):
            self.value = None
            err.update("Increment must be 0-59 seconds.")
        else:
            self.value = (mins, inc)
            err.update("")

        self.post_message(self.Changed(self.value))


class SetupForm(Widget):
    DEFAULT_CSS = """
    SetupForm {
        layout: grid;
        grid-size: 2;
        grid-columns: 16 1fr;
        grid-gutter: 1 3;
        height: auto;
    }

    SetupForm > .label {
        content-align: right middle;
        height: 100%;
        color: $text-muted;
    }

    #opponent-row {
        layout: horizontal;
        height: auto;
    }

    #bot-level-row {
        layout: horizontal;
        height: auto;
    }
    """

    class SettingsChanged(Message):
        bubble = True

        def __init__(self, selection: SetupSelection) -> None:
            super().__init__()
            self.selection = selection

            # Compatibility with existing SetupScreen code that expects msg.settings.
            self.settings = selection

    def compose(self) -> ComposeResult:
        yield Static("Opponent:", classes="label")
        yield RadioSet(
            RadioButton("Local (2P)", id="local", value=True),
            RadioButton("Bot", id="bot"),
            id="opponent-row",
        )

        yield Static("Bot level:", classes="label", id="bot-level-label")
        yield BotLevelSlider(id="bot-level-row")

        yield Static("Side:", classes="label", id="side-label")
        yield Select(
            [("Random", "random"), ("White", "white"), ("Black", "black")],
            allow_blank=False,
            value="random",
            id="side-select",
        )

        yield Static("Time:", classes="label")
        yield Select(
            [
                ("No clock", "none"),
                ("3+2", "3+2"),
                ("5+0", "5+0"),
                ("10+0", "10+0"),
                ("15+10", "15+10"),
                ("Custom", "custom"),
            ],
            allow_blank=False,
            value="5+0",
            id="time-select",
        )

        yield Static("Custom time:", classes="label", id="custom-time-label")
        yield CustomTimeInput(id="custom-time-input")

    def on_mount(self) -> None:
        self._sync_rows()
        self._emit()

    def settings(self) -> SetupSelection:
        opponent = self._selected_opponent()
        side_choice = self._selected_side_choice()
        time_control = self._selected_time_control()

        bot_level = None
        if opponent == "bot":
            bot_level = int(self.query_one("#bot-level-slider", Slider).value)

        return SetupSelection(
            opponent=opponent,
            side_choice=side_choice,
            time_control=time_control,
            bot_level=bot_level,
        )

    def _selected_opponent(self) -> OpponentType:
        opponent_set = self.query_one("#opponent-row", RadioSet)
        opponent_id = (
            opponent_set.pressed_button.id if opponent_set.pressed_button else "local"
        )

        return cast(OpponentType, "bot" if opponent_id == "bot" else "local")

    def _selected_side_choice(self) -> SideChoice:
        raw = str(self.query_one("#side-select", Select).value) or "random"
        return cast(SideChoice, raw)

    def _selected_time_control(self) -> TimeControl | None:
        time = str(self.query_one("#time-select", Select).value) or "none"

        if time == "none":
            return None

        if time == "custom":
            custom_time = self.query_one("#custom-time-input", CustomTimeInput).value
            if custom_time is None:
                return None

            mins, inc = custom_time
            return TimeControl(
                initial_seconds=mins * 60,
                increment_seconds=inc,
            )

        mins_s, inc_s = time.split("+")
        return TimeControl(
            initial_seconds=int(mins_s) * 60,
            increment_seconds=int(inc_s),
        )

    def _sync_rows(self) -> None:
        selection = self.settings()

        bot_selected = selection.opponent == "bot"
        self.query_one("#bot-level-label", Static).display = bot_selected
        self.query_one("#bot-level-row", Horizontal).display = bot_selected
        self.query_one("#side-label", Static).update(
            "Side:" if bot_selected else "Player 1 Side:"
        )

        custom_time = self.query_one("#time-select", Select).value == "custom"
        self.query_one("#custom-time-label", Static).display = custom_time
        self.query_one("#custom-time-input", CustomTimeInput).display = custom_time

    def _emit(self) -> None:
        self.post_message(self.SettingsChanged(self.settings()))

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "opponent-row":
            self._sync_rows()
            self._emit()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in {"side-select", "time-select"}:
            self._sync_rows()
            self._emit()

    def on_slider_changed(self, event: Slider.Changed) -> None:
        if event.slider.id == "bot-level-slider":
            self._emit()

    def on_custom_time_input_changed(self, _: CustomTimeInput.Changed) -> None:
        self._emit()