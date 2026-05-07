from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Click, Key
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static


class TerminalOption(Static, can_focus=True):
    """Compact bracketed option with mouse, Tab, Enter, and Space support."""

    label_text: reactive[str] = reactive("")
    selected: reactive[bool] = reactive(False)

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
        super().__init__(
            "",
            id=id,
            classes=self._initial_classes(classes, selected),
            markup=False,
        )
        self.label_text = label
        self.selected = selected

    def update_state(self, label: str, *, selected: bool) -> None:
        self.label_text = label
        self.selected = selected

    def watch_label_text(self, label: str) -> None:
        self.update(f"[ {label} ]")

    def watch_selected(self, selected: bool) -> None:
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

    def _initial_classes(self, classes: str | None, selected: bool) -> str:
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

    DEFAULT_CSS = (Path(__file__).parent / "css" / "inputs.tcss").read_text()

    value_text: reactive[str] = reactive("")

    class Changed(Message):
        bubble = True

    def __init__(self, value: str, *, id: str | None = None) -> None:
        super().__init__("", id=id, classes="terminal-number-field", markup=False)
        self._fresh_focus = False
        self.value_text = value

    @property
    def text_value(self) -> str:
        return self.value_text

    def watch_value_text(self, value: str) -> None:
        display = value if value else "--"
        self.update(f"[ {display:>2} ]")

    def on_focus(self) -> None:
        self._fresh_focus = True

    def on_click(self, event: Click) -> None:
        event.stop()
        self.focus()

    def on_key(self, event: Key) -> None:
        if event.character and event.character.isdigit():
            event.stop()
            if self._fresh_focus:
                next_value = event.character
            elif len(self.value_text) >= 2:
                next_value = event.character
            else:
                next_value = self.value_text + event.character

            self._fresh_focus = False
            self._set_value(next_value)
            return

        if event.key in {"backspace", "ctrl+h"}:
            event.stop()
            self._fresh_focus = False
            self._set_value(self.value_text[:-1])
            return

        if event.key in {"delete", "ctrl+x"}:
            event.stop()
            self._fresh_focus = False
            self._set_value("")
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
        current = int(self.value_text or "0")
        self._set_value(str(max(0, min(59, current + delta))))

    def _set_value(self, value: str) -> None:
        if value == self.value_text:
            return

        self.value_text = value
        self.post_message(self.Changed())


class CustomTimeInput(Vertical):
    DEFAULT_CSS = (Path(__file__).parent / "css" / "inputs.tcss").read_text()

    value: reactive[tuple[int, int] | None] = reactive(None)
    error_text: reactive[str] = reactive("")

    class Changed(Message):
        bubble = True

        def __init__(self, value: tuple[int, int] | None) -> None:
            super().__init__()
            self.value = value

    def compose(self) -> ComposeResult:
        with Horizontal(classes="custom-time-row"):
            yield Static("Custom:", classes="field-label", markup=False)
            yield TerminalNumberField("5", id="mins")
            yield Static("+", id="plus", markup=False)
            yield TerminalNumberField("0", id="inc")
        yield Static("", id="error", markup=False)

    def on_mount(self) -> None:
        self._recompute()

    def watch_value(self, value: tuple[int, int] | None) -> None:
        self.post_message(self.Changed(value))

    def watch_error_text(self, error_text: str) -> None:
        if self.is_mounted:
            self.query_one("#error", Static).update(error_text)

    def on_terminal_number_field_changed(self, _: TerminalNumberField.Changed) -> None:
        self._recompute()

    def _recompute(self) -> None:
        mins_s = self.query_one("#mins", TerminalNumberField).text_value.strip()
        inc_s = self.query_one("#inc", TerminalNumberField).text_value.strip()

        if not mins_s or not inc_s:
            self.error_text = "Enter minutes and increment."
            self.value = None
            return

        mins = int(mins_s)
        inc = int(inc_s)

        if not (0 < mins <= 59):
            self.error_text = "Start time must be 1-59 minutes."
            self.value = None
            return

        if not (0 <= inc <= 59):
            self.error_text = "Increment must be 0-59 seconds."
            self.value = None
            return

        self.error_text = ""
        self.value = (mins, inc)
