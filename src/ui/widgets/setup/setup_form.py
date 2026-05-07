from __future__ import annotations

from typing import cast

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Click, Key
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from src.application.session_types import OpponentType, TimeControl
from src.ui.models.setup_models import SetupSelection, SideChoice


class TerminalOption(Static, can_focus=True):
    """Compact bracketed option with mouse, Tab, Enter, and Space support."""

    class Pressed(Message):
        bubble = True

        def __init__(self, control_id: str) -> None:
            super().__init__()
            self.control_id = control_id

    def __init__(
        self,
        label: str,
        *,
        control_id: str,
        selected: bool = False,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.control_id = control_id
        self._label = label
        super().__init__(
            self._render_label(),
            id=id,
            classes=self._set_selected_class(classes, selected),
            markup=False,
        )

    def update_state(self, label: str, *, selected: bool) -> None:
        self._label = label
        self.update(self._render_label())
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")

    def on_click(self, event: Click) -> None:
        event.stop()
        self.post_message(self.Pressed(self.control_id))

    def on_key(self, event: Key) -> None:
        if event.key in {"enter", "space"}:
            event.stop()
            self.post_message(self.Pressed(self.control_id))

    def _render_label(self) -> str:
        return f"[ {self._label} ]"

    def _set_selected_class(self, classes: str | None, selected: bool) -> str:
        parts = ["terminal-option"]
        if classes:
            parts.append(classes)
        if selected:
            parts.append("selected")
        return " ".join(parts)


class TerminalStep(Static, can_focus=True):
    """Small one-line +/- control for bot level."""

    class Pressed(Message):
        bubble = True

        def __init__(self, control_id: str) -> None:
            super().__init__()
            self.control_id = control_id

    def __init__(self, label: str, *, control_id: str, id: str | None = None) -> None:
        self.control_id = control_id
        super().__init__(label, id=id, classes="terminal-step", markup=False)

    def on_click(self, event: Click) -> None:
        event.stop()
        self.post_message(self.Pressed(self.control_id))

    def on_key(self, event: Key) -> None:
        if event.key in {"enter", "space"}:
            event.stop()
            self.post_message(self.Pressed(self.control_id))


class TerminalNumberField(Static, can_focus=True):
    """Small bracketed numeric input for custom time values."""

    DEFAULT_CSS = """
    TerminalNumberField {
        width: 6;
        height: 1;
        padding: 0;
        margin: 0 1 0 0;
        background: transparent;
        color: $foreground;
        content-align: center middle;
    }

    TerminalNumberField:focus {
        background: $foreground;
        color: $background;
        text-style: bold;
    }
    """

    class Changed(Message):
        bubble = True

    def __init__(self, value: str, *, id: str | None = None) -> None:
        super().__init__("", id=id, classes="terminal-number-field", markup=False)
        self._value = value
        self._fresh_focus = False

    @property
    def text_value(self) -> str:
        return self._value

    def on_mount(self) -> None:
        self._sync()

    def on_focus(self) -> None:
        self._fresh_focus = True

    def on_click(self, event: Click) -> None:
        event.stop()
        self.focus()

    def on_key(self, event: Key) -> None:
        if event.character and event.character.isdigit():
            event.stop()
            if self._fresh_focus:
                self._value = event.character
            elif len(self._value) >= 2:
                self._value = event.character
            else:
                self._value += event.character
            self._fresh_focus = False
            self._sync_and_emit()
            return

        if event.key in {"backspace", "ctrl+h"}:
            event.stop()
            self._fresh_focus = False
            self._value = self._value[:-1]
            self._sync_and_emit()
            return

        if event.key in {"delete", "ctrl+x"}:
            event.stop()
            self._fresh_focus = False
            self._value = ""
            self._sync_and_emit()
            return

        if event.key == "up":
            event.stop()
            self._fresh_focus = False
            self._nudge(1)
            return

        if event.key == "down":
            event.stop()
            self._fresh_focus = False
            self._nudge(-1)
            return

    def _nudge(self, delta: int) -> None:
        current = int(self._value or "0")
        self._value = str(max(0, min(59, current + delta)))
        self._sync_and_emit()

    def _sync_and_emit(self) -> None:
        self._sync()
        self.post_message(self.Changed())

    def _sync(self) -> None:
        display = self._value if self._value else "--"
        self.update(f"[ {display:>2} ]")


class CustomTimeInput(Vertical):
    DEFAULT_CSS = """
    CustomTimeInput {
        height: auto;
        margin-top: 1;
    }

    CustomTimeInput .custom-time-row {
        height: 1;
        width: auto;
    }

    CustomTimeInput .field-label {
        margin-right: 2;
    }

    CustomTimeInput #plus {
        width: 3;
        height: 1;
        content-align: center middle;
        color: $text-muted;
    }

    CustomTimeInput #error {
        height: auto;
        margin-top: 1;
        margin-left: 18;
        color: $error;
    }
    """

    value: reactive[tuple[int, int] | None] = reactive(None)

    class Changed(Message):
        bubble = True

        def __init__(self, value: tuple[int, int] | None) -> None:
            super().__init__()
            self.value = value

    def _section_title(self, label: str) -> str:
        width = 76
        prefix = f"-- {label} "
        return prefix + "-" * max(0, width - len(prefix))

    def compose(self) -> ComposeResult:
        with Horizontal(classes="custom-time-row"):
            yield Static("Custom:", classes="field-label", markup=False)
            yield TerminalNumberField("5", id="mins")
            yield Static("+", id="plus", markup=False)
            yield TerminalNumberField("0", id="inc")
        yield Static("", id="error", markup=False)

    def on_mount(self) -> None:
        self._recompute()

    def on_terminal_number_field_changed(self, _: TerminalNumberField.Changed) -> None:
        self._recompute()

    def _recompute(self) -> None:
        mins_s = self.query_one("#mins", TerminalNumberField).text_value.strip()
        inc_s = self.query_one("#inc", TerminalNumberField).text_value.strip()
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


class SetupForm(Vertical):
    DEFAULT_CSS = """
    SetupForm {
        width: 1fr;
        min-width: 68;
        height: auto;
    }

    SetupForm .setup-section {
        width: 1fr;
        height: auto;
        margin-bottom: 1;
        background: $background;
    }

    SetupForm .section-title {
        height: 1;
        width: 1fr;
        margin-bottom: 0;
        color: $accent;
        text-style: bold;
        overflow: hidden;
    }

    SetupForm .field-row,
    SetupForm .option-row,
    SetupForm .level-row,
    SetupForm .custom-time-row {
        height: auto;
        width: auto;
    }

    SetupForm .field-row {
        margin-bottom: 1;
    }

    SetupForm .field-label {
        width: 16;
        height: 1;
        content-align: right middle;
        color: $text-muted;
        margin-right: 1;
    }

    TerminalOption,
    TerminalStep {
        height: 1;
        width: auto;
        min-width: 1;
        padding: 0 1;
        margin: 0 1 0 0;
        background: transparent;
        color: $foreground;
    }

    TerminalOption.selected {
        background: $accent;
        color: $background;
        text-style: bold;
    }

    TerminalOption:focus,
    TerminalStep:focus,
    TerminalOption.selected:focus {
        background: $foreground;
        color: $background;
        text-style: bold;
    }

    TerminalStep {
        color: $foreground;
        text-style: bold;
    }

    SetupForm #bot-level-display {
        width: 16;
        height: 1;
        content-align: center middle;
        text-style: bold;
    }

    SetupForm #bot-level-track {
        height: 1;
        margin-left: 17;
        color: $text-muted;
    }
    """

    _SIDES: tuple[tuple[SideChoice, str], ...] = (
        ("random", "Random"),
        ("white", "White"),
        ("black", "Black"),
    )
    _TIMES: tuple[tuple[str, str], ...] = (
        ("none", "No clock"),
        ("3+2", "3+2"),
        ("5+0", "5+0"),
        ("10+0", "10+0"),
        ("15+10", "15+10"),
        ("custom", "Custom"),
    )

    class SettingsChanged(Message):
        bubble = True

        def __init__(self, selection: SetupSelection) -> None:
            super().__init__()
            self.selection = selection
            # Compatibility with existing SetupScreen code that expects msg.settings.
            self.settings = selection

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._opponent: OpponentType = "local"
        self._side_choice: SideChoice = "random"
        self._time_choice = "5+0"
        self._bot_level = 4

    def _section_title(self, label: str) -> str:
        width = 76
        prefix = f"-- {label} "
        return prefix + "-" * max(0, width - len(prefix))

    def compose(self) -> ComposeResult:
        with Vertical(classes="setup-section", id="opponent-section"):
            yield Static(
                self._section_title("Opponent"), classes="section-title", markup=False
            )
            with Horizontal(classes="option-row", id="opponent-row"):
                yield Static("Opponent:", classes="field-label", markup=False)
                yield TerminalOption(
                    "Local (2P)",
                    control_id="local",
                    selected=True,
                    id="local",
                )
                yield TerminalOption("Bot", control_id="bot", id="bot")

        with Vertical(classes="setup-section", id="bot-section"):
            yield Static(
                self._section_title("Bot"),
                classes="section-title",
                id="bot-section-title",
                markup=False,
            )
            with Horizontal(classes="level-row", id="bot-level-row"):
                yield Static(
                    "Level:", classes="field-label", id="bot-level-label", markup=False
                )
                yield TerminalStep("[ - ]", control_id="level-minus", id="level-minus")
                yield Static("", id="bot-level-display", markup=False)
                yield TerminalStep("[ + ]", control_id="level-plus", id="level-plus")
            yield Static("", id="bot-level-track", markup=True)

        with Vertical(classes="setup-section", id="game-section"):
            yield Static(
                self._section_title("Game"), classes="section-title", markup=False
            )
            with Horizontal(classes="field-row", id="side-row"):
                yield Static(
                    "Side:", classes="field-label", id="side-label", markup=False
                )
                for value, label in self._SIDES:
                    yield TerminalOption(
                        label,
                        control_id=f"side-{value}",
                        selected=self._side_choice == value,
                        id=f"side-{value}",
                    )

            with Horizontal(classes="field-row", id="time-row-main"):
                yield Static("Time:", classes="field-label", markup=False)
                for value, label in self._TIMES[:4]:
                    yield TerminalOption(
                        label,
                        control_id=self._time_button_id(value),
                        selected=self._time_choice == value,
                        id=self._time_button_id(value),
                    )

            with Horizontal(classes="field-row", id="time-row-extra"):
                yield Static("", classes="field-label", markup=False)
                for value, label in self._TIMES[4:]:
                    yield TerminalOption(
                        label,
                        control_id=self._time_button_id(value),
                        selected=self._time_choice == value,
                        id=self._time_button_id(value),
                    )

            yield CustomTimeInput(id="custom-time-input")

    def on_mount(self) -> None:
        self._sync_rows()
        self._sync_controls()
        self._emit()

    def settings(self) -> SetupSelection:
        bot_level = self._bot_level if self._opponent == "bot" else None
        return SetupSelection(
            opponent=self._opponent,
            side_choice=self._side_choice,
            time_control=self._selected_time_control(),
            bot_level=bot_level,
        )

    def cycle_opponent(self) -> None:
        self._opponent = "bot" if self._opponent == "local" else "local"
        self._sync_rows()
        self._sync_controls()
        self._emit()

    def increment_bot_level(self) -> None:
        self._bot_level = min(10, self._bot_level + 1)
        self._sync_controls()
        self._emit()

    def cycle_time(self) -> None:
        values = [value for value, _label in self._TIMES]
        index = values.index(self._time_choice)
        self._time_choice = values[(index + 1) % len(values)]
        self._sync_rows()
        self._sync_controls()
        self._emit()

    def on_terminal_option_pressed(self, event: TerminalOption.Pressed) -> None:
        self._handle_control(event.control_id)

    def on_terminal_step_pressed(self, event: TerminalStep.Pressed) -> None:
        self._handle_control(event.control_id)

    def on_custom_time_input_changed(self, _: CustomTimeInput.Changed) -> None:
        self._emit()

    def _handle_control(self, control_id: str) -> None:
        if control_id == "local":
            self._opponent = "local"
        elif control_id == "bot":
            self._opponent = "bot"
        elif control_id == "level-minus":
            self._bot_level = max(1, self._bot_level - 1)
        elif control_id == "level-plus":
            self._bot_level = min(10, self._bot_level + 1)
        elif control_id.startswith("side-"):
            self._side_choice = cast(SideChoice, control_id.removeprefix("side-"))
        elif control_id.startswith("time-"):
            self._time_choice = self._time_value_from_button_id(control_id)
        else:
            return

        self._sync_rows()
        self._sync_controls()
        self._emit()

    def _selected_time_control(self) -> TimeControl | None:
        if self._time_choice == "none":
            return None

        if self._time_choice == "custom":
            custom_time = self.query_one("#custom-time-input", CustomTimeInput).value
            if custom_time is None:
                return None

            mins, inc = custom_time
            return TimeControl(
                initial_seconds=mins * 60,
                increment_seconds=inc,
            )

        mins_s, inc_s = self._time_choice.split("+")
        return TimeControl(
            initial_seconds=int(mins_s) * 60,
            increment_seconds=int(inc_s),
        )

    def _sync_rows(self) -> None:
        bot_selected = self._opponent == "bot"
        self.query_one("#bot-section", Vertical).display = bot_selected
        self.query_one("#side-label", Static).update(
            "Side:" if bot_selected else "Player 1 Side:"
        )
        self.query_one("#custom-time-input", CustomTimeInput).display = (
            self._time_choice == "custom"
        )

    def _sync_controls(self) -> None:
        self._set_option("#local", "Local (2P)", self._opponent == "local")
        self._set_option("#bot", "Bot", self._opponent == "bot")

        for value, label in self._SIDES:
            self._set_option(f"#side-{value}", label, self._side_choice == value)

        for value, label in self._TIMES:
            self._set_option(
                f"#{self._time_button_id(value)}",
                label,
                self._time_choice == value,
            )

        self.query_one("#bot-level-display", Static).update(
            f"{self._bot_level} ({self._format_bot_level(self._bot_level)})"
        )
        self.query_one("#bot-level-track", Static).update(self._format_level_track())

    def _set_option(self, selector: str, label: str, selected: bool) -> None:
        option = self.query_one(selector, TerminalOption)
        option.update_state(label, selected=selected)

    def _emit(self) -> None:
        self.post_message(self.SettingsChanged(self.settings()))

    def _format_bot_level(self, value: int) -> str:
        if value <= 2:
            return "easy"
        if value <= 5:
            return "medium"
        if value <= 8:
            return "hard"
        return "expert"

    def _format_level_track(self) -> str:
        cells: list[str] = []
        for value in range(1, 11):
            if value == self._bot_level:
                cells.append(f"[bold][{value}][/bold]")
            else:
                cells.append(f" {value} ")
        return " ".join(cells)

    def _time_button_id(self, value: str) -> str:
        return f"time-{value.replace('+', '-')}"

    def _time_value_from_button_id(self, button_id: str) -> str:
        value = button_id.removeprefix("time-")
        if value in {"3-2", "5-0", "10-0", "15-10"}:
            return value.replace("-", "+", 1)
        return value
