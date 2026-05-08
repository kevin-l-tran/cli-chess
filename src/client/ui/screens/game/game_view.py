from dataclasses import dataclass, field
from typing import cast

from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Static

from src.application.viewer_types import LocalDraftView, ViewerSessionView
from src.client.ui.models.setup_models import SetupSelection
from src.client.ui.screens.game.game_interactor import GameInteractor
from src.client.ui.widgets.game.chess_board import ChessBoard
from src.client.ui.widgets.game.controls import GameControls
from src.client.ui.widgets.game.game_over_panel import GameOverPanel
from src.client.ui.widgets.game.promotion_picker import PromotionPicker
from src.client.ui.widgets.game.side_panel import GameSidePanel
from src.shared.protocol_types import PlayerSide


@dataclass
class GameScreenView:
    screen: Screen
    selection: SetupSelection
    player_side: PlayerSide
    interactor: GameInteractor

    board: ChessBoard | None = None
    move_input: Input | None = None
    side_panel: GameSidePanel | None = None
    actions_panel: Vertical | None = None
    game_over_panel: GameOverPanel | None = None
    controls: GameControls | None = None
    promotion_picker: PromotionPicker | None = None
    draft_status: Static | None = None
    autocomplete: Static | None = None
    feedback: Static | None = None

    text_cache: dict[str, str] = field(default_factory=dict)
    syncing_input: bool = False

    def bind_widgets(self) -> None:
        self.board = self.screen.query_one("#board", ChessBoard)
        self.move_input = self.screen.query_one("#move-input", Input)
        self.side_panel = self.screen.query_one("#side-panel", GameSidePanel)
        self.actions_panel = self.screen.query_one("#actions-panel", Vertical)
        self.game_over_panel = self.screen.query_one(
            "#game-over-panel",
            GameOverPanel,
        )
        self.controls = self.screen.query_one("#controls", GameControls)
        self.promotion_picker = self.screen.query_one(
            "#promotion-row",
            PromotionPicker,
        )
        self.draft_status = self.screen.query_one("#draft-status", Static)
        self.autocomplete = self.screen.query_one("#autocomplete", Static)
        self.feedback = self.screen.query_one("#feedback", Static)

    def sync_all(self, *, pending_move_text: str | None) -> None:
        self.interactor.clear_invalid_offer_draw_state()

        view = self.interactor.latest_view
        snapshot = view.snapshot
        draft = self.interactor.latest_draft_view
        orientation = self.board_orientation_for(view)

        board = self.board_widget()
        board.set_orientation(orientation)
        board.refresh_from_view(snapshot=snapshot, draft=draft)

        self.sync_move_input(view, draft, pending_move_text=pending_move_text)
        self.sync_move_composer(view, draft)

        self.side_panel_widget().sync(
            view=view,
            selection=self.selection,
            player_side=orientation,
            offer_draw=self.interactor.offer_draw,
        )

        actions_panel = self.actions_panel_widget()
        actions_panel.border_title = "Game over" if snapshot.is_game_over else "Actions"

        if snapshot.is_game_over:
            self.controls_widget().display = False

            game_over_panel = self.game_over_panel_widget()
            game_over_panel.display = True
            game_over_panel.sync(view=view, selection=self.selection)
        else:
            self.game_over_panel_widget().display = False

            controls = self.controls_widget()
            controls.display = True
            controls.sync(
                view=view,
                draft=draft,
                offer_draw=self.interactor.offer_draw,
            )

        self.promotion_picker_widget().display = (
            draft.promotion_prompt_position is not None
        )

    def sync_responsive_classes(self) -> None:
        self.screen.set_class(self.screen.size.height < 44, "short")
        self.screen.set_class(self.screen.size.width < 118, "narrow")

    def focus_move_input(self) -> None:
        self.move_input_widget().focus()

    def sync_move_input(
        self,
        view: ViewerSessionView,
        draft: LocalDraftView,
        *,
        pending_move_text: str | None,
    ) -> None:
        if pending_move_text is not None:
            return

        move_input = self.move_input_widget()
        move_input.disabled = view.can_submit_for_side is None

        if move_input.value != draft.text:
            self.syncing_input = True
            move_input.value = draft.text
            self.syncing_input = False

    def sync_move_composer(
        self,
        view: ViewerSessionView,
        draft: LocalDraftView,
    ) -> None:
        canonical = f" -> {draft.canonical_text}" if draft.canonical_text else ""
        text = draft.text.strip() or "-"
        self.update_text(
            "draft-status",
            self.draft_status_widget(),
            f"Text: {text}    Status: {draft.status}{canonical}",
        )

        completions = ", ".join(draft.autocompletions[:8])
        self.update_text(
            "autocomplete",
            self.autocomplete_widget(),
            f"Completions: {completions or '-'}",
        )

        feedback = self.feedback_widget()
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

        self.update_text("feedback", feedback, feedback_text)

    def update_text(self, cache_key: str, widget: Static, text: str) -> None:
        if self.text_cache.get(cache_key) == text:
            return
        self.text_cache[cache_key] = text
        widget.update(text)

    def board_orientation_for(self, view: ViewerSessionView) -> PlayerSide:
        if (
            self.selection.opponent == "local"
            and view.snapshot.side_to_move is not None
        ):
            return view.snapshot.side_to_move

        return view.viewer_side or cast(PlayerSide, self.player_side)

    def board_widget(self) -> ChessBoard:
        if self.board is None:
            self.board = self.screen.query_one("#board", ChessBoard)
        return self.board

    def move_input_widget(self) -> Input:
        if self.move_input is None:
            self.move_input = self.screen.query_one("#move-input", Input)
        return self.move_input

    def side_panel_widget(self) -> GameSidePanel:
        if self.side_panel is None:
            self.side_panel = self.screen.query_one("#side-panel", GameSidePanel)
        return self.side_panel

    def actions_panel_widget(self) -> Vertical:
        if self.actions_panel is None:
            self.actions_panel = self.screen.query_one("#actions-panel", Vertical)
        return self.actions_panel

    def game_over_panel_widget(self) -> GameOverPanel:
        if self.game_over_panel is None:
            self.game_over_panel = self.screen.query_one(
                "#game-over-panel",
                GameOverPanel,
            )
        return self.game_over_panel

    def controls_widget(self) -> GameControls:
        if self.controls is None:
            self.controls = self.screen.query_one("#controls", GameControls)
        return self.controls

    def promotion_picker_widget(self) -> PromotionPicker:
        if self.promotion_picker is None:
            self.promotion_picker = self.screen.query_one(
                "#promotion-row",
                PromotionPicker,
            )
        return self.promotion_picker

    def draft_status_widget(self) -> Static:
        if self.draft_status is None:
            self.draft_status = self.screen.query_one("#draft-status", Static)
        return self.draft_status

    def autocomplete_widget(self) -> Static:
        if self.autocomplete is None:
            self.autocomplete = self.screen.query_one("#autocomplete", Static)
        return self.autocomplete

    def feedback_widget(self) -> Static:
        if self.feedback is None:
            self.feedback = self.screen.query_one("#feedback", Static)
        return self.feedback
