from pathlib import Path
from typing import cast

from textual.app import ComposeResult
from textual.containers import Horizontal, HorizontalScroll, Vertical
from textual.events import Resize
from textual.screen import Screen
from textual.widgets import Footer, Input, Static

from src.application.game_client import GameClient
from src.application.local_draft_controller import LocalDraftController
from src.application.viewer_types import LocalDraftView, ViewerSessionView
from src.client.ui.models.setup_models import SetupSelection
from src.client.ui.screens.game_interactor import GameInteractor, PromotionPiece
from src.client.ui.widgets.game.chess_board import ChessBoard
from src.client.ui.widgets.game.controls import GameControls
from src.client.ui.widgets.game.game_over_panel import GameOverPanel
from src.client.ui.widgets.game.promotion_picker import PromotionPicker
from src.client.ui.widgets.game.side_panel import GameSidePanel
from src.shared.ids import new_request_id
from src.shared.protocol_types import PlayerSide


class GameScreen(Screen):
    BINDINGS = [
        ("ctrl+g", "back", "Back"),
        ("ctrl+u", "undo", "Undo"),
    ]

    DEFAULT_CSS = (Path(__file__).parent / "css" / "game.tcss").read_text()

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

        self._syncing_input = False

        self._board: ChessBoard | None = None
        self._move_input: Input | None = None
        self._side_panel: GameSidePanel | None = None
        self._actions_panel: Vertical | None = None
        self._game_over_panel: GameOverPanel | None = None
        self._controls: GameControls | None = None
        self._promotion_picker: PromotionPicker | None = None
        self._draft_status: Static | None = None
        self._autocomplete: Static | None = None
        self._feedback: Static | None = None

        self._pending_move_text: str | None = None
        self._input_update_queued = False
        self._text_cache: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Static(
            "CLI Chess",
            id="topbar",
            markup=False,
        )

        with HorizontalScroll(id="game-scroll"):
            with Vertical(id="game-root"):
                with Horizontal(id="main"):
                    board_panel = Vertical(id="left", classes="frame titled-frame")
                    board_panel.border_title = "Board"
                    with board_panel:
                        yield ChessBoard(orientation="white", id="board")
                        yield PromotionPicker(id="promotion-row")

                    with Vertical(id="right"):
                        yield GameSidePanel(id="side-panel")

                        actions_panel = Vertical(
                            id="actions-panel",
                            classes="frame titled-frame",
                        )
                        actions_panel.border_title = "Actions"
                        self._actions_panel = actions_panel
                        with actions_panel:
                            yield GameControls(id="controls")
                            yield GameOverPanel(id="game-over-panel")

                move_composer = Vertical(
                    id="move-composer",
                    classes="frame titled-frame",
                )
                move_composer.border_title = "Move"
                with move_composer:
                    yield Input(
                        placeholder="Enter move (e2e4 / Nf3) ...",
                        id="move-input",
                    )
                    with Horizontal(id="draft-row"):
                        self._draft_status = Static(
                            "Status: empty",
                            id="draft-status",
                            classes="composer_meta",
                            markup=False,
                        )
                        yield self._draft_status
                        self._autocomplete = Static(
                            "Completions: -",
                            id="autocomplete",
                            classes="composer_meta",
                            markup=False,
                        )
                        yield self._autocomplete
                    self._feedback = Static(
                        "",
                        id="feedback",
                        classes="composer_feedback",
                        markup=False,
                    )
                    yield self._feedback

        yield Footer()

    def on_mount(self) -> None:
        self._board = self.query_one("#board", ChessBoard)
        self._move_input = self.query_one("#move-input", Input)
        self._side_panel = self.query_one("#side-panel", GameSidePanel)
        self._actions_panel = self.query_one("#actions-panel", Vertical)
        self._game_over_panel = self.query_one("#game-over-panel", GameOverPanel)
        self._controls = self.query_one("#controls", GameControls)
        self._promotion_picker = self.query_one("#promotion-row", PromotionPicker)
        self._draft_status = self.query_one("#draft-status", Static)
        self._autocomplete = self.query_one("#autocomplete", Static)
        self._feedback = self.query_one("#feedback", Static)

        self._sync_responsive_classes()
        self._refresh_view()
        self._move_input.focus()

        # Keep clocks/bot state fresh without forcing a full repaint every frame.
        # This is intentionally slower than the old 0.5s full refresh because the
        # styled board is widget-heavy and Textual hover/input events already repaint.
        self.set_interval(1.0, self._periodic_refresh)

    def on_resize(self, event: Resize) -> None:
        self._sync_responsive_classes()

    def _sync_responsive_classes(self) -> None:
        self.set_class(self.size.height < 44, "short")
        self.set_class(self.size.width < 118, "narrow")

    def _periodic_refresh(self) -> None:
        if self._pending_move_text is not None:
            return

        self.interactor.refresh_from_client()
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

        self.interactor.apply_text(text)

        if refresh:
            self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "move-input":
            self._apply_pending_input_now(refresh=False)
            self._confirm_move()

    def on_chess_board_square_pressed(self, msg: ChessBoard.SquarePressed) -> None:
        self._apply_pending_input_now(refresh=False)

        should_confirm = self.interactor.click_square(msg.square)
        if should_confirm:
            self._confirm_move()
            return

        self._refresh_view()
        self._move_input_widget().focus()

    def on_promotion_picker_piece_selected(
        self,
        msg: PromotionPicker.PieceSelected,
    ) -> None:
        self._apply_pending_input_now(refresh=False)

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
        self.interactor.confirm_move(request_id=new_request_id())
        self._refresh_view()
        self._move_input_widget().focus()

    def _accept_draw_offer(self) -> None:
        self.interactor.accept_draw_offer(request_id=new_request_id())
        self._refresh_view()

    def _request_undo(self) -> None:
        self.interactor.request_undo(request_id=new_request_id())
        self._refresh_view()

    def _resign(self) -> None:
        self.interactor.resign(request_id=new_request_id())
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
        self.interactor.clear_invalid_offer_draw_state()

        view = self.interactor.latest_view
        snapshot = view.snapshot
        draft = self.interactor.latest_draft_view

        board = self._board_widget()
        board.set_orientation(self._board_orientation_for(view))
        board.refresh_from_view(snapshot=snapshot, draft=draft)

        self._sync_move_input(view, draft)
        self._sync_move_composer(view, draft)

        self._side_panel_widget().sync(
            view=view,
            selection=self.selection,
            player_side=self._board_orientation_for(view),
            offer_draw=self.interactor.offer_draw,
        )

        actions_panel = self._actions_panel_widget()
        actions_panel.border_title = "Game over" if snapshot.is_game_over else "Actions"

        if snapshot.is_game_over:
            self._controls_widget().display = False

            game_over_panel = self._game_over_panel_widget()
            game_over_panel.display = True
            game_over_panel.sync(view=view, selection=self.selection)
        else:
            self._game_over_panel_widget().display = False

            controls = self._controls_widget()
            controls.display = True
            controls.sync(
                view=view,
                draft=draft,
                offer_draw=self.interactor.offer_draw,
            )

        self._promotion_picker_widget().display = (
            draft.promotion_prompt_position is not None
        )

    def _sync_move_input(self, view: ViewerSessionView, draft: LocalDraftView) -> None:
        if self._pending_move_text is not None:
            return

        move_input = self._move_input_widget()
        move_input.disabled = view.can_submit_for_side is None

        if move_input.value != draft.text:
            self._syncing_input = True
            move_input.value = draft.text
            self._syncing_input = False

    def _sync_move_composer(
        self,
        view: ViewerSessionView,
        draft: LocalDraftView,
    ) -> None:
        canonical = f" -> {draft.canonical_text}" if draft.canonical_text else ""
        text = draft.text.strip() or "-"
        self._update_text(
            "draft-status",
            self._draft_status_widget(),
            f"Text: {text}    Status: {draft.status}{canonical}",
        )

        completions = ", ".join(draft.autocompletions[:8])
        self._update_text(
            "autocomplete",
            self._autocomplete_widget(),
            f"Completions: {completions or '-'}",
        )

        feedback = self._feedback_widget()
        for css_class in ("error", "action", "info"):
            feedback.remove_class(css_class)

        public_feedback = view.snapshot.feedback
        if view.status_text is not None:
            feedback_text = f"info: {view.status_text}"
            feedback.add_class("info")
        elif public_feedback is None:
            feedback_text = ""
        else:
            feedback_text = f"{public_feedback.kind}: {public_feedback.text}"
            feedback.add_class(public_feedback.kind)

        self._update_text("feedback", feedback, feedback_text)

    def _update_text(self, cache_key: str, widget: Static, text: str) -> None:
        if self._text_cache.get(cache_key) == text:
            return
        self._text_cache[cache_key] = text
        widget.update(text)

    def _board_widget(self) -> ChessBoard:
        if self._board is None:
            self._board = self.query_one("#board", ChessBoard)
        return self._board

    def _board_orientation_for(self, view: ViewerSessionView) -> PlayerSide:
        if (
            self.selection.opponent == "local"
            and view.snapshot.side_to_move is not None
        ):
            return view.snapshot.side_to_move

        return view.viewer_side or cast(PlayerSide, self.player_side)

    def _move_input_widget(self) -> Input:
        if self._move_input is None:
            self._move_input = self.query_one("#move-input", Input)
        return self._move_input

    def _side_panel_widget(self) -> GameSidePanel:
        if self._side_panel is None:
            self._side_panel = self.query_one("#side-panel", GameSidePanel)
        return self._side_panel

    def _actions_panel_widget(self) -> Vertical:
        if self._actions_panel is None:
            self._actions_panel = self.query_one("#actions-panel", Vertical)
        return self._actions_panel

    def _game_over_panel_widget(self) -> GameOverPanel:
        if self._game_over_panel is None:
            self._game_over_panel = self.query_one("#game-over-panel", GameOverPanel)
        return self._game_over_panel

    def _controls_widget(self) -> GameControls:
        if self._controls is None:
            self._controls = self.query_one("#controls", GameControls)
        return self._controls

    def _promotion_picker_widget(self) -> PromotionPicker:
        if self._promotion_picker is None:
            self._promotion_picker = self.query_one("#promotion-row", PromotionPicker)
        return self._promotion_picker

    def _draft_status_widget(self) -> Static:
        if self._draft_status is None:
            self._draft_status = self.query_one("#draft-status", Static)
        return self._draft_status

    def _autocomplete_widget(self) -> Static:
        if self._autocomplete is None:
            self._autocomplete = self.query_one("#autocomplete", Static)
        return self._autocomplete

    def _feedback_widget(self) -> Static:
        if self._feedback is None:
            self._feedback = self.query_one("#feedback", Static)
        return self._feedback
