from typing import Literal, cast

from textual.app import ComposeResult
from textual.containers import Grid
from textual.message import Message
from textual.widgets import Button


PromotionPiece = Literal["Q", "R", "B", "N"]


class PromotionPicker(Grid):
    DEFAULT_CSS = """
    PromotionPicker {
        height: auto;
        width: 1fr;
        grid-size: 4;
        grid-columns: 1fr 1fr 1fr 1fr;
        grid-gutter: 0 1;
        margin-top: 1;
    }

    PromotionPicker Button {
        width: 1fr;
        height: 3;
        min-width: 8;
        margin: 0;
        border: ascii #19d66b;
        background: #0b0f10;
        color: #cfd6d6;
    }

    PromotionPicker Button:hover,
    PromotionPicker Button:focus {
        border: heavy #19d66b;
        text-style: bold;
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
