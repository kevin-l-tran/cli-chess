from dataclasses import dataclass
from typing import Callable

from src.application.click_draft import click_to_move_text
from src.application.snapshot import SnapshotInputs, build_snapshot
from src.engine.moves import Move, get_final_position, get_initial_position
from src.engine.game import (
    Game,
    GameConcludedError,
    IllegalMoveError,
    NoMoveToUndoError,
)

from .intents import CursorMove, GameUpdate
from .move_parser import ParseResult, parse
from .session_types import (
    MoveAttemptResult,
    ResignResult,
    SessionConfig,
    Snapshot,
    Square,
    UndoResult,
    UndoScope,
)


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

        outcome_banner (str | None):
            A prominent message used to display game conclusion messages.
            `None` means there is no active banner message to display.
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
        self._listeners: list[Callable] = []
        self._legal_moves: set[Move] = set()
        self._bootstrap_session(config=config, game=game)

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
              parse state, highlights, and feedback
            - refreshes cached legal moves and other derived position state
        """
        self._bootstrap_session(
            config=self._config if config is None else config,
            game=None,
        )

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
            - re-parses the current move draft against current legal moves
            - confirms that the draft uniquely resolves to a legal move
            - applies the resolved move through the engine
            - refreshes cached legal moves and derived position state
            - updates last-move highlight squares
            - clears the move draft and resets parse state
            - clears any active error message

        Failure behavior:
            - returns stable feedback for game-concluded, empty, ambiguous,
            no-match, and unexpected-resolution cases
            - preserves the current draft text for correction
            - stores a user-facing error message
            - does not modify the board position unless move application succeeds
        """
        self._state.parse_result = parse(self._state.move_text, self._legal_moves)
        parse_result = self._state.parse_result

        if self._game.outcome != "":
            self._refresh_position_state(clear_move_text=False)
            self._state.last_error_message = "Game has concluded."
            return MoveAttemptResult(False, "game_over", "Game has concluded.")

        if parse_result.status == "empty":
            self._state.last_error_message = "Enter a move first."
            return MoveAttemptResult(False, "empty", "Enter a move first.")

        if parse_result.status == "ambiguous":
            self._state.last_error_message = "Move is ambiguous."
            return MoveAttemptResult(False, "ambiguous", "Move is ambiguous.")

        if parse_result.status == "no_match":
            self._state.last_error_message = "No legal move matches the current draft."
            return MoveAttemptResult(
                False,
                "no_match",
                "No legal move matches the current draft.",
            )

        move = parse_result.resolved_move
        if move is None:
            self._state.last_error_message = "Could not resolve move."
            return MoveAttemptResult(False, "error", "Could not resolve move.")

        return self._apply_resolved_move(move, offer_draw=offer_draw)

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
        """
        Attempt to resign the current game through the session controller.

        Returns:
            ResignResult:
                Stable success/failure information suitable for the UI layer.

        Success behavior:
            - resigns the current game through the engine
            - refreshes cached legal moves and last-move highlight state
            - clears the current move-text draft and parse state
            - clears any active error message
            - returns a user-facing resignation message

        Failure behavior:
            - leaves the current move-text draft intact
            - refreshes session-owned position state
            - stores a user-facing failure message
            - returns a stable failure result
        """
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
            self._state.last_error_message = None

            resign_message = (
                "White resigns." if self._game.outcome == "0-1" else "Black resigns."
            )
            return ResignResult(True, "resigned", resign_message)

    def snapshot(self) -> Snapshot:
        """
        Build an immutable render-ready view of the current session.

        Returns:
            Snapshot:
                A presentation-friendly snapshot containing board glyphs,
                turn information, highlights, move history, draft-input state,
                check state, and user-facing feedback messages.
        """
        return build_snapshot(
            self._game,
            SnapshotInputs(
                player_side=self._config.player_side,
                orientation_override=self._state.orientation_override,
                cursor=self._state.cursor,
                move_text=self._state.move_text,
                parse_result=self._state.parse_result,
                last_move_from=self._state.last_move_from,
                last_move_to=self._state.last_move_to,
                outcome_banner=self._state.outcome_banner,
                last_error_message=self._state.last_error_message,
            ),
        )

    def set_move_text(self, text: str) -> None:
        """Store raw draft text and re-parse it against current legal moves."""
        self._state.move_text = text
        self._state.parse_result = parse(self._state.move_text, self._legal_moves)

    def clear_move_text(self) -> None:
        """Clear the current draft text and reset parse state to the empty-input result."""
        self._state.move_text = ""
        self._state.parse_result = parse(self._state.move_text, self._legal_moves)

    def click_square(self, square: Square) -> None:
        """
        Rewrite the move draft in response to a board-square click.

        Parameters:
            square (Square):
                The clicked board square.

        Behavior:
            - updates the session cursor to the clicked square
            - does nothing if the game has already concluded
            - derives the next move-draft text from the current draft,
              parse result, legal moves, and clicked square
            - stores that derived text through `set_move_text()`, so the
              standard parse/update path is reused

        Notes:
            This method does not apply a move directly. Clicks only edit the
            draft text.
        """
        self._state.cursor = square

        if self._game.outcome != "":
            return

        self.set_move_text(
            click_to_move_text(
                current_text=self._state.move_text,
                parse_result=self._state.parse_result,
                legal_moves=self._legal_moves,
                square=square,
            )
        )

    def _bootstrap_session(
        self,
        config: SessionConfig,
        game: Game | None = None,
    ) -> None:
        self._config = config
        self._game = Game() if game is None else game
        self._state = _SessionState()
        self._refresh_position_state(clear_move_text=False)

    def _update_cursor(self, update: CursorMove):
        r, f = self._state.cursor if self._state.cursor is not None else (0, 0)
        self._state.cursor = (
            max(0, min(7, r + update.dy)),
            max(0, min(7, f + update.dx)),
        )

    def _apply_resolved_move(
        self,
        move: Move,
        offer_draw: bool = False,
    ) -> MoveAttemptResult:
        try:
            self._game.make_move(move, draw_offered=offer_draw)
        except IllegalMoveError:
            self._state.last_error_message = "Could not apply illegal move."
            return MoveAttemptResult(False, "illegal", "Could not apply illegal move.")
        except GameConcludedError:
            self._refresh_position_state(clear_move_text=False)
            self._state.last_error_message = "Game has concluded."
            return MoveAttemptResult(False, "game_over", "Game has concluded.")
        except Exception:
            self._state.last_error_message = "Could not apply move."
            return MoveAttemptResult(False, "error", "Could not apply move.")
        else:
            self._refresh_position_state(clear_move_text=True)
            self._state.last_error_message = None
            return MoveAttemptResult(True, "applied", None)

    def _refresh_position_state(self, *, clear_move_text: bool):
        if self._game.outcome != "":
            self._legal_moves = set()
            if self._game.outcome == "1-0":
                self._state.outcome_banner = "White wins."
            elif self._game.outcome == "0-1":
                self._state.outcome_banner = "Black wins."
            elif self._game.outcome == "1/2-1/2":
                self._state.outcome_banner = "Draw."
        else:
            self._legal_moves = self._game.get_moves()
            self._state.outcome_banner = None

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
