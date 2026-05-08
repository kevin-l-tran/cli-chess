from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from src.application.viewer_types import ViewerSessionView
from src.client.ui.models.setup_models import SetupSelection
from src.client.ui.widgets.game.controls import ActionButton


class GameOverPanel(Vertical):
    DEFAULT_CSS = (Path(__file__).parent / "css" / "game_over_panel.tcss").read_text()

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._result: Static | None = None
        self._detail: Static | None = None
        self._buttons: dict[str, ActionButton] = {}

    def compose(self) -> ComposeResult:
        self._result = Static("", id="game-over-result", markup=False)
        yield self._result

        self._detail = Static("", id="game-over-detail", markup=False)
        yield self._detail

        with Horizontal(id="game-over-actions"):
            yield self._make_button("game-over-undo", "Undo", "request_undo")
            yield self._make_button("game-over-back", "Back", "back")

    def sync(self, *, view: ViewerSessionView, selection: SetupSelection) -> None:
        snapshot = view.snapshot
        result = snapshot.outcome.banner if snapshot.outcome else "Game over."
        self._result_widget().update(result)

        opponent = getattr(selection, "opponent", "")
        is_online = opponent == "online"

        if is_online:
            detail = (
                "This online game is final. Review the position or return to the lobby."
            )
        else:
            detail = "Review the final position, undo locally, or go back."

        self._detail_widget().update(detail)

        undo = self._button("game-over-undo")
        back = self._button("game-over-back")

        undo.set_enabled(view.can_request_undo)

        back.set_label("Return to lobby" if is_online else "Back")
        back.set_enabled(True)

    def _make_button(self, id: str, label: str, action: str) -> ActionButton:
        button = ActionButton(label, action, id=id)  # type: ignore[arg-type]
        self._buttons[id] = button
        return button

    def _button(self, id: str) -> ActionButton:
        button = self._buttons.get(id)
        if button is None:
            button = self.query_one(f"#{id}", ActionButton)
            self._buttons[id] = button
        return button

    def _result_widget(self) -> Static:
        if self._result is None:
            self._result = self.query_one("#game-over-result", Static)
        return self._result

    def _detail_widget(self) -> Static:
        if self._detail is None:
            self._detail = self.query_one("#game-over-detail", Static)
        return self._detail
