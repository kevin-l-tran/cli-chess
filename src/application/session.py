from dataclasses import dataclass
from typing import Callable, Literal

from engine.game import Game, GameConcludedError, IllegalMoveError
from engine.moves import Move, get_final_position, get_initial_position
from application.intents import CursorMove, GameUpdate
from application.session_types import SessionConfig, Square
from application.move_parser import ParseResult, parse

MoveAttemptStatus = Literal["applied", "illegal", "game_over", "error"]


@dataclass(frozen=True)
class MoveAttemptResult:
    ok: bool
    status: MoveAttemptStatus
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

        parse_result (ParseResult | None):
            The most recent parse result for `move_text`, if move text has
            been parsed. This allows the session to keep track of whether the
            current input is empty, invalid, ambiguous, or resolved to a
            unique legal move.

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
    parse_result: ParseResult | None = None
    
    orientation_override: bool | None = None

    last_move_from: Square | None = None
    last_move_to: Square | None = None
    last_error_message: str | None = None


class GameSession:
    def __init__(self, config: SessionConfig, game: Game | None = None):
        self._game = Game() if game is None else game
        self._config = config
        self._state: _SessionState = _SessionState()
        self._legal_moves: set[Move] = set(self._game.get_moves())
        self._listeners: list[Callable] = []

    def subscribe(self, fn: Callable):
        self._listeners.append(fn)

    def dispatch(self, intent: GameUpdate):
        if isinstance(intent, CursorMove):
            self._update_cursor(intent)

    def try_make_move(self, move: Move, offer_draw: bool = False) -> MoveAttemptResult:
        try:
            self._game.make_move(move, draw_offered=offer_draw)
        except IllegalMoveError as e:
            self._state.last_error_message = str(e)
            return MoveAttemptResult(ok=False, status="illegal", message=str(e))
        except GameConcludedError as e:
            self._state.last_error_message = str(e)
            return MoveAttemptResult(ok=False, status="game_over", message=str(e))
        except Exception as e:
            self._state.last_error_message = f"Unexpected error: {str(e)}"
            return MoveAttemptResult(ok=False, status="error", message="Could not apply move.")
        else:
            self._legal_moves = self._game.get_moves()

            self._state.last_move_from = get_initial_position(move)
            self._state.last_move_to = get_final_position(move)
            self._state.last_error_message = None
            self._state.move_text = ""
            self._state.parse_result = parse("", self._legal_moves)
            
            return MoveAttemptResult(ok=True, status="applied", message=None)

    def _update_cursor(self, update: CursorMove):
        r, f = self._state.cursor if self._state.cursor is not None else (0, 0)
        self._state.cursor = (
            max(0, min(7, r + update.dy)),
            max(0, min(7, f + update.dx)),
        )
