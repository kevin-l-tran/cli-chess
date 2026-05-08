from dataclasses import dataclass
from typing import cast

from src.application.command_types import CommandResult, GameEvent
from src.application.legacy.session import GameSession
from src.application.legacy.session_types import (
    DrawActionStatus,
    MoveAttemptStatus,
    ResignStatus,
    UndoScope,
    UndoStatus,
)
from src.application.viewer_types import ViewerSessionView
from src.shared.ids import LobbyId, PlayerId, RequestId
from src.shared.protocol_types import CommandStatus

from .view_translation import (
    current_ply_from_snapshot,
    viewer_view_from_legacy_snapshot,
)


@dataclass
class LegacyGameSessionClient:
    session: GameSession
    lobby_id: LobbyId = LobbyId("legacy-local")
    viewer_id: PlayerId = PlayerId("local-controller")

    def get_view(self) -> ViewerSessionView:
        return viewer_view_from_legacy_snapshot(
            self.session.snapshot(),
            lobby_id=self.lobby_id,
            viewer_id=self.viewer_id,
        )

    def submit_move(
        self,
        move_text: str,
        request_id: RequestId,
        expected_ply: int,
        offer_draw: bool = False,
    ) -> CommandResult:
        del request_id

        before = self.session.snapshot()
        if expected_ply != current_ply_from_snapshot(before):
            view = self.get_view()
            return CommandResult(
                ok=False,
                status=cast(CommandStatus, "stale_position"),
                message="Position changed.",
                event_seq=view.last_event_seq,
                view=view,
            )

        # The legacy session confirms only its own stored draft, so the adapter
        # copies the submitted text into that draft before confirming.
        self.session.set_move_text(move_text)
        legacy_result = self.session.confirm_move_draft(offer_draw=offer_draw)

        view = self.get_view()
        return CommandResult(
            ok=legacy_result.ok,
            status=_move_status_to_command_status(legacy_result.status),
            message=_message_from_view(view),
            event_seq=view.last_event_seq,
            view=view,
        )

    def accept_draw_offer(
        self,
        request_id: RequestId,
        expected_ply: int,
    ) -> CommandResult:
        del request_id

        before = self.session.snapshot()
        if expected_ply != current_ply_from_snapshot(before):
            view = self.get_view()
            return CommandResult(
                ok=False,
                status=cast(CommandStatus, "stale_position"),
                message="Position changed.",
                event_seq=view.last_event_seq,
                view=view,
            )

        legacy_result = self.session.accept_draw_offer()
        view = self.get_view()

        return CommandResult(
            ok=legacy_result.ok,
            status=_draw_status_to_command_status(legacy_result.status),
            message=_message_from_view(view),
            event_seq=view.last_event_seq,
            view=view,
        )

    def resign(
        self,
        request_id: RequestId,
    ) -> CommandResult:
        del request_id

        legacy_result = self.session.resign()
        view = self.get_view()

        return CommandResult(
            ok=legacy_result.ok,
            status=_resign_status_to_command_status(legacy_result.status),
            message=_message_from_view(view),
            event_seq=view.last_event_seq,
            view=view,
        )

    def request_undo(
        self,
        request_id: RequestId,
        scope: UndoScope | None = None,
    ) -> CommandResult:
        del request_id

        legacy_result = self.session.undo(scope)
        view = self.get_view()

        return CommandResult(
            ok=legacy_result.ok,
            status=_undo_status_to_command_status(legacy_result.status),
            message=_message_from_view(view),
            event_seq=view.last_event_seq,
            view=view,
        )

    def events_since(self, last_seen_seq: int) -> list[GameEvent]:
        del last_seen_seq
        return []

    def tick(self) -> None:
        # Snapshot syncs clocks in the legacy session.
        self.session.snapshot()

    # Transitional convenience. Do not add this to the GameClient protocol.
    def restart_game(self) -> ViewerSessionView:
        self.session.restart_game()
        return self.get_view()


def _message_from_view(view: ViewerSessionView) -> str | None:
    feedback = view.snapshot.feedback
    if feedback is None:
        return None
    return feedback.text


def _move_status_to_command_status(status: MoveAttemptStatus) -> CommandStatus:
    mapping: dict[MoveAttemptStatus, str] = {
        "applied": "accepted",
        "empty": "invalid_move",
        "no_match": "invalid_move",
        "ambiguous": "ambiguous_move",
        "illegal": "invalid_move",
        "game_over": "game_over",
        "error": "error",
    }
    return cast(CommandStatus, mapping[status])


def _draw_status_to_command_status(status: DrawActionStatus) -> CommandStatus:
    mapping: dict[DrawActionStatus, str] = {
        "accepted": "accepted",
        "unavailable": "draw_unavailable",
        "game_over": "game_over",
        "error": "error",
    }
    return cast(CommandStatus, mapping[status])


def _undo_status_to_command_status(status: UndoStatus) -> CommandStatus:
    mapping: dict[UndoStatus, str] = {
        "undone": "accepted",
        "unavailable": "undo_unavailable",
        "error": "error",
    }
    return cast(CommandStatus, mapping[status])


def _resign_status_to_command_status(status: ResignStatus) -> CommandStatus:
    mapping: dict[ResignStatus, str] = {
        "resigned": "accepted",
        "game_over": "game_over",
        "error": "error",
    }
    return cast(CommandStatus, mapping[status])
