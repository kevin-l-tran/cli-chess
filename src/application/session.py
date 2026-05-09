from typing import Any, cast

from src.application.command_types import CommandResult
from src.application.move_parser import (
    get_canonical,
    normalize_move_text,
    parse,
)
from src.application.viewer_types import FeedbackView, MoveListItem, ViewerSessionView
from src.engine.game import (
    Game,
    GameConcludedError,
    IllegalMoveError,
    NoDrawOfferError,
    NoMoveToUndoError,
)
from src.engine.moves import Move, get_final_position, get_initial_position
from src.shared.ids import LobbyId, PlayerId, RequestId
from src.shared.protocol_types import CommandStatus, ConnectionState, PlayerSide

from .session_helpers.command_cache import (
    CommandIdempotencyCache,
    command_fingerprint,
)
from .session_helpers.permissions import (
    PermissionResolver,
)
from .session_helpers.policy import SessionPolicy
from .session_helpers.projection import (
    SessionProjection,
    move_history,
)
from .session_helpers.session_types import (
    SessionConfig,
    CachedCommandResult,
    CommittedSessionState,
    SessionPhase,
    TerminalState,
    TimeControl,
    UndoScope,
)
from .session_helpers.timing import (
    ClockState,
    SessionTiming,
    TimeSource,
    system_time_ms,
)


class GameSession:
    config: SessionConfig

    game: Game
    legal_moves: set[Move]
    move_history: list[MoveListItem]

    draw_offered_by: PlayerSide | None
    terminal_state: TerminalState | None
    clock_state: ClockState | None

    request_id_cache: dict[tuple[PlayerId, RequestId], CachedCommandResult]
    player_sides: dict[PlayerId, PlayerSide]

    def __init__(
        self,
        config: SessionConfig,
        *,
        game: Game | None = None,
        player_sides: dict[PlayerId, PlayerSide] | None = None,
        time_source: TimeSource | None = None,
    ) -> None:
        self.config = config
        self.game = Game() if game is None else game
        self.legal_moves = set()
        self.move_history = []
        self.draw_offered_by = None
        self.terminal_state = None
        self.player_sides = dict(player_sides or {})

        self.request_id_cache = {}
        self._command_cache = CommandIdempotencyCache(self.request_id_cache)
        self._time_source = time_source or system_time_ms
        self._state = CommittedSessionState()

        self.clock_state = self._new_clock_state(config.time_control)
        self._timing = SessionTiming(
            clock_state=self.clock_state,
            time_control=config.time_control,
            time_source=self._time_source,
        )
        self._permissions = PermissionResolver(
            config=self.config,
            player_sides=self.player_sides,
        )

        self._refresh_position_state()

    @classmethod
    def local(
        cls,
        *,
        lobby_id: LobbyId = LobbyId("local"),
        time_control: TimeControl | None = None,
        time_source: TimeSource | None = None,
    ) -> "GameSession":
        return cls(
            SessionConfig(
                lobby_id=lobby_id,
                mode="local",
                time_control=time_control,
            ),
            time_source=time_source,
        )

    def submit_move(
        self,
        player_id: PlayerId,
        move_text: str,
        *,
        request_id: RequestId,
        expected_ply: int | None = None,
        offer_draw: bool = False,
    ) -> CommandResult:
        fingerprint = command_fingerprint(
            "submit_move",
            {
                "move_text": normalize_move_text(move_text),
                "expected_ply": expected_ply,
                "offer_draw": offer_draw,
            },
        )
        duplicate = self._duplicate_result(player_id, request_id, fingerprint)
        if duplicate is not None:
            return duplicate

        self._sync_timing()
        phase = self._phase()

        if expected_ply is not None and expected_ply != self.current_ply():
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="stale_position",
                message="Position changed.",
                public_feedback=False,
            )

        if phase.is_game_over:
            self._refresh_position_state()
            self._set_feedback("error", "Game has concluded.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="game_over",
                message="Game has concluded.",
            )

        if self._permissions.submit_side_for_viewer(player_id, phase) is None:
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="not_your_turn",
                message="Not your turn.",
                public_feedback=False,
            )

        if offer_draw and not self._can_offer_draw(player_id, phase):
            self._refresh_position_state()
            self._set_feedback("error", "Draw offers are not available.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="draw_unavailable",
                message="Draw offers are not available.",
            )

        parse_result = parse(move_text, self.legal_moves)
        if parse_result.status == "empty":
            self._set_feedback("error", "Enter a move first.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="invalid_move",
                message="Enter a move first.",
            )
        if parse_result.status == "ambiguous":
            self._set_feedback("error", "Move is ambiguous.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="ambiguous_move",
                message="Move is ambiguous.",
            )
        if parse_result.status == "no_match":
            self._set_feedback("error", "No legal move matches the submitted text.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="invalid_move",
                message="No legal move matches the submitted text.",
            )

        move = parse_result.resolved_move
        if move is None:
            self._set_feedback("error", "Could not resolve move.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="error",
                message="Could not resolve move.",
            )

        return self._commit_move(
            player_id=player_id,
            request_id=request_id,
            fingerprint=fingerprint,
            move=move,
            offer_draw=offer_draw,
        )

    def accept_draw_offer(
        self,
        player_id: PlayerId,
        *,
        request_id: RequestId,
        expected_ply: int | None = None,
    ) -> CommandResult:
        fingerprint = command_fingerprint(
            "accept_draw_offer",
            {"expected_ply": expected_ply},
        )
        duplicate = self._duplicate_result(player_id, request_id, fingerprint)
        if duplicate is not None:
            return duplicate

        self._sync_timing()
        phase = self._phase()

        if expected_ply is not None and expected_ply != self.current_ply():
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="stale_position",
                message="Position changed.",
                public_feedback=False,
            )
        if phase.is_game_over:
            self._refresh_position_state()
            self._set_feedback("error", "Game has concluded.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="game_over",
                message="Game has concluded.",
            )

        actor_side = self._permissions.actor_side_for_command(player_id, phase)
        offered_by = self._get_draw_offered_by()
        if actor_side is None:
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="not_player",
                message="Only a player may accept a draw offer.",
                public_feedback=False,
            )
        if offered_by is None or offered_by == actor_side:
            self._refresh_position_state()
            self._set_feedback("error", "No draw offer is available.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="draw_unavailable",
                message="No draw offer is available.",
            )

        try:
            self.game.accept_draw()
        except NoDrawOfferError:
            self._refresh_position_state()
            self._set_feedback("error", "No draw offer is available.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="draw_unavailable",
                message="No draw offer is available.",
            )
        except GameConcludedError:
            self._refresh_position_state()
            self._set_feedback("error", "Game has concluded.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="game_over",
                message="Game has concluded.",
            )
        except Exception:
            self._refresh_position_state()
            self._set_feedback("error", "Could not accept draw offer.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="error",
                message="Could not accept draw offer.",
            )

        self._set_terminal(TerminalState(winner=None, reason="draw"))
        self._refresh_position_state()
        self._set_feedback("action", "Draw offer accepted.")
        return self._record_and_return(
            player_id,
            request_id,
            fingerprint,
            ok=True,
            status="accepted",
            message="Draw offer accepted.",
        )

    def resign(
        self,
        player_id: PlayerId,
        *,
        request_id: RequestId,
    ) -> CommandResult:
        fingerprint = command_fingerprint("resign", {})
        duplicate = self._duplicate_result(player_id, request_id, fingerprint)
        if duplicate is not None:
            return duplicate

        self._sync_timing()
        phase = self._phase()

        if phase.is_game_over:
            self._refresh_position_state()
            self._set_feedback("error", "Game has concluded.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="game_over",
                message="Game has concluded.",
            )

        if self._permissions.submit_side_for_viewer(player_id, phase) is None:
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="not_your_turn",
                message="Resignation is currently limited to the side to move.",
                public_feedback=False,
            )

        try:
            self.game.resign()
        except GameConcludedError:
            self._refresh_position_state()
            self._set_feedback("error", "Game has concluded.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="game_over",
                message="Game has concluded.",
            )
        except Exception:
            self._refresh_position_state()
            self._set_feedback("error", "Could not resign game.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="error",
                message="Could not resign game.",
            )

        winner: PlayerSide = "black" if self.game.outcome == "0-1" else "white"
        self._set_terminal(TerminalState(winner=winner, reason="resignation"))
        self._refresh_position_state()

        message = "White resigns." if self.game.outcome == "0-1" else "Black resigns."
        self._set_feedback("action", message)
        return self._record_and_return(
            player_id,
            request_id,
            fingerprint,
            ok=True,
            status="accepted",
            message=message,
        )

    def request_undo(
        self,
        player_id: PlayerId,
        *,
        request_id: RequestId,
        scope: UndoScope | None = None,
    ) -> CommandResult:
        fingerprint = command_fingerprint("request_undo", {"scope": scope})
        duplicate = self._duplicate_result(player_id, request_id, fingerprint)
        if duplicate is not None:
            return duplicate

        self._sync_timing()
        if not self._permissions.viewer_is_player_or_local_controller(player_id):
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="not_player",
                message="Only a player may request undo.",
                public_feedback=False,
            )

        resolved_scope = SessionPolicy.resolve_undo_scope(
            self.config.mode,
            scope,
        )
        if resolved_scope is None:
            self._refresh_position_state()
            message = (
                "Can't undo in an online game."
                if self.config.mode == "online"
                else "Halfmove undo is only available in local games."
            )
            self._set_feedback("error", message)
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="undo_unavailable",
                message=message,
            )

        move_count = len(self.game.moves_list)
        if resolved_scope == "halfmove" and move_count == 0:
            return self._undo_unavailable(player_id, request_id, fingerprint)
        if resolved_scope == "fullmove" and move_count <= 1:
            return self._undo_unavailable(player_id, request_id, fingerprint)

        try:
            if resolved_scope == "fullmove":
                self.game.undo_fullmove()
                self._timing.pop_frame()
                self._timing.pop_frame()
                message = "Turn undone."
            else:
                self.game.undo_halfmove()
                self._timing.pop_frame()
                message = "Move undone."
        except NoMoveToUndoError:
            return self._undo_unavailable(player_id, request_id, fingerprint)
        except Exception:
            self._refresh_position_state()
            self._set_feedback("error", "Could not undo move.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="error",
                message="Could not undo move.",
            )

        self._clear_terminal()
        self._refresh_position_state()
        self._set_feedback("action", message)
        return self._record_and_return(
            player_id,
            request_id,
            fingerprint,
            ok=True,
            status="accepted",
            message=message,
        )

    def snapshot_for(
        self,
        viewer_id: PlayerId,
        *,
        connection_state: ConnectionState = "connected",
        viewer_status_text: str | None = None,
    ) -> ViewerSessionView:
        self._sync_timing()
        phase = self._phase()
        draw_offered_by = self._get_draw_offered_by()
        permissions = self._permissions.for_viewer(
            viewer_id,
            phase=phase,
            move_count=self.current_ply(),
            draw_offered_by=draw_offered_by,
        )
        snapshot = SessionProjection.snapshot(
            game=self.game,
            phase=phase,
            state=self._state,
            draw_offered_by=draw_offered_by,
            clock_state=self.clock_state,
            time_control=self.config.time_control,
        )
        preview_hints = SessionProjection.preview_hints(
            legal_moves=self.legal_moves,
            phase=phase,
            current_ply=self.current_ply(),
            include_preview_hints=(
                self.config.include_preview_hints and self.config.mode != "online"
            ),
        )
        return SessionProjection.viewer_session_view(
            lobby_id=self.config.lobby_id,
            viewer_id=viewer_id,
            current_ply=self.current_ply(),
            connection_state=connection_state,
            status_text=viewer_status_text,
            permissions=permissions,
            snapshot=snapshot,
            preview_hints=preview_hints,
        )

    def current_ply(self) -> int:
        return len(self.game.moves_list)

    def _commit_move(
        self,
        *,
        player_id: PlayerId,
        request_id: RequestId,
        fingerprint: str,
        move: Move,
        offer_draw: bool,
    ) -> CommandResult:
        self._timing.push_frame()
        try:
            self.game.make_move(move, draw_offered=offer_draw)
        except IllegalMoveError:
            self._timing.pop_frame()
            self._set_feedback("error", "Could not apply illegal move.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="invalid_move",
                message="Could not apply illegal move.",
            )
        except GameConcludedError:
            self._timing.pop_frame()
            self._refresh_position_state()
            self._set_feedback("error", "Game has concluded.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="game_over",
                message="Game has concluded.",
            )
        except Exception:
            self._timing.pop_frame()
            self._set_feedback("error", "Could not apply move.")
            return self._record_and_return(
                player_id,
                request_id,
                fingerprint,
                ok=False,
                status="error",
                message="Could not apply move.",
            )

        next_side: PlayerSide = "white" if self.game.is_white_turn else "black"
        self._timing.on_move_committed(next_side=next_side)
        self._refresh_terminal_from_engine()
        self._refresh_position_state()

        message = f"Played {get_canonical(move)}."
        if offer_draw and not self._phase().is_game_over:
            message += " Draw offered."
        self._set_feedback("action", message)
        return self._record_and_return(
            player_id,
            request_id,
            fingerprint,
            ok=True,
            status="accepted",
            message=message,
        )

    def _record_and_return(
        self,
        player_id: PlayerId,
        request_id: RequestId,
        fingerprint: str,
        *,
        ok: bool,
        status: CommandStatus,
        message: str | None,
        public_feedback: bool = True,
    ) -> CommandResult:
        self._command_cache.record(
            player_id=player_id,
            request_id=request_id,
            fingerprint=fingerprint,
            ok=ok,
            status=status,
            message=message,
        )
        return CommandResult(
            ok=ok,
            status=status,
            message=message,
            view=self.snapshot_for(
                player_id,
                viewer_status_text=None if public_feedback else message,
            ),
        )

    def _duplicate_result(
        self,
        player_id: PlayerId,
        request_id: RequestId,
        fingerprint: str,
    ) -> CommandResult | None:
        duplicate = self._command_cache.check(
            player_id=player_id,
            request_id=request_id,
            fingerprint=fingerprint,
        )
        if duplicate.kind == "miss":
            return None
        if duplicate.kind == "conflict":
            message = "Request ID was already used for a different command."
            return CommandResult(
                ok=False,
                status="duplicate_conflict",
                message=message,
                view=self.snapshot_for(player_id, viewer_status_text=message),
            )

        cached = duplicate.cached
        assert cached is not None
        return CommandResult(
            ok=cached.ok,
            status="duplicate",
            message=cached.message,
            view=self.snapshot_for(player_id),
        )

    def _undo_unavailable(
        self,
        player_id: PlayerId,
        request_id: RequestId,
        fingerprint: str,
    ) -> CommandResult:
        self._refresh_position_state()
        self._set_feedback("error", "No move to undo.")
        return self._record_and_return(
            player_id,
            request_id,
            fingerprint,
            ok=False,
            status="undo_unavailable",
            message="No move to undo.",
        )

    def _new_clock_state(self, time_control: TimeControl | None) -> ClockState | None:
        if time_control is None:
            return None
        active_side: PlayerSide | None = None
        if self.game.outcome == "":
            active_side = "white" if self.game.is_white_turn else "black"
        return ClockState(
            white_remaining_ms=time_control.initial_seconds * 1000,
            black_remaining_ms=time_control.initial_seconds * 1000,
            active_side=active_side,
            timeout_side=None,
            last_updated_ms=self._time_source(),
        )

    def _sync_timing(self) -> None:
        if self._timing.sync(engine_game_over=self.game.outcome != ""):
            loser = self._timing.timeout_side()
            winner: PlayerSide = "black" if loser == "white" else "white"
            self._set_terminal(TerminalState(winner=winner, reason="timeout"))
            self._refresh_position_state()

    def _refresh_position_state(self) -> None:
        phase = self._phase()
        if phase.kind == "active":
            assert phase.side_to_move is not None
            self.legal_moves = self.game.get_moves()
            self._timing.on_position_ready(
                side_to_move=phase.side_to_move,
                engine_game_over=False,
            )
        else:
            self.legal_moves = set()
            self._timing.freeze()

        if self.game.moves_list:
            last_move, _ = self.game.moves_list[-1]
            self._state.last_move_from = get_initial_position(last_move)
            self._state.last_move_to = get_final_position(last_move)
        else:
            self._state.last_move_from = None
            self._state.last_move_to = None

        self.draw_offered_by = self._get_draw_offered_by()
        self.move_history = move_history(self.game)

    def _set_feedback(self, kind: str, text: str) -> None:
        self._state.feedback = FeedbackView(cast(Any, kind), text)

    def _set_terminal(self, terminal: TerminalState) -> None:
        self.terminal_state = terminal

    def _clear_terminal(self) -> None:
        self.terminal_state = None

    def _refresh_terminal_from_engine(self) -> None:
        if self.terminal_state is not None:
            return
        if self.game.outcome == "":
            return
        if self.game.outcome == "1/2-1/2":
            self._set_terminal(TerminalState(winner=None, reason="draw"))
        elif self.game.outcome == "1-0":
            self._set_terminal(TerminalState(winner="white", reason="checkmate"))
        elif self.game.outcome == "0-1":
            self._set_terminal(TerminalState(winner="black", reason="checkmate"))

    def _phase(self) -> SessionPhase:
        self._refresh_terminal_from_engine()
        if self.terminal_state is not None:
            return SessionPhase(
                kind="timed_out"
                if self.terminal_state.reason == "timeout"
                else "concluded",
                side_to_move=None,
                terminal=self.terminal_state,
            )
        return SessionPhase(
            kind="active",
            side_to_move="white" if self.game.is_white_turn else "black",
            terminal=None,
        )

    def _get_draw_offered_by(self) -> PlayerSide | None:
        white_draw_offer = self.game.pending_draw_offer_side_is_white()
        if white_draw_offer is None:
            return None
        return "white" if white_draw_offer else "black"

    def _can_offer_draw(self, player_id: PlayerId, phase: SessionPhase) -> bool:
        return self._permissions.for_viewer(
            player_id,
            phase=phase,
            move_count=self.current_ply(),
            draw_offered_by=self._get_draw_offered_by(),
        ).can_offer_draw
