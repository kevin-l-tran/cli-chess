from textual.app import App

from ui.screens.menu import MenuScreen
from ui.themes import CHESS_VARIABLE_DEFAULTS, DEFAULT_THEME, register_chess_themes


class ChessApp(App[None]):
    """A Textual app to play chess."""

    BINDINGS = []
    SCREENS = {"menu": MenuScreen}

    def get_theme_variable_defaults(self) -> dict[str, str]:
        return CHESS_VARIABLE_DEFAULTS

    def on_mount(self) -> None:
        register_chess_themes(self)
        self.theme = DEFAULT_THEME
        self.push_screen("menu")
