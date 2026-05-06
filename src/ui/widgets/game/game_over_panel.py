from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.widgets import Static

from src.application.session_types import Snapshot
from src.ui.models.setup_models import SetupSelection
from src.ui.widgets.game.controls import ActionButton


class GameOverPanel(Vertical):
    DEFAULT_CSS = (
        Path(__file__).parent / "css" / "game_over_panel.tcss"
    ).read_text()

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

        with Grid(id="game-over-actions"):
            yield self._make_button("game-over-undo-half", "Undo move", "undo_halfmove")
            yield self._make_button("game-over-undo-full", "Undo turn", "undo_fullmove")
            yield self._make_button("game-over-restart", "Restart", "restart")
            yield self._make_button("game-over-back", "Back", "back")

    def sync(self, snapshot: Snapshot, *, selection: SetupSelection) -> None:
        result = snapshot.outcome.banner if snapshot.outcome else "Game over."
        self._result_widget().update(result)

        opponent = getattr(selection, "opponent", "")
        is_online = opponent == "online"

        if is_online:
            detail = "This online game is final. Review the position or return to the lobby."
        else:
            detail = "Review the final position, undo locally, restart, or go back."

        self._detail_widget().update(detail)

        undo_half = self._button("game-over-undo-half")
        undo_full = self._button("game-over-undo-full")
        restart = self._button("game-over-restart")
        back = self._button("game-over-back")

        undo_half.set_enabled(snapshot.can_undo_halfmove)

        undo_full.set_enabled(snapshot.can_undo_fullmove)

        restart.display = not is_online
        restart.set_enabled(not is_online)

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