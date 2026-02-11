from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Input, Static

from board_widget import BoxedBoard, THEMES


class ChessMockApp(App[None]):
    CSS = """
    Screen {
        padding: 1 2;
        background: #0b0f10;
        color: #cfd6d6;
    }

    #topbar { height: 1; margin-bottom: 1; }

    #main { height: 1fr; }

    /* KEY: left is fixed; right is flexible */
    #left  { width: 46; height: 1fr; }
    #right { width: 1fr; height: 1fr; padding-left: 2; }

    #bottombar { height: 3; margin-top: 1; }

    .frame { border: ascii #19d66b; padding: 0 1; }
    .frame_title { height: 1; text-style: bold; }

    .panel { height: auto; margin-bottom: 1; }
    #moves_panel { height: 1fr; }
    #moves_list { height: 1fr; }

    #cmdline { width: 1fr; }
    #hint { width: 32; content-align: right middle; }

    Input { border: ascii #19d66b; }

    /* Theme hook (keep simple; green only for mock; you can expand) */
    Screen.theme-green { background: #0b0f10; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("t", "cycle_theme", "Theme"),
    ]

    def on_mount(self) -> None:
        self._theme_index = 0
        self.screen.add_class(THEMES[self._theme_index])

    def action_cycle_theme(self) -> None:
        self.screen.remove_class(THEMES[self._theme_index])
        self._theme_index = (self._theme_index + 1) % len(THEMES)
        self.screen.add_class(THEMES[self._theme_index])

    def compose(self) -> ComposeResult:
        yield Static("CLI Chess (mock)  •  press 't' to cycle themes  •  press 'q' to quit", id="topbar", markup=False)

        with Horizontal(id="main"):
            with Vertical(id="left", classes="frame"):
                yield Static("Board", classes="frame_title", markup=False)
                yield BoxedBoard()

            with Vertical(id="right"):
                with Vertical(classes="frame panel"):
                    yield Static("Status", classes="frame_title", markup=False)
                    yield Static(
                        "Turn: White\n"
                        "State: —\n"
                        "Castling: KQkq\n"
                        "En passant: —\n"
                        "Halfmove: 0   Fullmove: 1\n"
                        "Mode: Human vs Bot (mock)\n"
                        "Eval: +0.2 (mock)",
                        markup=False,
                    )

                with Vertical(classes="frame panel"):
                    yield Static("Clocks", classes="frame_title", markup=False)
                    yield Static("Black: 05:00.0\nWhite: 05:00.0\nIncrement: +2s", markup=False)

                with Vertical(classes="frame panel"):
                    yield Static("Captures", classes="frame_title", markup=False)
                    yield Static("White captured: —\nBlack captured: —\nMaterial: =", markup=False)

                with Vertical(classes="frame panel", id="moves_panel"):
                    yield Static("Moves", classes="frame_title", markup=False)
                    with VerticalScroll(id="moves_list"):
                        yield Static(
                            "1. e4      c5\n"
                            "2. Nf3     d6\n"
                            "3. d4      cxd4\n"
                            "4. Nxd4   Nf6\n"
                            "5. Nc3    a6\n"
                            "6. Be3    e6\n"
                            "7. f3     b5\n"
                            "8. Qd2    Nbd7\n"
                            "9. O-O-O  Bb7\n"
                            "10. g4    h6\n",
                            markup=False,
                        )

        with Horizontal(id="bottombar"):
            yield Input(placeholder="Enter move (e2e4 / Nf3) …", id="cmdline")
            yield Static("Keys: t theme  •  q quit", id="hint", markup=False)

        yield Footer()


if __name__ == "__main__":
    ChessMockApp().run()
