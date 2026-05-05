from textual.app import ComposeResult
from textual.containers import Grid
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button

from src.application.session_types import Snapshot, Square


class ChessBoard(Widget):
    DEFAULT_CSS = """
    ChessBoard {
        width: auto;
        height: auto;
    }

    #board-grid {
        grid-size: 8;
        grid-columns: 4 4 4 4 4 4 4 4;
        grid-rows: 3 3 3 3 3 3 3 3;
        width: 32;
        height: 24;
    }

    ChessBoard Button.square {
        width: 4;
        height: 3;
        min-width: 4;
        margin: 0;
        padding: 0;
        border: none;
        content-align: center middle;
    }

    ChessBoard Button.last {
        text-style: bold;
    }

    ChessBoard Button.candidate {
        text-style: reverse;
    }

    ChessBoard Button.check {
        text-style: bold reverse;
    }
    """

    class SquarePressed(Message):
        bubble = True

        def __init__(self, square: Square) -> None:
            super().__init__()
            self.square = square

    def __init__(self, *, orientation: str = "white", id: str | None = None) -> None:
        super().__init__(id=id)
        self.orientation = orientation

    def compose(self) -> ComposeResult:
        with Grid(id="board-grid"):
            for row in range(8):
                for col in range(8):
                    yield Button("", id=f"sq-{row}-{col}", classes="square")

    def refresh_from_snapshot(self, snapshot: Snapshot) -> None:
        highlighted: dict[tuple[int, int], set[str]] = {}

        def add_highlight(square: Square | None, css_class: str) -> None:
            if square is None:
                return
            highlighted.setdefault(self._square_to_display(square), set()).add(
                css_class
            )

        for from_square, to_square in snapshot.candidate_moves:
            add_highlight(from_square, "candidate")
            add_highlight(to_square, "candidate")

        add_highlight(snapshot.last_move_from, "last")
        add_highlight(snapshot.last_move_to, "last")
        add_highlight(snapshot.check_square, "check")

        for display_row in range(8):
            for display_col in range(8):
                file, rank = self._display_to_square(display_row, display_col)
                glyph = snapshot.board_glyphs[7 - rank][file]

                button = self.query_one(f"#sq-{display_row}-{display_col}", Button)
                button.label = self._display_glyph(glyph)

                for css_class in ("candidate", "last", "check"):
                    button.remove_class(css_class)

                for css_class in highlighted.get((display_row, display_col), set()):
                    button.add_class(css_class)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if not button_id.startswith("sq-"):
            return

        _, row_s, col_s = button_id.split("-")
        square = self._display_to_square(int(row_s), int(col_s))
        event.stop()
        self.post_message(self.SquarePressed(square))

    def _display_to_square(self, display_row: int, display_col: int) -> Square:
        if self.orientation == "black":
            return 7 - display_col, display_row
        return display_col, 7 - display_row

    def _square_to_display(self, square: Square) -> tuple[int, int]:
        file, rank = square
        if self.orientation == "black":
            return rank, 7 - file
        return 7 - rank, file

    def _display_glyph(self, glyph: str) -> str:
        glyph = glyph.strip()
        return glyph if glyph else "·"
