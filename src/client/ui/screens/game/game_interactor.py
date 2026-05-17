import asyncio
from dataclasses import dataclass, field

from src.application.command_types import CommandResult
from src.application.game_client import GameClient
from src.application.local_draft_controller import LocalDraftController
from src.application.viewer_types import LocalDraftView, ViewerSessionView
from src.client.ui.screens.game.clock_projector import ClientClockProjector
from src.shared.ids import RequestId
from src.shared.protocol_types import PromotionPiece, Square


@dataclass
class GameInteractor:
    """
    Coordinate UI-facing game actions across the committed client and local draft.

    The interactor keeps the latest authoritative view, the latest draft view,
    and transient command options such as whether the next move offers a draw.
    """

    client: GameClient
    draft: LocalDraftController
    authoritative_view: ViewerSessionView
    latest_draft_view: LocalDraftView
    offer_draw: bool = False
    clock_projector: ClientClockProjector = field(
        default_factory=ClientClockProjector,
        init=False,
        repr=False,
    )

    _client_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock,
        init=False,
        repr=False,
    )

    @classmethod
    async def create(
        cls,
        *,
        client: GameClient,
        draft: LocalDraftController,
    ) -> "GameInteractor":
        """
        Build an interactor from a game client and draft controller.

        The initial authoritative view is fetched from the client, then the
        draft controller is synchronized to that view before use.
        """
        view = await client.get_view()
        draft.sync_to_view(view)

        return cls(
            client=client,
            draft=draft,
            authoritative_view=view,
            latest_draft_view=draft.view(),
        )

    async def refresh_from_client(self) -> None:
        """Fetch the latest view from the client and sync the local draft."""
        view = await self.client.get_view()
        async with self._client_lock:
            self.replace_view(view)

    async def apply_pushed_view(self, view: ViewerSessionView) -> None:
        """Apply a view pushed from the view stream."""
        async with self._client_lock:
            if view.view_revision <= self.authoritative_view.view_revision:
                return
            self._apply_view(view)

    def apply_text(self, text: str) -> None:
        """
        Apply typed move text to the local draft when submission is allowed.

        This updates only draft state; no committed game command is sent.
        """
        if self.authoritative_view.can_submit_for_side is None:
            return
        self.latest_draft_view = self.draft.set_text(text)

    def click_square(self, square: Square) -> bool:
        """
        Apply a board-square click to the local draft.

        Returns True when the resulting draft is resolved and the UI should
        auto-confirm the move.
        """
        if self.authoritative_view.can_submit_for_side is None:
            return False

        self.latest_draft_view = self.draft.click_square(square)
        return self.should_auto_confirm_click()

    def select_promotion_piece(self, piece: PromotionPiece) -> None:
        """
        Resolve a pending promotion draft with the selected promotion piece.

        The selection is ignored when the current viewer cannot submit a move.
        """
        if self.authoritative_view.can_submit_for_side is None:
            return

        self.latest_draft_view = self.draft.select_promotion_piece(piece)

    def toggle_draw_offer(self) -> None:
        """Toggle whether the next submitted move should include a draw offer."""
        if not self.authoritative_view.can_offer_draw:
            self.offer_draw = False
            return

        self.offer_draw = not self.offer_draw

    def clear_invalid_offer_draw_state(self) -> None:
        """
        Clear a pending draw-offer flag when it is no longer valid.

        This prevents stale UI state from offering a draw after the game ends
        or when the latest permissions no longer allow draw offers.
        """
        snapshot = self.authoritative_view.snapshot
        if self.offer_draw and (
            snapshot.is_game_over or not self.authoritative_view.can_offer_draw
        ):
            self.offer_draw = False

    async def confirm_move(self, *, request_id: RequestId) -> CommandResult | None:
        """
        Submit the current resolved draft as an authoritative move command.

        Returns None when the viewer cannot submit or the draft has no submit
        text. On accepted results, the draft and draw-offer flag are cleared.
        """
        async with self._client_lock:
            view = self.authoritative_view
            draft = self.latest_draft_view

            if view.can_submit_for_side is None:
                return None
            if draft.submit_text is None:
                return None

            result = await self.client.submit_move(
                draft.submit_text,
                request_id=request_id,
                expected_ply=view.current_ply,
                offer_draw=self.offer_draw,
            )

            self.replace_view(result.view)

            if result.ok:
                self.latest_draft_view = self.draft.clear()
                self.offer_draw = False

            return result

    async def accept_draw_offer(self, *, request_id: RequestId) -> CommandResult | None:
        """
        Accept the currently available draw offer, if permitted.

        The returned command result may include a replacement authoritative
        view, which is applied immediately.
        """
        async with self._client_lock:
            view = self.authoritative_view
            if not view.can_accept_draw:
                return None

            result = await self.client.accept_draw_offer(
                request_id=request_id,
                expected_ply=view.current_ply,
            )
            self.replace_view(result.view)

            self.offer_draw = False
            return result

    async def request_undo(self, *, request_id: RequestId) -> CommandResult | None:
        """
        Request an undo through the authoritative game client, if permitted.

        Any returned view replaces the local authoritative view and resyncs the
        local draft controller.
        """
        async with self._client_lock:
            if not self.authoritative_view.can_request_undo:
                return None

            result = await self.client.request_undo(request_id=request_id)
            self.replace_view(result.view)

            self.offer_draw = False
            return result

    async def resign(self, *, request_id: RequestId) -> CommandResult | None:
        """
        Resign the game through the authoritative game client, if permitted.

        Any returned view replaces the local authoritative view and the pending
        draw-offer flag is cleared.
        """
        async with self._client_lock:
            if not self.authoritative_view.can_resign:
                return None

            result = await self.client.resign(request_id=request_id)
            self.replace_view(result.view)

            self.offer_draw = False
            return result

    def replace_view(self, view: ViewerSessionView) -> None:
        """
        Directly replace the latest authoritative view and resync draft state.

        Use this after command results, polling, or any other client refresh
        that returns a newer viewer-specific session view.
        """
        if view.view_revision < self.authoritative_view.view_revision:
            return
        if view.view_revision == self.authoritative_view.view_revision:
            if view == self.authoritative_view:
                return
        self._apply_view(view)

    def should_auto_confirm_click(self) -> bool:
        """
        Return whether the current click-built draft should auto-submit.

        Auto-confirm is allowed only for resolved non-promotion drafts in an
        active game where the viewer can submit for the current side.
        """
        view = self.authoritative_view
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

    def view_for_render(self) -> ViewerSessionView:
        """Returns a view with the clock locally updated."""
        return self.clock_projector.project(self.authoritative_view)

    def _apply_view(self, view: ViewerSessionView) -> None:
        self.authoritative_view = view
        self.clock_projector.reset_anchor()
        self.draft.sync_to_view(view)
        self.latest_draft_view = self.draft.view()
        self.clear_invalid_offer_draw_state()
