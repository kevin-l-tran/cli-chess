from dataclasses import dataclass
from typing import Callable

from engine.game import Game
from application.intents import CursorMove, GameUpdate


@dataclass
class UiState:
    selected: list[tuple[int, int]] = []
    cursor: tuple[int, int] = (0, 0)
    flipped: bool = False
    show_legal_targets: bool = True


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
