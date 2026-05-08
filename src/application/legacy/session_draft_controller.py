from dataclasses import dataclass
from typing import cast

from src.application.legacy.session import GameSession
from src.application.viewer_types import LocalDraftView, ViewerSessionView
from src.shared.protocol_types import PromotionPiece, Square

from .view_translation import local_draft_from_legacy_snapshot


@dataclass
class LegacySessionDraftController:
    session: GameSession
    _last_synced_ply: int | None = None

    def sync_to_view(self, view: ViewerSessionView) -> None:
        # In the legacy bridge, draft state lives inside GameSession. If the
        # committed position changes outside the draft path, discard stale text.
        if (
            self._last_synced_ply is not None
            and self._last_synced_ply != view.current_ply
        ):
            self.session.clear_move_text()

        self._last_synced_ply = view.current_ply

    def set_text(self, text: str) -> LocalDraftView:
        self.session.set_move_text(text)
        return self.view()

    def clear(self) -> LocalDraftView:
        self.session.clear_move_text()
        return self.view()

    def click_square(self, square: Square) -> LocalDraftView:
        self.session.click_square(square)
        return self.view()

    def select_promotion_piece(
        self,
        piece: PromotionPiece,
    ) -> LocalDraftView:
        self.session.select_promotion_piece(cast(PromotionPiece, piece))
        return self.view()

    def view(self) -> LocalDraftView:
        return local_draft_from_legacy_snapshot(self.session.snapshot())
