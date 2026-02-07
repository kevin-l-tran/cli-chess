# board.py
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

FILES = "abcdefgh"

START = [
    "rnbqkbnr",
    "pppppppp",
    "........",
    "........",
    "........",
    "........",
    "PPPPPPPP",
    "RNBQKBNR",
]

THEMES = [
    "theme-green",
    "theme-gray",
    "theme-amber",
    "theme-cyan",
    "theme-blue",
    "theme-purple",
    "theme-red",
    "theme-solarized",
    "theme-paper",
]


class BoxedBoardApp(App[None]):
    CSS = """
    Screen {
        padding: 1 2;
    }

    #title {
        margin-bottom: 1;
    }

    .row, .files {
        height: auto;
    }

    .spacer, .rank, .file, .square {
        padding: 0;
        margin: 0;
        text-wrap: nowrap;
        content-align: center middle;
    }

    /* Left/right rank labels */
    .spacer, .rank {
        width: 3;
        height: 2;
    }
    .rank.top {
        height: 3;
    }

    /* File labels */
    .file {
        width: 4;
        height: 1;
    }
    .file.first {
        width: 5;
    }

    /*
      Border-collapsing approach:
      - Every square draws RIGHT + BOTTOM (shared lines)
      - First column draws LEFT (outer frame)
      - Top row draws TOP (outer frame)
    */
    .square {
        width: 4;
        height: 2;

        border-right: ascii;
        border-bottom: ascii;
    }
    .square.first {
        width: 5;
        border-left: ascii;
    }
    .square.top {
        height: 3;
        border-top: ascii;
    }

    /* Empty texture */
    .square.empty {
        text-style: dim;
    }

    /* ---------------- THEME: GREEN ---------------- */
    Screen.theme-green {
        background: #0b0f10;
    }

    Screen.theme-green .rank,
    Screen.theme-green .file {
        color: #9aa4a6;
    }

    Screen.theme-green .square {
        border-right: ascii #19d66b;
        border-bottom: ascii #19d66b;
    }
    Screen.theme-green .square.first { border-left: ascii #19d66b; }
    Screen.theme-green .square.top   { border-top: ascii #19d66b; }

    Screen.theme-green .square.light { background: #111718; }
    Screen.theme-green .square.dark  { background: #0c1213; }

    Screen.theme-green .square.light.empty { color: #314043; }
    Screen.theme-green .square.dark.empty  { color: #263234; }

    Screen.theme-green .square.white_piece { color: #e8ecec; text-style: bold; }
    Screen.theme-green .square.black_piece { color: #b4bcbc; text-style: bold; }

    /* ---------------- THEME: GRAY ---------------- */
    Screen.theme-gray {
        background: #0b0f10;
    }

    Screen.theme-gray .rank,
    Screen.theme-gray .file {
        color: #9aa4a6;
    }

    Screen.theme-gray .square {
        border-right: ascii #c9d1d3;
        border-bottom: ascii #c9d1d3;
    }
    Screen.theme-gray .square.first { border-left: ascii #c9d1d3; }
    Screen.theme-gray .square.top   { border-top: ascii #c9d1d3; }

    Screen.theme-gray .square.light { background: #111718; }
    Screen.theme-gray .square.dark  { background: #0c1213; }

    Screen.theme-gray .square.light.empty { color: #2f3c3e; }
    Screen.theme-gray .square.dark.empty  { color: #222c2e; }

    Screen.theme-gray .square.white_piece { color: #e8ecec; text-style: bold; }
    Screen.theme-gray .square.black_piece { color: #c6cccc; text-style: bold; }

    /* ---------------- THEME: AMBER ---------------- */
    Screen.theme-amber {
        background: #0d0b07;
    }

    Screen.theme-amber .rank,
    Screen.theme-amber .file {
        color: #d2b57e;
    }

    Screen.theme-amber .square {
        border-right: ascii #ffb000;
        border-bottom: ascii #ffb000;
    }
    Screen.theme-amber .square.first { border-left: ascii #ffb000; }
    Screen.theme-amber .square.top   { border-top: ascii #ffb000; }

    Screen.theme-amber .square.light { background: #141007; }
    Screen.theme-amber .square.dark  { background: #100c05; }

    Screen.theme-amber .square.light.empty { color: #4a3a1f; }
    Screen.theme-amber .square.dark.empty  { color: #3b2f19; }

    Screen.theme-amber .square.white_piece { color: #ffe2a8; text-style: bold; }
    Screen.theme-amber .square.black_piece { color: #f5c46a; text-style: bold; }

    /* ---------------- THEME: CYAN ---------------- */
    Screen.theme-cyan {
        background: #071012;
    }
    Screen.theme-cyan .rank,
    Screen.theme-cyan .file {
        color: #93a9ad;
    }
    Screen.theme-cyan .square {
        border-right: ascii #2ee6d6;
        border-bottom: ascii #2ee6d6;
    }
    Screen.theme-cyan .square.first { border-left: ascii #2ee6d6; }
    Screen.theme-cyan .square.top   { border-top: ascii #2ee6d6; }

    Screen.theme-cyan .square.light { background: #0d1c1f; }
    Screen.theme-cyan .square.dark  { background: #071417; }

    Screen.theme-cyan .square.light.empty { color: #3e666b; }
    Screen.theme-cyan .square.dark.empty  { color: #2f5256; }

    Screen.theme-cyan .square.white_piece { color: #e6fffd; text-style: bold; }
    Screen.theme-cyan .square.black_piece { color: #bfe9e6; text-style: bold; }

    /* ---------------- THEME: BLUE ---------------- */
    Screen.theme-blue {
        background: #070b12;
    }
    Screen.theme-blue .rank,
    Screen.theme-blue .file {
        color: #98a6bf;
    }
    Screen.theme-blue .square {
        border-right: ascii #4aa3ff;
        border-bottom: ascii #4aa3ff;
    }
    Screen.theme-blue .square.first { border-left: ascii #4aa3ff; }
    Screen.theme-blue .square.top   { border-top: ascii #4aa3ff; }

    Screen.theme-blue .square.light { background: #101a2a; }
    Screen.theme-blue .square.dark  { background: #0a1220; }

    Screen.theme-blue .square.light.empty { color: #3b4f73; }
    Screen.theme-blue .square.dark.empty  { color: #2f405f; }

    Screen.theme-blue .square.white_piece { color: #eef4ff; text-style: bold; }
    Screen.theme-blue .square.black_piece { color: #cbd7f2; text-style: bold; }

    /* ---------------- THEME: PURPLE ---------------- */
    Screen.theme-purple {
        background: #0e0712;
    }
    Screen.theme-purple .rank,
    Screen.theme-purple .file {
        color: #b5a1c4;
    }
    Screen.theme-purple .square {
        border-right: ascii #c86bff;
        border-bottom: ascii #c86bff;
    }
    Screen.theme-purple .square.first { border-left: ascii #c86bff; }
    Screen.theme-purple .square.top   { border-top: ascii #c86bff; }

    Screen.theme-purple .square.light { background: #1b0f24; }
    Screen.theme-purple .square.dark  { background: #120a1a; }

    Screen.theme-purple .square.light.empty { color: #6c4a86; }
    Screen.theme-purple .square.dark.empty  { color: #573a70; }

    Screen.theme-purple .square.white_piece { color: #f6eaff; text-style: bold; }
    Screen.theme-purple .square.black_piece { color: #dcc3ee; text-style: bold; }

    /* ---------------- THEME: RED ---------------- */
    Screen.theme-red {
        background: #120707;
    }
    Screen.theme-red .rank,
    Screen.theme-red .file {
        color: #c2a0a0;
    }
    Screen.theme-red .square {
        border-right: ascii #ff4d4d;
        border-bottom: ascii #ff4d4d;
    }
    Screen.theme-red .square.first { border-left: ascii #ff4d4d; }
    Screen.theme-red .square.top   { border-top: ascii #ff4d4d; }

    Screen.theme-red .square.light { background: #241010; }
    Screen.theme-red .square.dark  { background: #180a0a; }

    Screen.theme-red .square.light.empty { color: #7a3c3c; }
    Screen.theme-red .square.dark.empty  { color: #673131; }

    Screen.theme-red .square.white_piece { color: #fff0f0; text-style: bold; }
    Screen.theme-red .square.black_piece { color: #f0c6c6; text-style: bold; }

    /* ---------------- THEME: SOLARIZED (DARK-ISH) ---------------- */
    Screen.theme-solarized {
        background: #002b36;
    }
    Screen.theme-solarized .rank,
    Screen.theme-solarized .file {
        color: #93a1a1;
    }
    Screen.theme-solarized .square {
        border-right: ascii #2aa198;
        border-bottom: ascii #2aa198;
    }
    Screen.theme-solarized .square.first { border-left: ascii #2aa198; }
    Screen.theme-solarized .square.top   { border-top: ascii #2aa198; }

    Screen.theme-solarized .square.light { background: #073642; }
    Screen.theme-solarized .square.dark  { background: #002b36; }

    Screen.theme-solarized .square.light.empty { color: #586e75; }
    Screen.theme-solarized .square.dark.empty  { color: #465a61; }

    Screen.theme-solarized .square.white_piece { color: #eee8d5; text-style: bold; }
    Screen.theme-solarized .square.black_piece { color: #b7c3b0; text-style: bold; }

    /* ---------------- THEME: PAPER (LIGHT BACKGROUND) ---------------- */
    Screen.theme-paper {
        background: #f3f1e6;
    }
    Screen.theme-paper .rank,
    Screen.theme-paper .file {
        color: #3b3b3b;
    }
    Screen.theme-paper .square {
        border-right: ascii #2b2b2b;
        border-bottom: ascii #2b2b2b;
    }
    Screen.theme-paper .square.first { border-left: ascii #2b2b2b; }
    Screen.theme-paper .square.top   { border-top: ascii #2b2b2b; }

    Screen.theme-paper .square.light { background: #ffffff; }
    Screen.theme-paper .square.dark  { background: #e7e2d2; }

    Screen.theme-paper .square.light.empty { color: #b3ada0; }
    Screen.theme-paper .square.dark.empty  { color: #9f988a; }

    Screen.theme-paper .square.white_piece { color: #111111; text-style: bold; }
    Screen.theme-paper .square.black_piece { color: #333333; text-style: bold; }
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
        yield Static("Boxed / Start position  (press 't' to cycle themes)", id="title", markup=False)

        # Top file labels
        with Horizontal(classes="files"):
            yield Static("", classes="spacer", markup=False)
            for i, f in enumerate(FILES):
                yield Static(f, classes=("file first" if i == 0 else "file"), markup=False)
            yield Static("", classes="spacer", markup=False)

        # Board rows (rank 8 down to 1)
        for row_index, row in enumerate(START):
            rank = 8 - row_index
            is_top = row_index == 0

            with Horizontal(classes="row"):
                yield Static(str(rank), classes=("rank top" if is_top else "rank"), markup=False)

                for col_index, ch in enumerate(row):
                    is_light = (row_index + col_index) % 2 == 0

                    if ch == ".":
                        text = "." if is_light else ":"
                        piece_class = "empty"
                    else:
                        text = ch
                        piece_class = "white_piece" if ch.isupper() else "black_piece"

                    classes = [
                        "square", "light" if is_light else "dark", piece_class]
                    if is_top:
                        classes.append("top")
                    if col_index == 0:
                        classes.append("first")

                    yield Static(text, classes=" ".join(classes), markup=False)

                yield Static(str(rank), classes=("rank top" if is_top else "rank"), markup=False)

        # Bottom file labels
        with Horizontal(classes="files"):
            yield Static("", classes="spacer", markup=False)
            for i, f in enumerate(FILES):
                yield Static(f, classes=("file first" if i == 0 else "file"), markup=False)
            yield Static("", classes="spacer", markup=False)


if __name__ == "__main__":
    BoxedBoardApp().run()
