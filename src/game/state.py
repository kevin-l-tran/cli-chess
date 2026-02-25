from dataclasses import dataclass

from core.moves import Move


@dataclass
class UiState:
    selected: list[tuple[int, int]] = []
    cursor: tuple[int, int] = (0, 0)
    flipped: bool = False
    show_legal_targets: bool = True


@dataclass(frozen=True)
class GameView:
    board_glyphs: list[list[str]]
    turn_white: bool
    outcome: str
    last_move: Move | None
    legal_moves: set[Move]
    highlights: set[tuple[int, int]]
    