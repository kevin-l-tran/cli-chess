from typing import cast

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Static

from src.application.session import GameSession
from src.application.session_types import SessionConfig, Snapshot
from src.ui.controllers.game_controller import (
    CurrentSessionController,
    GameController,
    PromotionPiece,
)
from src.ui.models.setup_models import SetupSelection
from src.ui.widgets.game.chess_board import ChessBoard
from src.ui.widgets.game.controls import GameControls
from src.ui.widgets.game.side_panel import GameSidePanel
from src.ui.widgets.game.promotion_picker import PromotionPicker


class GameScreen(Screen):
    BINDINGS = [
        ("escape", "back", "Back"),
        ("ctrl+r", "restart", "Restart"),
        ("ctrl+u", "undo_fullmove", "Undo turn"),
        ("ctrl+h", "undo_halfmove", "Undo move"),
    ]

    CSS = """
    GameScreen {
        padding: 1 2;
    }

    #game-root {
        height: 1fr;
        width: 1fr;
    }

    #top-layout {
        height: 1fr;
        width: 1fr;
    }

    #board-panel {
        width: auto;
        height: auto;
        margin-right: 2;
    }

    #side-panel {
        width: 50;
        height: 1fr;
    }

    #title {
        text-style: bold;
        height: auto;
        margin-bottom: 1;
    }

    #move-input {
        width: 1fr;
        height: auto;
        margin-top: 1;
    }

    #promotion-row {
        height: auto;
    }

    #controls {
        height: auto;
    }
    """

    def __init__(
        self,
        selection: SetupSelection,
        controller: GameController | None = None,
    ) -> None:
        super().__init__()
        self.selection = selection
        self.config: SessionConfig = selection.to_session_config()
        self.controller = controller or CurrentSessionController(
            GameSession(self.config)
        )
        self.offer_draw = False
        self._syncing_input = False

    def compose(self) -> ComposeResult:
        yield Static("Chess", id="title")

        with Vertical(id="game-root"):
            with Horizontal(id="top-layout"):
                with Vertical(id="board-panel"):
                    yield ChessBoard(orientation=self.config.player_side, id="board")

                yield GameSidePanel(id="side-panel")

            yield Input(placeholder="Move, e.g. e2e4 or Nc3", id="move-input")
            yield PromotionPicker(id="promotion-row")
            yield GameControls(id="controls")

    def on_mount(self) -> None:
        self._refresh_view()
        self.query_one("#move-input", Input).focus()
        self.set_interval(0.5, self._refresh_view)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "move-input" or self._syncing_input:
            return

        self.controller.set_move_text(event.value)
        self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "move-input":
            self._confirm_move()

    def on_chess_board_square_pressed(self, msg: ChessBoard.SquarePressed) -> None:
        self.controller.click_square(msg.square)
        self._refresh_view()
        self.query_one("#move-input", Input).focus()

    def on_promotion_picker_piece_selected(
        self,
        msg: PromotionPicker.PieceSelected,
    ) -> None:
        self.controller.select_promotion_piece(cast(PromotionPiece, msg.piece))
        self._refresh_view()
        self.query_one("#move-input", Input).focus()

    def on_game_controls_action_pressed(
        self,
        msg: GameControls.ActionPressed,
    ) -> None:
        match msg.action:
            case "confirm":
                self._confirm_move()
            case "toggle_draw_offer":
                self.offer_draw = not self.offer_draw
                self._refresh_view()
            case "accept_draw":
                self.controller.accept_draw_offer()
                self._refresh_view()
            case "undo_halfmove":
                self.controller.undo("halfmove")
                self._refresh_view()
            case "undo_fullmove":
                self.controller.undo("fullmove")
                self._refresh_view()
            case "resign":
                self.controller.resign()
                self._refresh_view()
            case "restart":
                self.controller.restart_game()
                self.offer_draw = False
                self._refresh_view()
            case "back":
                self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_restart(self) -> None:
        self.controller.restart_game()
        self.offer_draw = False
        self._refresh_view()

    def action_undo_fullmove(self) -> None:
        self.controller.undo("fullmove")
        self._refresh_view()

    def action_undo_halfmove(self) -> None:
        self.controller.undo("halfmove")
        self._refresh_view()

    def _confirm_move(self) -> None:
        self.controller.confirm_move(offer_draw=self.offer_draw)
        snapshot = self.controller.snapshot()

        if snapshot.feedback is None or snapshot.feedback.kind != "error":
            self.offer_draw = False

        self._refresh_view(snapshot)
        self.query_one("#move-input", Input).focus()

    def _refresh_view(self, snapshot: Snapshot | None = None) -> None:
        snapshot = self.controller.snapshot() if snapshot is None else snapshot

        self.query_one("#board", ChessBoard).refresh_from_snapshot(snapshot)
        self._sync_move_input(snapshot)

        self.query_one("#side-panel", GameSidePanel).sync(
            snapshot,
            selection=self.selection,
            config=self.config,
            offer_draw=self.offer_draw,
        )

        self.query_one("#controls", GameControls).sync(
            snapshot,
            offer_draw=self.offer_draw,
        )

        self.query_one(
            "#promotion-row", PromotionPicker
        ).display = snapshot.is_promotion_pending

    def _sync_move_input(self, snapshot: Snapshot) -> None:
        move_input = self.query_one("#move-input", Input)
        move_input.disabled = snapshot.is_game_over

        if move_input.value != snapshot.move_draft.text:
            self._syncing_input = True
            move_input.value = snapshot.move_draft.text
            self._syncing_input = False
