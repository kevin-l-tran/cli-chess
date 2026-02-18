from textual.app import App

from ui.screens.menu import MenuScreen


class ChessApp(App[None]):
    """A Textual app to play chess."""

    BINDINGS = []
    SCREENS = {"menu": MenuScreen}

    def on_mount(self) -> None:
        self.push_screen("menu")
