from pathlib import Path
from typing import cast

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Input, Static

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

    DEFAULT_CSS = (Path(__file__).parent / "css" / "game.tcss").read_text()

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

        self._board: ChessBoard | None = None
        self._move_input: Input | None = None
        self._side_panel: GameSidePanel | None = None
        self._controls: GameControls | None = None
        self._promotion_picker: PromotionPicker | None = None

        self._pending_move_text: str | None = None
        self._input_update_queued = False

    def compose(self) -> ComposeResult:
        yield Static(
            "CLI Chess - press 't' to cycle themes - Esc to go back",
            id="topbar",
            markup=False,
        )

        with Vertical(id="game-root"):
            with Horizontal(id="main"):
                with Vertical(id="left", classes="frame"):
                    yield Static("Board", classes="frame_title", markup=False)
                    yield ChessBoard(orientation=self.config.player_side, id="board")
                    yield PromotionPicker(id="promotion-row")

                with Vertical(id="right"):
                    yield GameSidePanel(id="side-panel")
                    with Vertical(id="actions-panel", classes="frame panel"):
                        yield Static("Actions", classes="frame_title", markup=False)
                        yield GameControls(id="controls")

            with Horizontal(id="bottombar"):
                yield Input(
                    placeholder="Enter move (e2e4 / Nf3) ...",
                    id="move-input",
                )
                yield Static(
                    "Keys: Ctrl+R restart - Ctrl+U undo turn",
                    id="hint",
                    markup=False,
                )

        yield Footer()

    def on_mount(self) -> None:
        self._board = self.query_one("#board", ChessBoard)
        self._move_input = self.query_one("#move-input", Input)
        self._side_panel = self.query_one("#side-panel", GameSidePanel)
        self._controls = self.query_one("#controls", GameControls)
        self._promotion_picker = self.query_one("#promotion-row", PromotionPicker)

        self._refresh_view()
        self._move_input.focus()

        # Keep clocks/bot state fresh without forcing a full repaint every frame.
        # This is intentionally slower than the old 0.5s full refresh because the
        # styled board is widget-heavy and Textual hover/input events already repaint.
        self.set_interval(1.0, self._periodic_refresh)

    def _periodic_refresh(self) -> None:
        if self._pending_move_text is not None:
            return
        self._refresh_view()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "move-input" or self._syncing_input:
            return

        self._pending_move_text = event.value
        if not self._input_update_queued:
            self._input_update_queued = True
            self.set_timer(0.04, self._flush_pending_input)

    def _flush_pending_input(self) -> None:
        self._input_update_queued = False
        self._apply_pending_input_now(refresh=True)

    def _apply_pending_input_now(self, *, refresh: bool = False) -> None:
        if self._pending_move_text is None:
            return

        text = self._pending_move_text
        self._pending_move_text = None
        self.controller.set_move_text(text)

        if refresh:
            self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "move-input":
            self._apply_pending_input_now(refresh=False)
            self._confirm_move()

    def on_chess_board_square_pressed(self, msg: ChessBoard.SquarePressed) -> None:
        self._apply_pending_input_now(refresh=False)
        self.controller.click_square(msg.square)
        self._refresh_view()
        self._move_input_widget().focus()

    def on_promotion_picker_piece_selected(
        self,
        msg: PromotionPicker.PieceSelected,
    ) -> None:
        self._apply_pending_input_now(refresh=False)
        self.controller.select_promotion_piece(cast(PromotionPiece, msg.piece))
        self._refresh_view()
        self._move_input_widget().focus()

    def on_game_controls_action_pressed(
        self,
        msg: GameControls.ActionPressed,
    ) -> None:
        self._apply_pending_input_now(refresh=False)
        match msg.action:
            case "confirm":
                self._confirm_move()
            case "toggle_draw_offer":
                self.offer_draw = not self.offer_draw
                self._refresh_view()
            case "accept_draw":
                self.controller.accept_draw_offer()
                self.offer_draw = False
                self._refresh_view()
            case "undo_halfmove":
                self.controller.undo("halfmove")
                self._refresh_view()
            case "undo_fullmove":
                self.controller.undo("fullmove")
                self._refresh_view()
            case "resign":
                self.controller.resign()
                self.offer_draw = False
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
        self._apply_pending_input_now(refresh=False)
        self.controller.restart_game()
        self.offer_draw = False
        self._refresh_view()

    def action_undo_fullmove(self) -> None:
        self._apply_pending_input_now(refresh=False)
        self.controller.undo("fullmove")
        self._refresh_view()

    def action_undo_halfmove(self) -> None:
        self._apply_pending_input_now(refresh=False)
        self.controller.undo("halfmove")
        self._refresh_view()

    def _confirm_move(self) -> None:
        self.controller.confirm_move(offer_draw=self.offer_draw)
        snapshot = self.controller.snapshot()

        if snapshot.feedback is None or snapshot.feedback.kind != "error":
            self.offer_draw = False

        self._refresh_view(snapshot)
        self._move_input_widget().focus()

    def _refresh_view(self, snapshot: Snapshot | None = None) -> None:
        snapshot = self.controller.snapshot() if snapshot is None else snapshot

        if self.offer_draw and (snapshot.is_game_over or not snapshot.can_offer_draw):
            self.offer_draw = False

        self._board_widget().refresh_from_snapshot(snapshot)
        self._sync_move_input(snapshot)

        self._side_panel_widget().sync(
            snapshot,
            selection=self.selection,
            config=self.config,
            offer_draw=self.offer_draw,
        )

        self._controls_widget().sync(
            snapshot,
            offer_draw=self.offer_draw,
        )

        self._promotion_picker_widget().display = snapshot.is_promotion_pending

    def _sync_move_input(self, snapshot: Snapshot) -> None:
        if self._pending_move_text is not None:
            return

        move_input = self._move_input_widget()
        move_input.disabled = snapshot.is_game_over

        if move_input.value != snapshot.move_draft.text:
            self._syncing_input = True
            move_input.value = snapshot.move_draft.text
            self._syncing_input = False

    def _board_widget(self) -> ChessBoard:
        if self._board is None:
            self._board = self.query_one("#board", ChessBoard)
        return self._board

    def _move_input_widget(self) -> Input:
        if self._move_input is None:
            self._move_input = self.query_one("#move-input", Input)
        return self._move_input

    def _side_panel_widget(self) -> GameSidePanel:
        if self._side_panel is None:
            self._side_panel = self.query_one("#side-panel", GameSidePanel)
        return self._side_panel

    def _controls_widget(self) -> GameControls:
        if self._controls is None:
            self._controls = self.query_one("#controls", GameControls)
        return self._controls

    def _promotion_picker_widget(self) -> PromotionPicker:
        if self._promotion_picker is None:
            self._promotion_picker = self.query_one("#promotion-row", PromotionPicker)
        return self._promotion_picker
