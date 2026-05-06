from textual.app import App

from src.ui.screens.menu import MenuScreen
from src.ui.screens.setup import SetupScreen
from src.ui.themes import CHESS_THEMES, CHESS_VARIABLE_DEFAULTS, DEFAULT_THEME, register_chess_themes


class ChessApp(App[None]):
    """A Textual app to play chess."""

    BINDINGS = [
        ("t", "cycle_theme", "Theme"),
    ]
    SCREENS = {"menu": MenuScreen, "setup": SetupScreen}

    def get_theme_variable_defaults(self) -> dict[str, str]:
        return CHESS_VARIABLE_DEFAULTS

    def on_mount(self) -> None:
        register_chess_themes(self)
        self.theme = DEFAULT_THEME
        self.push_screen("menu")

    def action_cycle_theme(self) -> None:
        themes = tuple(CHESS_THEMES)
        if not themes:
            return

        current = self.theme if self.theme in themes else DEFAULT_THEME
        current_index = themes.index(current) if current in themes else 0
        self.theme = themes[(current_index + 1) % len(themes)]
