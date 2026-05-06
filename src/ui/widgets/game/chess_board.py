from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.events import Click
from textual.message import Message
from textual.widgets import Static

from src.application.session_types import Snapshot, Square as BoardCoordinate


FILES = "abcdefgh"
CELL_STATE_CLASSES = (
    "light",
    "dark",
    "empty",
    "white_piece",
    "black_piece",
    "candidate",
    "capture",
    "last",
    "check",
)
EMPTY_GLYPHS = {"", ".", ":", "\u00b7"}


class BoardSquare(Container):
    """A clickable board square with border on the container and fill on a child."""

    def __init__(
        self,
        square: BoardCoordinate,
        *,
        id: str,
        square_classes: str,
        cell_classes: str,
    ) -> None:
        super().__init__(id=id, classes=square_classes)
        self.square = square
        self._initial_cell_classes = cell_classes
        self._cell: Static | None = None
        self._render_text: str | None = None
        self._render_classes: frozenset[str] = frozenset()
        self._render_highlights: frozenset[str] = frozenset()

    def compose(self) -> ComposeResult:
        self._cell = Static("", classes=self._initial_cell_classes, markup=False)
        yield self._cell

    def update_content(
        self,
        text: str,
        *,
        cell_classes: str,
        highlight_classes: set[str],
    ) -> None:
        highlights = frozenset(highlight_classes)
        class_set = frozenset(cell_classes.split()).union(highlights)
        display_text = self._highlight_text(text, highlights)

        if (
            display_text == self._render_text
            and class_set == self._render_classes
            and highlights == self._render_highlights
        ):
            return

        cell = self._cell or self.query_one(Static)
        if display_text != self._render_text:
            cell.update(display_text)
            self._render_text = display_text

        if class_set != self._render_classes:
            for css_class in CELL_STATE_CLASSES:
                cell.remove_class(css_class)
            for css_class in class_set:
                cell.add_class(css_class)
            self._render_classes = class_set

        self._render_highlights = highlights

    def on_click(self, event: Click) -> None:
        event.stop()
        self.post_message(ChessBoard.SquarePressed(self.square))

    def _highlight_text(self, text: str, highlight_classes: frozenset[str]) -> str:
        if text not in EMPTY_GLYPHS:
            return text
        if "check" in highlight_classes:
            return "!"
        if "capture" in highlight_classes:
            return "x"
        if "candidate" in highlight_classes:
            return "o"
        if "last" in highlight_classes:
            return "*"
        return text


class ChessBoard(Container):
    DEFAULT_CSS = (Path(__file__).parent / "css" / "chess_board.tcss").read_text()

    class SquarePressed(Message):
        bubble = True

        def __init__(self, square: BoardCoordinate) -> None:
            super().__init__()
            self.square = square

    def __init__(self, *, orientation: str = "white", id: str | None = None) -> None:
        super().__init__(id=id)
        self.orientation = orientation
        self._squares: dict[tuple[int, int], BoardSquare] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(classes="board-files"):
            yield Static("", classes="board-spacer", markup=False)
            for index, file_label in enumerate(self._display_files()):
                classes = "board-file first" if index == 0 else "board-file"
                yield Static(file_label, classes=classes, markup=False)
            yield Static("", classes="board-spacer", markup=False)

        for display_row in range(8):
            is_top = display_row == 0
            rank_classes = "board-rank top" if is_top else "board-rank"

            with Horizontal(classes="board-row"):
                yield Static(
                    self._display_rank_label(display_row),
                    classes=rank_classes,
                    markup=False,
                )

                for display_col in range(8):
                    square = self._display_to_square(display_row, display_col)
                    cell_classes = self._cell_classes_for("", square)
                    square_classes = ["board-square"]
                    if is_top:
                        square_classes.append("top")
                    if display_col == 0:
                        square_classes.append("first")

                    board_square = BoardSquare(
                        square,
                        id=f"sq-{display_row}-{display_col}",
                        square_classes=" ".join(square_classes),
                        cell_classes=cell_classes,
                    )
                    self._squares[(display_row, display_col)] = board_square
                    yield board_square

                yield Static(
                    self._display_rank_label(display_row),
                    classes=rank_classes,
                    markup=False,
                )

        with Horizontal(classes="board-files"):
            yield Static("", classes="board-spacer", markup=False)
            for index, file_label in enumerate(self._display_files()):
                classes = "board-file first" if index == 0 else "board-file"
                yield Static(file_label, classes=classes, markup=False)
            yield Static("", classes="board-spacer", markup=False)

    def refresh_from_snapshot(self, snapshot: Snapshot) -> None:
        highlighted: dict[tuple[int, int], set[str]] = {}

        def add_highlight(square: BoardCoordinate | None, css_class: str) -> None:
            if square is None:
                return
            highlighted.setdefault(self._square_to_display(square), set()).add(
                css_class
            )

        for from_square, to_square in snapshot.candidate_moves:
            add_highlight(from_square, "candidate")
            add_highlight(
                to_square,
                "capture"
                if self._square_has_piece(snapshot, to_square)
                else "candidate",
            )

        add_highlight(snapshot.last_move_from, "last")
        add_highlight(snapshot.last_move_to, "last")
        add_highlight(snapshot.check_square, "check")

        for display_row in range(8):
            for display_col in range(8):
                square = self._display_to_square(display_row, display_col)
                file, rank = square
                glyph = snapshot.board_glyphs[7 - rank][file]
                cell_classes = self._cell_classes_for(glyph, square)
                text = self._display_glyph(glyph, square)

                board_square = self._squares.get((display_row, display_col))
                if board_square is None:
                    board_square = self.query_one(
                        f"#sq-{display_row}-{display_col}", BoardSquare
                    )
                    self._squares[(display_row, display_col)] = board_square

                board_square.update_content(
                    text,
                    cell_classes=cell_classes,
                    highlight_classes=highlighted.get(
                        (display_row, display_col), set()
                    ),
                )

    def _square_has_piece(self, snapshot: Snapshot, square: BoardCoordinate) -> bool:
        file, rank = square
        glyph = snapshot.board_glyphs[7 - rank][file].strip()
        return bool(glyph and glyph not in EMPTY_GLYPHS)

    def _display_to_square(self, display_row: int, display_col: int) -> BoardCoordinate:
        if self.orientation == "black":
            return 7 - display_col, display_row
        return display_col, 7 - display_row

    def _square_to_display(self, square: BoardCoordinate) -> tuple[int, int]:
        file, rank = square
        if self.orientation == "black":
            return rank, 7 - file
        return 7 - rank, file

    def _display_files(self) -> str:
        if self.orientation == "black":
            return FILES[::-1]
        return FILES

    def _display_rank_label(self, display_row: int) -> str:
        if self.orientation == "black":
            return str(display_row + 1)
        return str(8 - display_row)

    def _cell_classes_for(self, glyph: str, square: BoardCoordinate) -> str:
        shade = "light" if self._is_light_square(square) else "dark"
        piece_class = self._piece_class(glyph)
        return f"board-cell {shade} {piece_class}"

    def _display_glyph(self, glyph: str, square: BoardCoordinate) -> str:
        glyph = glyph.strip()
        if glyph and glyph not in EMPTY_GLYPHS:
            return glyph
        return "." if self._is_light_square(square) else ":"

    def _piece_class(self, glyph: str) -> str:
        glyph = glyph.strip()
        if not glyph or glyph in EMPTY_GLYPHS:
            return "empty"
        codepoint = ord(glyph[0])
        if glyph.isupper() or 0x2654 <= codepoint <= 0x2659:
            return "white_piece"
        if glyph.islower() or 0x265A <= codepoint <= 0x265F:
            return "black_piece"
        return "white_piece"

    def _is_light_square(self, square: BoardCoordinate) -> bool:
        file, rank = square
        return (file + rank) % 2 == 1
