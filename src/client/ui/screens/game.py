from dataclasses import dataclass
from inspect import signature
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from textual.app import ComposeResult
from textual.containers import Horizontal, HorizontalScroll, Vertical
from textual.events import Resize
from textual.screen import Screen
from textual.widgets import Footer, Input, Static

from src.application.game_client import GameClient
from src.application.legacy.session_types import (
    ClockView,
    FeedbackView,
    MoveDraftView,
    MoveListItem,
    OutcomeView,
    ParseStatus,
    SessionConfig,
    Snapshot,
    TimedGameView,
    UndoScope,
)
from src.application.local_draft_controller import LocalDraftController
from src.application.viewer_types import (
    AuthoritativeSnapshot,
    LocalDraftView,
    ViewerSessionView,
)
from src.client.ui.models.setup_models import SetupSelection
from src.client.ui.widgets.game.chess_board import ChessBoard
from src.client.ui.widgets.game.controls import GameControls
from src.client.ui.widgets.game.game_over_panel import GameOverPanel
from src.client.ui.widgets.game.promotion_picker import PromotionPicker
from src.client.ui.widgets.game.side_panel import GameSidePanel
from src.shared.ids import RequestId
from src.shared.protocol_types import PlayerSide


PromotionPiece = Literal["Q", "R", "B", "N"]


@dataclass
class GameScreenState:
    client: GameClient
    draft: LocalDraftController
    latest_view: ViewerSessionView
    latest_draft_view: LocalDraftView
    last_event_seq: int
    offer_draw: bool = False


class GameScreen(Screen):
    BINDINGS = [
        ("ctrl+g", "back", "Back"),
        ("ctrl+r", "restart", "Restart"),
        ("ctrl+u", "undo_fullmove", "Undo turn"),
        ("ctrl+y", "undo_halfmove", "Undo move"),
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

        view = client.get_view()
        draft.sync_to_view(view)

        self.selection = selection
        self.config: SessionConfig = selection.to_session_config()
        self.state = GameScreenState(
            client=client,
            draft=draft,
            latest_view=view,
            latest_draft_view=draft.view(),
            last_event_seq=view.last_event_seq,
        )
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
                    id="move-composer", classes="frame titled-frame"
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

        self.state.client.tick()
        self._replace_view(self.state.client.get_view())
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

        if self.state.latest_view.can_submit_move:
            self.state.latest_draft_view = self.state.draft.set_text(text)

        if refresh:
            self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "move-input":
            self._apply_pending_input_now(refresh=False)
            self._confirm_move()

    def on_chess_board_square_pressed(self, msg: ChessBoard.SquarePressed) -> None:
        self._apply_pending_input_now(refresh=False)

        if not self.state.latest_view.can_submit_move:
            return

        self.state.latest_draft_view = self.state.draft.click_square(msg.square)

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

        if not self.state.latest_view.can_submit_move:
            return

        self.state.latest_draft_view = self.state.draft.select_promotion_piece(
            cast(PromotionPiece, msg.piece)
        )
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
                self.state.offer_draw = not self.state.offer_draw
                self._refresh_view()
            case "accept_draw":
                self._accept_draw_offer()
            case "undo_halfmove":
                self._request_undo("halfmove")
            case "undo_fullmove":
                self._request_undo("fullmove")
            case "resign":
                self._resign()
            case "restart":
                self._restart_game()
            case "back":
                self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_restart(self) -> None:
        self._apply_pending_input_now(refresh=False)
        self._restart_game()

    def action_undo_fullmove(self) -> None:
        self._apply_pending_input_now(refresh=False)
        self._request_undo("fullmove")

    def action_undo_halfmove(self) -> None:
        self._apply_pending_input_now(refresh=False)
        self._request_undo("halfmove")

    def _confirm_move(self) -> None:
        view = self.state.latest_view
        draft = self.state.latest_draft_view

        if not view.can_submit_move:
            return

        if draft.submit_text is None:
            return

        result = self.state.client.submit_move(
            draft.submit_text,
            request_id=_new_request_id(),
            expected_ply=view.current_ply,
            offer_draw=self.state.offer_draw,
        )

        if result.view is not None:
            self._replace_view(result.view)

        if result.ok:
            self.state.latest_draft_view = self.state.draft.clear()
            self.state.offer_draw = False

        self._refresh_view()
        self._move_input_widget().focus()

    def _accept_draw_offer(self) -> None:
        view = self.state.latest_view
        if not view.can_accept_draw:
            return

        result = self.state.client.accept_draw_offer(
            request_id=_new_request_id(),
            expected_ply=view.current_ply,
        )
        if result.view is not None:
            self._replace_view(result.view)

        self.state.offer_draw = False
        self._refresh_view()

    def _request_undo(self, scope: UndoScope) -> None:
        if not self.state.latest_view.can_request_undo:
            return

        request_undo = self.state.client.request_undo
        parameters = signature(request_undo).parameters
        if "scope" in parameters:
            result = request_undo(
                request_id=_new_request_id(),
                scope=scope,  # type: ignore
            )
        else:
            result = request_undo(request_id=_new_request_id())

        if result.view is not None:
            self._replace_view(result.view)

        self.state.offer_draw = False
        self._refresh_view()

    def _resign(self) -> None:
        if not self.state.latest_view.can_resign:
            return

        result = self.state.client.resign(request_id=_new_request_id())
        if result.view is not None:
            self._replace_view(result.view)

        self.state.offer_draw = False
        self._refresh_view()

    def _restart_game(self) -> None:
        restart_game = getattr(self.state.client, "restart_game", None)
        if restart_game is None:
            return

        view = restart_game()
        if view is None:
            view = self.state.client.get_view()

        self._replace_view(view)
        self.state.latest_draft_view = self.state.draft.clear()
        self.state.offer_draw = False
        self._refresh_view()

    def _replace_view(self, view: ViewerSessionView) -> None:
        self.state.latest_view = view
        self.state.last_event_seq = view.last_event_seq
        self.state.draft.sync_to_view(view)
        self.state.latest_draft_view = self.state.draft.view()

    def _should_auto_confirm_click(self) -> bool:
        view = self.state.latest_view
        draft = self.state.latest_draft_view
        canonical_text = draft.canonical_text

        if view.snapshot.is_game_over:
            return False

        if draft.is_promotion_pending:
            return False

        if not view.can_submit_move:
            return False

        if canonical_text is None:
            return False

        return draft.text.strip() == canonical_text.strip()

    def _refresh_view(self) -> None:
        snapshot = self._legacy_render_snapshot()

        if self.state.offer_draw and (
            snapshot.is_game_over or not snapshot.can_offer_draw
        ):
            self.state.offer_draw = False

        board = self._board_widget()
        board.set_orientation(self._board_orientation_for(snapshot))
        board.refresh_from_snapshot(snapshot)

        self._sync_move_input(snapshot)
        self._sync_move_composer(snapshot)

        self._side_panel_widget().sync(
            snapshot,
            selection=self.selection,
            config=self.config,
            offer_draw=self.state.offer_draw,
        )

        actions_panel = self._actions_panel_widget()
        actions_panel.border_title = "Game over" if snapshot.is_game_over else "Actions"

        if snapshot.is_game_over:
            self._controls_widget().display = False

            game_over_panel = self._game_over_panel_widget()
            game_over_panel.display = True
            game_over_panel.sync(snapshot, selection=self.selection)
        else:
            self._game_over_panel_widget().display = False

            controls = self._controls_widget()
            controls.display = True
            controls.sync(
                snapshot,
                offer_draw=self.state.offer_draw,
            )

        self._promotion_picker_widget().display = snapshot.is_promotion_pending

    def _legacy_render_snapshot(self) -> Snapshot:
        view = self.state.latest_view
        snapshot = view.snapshot
        draft = self.state.latest_draft_view

        return Snapshot(
            board_glyphs=snapshot.board_glyphs,
            side_to_move=snapshot.side_to_move,
            candidate_moves=draft.candidate_moves,
            last_move_from=snapshot.last_move_from,
            last_move_to=snapshot.last_move_to,
            move_list=[
                MoveListItem(ply=item.ply, notation=item.notation)
                for item in snapshot.move_list
            ],
            move_draft=MoveDraftView(
                text=draft.text,
                status=_legacy_parse_status(draft),
                canonical_text=draft.canonical_text,
            ),
            move_autocompletions=draft.autocompletions,
            promotion_prompt_position=draft.promotion_prompt_position,
            draw_offered_by=snapshot.draw_offered_by,
            check_square=snapshot.check_square,
            is_player_checked=snapshot.is_player_checked,
            is_game_over=snapshot.is_game_over,
            can_confirm_move=_can_confirm_move(view, draft),
            can_offer_draw=view.can_offer_draw,
            can_undo_fullmove=view.can_request_undo,
            can_undo_halfmove=view.can_request_undo,
            can_resign=view.can_resign,
            is_promotion_pending=draft.is_promotion_pending,
            timed_game=_legacy_timed_game(snapshot),
            outcome=_legacy_outcome(snapshot),
            feedback=_legacy_feedback(snapshot),
        )

    def _sync_move_input(self, snapshot: Snapshot) -> None:
        if self._pending_move_text is not None:
            return

        move_input = self._move_input_widget()
        move_input.disabled = not self.state.latest_view.can_submit_move

        if move_input.value != snapshot.move_draft.text:
            self._syncing_input = True
            move_input.value = snapshot.move_draft.text
            self._syncing_input = False

    def _sync_move_composer(self, snapshot: Snapshot) -> None:
        draft = snapshot.move_draft
        canonical = f" -> {draft.canonical_text}" if draft.canonical_text else ""
        text = draft.text.strip() or "-"
        self._update_text(
            "draft-status",
            self._draft_status_widget(),
            f"Text: {text}    Status: {draft.status}{canonical}",
        )

        completions = ", ".join(snapshot.move_autocompletions[:8])
        self._update_text(
            "autocomplete",
            self._autocomplete_widget(),
            f"Completions: {completions or '-'}",
        )

        feedback = self._feedback_widget()
        for css_class in ("error", "action", "info"):
            feedback.remove_class(css_class)

        if self.state.latest_view.status_text is not None:
            feedback_text = f"info: {self.state.latest_view.status_text}"
            feedback.add_class("info")
        elif snapshot.feedback is None:
            feedback_text = ""
        else:
            feedback_text = f"{snapshot.feedback.kind}: {snapshot.feedback.text}"
            feedback.add_class(snapshot.feedback.kind)

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

    def _board_orientation_for(self, snapshot: Snapshot) -> PlayerSide:
        if self.config.opponent == "local" and snapshot.side_to_move is not None:
            return snapshot.side_to_move

        return self.config.player_side

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


def _new_request_id() -> RequestId:
    return RequestId(str(uuid4()))


def _can_confirm_move(view: ViewerSessionView, draft: LocalDraftView) -> bool:
    if not view.can_submit_move:
        return False
    if draft.submit_text is None:
        return False
    return draft.status not in {"empty", "no_match", "ambiguous", "stale"}


def _legacy_parse_status(draft: LocalDraftView) -> ParseStatus:
    if draft.status in {"empty", "no_match", "ambiguous", "resolved"}:
        return cast(ParseStatus, draft.status)
    if not draft.text.strip():
        return "empty"
    return "no_match"


def _legacy_timed_game(snapshot: AuthoritativeSnapshot) -> TimedGameView | None:
    timed_game = snapshot.timed_game
    if timed_game is None:
        return None

    return TimedGameView(
        white=ClockView(
            remaining_ms=timed_game.white.remaining_ms,
            display_text=timed_game.white.display_text,
            is_active=timed_game.white.is_active,
            is_flagged=timed_game.white.is_flagged,
        ),
        black=ClockView(
            remaining_ms=timed_game.black.remaining_ms,
            display_text=timed_game.black.display_text,
            is_active=timed_game.black.is_active,
            is_flagged=timed_game.black.is_flagged,
        ),
        active_side=timed_game.active_side,
        timeout_side=timed_game.timeout_side,
        increment_seconds=timed_game.increment_seconds,
    )


def _legacy_outcome(snapshot: AuthoritativeSnapshot) -> OutcomeView | None:
    outcome = snapshot.outcome
    if outcome is None:
        return None

    return OutcomeView(
        winner=outcome.winner,
        reason=outcome.reason,
        banner=outcome.banner,
    )


def _legacy_feedback(snapshot: AuthoritativeSnapshot) -> FeedbackView | None:
    feedback = snapshot.feedback
    if feedback is None:
        return None

    if feedback.kind not in {"error", "action"}:
        return FeedbackView(kind="action", text=feedback.text)

    assert feedback.kind == "error" or feedback.kind == "action"
    return FeedbackView(
        kind=feedback.kind,
        text=feedback.text,
    )
