from typing import Literal, cast

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button


PromotionPiece = Literal["Q", "R", "B", "N"]


class PromotionPicker(Horizontal):
    DEFAULT_CSS = """
    PromotionPicker {
        height: auto;
        margin-top: 1;
    }

    PromotionPicker Button {
        width: auto;
        min-width: 10;
        margin-right: 1;
    }
    """

    class PieceSelected(Message):
        bubble = True

        def __init__(self, piece: PromotionPiece) -> None:
            super().__init__()
            self.piece = piece

    def compose(self) -> ComposeResult:
        yield Button("Queen", id="promote-q")
        yield Button("Rook", id="promote-r")
        yield Button("Bishop", id="promote-b")
        yield Button("Knight", id="promote-n")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        pieces = {
            "promote-q": "Q",
            "promote-r": "R",
            "promote-b": "B",
            "promote-n": "N",
        }

        if event.button.id in pieces:
            event.stop()
            self.post_message(
                self.PieceSelected(cast(PromotionPiece, pieces[event.button.id]))
            )
