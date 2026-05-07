from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.events import Click, Key
from textual.message import Message
from textual.widgets import Static


class TerminalAction(Static, can_focus=True):
    class Pressed(Message):
        bubble = True

        def __init__(self, action_id: str) -> None:
            super().__init__()
            self.action_id = action_id

    def __init__(
        self,
        label: str,
        *,
        action_id: str,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        self.action_id = action_id
        super().__init__(label, id=id, classes=classes, markup=False)

    def on_click(self, event: Click) -> None:
        event.stop()
        self.post_message(self.Pressed(self.action_id))

    def on_key(self, event: Key) -> None:
        if event.key in {"enter", "space"}:
            event.stop()
            self.post_message(self.Pressed(self.action_id))


class SetupActions(Horizontal):
    DEFAULT_CSS = """
    SetupActions {
        align-horizontal: center;
        height: auto;
        margin-top: 1;
    }

    TerminalAction {
        width: auto;
        min-width: 12;
        height: 1;
        padding: 0 1;
        margin: 0 1;
        background: transparent;
        color: $foreground;
        text-style: bold;
        content-align: center middle;
    }

    TerminalAction.primary {
        color: $accent;
    }

    TerminalAction:focus {
        background: $foreground;
        color: $background;
        text-style: bold;
    }
    """

    class StartPressed(Message):
        bubble = True

    class BackPressed(Message):
        bubble = True

    def compose(self) -> ComposeResult:
        yield TerminalAction("[ Start ]", action_id="start", id="start", classes="primary")
        yield TerminalAction("[ Back ]", action_id="back", id="back")

    def on_terminal_action_pressed(self, event: TerminalAction.Pressed) -> None:
        if event.action_id == "start":
            self.post_message(self.StartPressed())
        elif event.action_id == "back":
            self.post_message(self.BackPressed())
