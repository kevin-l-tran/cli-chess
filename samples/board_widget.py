from __future__ import annotations

from textual.containers import Container, Horizontal
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


class Square(Container):
    """Border on the container; background on inner child to avoid bleed."""

    def __init__(self, text: str, *, square_classes: str, cell_classes: str) -> None:
        super().__init__(classes=square_classes)
        self._text = text
        self._cell_classes = cell_classes

    def compose(self):
        yield Static(self._text, classes=self._cell_classes, markup=False)


class BoxedBoard(Container):
    DEFAULT_CSS = """
    BoxedBoard {
        height: auto;
        width: auto;
    }

    /* CRITICAL: prevent Horizontal rows from expanding */
    .board-row, .board-files {
        height: auto;
        width: auto;
    }

    .board-spacer, .board-rank, .board-file, .board-cell {
        padding: 0;
        margin: 0;
        text-wrap: nowrap;
        content-align: center middle;
    }

    .board-spacer, .board-rank {
        width: 3;
        height: 2;
    }
    .board-rank.top {
        height: 3;
    }

    .board-file {
        width: 4;
        height: 1;
    }
    .board-file.first {
        width: 5;
    }

    .board-square {
        width: 4;
        height: 2;
        border-right: ascii;
        border-bottom: ascii;
    }
    .board-square.first {
        width: 5;
        border-left: ascii;
    }
    .board-square.top {
        height: 3;
        border-top: ascii;
    }

    .board-cell {
        width: 1fr;
        height: 1fr;
    }

    /* Theme: green (add others as needed; this is enough for the mock) */
    Screen.theme-green BoxedBoard .board-rank,
    Screen.theme-green BoxedBoard .board-file { color: #9aa4a6; }

    Screen.theme-green BoxedBoard .board-square {
        border-right: ascii #19d66b;
        border-bottom: ascii #19d66b;
    }
    Screen.theme-green BoxedBoard .board-square.first { border-left: ascii #19d66b; }
    Screen.theme-green BoxedBoard .board-square.top   { border-top: ascii #19d66b; }

    Screen.theme-green BoxedBoard .board-cell.light { background: #111718; }
    Screen.theme-green BoxedBoard .board-cell.dark  { background: #0c1213; }

    Screen.theme-green BoxedBoard .board-cell.light.empty { color: #314043; }
    Screen.theme-green BoxedBoard .board-cell.dark.empty  { color: #263234; }

    Screen.theme-green BoxedBoard .board-cell.white_piece { color: #e8ecec; text-style: bold; }
    Screen.theme-green BoxedBoard .board-cell.black_piece { color: #b4bcbc; text-style: bold; }
    """

    def __init__(self, position: list[str] = START) -> None:
        super().__init__()
        self.position = position

    def compose(self):
        with Horizontal(classes="board-files"):
            yield Static("", classes="board-spacer", markup=False)
            for i, f in enumerate(FILES):
                yield Static(f, classes=("board-file first" if i == 0 else "board-file"), markup=False)
            yield Static("", classes="board-spacer", markup=False)

        for row_index, row in enumerate(self.position):
            rank = 8 - row_index
            is_top = row_index == 0

            with Horizontal(classes="board-row"):
                yield Static(str(rank), classes=("board-rank top" if is_top else "board-rank"), markup=False)

                for col_index, ch in enumerate(row):
                    is_light = (row_index + col_index) % 2 == 0

                    if ch == ".":
                        text = "." if is_light else ":"
                        piece_class = "empty"
                    else:
                        text = ch
                        piece_class = "white_piece" if ch.isupper() else "black_piece"

                    square_classes = ["board-square"]
                    if is_top:
                        square_classes.append("top")
                    if col_index == 0:
                        square_classes.append("first")

                    cell_classes = [
                        "board-cell", "light" if is_light else "dark", piece_class]

                    yield Square(
                        text,
                        square_classes=" ".join(square_classes),
                        cell_classes=" ".join(cell_classes),
                    )

                yield Static(str(rank), classes=("board-rank top" if is_top else "board-rank"), markup=False)

        with Horizontal(classes="board-files"):
            yield Static("", classes="board-spacer", markup=False)
            for i, f in enumerate(FILES):
                yield Static(f, classes=("board-file first" if i == 0 else "board-file"), markup=False)
            yield Static("", classes="board-spacer", markup=False)
