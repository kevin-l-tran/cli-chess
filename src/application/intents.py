from dataclasses import dataclass


class GameUpdate:
    pass


@dataclass(frozen=True)
class CursorMove(GameUpdate):
    dx: int
    dy: int
