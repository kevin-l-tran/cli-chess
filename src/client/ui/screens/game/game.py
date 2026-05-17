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

        self._client = client
        self._draft = draft
        self.interactor: GameInteractor | None = None
        self._screen_view: GameScreenView | None = None

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
        if self._screen_view is None:
            return False
        return self._screen_view.syncing_input

    @_syncing_input.setter
    def _syncing_input(self, value: bool) -> None:
        self._require_screen_view().syncing_input = value

    def compose(self) -> ComposeResult:
        yield from compose_game_screen()

    async def on_mount(self) -> None:
        self.interactor = await GameInteractor.create(
            client=self._client,
            draft=self._draft,
        )
        self._screen_view = GameScreenView(
            screen=self,
            selection=self.selection,
            player_side=cast(PlayerSide, self.player_side),
            interactor=self.interactor,
        )

        self._screen_view.bind_widgets()
        self._sync_responsive_classes()
        self._refresh_view()
        self._screen_view.focus_move_input()

        self.run_worker(
            self._watch_game_updates(),
            group="game-updates",
            exclusive=True,
        )

        # Keep clocks/bot state fresh without forcing a full repaint every frame.
        self.set_interval(0.5, self._refresh_clock_projection)

    async def on_unmount(self) -> None:
        await self._client.close()

    def on_resize(self, event: Resize) -> None:
        self._sync_responsive_classes()

    def _require_interactor(self) -> GameInteractor:
        if self.interactor is None:
            raise RuntimeError("Game interactor is not ready.")
        return self.interactor

    def _require_screen_view(self) -> GameScreenView:
        if self._screen_view is None:
            raise RuntimeError("Game screen view is not ready.")
        return self._screen_view

    def _sync_responsive_classes(self) -> None:
        if self._screen_view is None:
            return
        self._screen_view.sync_responsive_classes()

    async def _watch_game_updates(self) -> None:
        interactor = self._require_interactor()

        async for view in interactor.client.view_updates():
            await interactor.apply_pushed_view(view)
            self._refresh_view()

    def _refresh_clock_projection(self) -> None:
        if self.interactor is None:
            return
        self._refresh_view()

    def on_input_changed(self, event: Input.Changed) -> None:
        if self.interactor is None:
            return
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

        self._require_interactor().apply_text(text)

        if refresh:
            self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "move-input":
            self._apply_pending_input_now(refresh=False)
            self._confirm_move()

    def on_chess_board_square_pressed(self, msg: ChessBoard.SquarePressed) -> None:
        self._apply_pending_input_now(refresh=False)

        interactor = self._require_interactor()
        if interactor.authoritative_view.can_submit_for_side is None:
            return

        interactor.click_square(msg.square)
        if self._require_interactor().should_auto_confirm_click():
            self._confirm_move()
            return

        self._refresh_view()
        self._move_input_widget().focus()

    def on_promotion_picker_piece_selected(
        self,
        msg: PromotionPicker.PieceSelected,
    ) -> None:
        self._apply_pending_input_now(refresh=False)

        interactor = self._require_interactor()
        if interactor.authoritative_view.can_submit_for_side is None:
            return

        interactor.select_promotion_piece(cast(PromotionPiece, msg.piece))
        self._refresh_view()
        self._move_input_widget().focus()

    def on_game_controls_action_pressed(
        self,
        msg: GameControls.ActionPressed,
    ) -> None:
        self._apply_pending_input_now(refresh=False)
        interactor = self._require_interactor()

        match msg.action:
            case "confirm":
                self._confirm_move()
            case "toggle_draw_offer":
                interactor.toggle_draw_offer()
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
        if self.interactor is None:
            return
        self.run_worker(self._confirm_move_async(), group="game-command")

    async def _confirm_move_async(self) -> None:
        result = await self._require_interactor().confirm_move(
            request_id=new_request_id(),
        )
        if result is None:
            return

        self._refresh_view()
        self._move_input_widget().focus()

    def _accept_draw_offer(self) -> None:
        if self.interactor is None:
            return
        self.run_worker(self._accept_draw_offer_async(), group="game-command")

    async def _accept_draw_offer_async(self) -> None:
        result = await self._require_interactor().accept_draw_offer(
            request_id=new_request_id(),
        )
        if result is None:
            return

        self._refresh_view()

    def _request_undo(self) -> None:
        if self.interactor is None:
            return
        self.run_worker(self._request_undo_async(), group="game-command")

    async def _request_undo_async(self) -> None:
        result = await self._require_interactor().request_undo(
            request_id=new_request_id(),
        )
        if result is None:
            return

        self._refresh_view()

    def _resign(self) -> None:
        if self.interactor is None:
            return
        self.run_worker(self._resign_async(), group="game-command")

    async def _resign_async(self) -> None:
        result = await self._require_interactor().resign(
            request_id=new_request_id(),
        )
        if result is None:
            return

        self._refresh_view()

    def _refresh_view(self) -> None:
        self._require_screen_view().sync_all(pending_move_text=self._pending_move_text)

    def _sync_move_input(self, view: ViewerSessionView, draft: LocalDraftView) -> None:
        self._require_screen_view().sync_move_input(
            view,
            draft,
            pending_move_text=self._pending_move_text,
        )

    def _sync_move_composer(
        self,
        view: ViewerSessionView,
        draft: LocalDraftView,
    ) -> None:
        self._require_screen_view().sync_move_composer(view, draft)

    def _update_text(self, cache_key: str, widget: Static, text: str) -> None:
        self._require_screen_view().update_text(cache_key, widget, text)

    def _board_widget(self) -> ChessBoard:
        return self._require_screen_view().board_widget()

    def _board_orientation_for(self, view: ViewerSessionView) -> PlayerSide:
        return self._require_screen_view().board_orientation_for(view)

    def _move_input_widget(self) -> Input:
        return self._require_screen_view().move_input_widget()

    def _side_panel_widget(self) -> GameSidePanel:
        return self._require_screen_view().side_panel_widget()

    def _actions_panel_widget(self) -> Vertical:
        return self._require_screen_view().actions_panel_widget()

    def _game_over_panel_widget(self) -> GameOverPanel:
        return self._require_screen_view().game_over_panel_widget()

    def _controls_widget(self) -> GameControls:
        return self._require_screen_view().controls_widget()

    def _promotion_picker_widget(self) -> PromotionPicker:
        return self._require_screen_view().promotion_picker_widget()

    def _draft_status_widget(self) -> Static:
        return self._require_screen_view().draft_status_widget()

    def _autocomplete_widget(self) -> Static:
        return self._require_screen_view().autocomplete_widget()

    def _feedback_widget(self) -> Static:
        return self._require_screen_view().feedback_widget()
