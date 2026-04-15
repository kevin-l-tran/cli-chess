from dataclasses import dataclass, field
from typing import Callable, Literal

from engine.game import Game, GameConcludedError, IllegalMoveError
from engine.moves import Move, get_final_position, get_initial_position
from application.intents import CursorMove, GameUpdate
from application.session_types import Square
from application.move_parser import ParseResult

MoveAttemptStatus = Literal["applied", "illegal", "game_over", "error"]


@dataclass(frozen=True)
class MoveAttemptResult:
    ok: bool
    status: MoveAttemptStatus
    message: str | None


@dataclass
class _SessionState:
    cursor: Square | None = (0, 0)
    selected: Square | None = None
    flipped: bool = False

    move_text: str = ""
    parse_result: ParseResult | None = None

    legal_targets: set[Square] = field(default_factory=set)
    last_move_from: Square | None = None
    last_move_to: Square | None = None
    last_error_message: str | None = None


class GameSession:
    def __init__(self, game: Game | None = None):
        self.game = Game() if game is None else game
        self._state: _SessionState = _SessionState()
        self._listeners: list[Callable] = []

    def subscribe(self, fn: Callable):
        self._listeners.append(fn)

    def dispatch(self, intent: GameUpdate):
        if isinstance(intent, CursorMove):
            self._update_cursor(intent)

    def try_make_move(self, move: Move, offer_draw: bool) -> MoveAttemptResult:
        try:
            self.game.make_move(move, draw_offered=offer_draw)
        except IllegalMoveError as e:
            self._state.last_error_message = str(e)
            return MoveAttemptResult(ok=False, status="illegal", message=str(e))
        except GameConcludedError as e:
            self._state.last_error_message = str(e)
            return MoveAttemptResult(ok=False, status="game_over", message=str(e))
        except Exception as e:
            self._state.last_error_message = f"Unexpected error: {str(e)}"
            return MoveAttemptResult(ok=False, status="error", message=str(e))
        else:
            self._state.last_move_from = get_initial_position(move)
            self._state.last_move_to = get_final_position(move)
            self._state.last_error_message = None
            self._state.selected = None
            self._state.legal_targets.clear()
            return MoveAttemptResult(ok=True, status="applied", message=None)

    def _update_cursor(self, update: CursorMove):
        r, f = self._state.cursor if self._state.cursor is not None else (0, 0)
        self._state.cursor = (
            max(0, min(7, r + update.dy)),
            max(0, min(7, f + update.dx)),
        )
