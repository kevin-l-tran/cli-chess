from typing import Literal, Protocol

from src.application.viewer_types import LocalDraftView, ViewerSessionView
from src.shared.protocol_types import Square


class LocalDraftController(Protocol):
    def sync_to_view(self, view: ViewerSessionView) -> None:
        """Refresh preview hints and mark or clear stale draft state."""
        ...

    def set_text(self, text: str) -> LocalDraftView:
        """Update typed draft locally."""
        ...

    def clear(self) -> LocalDraftView:
        """Clear local draft."""
        ...

    def click_square(self, square: Square) -> LocalDraftView:
        """Update local draft from a logical board-square click."""
        ...

    def select_promotion_piece(
        self,
        piece: Literal["Q", "R", "B", "N"],
    ) -> LocalDraftView:
        """Resolve a local promotion draft if possible."""
        ...

    def view(self) -> LocalDraftView:
        """Return current local draft view."""
        ...
