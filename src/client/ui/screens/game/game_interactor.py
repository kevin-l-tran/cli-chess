from dataclasses import dataclass

from src.application.command_types import CommandResult
from src.application.game_client import GameClient
from src.application.local_draft_controller import LocalDraftController
from src.application.viewer_types import LocalDraftView, ViewerSessionView
from src.shared.ids import RequestId
from src.shared.protocol_types import PromotionPiece, Square


@dataclass
class GameInteractor:
    client: GameClient
    draft: LocalDraftController
    latest_view: ViewerSessionView
    latest_draft_view: LocalDraftView
    offer_draw: bool = False

    @classmethod
    def create(
        cls,
        *,
        client: GameClient,
        draft: LocalDraftController,
    ) -> "GameInteractor":
        view = client.get_view()
        draft.sync_to_view(view)
        return cls(
            client=client,
            draft=draft,
            latest_view=view,
            latest_draft_view=draft.view(),
        )

    def refresh_from_client(self) -> None:
        self.replace_view(self.client.get_view())

    def apply_text(self, text: str) -> None:
        if self.latest_view.can_submit_for_side is None:
            return
        self.latest_draft_view = self.draft.set_text(text)

    def click_square(self, square: Square) -> bool:
        """Return True when the UI should auto-confirm after this click."""
        if self.latest_view.can_submit_for_side is None:
            return False

        self.latest_draft_view = self.draft.click_square(square)
        return self.should_auto_confirm_click()

    def select_promotion_piece(self, piece: PromotionPiece) -> None:
        if self.latest_view.can_submit_for_side is None:
            return

        self.latest_draft_view = self.draft.select_promotion_piece(piece)

    def toggle_draw_offer(self) -> None:
        self.offer_draw = not self.offer_draw

    def clear_invalid_offer_draw_state(self) -> None:
        snapshot = self.latest_view.snapshot
        if self.offer_draw and (
            snapshot.is_game_over or not self.latest_view.can_offer_draw
        ):
            self.offer_draw = False

    def confirm_move(self, *, request_id: RequestId) -> CommandResult | None:
        view = self.latest_view
        draft = self.latest_draft_view

        if view.can_submit_for_side is None:
            return None
        if draft.submit_text is None:
            return None

        result = self.client.submit_move(
            draft.submit_text,
            request_id=request_id,
            expected_ply=view.current_ply,
            offer_draw=self.offer_draw,
        )

        if result.view is not None:
            self.replace_view(result.view)

        if result.ok:
            self.latest_draft_view = self.draft.clear()
            self.offer_draw = False

        return result

    def accept_draw_offer(self, *, request_id: RequestId) -> CommandResult | None:
        view = self.latest_view
        if not view.can_accept_draw:
            return None

        result = self.client.accept_draw_offer(
            request_id=request_id,
            expected_ply=view.current_ply,
        )
        if result.view is not None:
            self.replace_view(result.view)

        self.offer_draw = False
        return result

    def request_undo(self, *, request_id: RequestId) -> CommandResult | None:
        if not self.latest_view.can_request_undo:
            return None

        result = self.client.request_undo(request_id=request_id)
        if result.view is not None:
            self.replace_view(result.view)

        self.offer_draw = False
        return result

    def resign(self, *, request_id: RequestId) -> CommandResult | None:
        if not self.latest_view.can_resign:
            return None

        result = self.client.resign(request_id=request_id)
        if result.view is not None:
            self.replace_view(result.view)

        self.offer_draw = False
        return result

    def replace_view(self, view: ViewerSessionView) -> None:
        self.latest_view = view
        self.draft.sync_to_view(view)
        self.latest_draft_view = self.draft.view()

    def should_auto_confirm_click(self) -> bool:
        view = self.latest_view
        draft = self.latest_draft_view
        canonical_text = draft.canonical_text

        if view.snapshot.is_game_over:
            return False
        if draft.promotion_prompt_position is not None:
            return False
        if view.can_submit_for_side is None:
            return False
        if canonical_text is None:
            return False

        return draft.text.strip() == canonical_text.strip()
