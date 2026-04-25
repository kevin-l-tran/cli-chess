from dataclasses import dataclass
from typing import Callable, Literal

from src.engine.game import (
    Game,
    GameConcludedError,
    IllegalMoveError,
    NoMoveToUndoError,
)
from src.engine.moves import Move, get_final_position, get_initial_position
from .intents import CursorMove, GameUpdate
from .session_types import SessionConfig, Square
from .move_parser import ParseResult, parse

MoveAttemptStatus = Literal["applied", "illegal", "game_over", "error"]
UndoStatus = Literal["undone", "unavailable", "error"]
UndoScope = Literal["halfmove", "fullmove"]
ResignStatus = Literal["resigned", "game_over", "error"]


@dataclass(frozen=True)
class MoveAttemptResult:
    ok: bool
    status: MoveAttemptStatus
    message: str | None


@dataclass(frozen=True)
class UndoResult:
    ok: bool
    status: UndoStatus
    message: str | None


@dataclass(frozen=True)
class ResignResult:
    ok: bool
    status: ResignStatus
    message: str | None


@dataclass
class _SessionState:
    """
    Private mutable working state for a `GameSession`.

    This object stores UI-adjacent and controller-owned session data that is
    used to build an immutable render-ready snapshot.

    Attributes:
        cursor (Square | None):
            The square currently focused by keyboard/controller navigation.
            `None` means there is no active cursor.

        move_text (str):
            The current raw move text being edited by the user, such as
            `"Nf3"` or `"Pe2-e4"` depending on the accepted input format.

        parse_result (ParseResult):
            The most recent parse result for `move_text`.

        orientation_override (bool):
            An optional override for board orientation. `True` means the board
            should be rendered opposite of the default orientation for the
            current player, while `False` means it should be rendered in the
            default orientation.

        last_move_from (Square | None):
            The origin square of the most recently applied move, if any. Used
            for last-move highlighting in the UI.

        last_move_to (Square | None):
            The destination square of the most recently applied move, if any.
            Used together with `last_move_from` for move highlighting.

        last_error_message (str | None):
            The most recent user-facing failure message produced by the
            session, such as an illegal-move or game-concluded message.
            `None` means there is no active error to display.
    """

    cursor: Square | None = (0, 0)

    move_text: str = ""
    parse_result: ParseResult = parse("", set())

    orientation_override: bool = False

    last_move_from: Square | None = None
    last_move_to: Square | None = None
    last_error_message: str | None = None
    outcome_banner: str | None = None


class GameSession:
    """
    Application-layer controller for a single chess session.

    A `GameSession` owns:
    - the active engine `Game`
    - session configuration
    - mutable UI-adjacent working state
    - a cached legal-move set for the current position
    - optional listeners for future publication of session updates
    """

    def __init__(self, config: SessionConfig, game: Game | None = None):
        self._game = Game() if game is None else game
        self._config = config
        self._state: _SessionState = _SessionState()
        self._legal_moves: set[Move] = self._game.get_moves()
        self._listeners: list[Callable] = []

    def subscribe(self, fn: Callable):
        """
        Register a listener for future session updates.

        Parameters:
            fn (Callable):
                Callback to store for later notification.

        Notes:
            Listeners are currently only stored and not yet invoked. This
            method exists to support a future publication path when the
            session begins producing snapshots or explicit update events.
        """
        self._listeners.append(fn)

    def dispatch(self, intent: GameUpdate):
        """
        Handle a UI-originated session intent.

        Parameters:
            intent (GameUpdate):
                The application intent to process.

        Notes:
            This method currently handles cursor movement only. As the session
            grows, this method can route additional intent types such as move
            text changes, square selection, board flipping, and move
            confirmation.
        """
        if isinstance(intent, CursorMove):
            self._update_cursor(intent)

    def try_make_move(self, move: Move, offer_draw: bool = False) -> MoveAttemptResult:
        """
        Attempt to apply a resolved move through the engine.

        This is the main application-layer move entrypoint for callers that
        already have a resolved engine move. It translates engine failures into
        stable session-level results and updates session-owned feedback state.

        Parameters:
            move (Move):
                The fully resolved engine move to attempt.

            offer_draw (bool):
                Whether the move should also carry a draw offer.

        Returns:
            MoveAttemptResult:
                Stable success/failure information suitable for the UI layer.

        Success behavior:
            - applies the move through the engine
            - refreshes the cached legal-move set
            - records last-move highlight squares
            - clears any prior error message
            - clears the move-text draft
            - resets the draft parse result to the empty-input parse state

        Failure behavior:
            - preserves existing draft input state
            - records a user-facing error message
            - returns a stable failure result
        """
        try:
            self._game.make_move(move, draw_offered=offer_draw)
        except IllegalMoveError:
            self._state.last_error_message = "Could not apply illegal move."
            return MoveAttemptResult(
                ok=False, status="illegal", message="Could not apply illegal move."
            )
        except GameConcludedError:
            self._state.last_error_message = "Game has concluded."
            return MoveAttemptResult(
                ok=False, status="game_over", message="Game has concluded."
            )
        except Exception:
            self._state.last_error_message = "Could not apply move."
            return MoveAttemptResult(
                ok=False, status="error", message="Could not apply move."
            )
        else:
            self._refresh_position_state(clear_move_text=True)
            self._state.last_error_message = None
            return MoveAttemptResult(ok=True, status="applied", message=None)

    def undo(self, scope: UndoScope | None = None) -> UndoResult:
        """
        Attempt to undo the most recent move through the session controller.

        Parameters:
            scope (UndoScope | None):
                Which undo policy to apply. `"halfmove"` undoes one ply and
                `"fullmove"` undoes two plies as a turn pair. If `None`, the
                session chooses a default based on the configured opponent:
                `"halfmove"` for local play and `"fullmove"` for bot play.

        Returns:
            UndoResult:
                Stable success/failure information for the UI layer.

        Success behavior:
            - calls the engine undo operation for the resolved scope
            - refreshes cached legal moves and last-move highlight state
            - clears the current move-text draft and parse state
            - clears any active error message

        Failure behavior:
            - leaves the current move-text draft intact
            - refreshes session-owned position state
            - stores a user-facing failure message
            - returns a stable failure result
        """
        if scope is None:
            scope = "fullmove" if self._config.opponent == "bot" else "halfmove"

        try:
            if scope == "fullmove":
                self._game.undo_fullmove()
                success_message = "Turn undone."
            else:
                self._game.undo_halfmove()
                success_message = "Move undone."
        except NoMoveToUndoError:
            self._refresh_position_state(clear_move_text=False)
            self._state.last_error_message = "No move to undo."
            return UndoResult(False, "unavailable", "No move to undo.")
        except Exception:
            self._refresh_position_state(clear_move_text=False)
            self._state.last_error_message = "Could not undo move."
            return UndoResult(False, "error", "Could not undo move.")
        else:
            self._refresh_position_state(clear_move_text=True)
            self._state.last_error_message = None
            return UndoResult(True, "undone", success_message)

    def resign(self) -> ResignResult:
        try:
            self._game.resign()
        except GameConcludedError:
            self._refresh_position_state(clear_move_text=False)
            self._state.last_error_message = "Game has concluded."
            return ResignResult(False, "game_over", "Game has concluded.")
        except Exception:
            self._refresh_position_state(clear_move_text=False)
            self._state.last_error_message = "Could not resign game."
            return ResignResult(False, "error", "Could not resign game.")
        else:
            self._refresh_position_state(clear_move_text=True)

            banner = (
                "Black wins by resignation."
                if self._game.outcome == "0-1"
                else "White wins by resignation."
            )
            self._state.outcome_banner = banner
            self._state.last_error_message = None
            return ResignResult(True, "resigned", banner)

    def _update_cursor(self, update: CursorMove):
        r, f = self._state.cursor if self._state.cursor is not None else (0, 0)
        self._state.cursor = (
            max(0, min(7, r + update.dy)),
            max(0, min(7, f + update.dx)),
        )

    def _refresh_position_state(self, *, clear_move_text: bool) -> None:
        self._legal_moves = self._game.get_moves()

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
