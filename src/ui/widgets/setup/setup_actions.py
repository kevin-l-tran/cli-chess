from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button

class SetupActions(Widget):
    DEFAULT_CSS = """
    SetupActions {
        layout: horizontal;
        align-horizontal: center;
        height: auto;
        margin-top: 1;
    }

    SetupActions Button {
        width: 18;
        margin: 0 1;
        background: transparent;
        border: solid $border;
        color: $foreground;
        text-style: bold;
    }

    SetupActions Button.primary {
        background: $accent;
        border: solid $accent;
        color: $text;
    }
    """

    class StartPressed(Message):
        bubble = True

    class BackPressed(Message):
        bubble = True

    def compose(self) -> ComposeResult:
        yield Button("Start", id="start", classes="primary")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            self.post_message(self.StartPressed())
        elif event.button.id == "back":
            self.post_message(self.BackPressed())
