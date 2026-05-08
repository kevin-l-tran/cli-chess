from pathlib import Path
from typing import Literal, cast

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.events import Click, Key
from textual.message import Message
from textual.widgets import Static

from src.application.viewer_types import LocalDraftView, ViewerSessionView


GameAction = Literal[
    "confirm",
    "toggle_draw_offer",
    "accept_draw",
    "request_undo",
    "resign",
    "back",
]


class ActionButton(Static):
    """Small clickable control with stable layout and low-cost hover styling."""

    can_focus = True

    def __init__(self, label: str, action: GameAction, *, id: str) -> None:
        super().__init__(
            self._display_label(label),
            id=id,
            classes="action-button",
            markup=False,
        )
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


class GameControls(Vertical):
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
        top_specs: tuple[tuple[str, str, GameAction], ...] = (
            ("confirm", "Confirm", "confirm"),
            ("offer-draw", "Offer draw", "toggle_draw_offer"),
            ("accept-draw", "Accept draw", "accept_draw"),
        )

        bottom_specs: tuple[tuple[str, str, GameAction], ...] = (
            ("undo", "Undo", "request_undo"),
            ("resign", "Resign", "resign"),
            ("back", "Back", "back"),
        )

        with Horizontal(classes="action-row"):
            for button_id, label, action in top_specs:
                yield self._make_button(button_id, label, action)

        with Horizontal(classes="action-row"):
            for button_id, label, action in bottom_specs:
                yield self._make_button(button_id, label, action)

    def sync(
        self,
        *,
        view: ViewerSessionView,
        draft: LocalDraftView,
        offer_draw: bool,
    ) -> None:
        self._button("confirm").set_enabled(self._can_confirm_move(view, draft))
        self._button("offer-draw").set_enabled(view.can_offer_draw)
        self._button("accept-draw").set_enabled(view.can_accept_draw)
        self._button("undo").set_enabled(view.can_request_undo)
        self._button("resign").set_enabled(view.can_resign)

        self._button("offer-draw").set_label(
            "Cancel draw" if offer_draw else "Offer draw"
        )

    def _can_confirm_move(
        self,
        view: ViewerSessionView,
        draft: LocalDraftView,
    ) -> bool:
        if not view.can_submit_move:
            return False
        if draft.submit_text is None:
            return False
        return draft.status not in {"empty", "no_match", "ambiguous", "stale"}

    def _button(self, button_id: str) -> ActionButton:
        button = self._buttons.get(button_id)
        if button is None:
            button = self.query_one(f"#{button_id}", ActionButton)
            self._buttons[button_id] = button
        return button

    def _make_button(
        self,
        button_id: str,
        label: str,
        action: GameAction,
    ) -> ActionButton:
        button = ActionButton(label, action, id=button_id)
        self._buttons[button_id] = button
        return button
