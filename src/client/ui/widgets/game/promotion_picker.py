from typing import cast

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.events import Click, Key
from textual.message import Message
from textual.widgets import Static

from src.shared.protocol_types import PromotionPiece


class PromotionButton(Static):
    can_focus = True

    def __init__(self, label: str, piece: PromotionPiece, *, id: str) -> None:
        super().__init__(
            f"[ {label} ]",
            id=id,
            classes="promotion-button",
            markup=False,
        )
        self.piece = piece

    def on_click(self, event: Click) -> None:
        event.stop()
        self.post_message(
            PromotionPicker.PieceSelected(cast(PromotionPiece, self.piece))
        )

    def on_key(self, event: Key) -> None:
        if event.key in {"enter", "space"}:
            event.stop()
            self.post_message(
                PromotionPicker.PieceSelected(cast(PromotionPiece, self.piece))
            )


class PromotionPicker(Horizontal):
    DEFAULT_CSS = """
    PromotionPicker {
        height: 1;
        min-height: 1;
        width: 1fr;
        align: center middle;
        margin-top: 1;
    }

    PromotionPicker .promotion-button {
        width: auto;
        min-width: 8;
        height: 1;
        margin: 0 1;
        padding: 0;
        border: none;
        background: $background;
        color: $foreground;
        content-align: center middle;
        text-style: bold;
    }

    PromotionPicker .promotion-button:hover {
        color: $accent;
    }

    PromotionPicker .promotion-button:focus {
        color: $foreground;
        background: $surface;
        text-style: bold reverse;
    }
    """

    class PieceSelected(Message):
        bubble = True

        def __init__(self, piece: PromotionPiece) -> None:
            super().__init__()
            self.piece = piece

    def compose(self) -> ComposeResult:
        yield PromotionButton("Q", cast(PromotionPiece, "Q"), id="promote-q")
        yield PromotionButton("R", cast(PromotionPiece, "R"), id="promote-r")
        yield PromotionButton("B", cast(PromotionPiece, "B"), id="promote-b")
        yield PromotionButton("N", cast(PromotionPiece, "N"), id="promote-n")
