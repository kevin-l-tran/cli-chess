from dataclasses import dataclass, field
from typing import Literal

from src.engine.moves import (
    Move,
    get_final_position,
    get_initial_position,
    get_promotion,
)
from src.engine.game import (
    Game,
    GameConcludedError,
    IllegalMoveError,
    NoMoveToUndoError,
)

from .move_parser import ParseResult, get_canonical, parse
from .click_draft import click_to_move_text
from .clock import ClockState, TimeSource, system_time_ms
from .session_timing import SessionTiming
from .session_policy import SessionCapabilities, SessionPolicy
from .session_projection import (
    SessionProjection,
    SessionProjectionInputs,
    TimingProjectionInputs,
)
from .session_types import (
    MoveAttemptResult,
    PlayerSide,
    ResignResult,
    SessionConfig,
    SessionPhase,
    Snapshot,
    Square,
    TerminalState,
    UndoResult,
    UndoScope,
)


@dataclass
class _SessionState:
    """
    Private mutable state owned by `GameSession`.

    This structure stores controller-owned working state that is projected into the
    immutable `Snapshot` read model. It includes the current move draft and parse
    result, last-move highlight squares, and the latest user-facing action or error
    message.

    Attributes:
        move_text (str):
            The raw move text currently being edited by the user.

        parse_result (ParseResult):
            The most recent parse result for `move_text` against the cached legal
            move set.

        last_move_from (Square | None):
            Origin square of the most recently applied move, if any.

        last_move_to (Square | None):
            Destination square of the most recently applied move, if any.

        last_error_message (str | None):
            The most recent user-facing failure message, or `None` when no error is
            active.

        last_action_message (str | None):
            The most recent user-facing success or action message, or `None` when no
            action message is active.
    """

    move_text: str = ""
    parse_result: ParseResult = field(default_factory=lambda: parse("", set()))

    last_move_from: Square | None = None
    last_move_to: Square | None = None

    last_error_message: str | None = None
    last_action_message: str | None = None


class GameSession:
    """
    Application-layer controller for a single chess session.

    A `GameSession` owns the active engine `Game`, session configuration, timing
    coordinator, cached legal moves, terminal state, and UI-adjacent working state
    such as the current move draft and feedback messages.

    Its public API accepts session-level intents from the presentation layer
    (move-text edits, square clicks, move confirmation, undo, resignation, and
    snapshot reads) and translates them into engine operations plus immutable
    render-ready `Snapshot` values.
    """

    def __init__(
        self,
        config: SessionConfig,
        game: Game | None = None,
        time_source: TimeSource | None = None,
    ):
        self._time_source = time_source or system_time_ms
        self._legal_moves: set[Move] = set()
        self._terminal_state: TerminalState | None = None
        self._bootstrap_session(config=config, game=game)

    # ============================================================================
    # Lifecycle
    # ============================================================================

    def restart_game(self, config: SessionConfig | None = None) -> None:
        """
        Start a fresh game session using the current or supplied configuration.

        Parameters:
            config (SessionConfig | None):
                Optional replacement session configuration. When `None`, the
                existing session configuration is preserved.

        Behavior:
            - rebuilds the backing engine `Game`
            - resets controller-owned working state such as draft input,
            parse state, highlights, feedback, and timing state
            - refreshes cached legal moves and other derived position state
            - records a user-facing restart message
        """
        self._clear_terminal()
        self._bootstrap_session(
            config=self._config if config is None else config,
            game=None,
        )
        self._set_action_message("Game restarted.")

    # ============================================================================
    # Draft editing
    # ============================================================================

    def set_move_text(self, text: str) -> None:
        """
        Store raw move-input text and re-parse it against the current legal moves.

        Parameters:
            text (str):
                The raw move text entered by the user.

        Behavior:
            - updates the session-owned move draft
            - re-parses the draft against the current cached legal-move set
            - does not apply a move or otherwise change the board position
        """
        self._store_move_text(text)

    def clear_move_text(self) -> None:
        """
        Clear the current move-input draft and reset parse state.

        Behavior:
            - replaces the current draft text with the empty string
            - re-parses the empty draft against the current legal moves
            - does not apply a move or otherwise change the board position
        """
        self._store_move_text("")

    def click_square(self, square: Square) -> None:
        """
        Rewrite the current move draft in response to a board-square click.

        Parameters:
            square (Square):
                The clicked board square.

        Behavior:
            - derives the next move-draft text from the current parse result, cached
            legal moves, and clicked square through `click_to_move_text()`
            - stores the derived text as the new session-owned draft
            - re-parses the stored draft against the current cached legal moves
            - does not apply a move or otherwise change the board position

        Notes:
            This method only edits draft text. It does not synchronize timing or apply
            a terminal-state guard on its own.
        """
        self._store_move_text(
            click_to_move_text(
                parse_result=self._state.parse_result,
                legal_moves=self._legal_moves,
                square=square,
            )
        )

    def select_promotion_piece(self, piece: Literal["Q", "R", "B", "N"]) -> None:
        """
        Resolve the current promotion draft to a specific promotion piece.

        Parameters:
            piece (Literal["Q", "R", "B", "N"]):
                The promotion piece to select.

        Behavior:
            - scans the current parse result's matching moves for a promotion move whose
            promotion piece matches `piece`
            - when a match is found, rewrites the draft to that move's canonical text
            - reuses the normal draft storage and parse-update path
            - leaves session state unchanged when no matching promotion move exists

        Notes:
            This method only rewrites the move draft. It does not apply a move,
            synchronize timing, or enforce terminal-state guards on its own.
        """
        for move in self._state.parse_result.matching_moves:
            if get_promotion(move) == piece:
                self._store_move_text(get_canonical(move))
                return

    # ============================================================================
    # Game commands
    # ============================================================================

    def confirm_move_draft(self, offer_draw: bool = False) -> MoveAttemptResult:
        """
        Attempt to confirm and apply the current draft text.

        Parameters:
            offer_draw (bool):
                Whether the confirmed move should also include a draw offer.

        Returns:
            MoveAttemptResult:
                Stable success/failure information suitable for the UI layer.

        Success behavior:
            - synchronizes session-owned timing before validating the draft
            - re-parses the current move draft against current legal moves
            - confirms that the draft uniquely resolves to a legal move
            - applies the resolved move through the engine
            - updates session-owned timing state, including increment and active-side
            switching for timed sessions
            - refreshes cached legal moves and derived position state
            - updates last-move highlight squares
            - clears the move draft and resets parse state
            - clears any active error message

        Failure behavior:
            - rejects attempts when the session has already ended due to engine
            conclusion or timeout
            - returns stable feedback for empty, ambiguous, no-match, illegal, and
            unexpected-resolution cases
            - preserves the current draft text for correction unless move
            application succeeds
            - stores a user-facing error message
            - does not modify the board position unless move application succeeds
        """
        self._sync_timing()
        if self._phase().is_game_over:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Game has concluded.")
            return MoveAttemptResult(False, "game_over", "Game has concluded.")

        self._state.parse_result = parse(self._state.move_text, self._legal_moves)
        parse_result = self._state.parse_result

        if parse_result.status == "empty":
            self._set_error_message("Enter a move first.")
            return MoveAttemptResult(False, "empty", "Enter a move first.")

        if parse_result.status == "ambiguous":
            self._set_error_message("Move is ambiguous.")
            return MoveAttemptResult(False, "ambiguous", "Move is ambiguous.")

        if parse_result.status == "no_match":
            self._set_error_message("No legal move matches the current draft.")
            return MoveAttemptResult(
                False,
                "no_match",
                "No legal move matches the current draft.",
            )

        move = parse_result.resolved_move
        if move is None:
            self._set_error_message("Could not resolve move.")
            return MoveAttemptResult(False, "error", "Could not resolve move.")

        return self._apply_resolved_move(move, offer_draw=offer_draw)

    def undo(self, scope: UndoScope | None = None) -> UndoResult:
        """
        Attempt to undo recent move history through the session controller.

        Parameters:
            scope (UndoScope | None):
                Which undo policy to apply. `"halfmove"` undoes one ply and
                `"fullmove"` undoes two plies as a turn pair.

                When `None`, the session chooses a default based on the configured
                opponent:
                - `"halfmove"` for local play
                - `"fullmove"` for bot play

                Online play does not permit undo through this controller; in that
                case the method fails with an unavailable result regardless of scope.

        Returns:
            UndoResult:
                Stable success/failure information for the UI layer.

        Policy:
            Undo remains available even after the game has ended, provided undo is
            allowed for the current opponent mode and there is move history to undo.
            This allows the UI to step backward from terminal positions such as
            checkmate, stalemate, resignation, or timeout.

        Success behavior:
            - synchronizes session-owned timing before undo is attempted
            - calls the engine undo operation for the resolved scope
            - restores prior session-owned timing state for timed sessions
            - refreshes cached legal moves, timing state, and last-move highlights
            - clears the current move-text draft and parse state
            - clears any active error message

        Failure behavior:
            - returns `"unavailable"` when undo is not allowed for the current
            session mode or when there is no move to undo
            - leaves the current move-text draft intact
            - refreshes session-owned position state
            - stores a user-facing failure message
            - returns a stable failure result
        """
        self._sync_timing()

        scope = SessionPolicy.resolve_undo_scope(
            opponent=self._config.opponent,
            requested=scope,
        )
        if scope is None:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Can't undo in an online game.")
            return UndoResult(False, "unavailable", "Can't undo in an online game.")

        caps = self._capabilities()
        if scope == "halfmove" and not caps.can_undo_halfmove:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("No move to undo.")
            return UndoResult(False, "unavailable", "No move to undo.")
        if scope == "fullmove" and not caps.can_undo_fullmove:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("No move to undo.")
            return UndoResult(False, "unavailable", "No move to undo.")

        try:
            if scope == "fullmove":
                self._game.undo_fullmove()
                self._timing.pop_frame()
                self._timing.pop_frame()
                success_message = "Turn undone."
            else:
                self._game.undo_halfmove()
                self._timing.pop_frame()
                success_message = "Move undone."
        except NoMoveToUndoError:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("No move to undo.")
            return UndoResult(False, "unavailable", "No move to undo.")
        except Exception:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Could not undo move.")
            return UndoResult(False, "error", "Could not undo move.")
        else:
            self._clear_terminal()
            self._refresh_position_state(clear_move_text=True)
            self._set_action_message(success_message)
            return UndoResult(True, "undone", success_message)

    def resign(self) -> ResignResult:
        """
        Attempt to resign the current game through the session controller.

        Returns:
            ResignResult:
                Stable success/failure information suitable for the UI layer.

        Success behavior:
            - synchronizes session-owned timing before resignation is attempted
            - resigns the current game through the engine
            - refreshes cached legal moves, timing state, and last-move highlights
            - clears the current move-text draft and parse state
            - clears any active error message
            - returns a user-facing resignation message

        Failure behavior:
            - rejects attempts when the session has already ended due to engine
            conclusion or timeout
            - leaves the current move-text draft intact
            - refreshes session-owned position state
            - stores a user-facing failure message
            - returns a stable failure result
        """
        self._sync_timing()
        if not self._capabilities().can_resign:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Game has concluded.")
            return ResignResult(False, "game_over", "Game has concluded.")

        try:
            self._game.resign()
        except GameConcludedError:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Game has concluded.")
            return ResignResult(False, "game_over", "Game has concluded.")
        except Exception:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Could not resign game.")
            return ResignResult(False, "error", "Could not resign game.")
        else:
            winner = "black" if self._game.outcome == "0-1" else "white"
            self._set_terminal(TerminalState(winner=winner, reason="resignation"))

            self._refresh_position_state(clear_move_text=True)

            resign_message = (
                "White resigns." if self._game.outcome == "0-1" else "Black resigns."
            )
            self._set_action_message(resign_message)
            return ResignResult(True, "resigned", resign_message)

    # ============================================================================
    # Read model
    # ============================================================================

    def snapshot(self) -> Snapshot:
        """
        Build an immutable render-ready view of the current session.

        Returns:
            Snapshot:
                A presentation-friendly snapshot containing board glyphs, side-to-move
                state, candidate and last-move highlights, move history, move-draft
                state, promotion-prompt state, check state, capability flags, optional
                clock state, terminal outcome data, and the latest user-facing feedback
                messages.

        Behavior:
            - synchronizes session-owned timing before projection so the active clock
            reflects elapsed time at read time
            - derives the current session phase and capability flags
            - projects engine state and controller-owned application state through
            `SessionProjection.build()`
            - returns a UI-ready read model rather than exposing mutable engine or
            session internals
        """
        self._sync_timing()

        phase = self._phase()
        clock = self._clock_state
        time_control = self._config.time_control
        capabilities = self._capabilities()

        return SessionProjection.build(
            self._game,
            SessionProjectionInputs(
                move_text=self._state.move_text,
                parse_result=self._state.parse_result,
                side_to_move=phase.side_to_move,
                last_move_from=self._state.last_move_from,
                last_move_to=self._state.last_move_to,
                terminal=phase.terminal,
                last_error_message=self._state.last_error_message,
                last_action_message=self._state.last_action_message,
                is_game_over=phase.is_game_over,
                capabilities=capabilities,
                timing=TimingProjectionInputs(
                    clock_state=clock,
                    increment_seconds=None
                    if time_control is None
                    else time_control.increment_seconds,
                ),
            ),
        )

    # ============================================================================
    # Private helpers
    # ============================================================================

    def _bootstrap_session(
        self,
        config: SessionConfig,
        game: Game | None = None,
    ) -> None:
        self._config = config
        self._game = Game() if game is None else game
        self._state = _SessionState()
        self._terminal_state = None

        time_control = self._config.time_control
        if time_control is None:
            self._clock_state = None
        else:
            active_side: PlayerSide | None = None
            if self._game.outcome == "":
                active_side = "white" if self._game.is_white_turn else "black"

            self._clock_state = ClockState(
                white_remaining_ms=time_control.initial_seconds * 1000,
                black_remaining_ms=time_control.initial_seconds * 1000,
                active_side=active_side,
                timeout_side=None,
                last_updated_ms=self._time_source(),
            )

        self._timing = SessionTiming(
            clock_state=self._clock_state,
            time_control=self._config.time_control,
            time_source=self._time_source,
        )

        self._refresh_position_state(clear_move_text=False)

    def _store_move_text(self, text: str) -> None:
        self._state.move_text = text
        self._state.parse_result = parse(text, self._legal_moves)

    def _set_action_message(self, message: str | None) -> None:
        self._state.last_action_message = message
        self._state.last_error_message = None

    def _set_error_message(self, message: str | None) -> None:
        self._state.last_error_message = message
        self._state.last_action_message = None

    def _sync_timing(self) -> None:
        if self._timing.sync(engine_game_over=self._game.outcome != ""):
            loser = self._timing.timeout_side()
            winner = "black" if loser == "white" else "white"
            self._set_terminal(TerminalState(winner=winner, reason="timeout"))
            self._refresh_position_state(clear_move_text=False)

    def _capabilities(self) -> SessionCapabilities:
        return SessionPolicy.capabilities(
            opponent=self._config.opponent,
            move_count=len(self._game.moves_list),
            parse_result=self._state.parse_result,
            is_game_over=self._phase().is_game_over,
        )

    def _apply_resolved_move(
        self,
        move: Move,
        offer_draw: bool = False,
    ) -> MoveAttemptResult:
        self._timing.push_frame()

        try:
            self._game.make_move(move, draw_offered=offer_draw)
        except IllegalMoveError:
            self._timing.pop_frame()
            self._set_error_message("Could not apply illegal move.")
            return MoveAttemptResult(False, "illegal", "Could not apply illegal move.")
        except GameConcludedError:
            self._timing.pop_frame()
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Game has concluded.")
            return MoveAttemptResult(False, "game_over", "Game has concluded.")
        except Exception:
            self._timing.pop_frame()
            self._set_error_message("Could not apply move.")
            return MoveAttemptResult(False, "error", "Could not apply move.")
        else:
            next_side = "white" if self._game.is_white_turn else "black"
            self._timing.on_move_committed(next_side=next_side)

            self._refresh_terminal_from_engine()
            self._refresh_position_state(clear_move_text=True)

            action_message = f"Played {get_canonical(move)}."
            self._set_action_message(action_message)

            return MoveAttemptResult(True, "applied", action_message)

    def _refresh_position_state(self, clear_move_text: bool):
        phase = self._phase()

        if phase.kind == "active":
            assert phase.side_to_move

            self._legal_moves = self._game.get_moves()
            self._timing.on_position_ready(
                side_to_move=phase.side_to_move,
                engine_game_over=False,
            )
        else:
            self._legal_moves = set()
            self._timing.freeze()

        if self._game.moves_list:
            last_move, _ = self._game.moves_list[-1]
            self._state.last_move_from = get_initial_position(last_move)
            self._state.last_move_to = get_final_position(last_move)
        else:
            self._state.last_move_from = None
            self._state.last_move_to = None

        if clear_move_text:
            self._state.move_text = ""

        self._state.parse_result = parse(self._state.move_text, self._legal_moves)

    def _set_terminal(self, terminal: TerminalState) -> None:
        self._terminal_state = terminal

    def _clear_terminal(self) -> None:
        self._terminal_state = None

    def _refresh_terminal_from_engine(self) -> None:
        if self._terminal_state is not None:
            return

        if self._game.outcome == "":
            return
        if self._game.outcome == "1/2-1/2":
            self._set_terminal(TerminalState(winner=None, reason="draw"))
        elif self._game.outcome == "1-0":
            self._set_terminal(TerminalState(winner="white", reason="checkmate"))
        elif self._game.outcome == "0-1":
            self._set_terminal(TerminalState(winner="black", reason="checkmate"))

    def _phase(self) -> SessionPhase:
        self._refresh_terminal_from_engine()

        if self._terminal_state is not None:
            kind = (
                "timed_out" if self._terminal_state.reason == "timeout" else "concluded"
            )
            return SessionPhase(
                kind=kind, side_to_move=None, terminal=self._terminal_state
            )

        return SessionPhase(
            kind="active",
            side_to_move="white" if self._game.is_white_turn else "black",
            terminal=None,
        )
