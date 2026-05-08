from pathlib import Path
from typing import cast

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.events import Resize
from textual.screen import Screen
from textual.widgets import Input, Static

from src.application.game_client import GameClient
from src.application.local_draft_controller import LocalDraftController
from src.application.viewer_types import LocalDraftView, ViewerSessionView
from src.client.ui.models.setup_models import SetupSelection
from src.client.ui.screens.game.debounced_input import DebouncedTextInput
from src.client.ui.screens.game.game_interactor import GameInteractor
from src.client.ui.screens.game.game_layout import compose_game_screen
from src.client.ui.screens.game.game_view import GameScreenView
from src.client.ui.widgets.game.chess_board import ChessBoard
from src.client.ui.widgets.game.controls import GameControls
from src.client.ui.widgets.game.game_over_panel import GameOverPanel
from src.client.ui.widgets.game.promotion_picker import PromotionPicker
from src.client.ui.widgets.game.side_panel import GameSidePanel
from src.shared.ids import new_request_id
from src.shared.protocol_types import PlayerSide, PromotionPiece


class GameScreen(Screen):
    BINDINGS = [
        ("ctrl+g", "back", "Back"),
        ("ctrl+u", "undo", "Undo"),
    ]

    DEFAULT_CSS = (Path(__file__).parent.parent / "css" / "game.tcss").read_text()

    def __init__(
        self,
        *,
        client: GameClient,
        draft: LocalDraftController,
        selection: SetupSelection,
    ) -> None:
        super().__init__()

        self.selection = selection
        self.player_side = selection.require_player_side()

        self.interactor = GameInteractor.create(client=client, draft=draft)

        self._screen_view = GameScreenView(
            screen=self,
            selection=selection,
            player_side=self.player_side,
            interactor=self.interactor,
        )
        self._input_buffer = DebouncedTextInput(delay_seconds=0.04)

    @property
    def _pending_move_text(self) -> str | None:
        return self._input_buffer.pending_text

    @_pending_move_text.setter
    def _pending_move_text(self, value: str | None) -> None:
        self._input_buffer.pending_text = value

    @property
    def _input_update_queued(self) -> bool:
        return self._input_buffer.update_queued

    @_input_update_queued.setter
    def _input_update_queued(self, value: bool) -> None:
        self._input_buffer.update_queued = value

    @property
    def _syncing_input(self) -> bool:
        return self._screen_view.syncing_input

    @_syncing_input.setter
    def _syncing_input(self, value: bool) -> None:
        self._screen_view.syncing_input = value

    def compose(self) -> ComposeResult:
        yield from compose_game_screen()

    def on_mount(self) -> None:
        self._screen_view.bind_widgets()
        self._sync_responsive_classes()
        self._refresh_view()
        self._screen_view.focus_move_input()

        # Keep clocks/bot state fresh without forcing a full repaint every frame.
        # This is intentionally slower than the old 0.5s full refresh because the
        # styled board is widget-heavy and Textual hover/input events already repaint.
        self.set_interval(1.0, self._periodic_refresh)

    def on_resize(self, event: Resize) -> None:
        self._sync_responsive_classes()

    def _sync_responsive_classes(self) -> None:
        self._screen_view.sync_responsive_classes()

    def _periodic_refresh(self) -> None:
        if self._input_buffer.has_pending():
            return

        self.interactor.refresh_from_client()
        self._refresh_view()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "move-input" or self._syncing_input:
            return

        should_arm_timer = self._input_buffer.schedule(event.value)
        if should_arm_timer:
            self.set_timer(self._input_buffer.delay_seconds, self._flush_pending_input)

    def _flush_pending_input(self) -> None:
        self._apply_pending_input_now(refresh=True)

    def _apply_pending_input_now(self, *, refresh: bool = False) -> None:
        text = self._input_buffer.pop_pending()
        if text is None:
            return

        self.interactor.apply_text(text)

        if refresh:
            self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "move-input":
            self._apply_pending_input_now(refresh=False)
            self._confirm_move()

    def on_chess_board_square_pressed(self, msg: ChessBoard.SquarePressed) -> None:
        self._apply_pending_input_now(refresh=False)

        if self.interactor.latest_view.can_submit_for_side is None:
            return

        self.interactor.click_square(msg.square)
        if self._should_auto_confirm_click():
            self._confirm_move()
            return

        self._refresh_view()
        self._move_input_widget().focus()

    def on_promotion_picker_piece_selected(
        self,
        msg: PromotionPicker.PieceSelected,
    ) -> None:
        self._apply_pending_input_now(refresh=False)

        if self.interactor.latest_view.can_submit_for_side is None:
            return

        self.interactor.select_promotion_piece(cast(PromotionPiece, msg.piece))
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
                self.interactor.toggle_draw_offer()
                self._refresh_view()
            case "accept_draw":
                self._accept_draw_offer()
            case "request_undo":
                self._request_undo()
            case "resign":
                self._resign()
            case "back":
                self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_undo(self) -> None:
        self._apply_pending_input_now(refresh=False)
        self._request_undo()

    def _confirm_move(self) -> None:
        result = self.interactor.confirm_move(request_id=new_request_id())
        if result is None:
            return

        self._refresh_view()
        self._move_input_widget().focus()

    def _accept_draw_offer(self) -> None:
        result = self.interactor.accept_draw_offer(request_id=new_request_id())
        if result is None:
            return

        self._refresh_view()

    def _request_undo(self) -> None:
        result = self.interactor.request_undo(request_id=new_request_id())
        if result is None:
            return

        self._refresh_view()

    def _resign(self) -> None:
        result = self.interactor.resign(request_id=new_request_id())
        if result is None:
            return

        self._refresh_view()

    def _replace_view(self, view: ViewerSessionView) -> None:
        # Compatibility method for tests/callers that still patch or invoke this
        # private method. New code should prefer interactor.replace_view().
        self.interactor.replace_view(view)

    def _should_auto_confirm_click(self) -> bool:
        # Compatibility method for tests/callers that still patch or invoke this
        # private method. New code should prefer interactor.should_auto_confirm_click().
        return self.interactor.should_auto_confirm_click()

    def _refresh_view(self) -> None:
        self._screen_view.sync_all(pending_move_text=self._pending_move_text)

    def _sync_move_input(self, view: ViewerSessionView, draft: LocalDraftView) -> None:
        self._screen_view.sync_move_input(
            view,
            draft,
            pending_move_text=self._pending_move_text,
        )

    def _sync_move_composer(
        self,
        view: ViewerSessionView,
        draft: LocalDraftView,
    ) -> None:
        self._screen_view.sync_move_composer(view, draft)

    def _update_text(self, cache_key: str, widget: Static, text: str) -> None:
        self._screen_view.update_text(cache_key, widget, text)

    def _board_widget(self) -> ChessBoard:
        return self._screen_view.board_widget()

    def _board_orientation_for(self, view: ViewerSessionView) -> PlayerSide:
        return self._screen_view.board_orientation_for(view)

    def _move_input_widget(self) -> Input:
        return self._screen_view.move_input_widget()

    def _side_panel_widget(self) -> GameSidePanel:
        return self._screen_view.side_panel_widget()

    def _actions_panel_widget(self) -> Vertical:
        return self._screen_view.actions_panel_widget()

    def _game_over_panel_widget(self) -> GameOverPanel:
        return self._screen_view.game_over_panel_widget()

    def _controls_widget(self) -> GameControls:
        return self._screen_view.controls_widget()

    def _promotion_picker_widget(self) -> PromotionPicker:
        return self._screen_view.promotion_picker_widget()

    def _draft_status_widget(self) -> Static:
        return self._screen_view.draft_status_widget()

    def _autocomplete_widget(self) -> Static:
        return self._screen_view.autocomplete_widget()

    def _feedback_widget(self) -> Static:
        return self._screen_view.feedback_widget()
