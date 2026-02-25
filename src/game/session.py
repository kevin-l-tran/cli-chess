from dataclasses import dataclass
from typing import Callable

from core.game import Game
from game.state import UiState


class GameUpdate:
    pass


@dataclass(frozen=True)
class CursorMove(GameUpdate):
    dx: int
    dy: int


class GameSession:
    def __init__(self):
        self.game = Game()
        self.ui: UiState
        self._listeners: list[Callable] = []

    def subscribe(self, fn: Callable):
        self._listeners.append(fn)

    def dispatch(self, intent: GameUpdate):
        if isinstance(intent, CursorMove):
            self._update_cursor(intent)

    def _update_cursor(self, update: CursorMove):
        r, f = self.ui.cursor
        self.ui.cursor = (
            max(0, min(7, r + update.dy)),
            max(0, min(7, f + update.dx)),
        )
