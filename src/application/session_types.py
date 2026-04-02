from dataclasses import dataclass

from src.engine.moves import Move


@dataclass(frozen=True)
class GameView:
    board_glyphs: list[list[str]]
    turn_white: bool
    outcome: str
    last_move: Move | None
    legal_moves: set[Move]
    highlights: set[tuple[int, int]]