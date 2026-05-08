from pathlib import Path
from typing import Literal, cast

from textual.app import ComposeResult
from textual.containers import Grid
from textual.events import Click, Key
from textual.message import Message
from textual.widgets import Static

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


class ActionButton(Static):
    """Small clickable control with stable layout and low-cost hover styling.

    The visual brackets are part of the rendered label rather than CSS borders.
    This keeps the action area compact on short terminals while preserving a
    large enough mouse target for each command.
    """

    can_focus = True

    def __init__(self, label: str, action: GameAction, *, id: str) -> None:
        super().__init__(self._display_label(label), id=id, classes="action-button", markup=False)
        self.action = action
        self._label = label
        self._enabled = True

    def set_label(self, label: str) -> None:
        if label == self._label:
            return
        self._label = label
        self.update(self._display_label(label))

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self.disabled = not enabled
        self.set_class(not enabled, "disabled")

    def on_click(self, event: Click) -> None:
        event.stop()
        if self._enabled:
            self.post_message(GameControls.ActionPressed(cast(GameAction, self.action)))

    def on_key(self, event: Key) -> None:
        if event.key in {"enter", "space"}:
            event.stop()
            if self._enabled:
                self.post_message(
                    GameControls.ActionPressed(cast(GameAction, self.action))
                )

    def _display_label(self, label: str) -> str:
        return f"[ {label} ]"


class GameControls(Grid):
    DEFAULT_CSS = (Path(__file__).parent / "css" / "controls.tcss").read_text()

    class ActionPressed(Message):
        bubble = True

        def __init__(self, action: GameAction) -> None:
            super().__init__()
            self.action = action

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._buttons: dict[str, ActionButton] = {}

    def compose(self) -> ComposeResult:
        specs: tuple[tuple[str, str, GameAction], ...] = (
            ("confirm", "Confirm", "confirm"),
            ("offer-draw", "Offer draw", "toggle_draw_offer"),
            ("accept-draw", "Accept draw", "accept_draw"),
            ("undo-half", "Undo move", "undo_halfmove"),
            ("undo-full", "Undo turn", "undo_fullmove"),
            ("resign", "Resign", "resign"),
            ("restart", "Restart", "restart"),
            ("back", "Back", "back"),
        )
        for button_id, label, action in specs:
            button = ActionButton(label, action, id=button_id)
            self._buttons[button_id] = button
            yield button

    def sync(self, snapshot: Snapshot, *, offer_draw: bool) -> None:
        self._button("confirm").set_enabled(snapshot.can_confirm_move)
        self._button("offer-draw").set_enabled(snapshot.can_offer_draw)
        self._button("accept-draw").set_enabled(self._can_accept_draw(snapshot))
        self._button("undo-half").set_enabled(snapshot.can_undo_halfmove)
        self._button("undo-full").set_enabled(snapshot.can_undo_fullmove)
        self._button("resign").set_enabled(snapshot.can_resign)

        self._button("offer-draw").set_label(
            "Cancel draw" if offer_draw else "Offer draw"
        )

    def _can_accept_draw(self, snapshot: Snapshot) -> bool:
        explicit = getattr(snapshot, "can_accept_draw", None)
        if explicit is not None:
            return bool(explicit)
        return snapshot.draw_offered_by is not None and not snapshot.is_game_over

    def _button(self, button_id: str) -> ActionButton:
        button = self._buttons.get(button_id)
        if button is None:
            button = self.query_one(f"#{button_id}", ActionButton)
            self._buttons[button_id] = button
        return button
