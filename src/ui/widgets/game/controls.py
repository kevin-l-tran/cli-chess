from typing import Literal

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button

from src.application.session_types import Snapshot


GameAction = Literal[
    "confirm",
    "toggle_draw_offer",
    "accept_draw",
    "undo_halfmove",
    "undo_fullmove",
    "resign",
    "restart",
    "back",
]


class GameControls(Horizontal):
    DEFAULT_CSS = """
    GameControls {
        height: auto;
        margin-top: 1;
    }

    GameControls Button {
        width: auto;
        min-width: 10;
        margin-right: 1;
    }
    """

    class ActionPressed(Message):
        bubble = True

        def __init__(self, action: GameAction) -> None:
            super().__init__()
            self.action = action

    def compose(self) -> ComposeResult:
        yield Button("Confirm", id="confirm")
        yield Button("Offer draw", id="offer-draw")
        yield Button("Accept draw", id="accept-draw")
        yield Button("Undo last move", id="undo-half")
        yield Button("Undo last 2 moves", id="undo-full")
        yield Button("Resign", id="resign")
        yield Button("Restart", id="restart")
        yield Button("Back", id="back")

    def sync(self, snapshot: Snapshot, *, offer_draw: bool) -> None:
        self.query_one("#confirm", Button).disabled = not snapshot.can_confirm_move
        self.query_one("#offer-draw", Button).disabled = not snapshot.can_offer_draw
        self.query_one("#accept-draw", Button).disabled = (
            snapshot.draw_offered_by is None or snapshot.is_game_over
        )
        self.query_one("#undo-half", Button).disabled = not snapshot.can_undo_halfmove
        self.query_one("#undo-full", Button).disabled = not snapshot.can_undo_fullmove
        self.query_one("#resign", Button).disabled = not snapshot.can_resign

        self.query_one("#offer-draw", Button).label = (
            "Cancel draw" if offer_draw else "Offer draw"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions: dict[str, GameAction] = {
            "confirm": "confirm",
            "offer-draw": "toggle_draw_offer",
            "accept-draw": "accept_draw",
            "undo-half": "undo_halfmove",
            "undo-full": "undo_fullmove",
            "resign": "resign",
            "restart": "restart",
            "back": "back",
        }

        if event.button.id in actions:
            event.stop()
            self.post_message(self.ActionPressed(actions[event.button.id]))
