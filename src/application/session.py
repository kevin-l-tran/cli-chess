from dataclasses import dataclass, field
from typing import Callable, Literal

from src.application.click_draft import click_to_move_text
from src.application.snapshot import SnapshotInputs, build_snapshot
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
from .session_types import (
    MoveAttemptResult,
    PlayerSide,
    ResignResult,
    SessionConfig,
    Snapshot,
    Square,
    UndoResult,
    UndoScope,
)

TimeSource = Callable[[], int]


@dataclass(frozen=True)
class _ClockFrame:
    white_remaining_ms: int
    black_remaining_ms: int
    active_side: PlayerSide | None
    timeout_side: PlayerSide | None
    last_updated_ms: int | None


@dataclass
class _ClockState:
    white_remaining_ms: int
    black_remaining_ms: int
    active_side: PlayerSide | None
    timeout_side: PlayerSide | None
    last_updated_ms: int | None
    history: list[_ClockFrame] = field(default_factory=list)


@dataclass
class _SessionState:
    """
    Private mutable working state for a `GameSession`.

    This object stores UI-adjacent and controller-owned session data that is
    used to build an immutable render-ready snapshot.

    Attributes:
        move_text (str):
            The current raw move text being edited by the user, such as
            `"Nf3"` or `"Pe2-e4"` depending on the accepted input format.

        parse_result (ParseResult):
            The most recent parse result for `move_text`.

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

        last_action_message (str | None):
            The most recent user-facing action message produced by the
            session, such as an applied-move or undone-move message.
            `None` means there is no active action to display.

        outcome_banner (str | None):
            A prominent message used to display game conclusion messages.
            `None` means there is no active banner message to display.
    """

    move_text: str = ""
    parse_result: ParseResult = field(default_factory=lambda: parse("", set()))

    last_move_from: Square | None = None
    last_move_to: Square | None = None

    last_error_message: str | None = None
    last_action_message: str | None = None
    outcome_banner: str | None = None


class GameSession:
    """
    Application-layer controller for a single chess session.

    A `GameSession` owns:
    - the active engine `Game`
    - session configuration
    - mutable UI-adjacent working state
    - a cached legal-move set for the current position
    """

    def __init__(self, config: SessionConfig, game: Game | None = None):
        self._legal_moves: set[Move] = set()
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
              parse state, highlights, and feedback
            - refreshes cached legal moves and other derived position state
        """
        self._bootstrap_session(
            config=self._config if config is None else config,
            game=None,
        )
        self._set_action_message("Game restarted.")

    # ============================================================================
    # Draft editing
    # ============================================================================

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
            - does nothing if the game has already concluded
            - derives the next move-draft text from the current draft,
              parse result, legal moves, and clicked square
            - stores that derived text through `set_move_text()`, so the
              standard parse/update path is reused

        Notes:
            This method does not apply a move directly. Clicks only edit the
            draft text.
        """
        if self._game.outcome != "":
            return

        self.set_move_text(
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
                The promotion piece chosen by the user.

        Behavior:
            - scans the current parse result's matching moves for a promotion move
            whose promotion piece matches the requested value
            - when a match is found, rewrites the draft to that move's canonical
            text through ``set_move_text()``
            - reuses the normal parse/update path so the draft, highlights, and
            promotion prompt state refresh consistently
        """
        for move in self._state.parse_result.matching_moves:
            if get_promotion(move) == piece:
                self.set_move_text(get_canonical(move))
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
            self._set_error_message("Game has concluded.")
            return MoveAttemptResult(False, "game_over", "Game has concluded.")

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

        Success behavior:
            - calls the engine undo operation for the resolved scope
            - refreshes cached legal moves and last-move highlight state
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
        if self._config.opponent == "online":
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Can't undo in an online game.")
            return UndoResult(False, "unavailable", "Can't undo in an online game.")

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
            self._set_error_message("No move to undo.")
            return UndoResult(False, "unavailable", "No move to undo.")
        except Exception:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Could not undo move.")
            return UndoResult(False, "error", "Could not undo move.")
        else:
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
            self._set_error_message("Game has concluded.")
            return ResignResult(False, "game_over", "Game has concluded.")
        except Exception:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Could not resign game.")
            return ResignResult(False, "error", "Could not resign game.")
        else:
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
                A presentation-friendly snapshot containing board glyphs, turn
                information, highlights, move history, draft-input state, check state,
                opponent-sensitive action availability flags, and user-facing feedback
                messages.
        """
        return build_snapshot(
            self._game,
            SnapshotInputs(
                move_text=self._state.move_text,
                parse_result=self._state.parse_result,
                last_move_from=self._state.last_move_from,
                last_move_to=self._state.last_move_to,
                outcome_banner=self._state.outcome_banner,
                last_error_message=self._state.last_error_message,
                last_action_message=self._state.last_action_message,
                opponent_type=self._config.opponent,
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
        self._refresh_position_state(clear_move_text=False)

    def _apply_resolved_move(
        self,
        move: Move,
        offer_draw: bool = False,
    ) -> MoveAttemptResult:
        try:
            self._game.make_move(move, draw_offered=offer_draw)
        except IllegalMoveError:
            self._set_error_message("Could not apply illegal move.")
            return MoveAttemptResult(False, "illegal", "Could not apply illegal move.")
        except GameConcludedError:
            self._refresh_position_state(clear_move_text=False)
            self._set_error_message("Game has concluded.")
            return MoveAttemptResult(False, "game_over", "Game has concluded.")
        except Exception:
            self._set_error_message("Could not apply move.")
            return MoveAttemptResult(False, "error", "Could not apply move.")
        else:
            self._refresh_position_state(clear_move_text=True)
            action_message = f"Played {get_canonical(move)}."
            self._set_action_message(action_message)
            return MoveAttemptResult(True, "applied", action_message)

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

    def _set_action_message(self, message: str | None) -> None:
        self._state.last_action_message = message
        self._state.last_error_message = None

    def _set_error_message(self, message: str | None) -> None:
        self._state.last_error_message = message
        self._state.last_action_message = None
