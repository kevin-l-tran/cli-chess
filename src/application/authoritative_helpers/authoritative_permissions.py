from dataclasses import dataclass
from typing import cast

from src.shared.ids import PlayerId
from src.shared.protocol_types import ParticipantRole, PlayerSide

from .authoritative_policy import AuthoritativeSessionPolicy
from .authoritative_session_types import AuthoritativeSessionConfig, SessionPhase


@dataclass(frozen=True)
class ViewerPermissions:
    viewer_role: ParticipantRole
    viewer_side: PlayerSide | None
    can_submit_for_side: PlayerSide | None
    can_submit_move: bool
    can_offer_draw: bool
    can_accept_draw: bool
    can_resign: bool
    can_request_undo: bool
    can_spectate: bool


class AuthoritativePermissionResolver:
    def __init__(
        self,
        *,
        config: AuthoritativeSessionConfig,
        player_sides: dict[PlayerId, PlayerSide],
    ) -> None:
        self._config = config
        self._player_sides = player_sides

    def for_viewer(
        self,
        viewer_id: PlayerId,
        *,
        phase: SessionPhase,
        move_count: int,
        draw_offered_by: PlayerSide | None,
    ) -> ViewerPermissions:
        role = self.viewer_role_for(viewer_id)
        side = self._player_sides.get(viewer_id)
        can_submit_for_side = self.submit_side_for_viewer(viewer_id, phase)
        actor_side = self.actor_side_for_command(viewer_id, phase)

        can_accept_draw = (
            actor_side is not None
            and draw_offered_by is not None
            and draw_offered_by != actor_side
            and not phase.is_game_over
        )
        can_offer_draw = (
            can_submit_for_side is not None
            and AuthoritativeSessionPolicy.can_offer_draw(
                self._config.mode,
                phase,
                draw_offered_by,
            )
        )
        can_resign = (
            can_submit_for_side is not None
            and AuthoritativeSessionPolicy.can_resign(phase)
        )
        can_request_undo = self.viewer_is_player_or_local_controller(viewer_id) and (
            AuthoritativeSessionPolicy.can_undo_halfmove(self._config.mode, move_count)
            or AuthoritativeSessionPolicy.can_undo_fullmove(self._config.mode, move_count)
        )

        return ViewerPermissions(
            viewer_role=role,
            viewer_side=side,
            can_submit_for_side=can_submit_for_side,
            can_submit_move=can_submit_for_side is not None,
            can_offer_draw=can_offer_draw,
            can_accept_draw=can_accept_draw,
            can_resign=can_resign,
            can_request_undo=can_request_undo,
            can_spectate=role == "spectator",
        )

    def viewer_role_for(self, viewer_id: PlayerId) -> ParticipantRole:
        side = self._player_sides.get(viewer_id)
        if side is not None:
            return cast(ParticipantRole, side)
        if self._config.mode == "local":
            return cast(ParticipantRole, "local_controller")
        return cast(ParticipantRole, "spectator")

    def viewer_is_player_or_local_controller(self, viewer_id: PlayerId) -> bool:
        return (
            viewer_id in self._player_sides
            or self.viewer_role_for(viewer_id) == "local_controller"
        )

    def submit_side_for_viewer(
        self,
        viewer_id: PlayerId,
        phase: SessionPhase,
    ) -> PlayerSide | None:
        if phase.kind != "active" or phase.side_to_move is None:
            return None
        if self.viewer_role_for(viewer_id) == "local_controller":
            return phase.side_to_move
        side = self._player_sides.get(viewer_id)
        return side if side == phase.side_to_move else None

    def actor_side_for_command(
        self,
        player_id: PlayerId,
        phase: SessionPhase,
    ) -> PlayerSide | None:
        if phase.side_to_move is None:
            return None
        if self.viewer_role_for(player_id) == "local_controller":
            return phase.side_to_move
        return self._player_sides.get(player_id)
