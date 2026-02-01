from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.moves import Move


class Board:
    """
    Represents a chess board.

    Attributes:
        board (list[list[Piece | None]]): An 8x8 array representing the board.
    """

    def __init__(self) -> None:
        pass


class Piece(ABC):
    """
    Represents a chess piece.

    Attributes:
        is_white (bool): Whether the piece is white or black.
        position (tuple[int, int]): The position of the piece.
    """

    def __init__(self, is_white: bool, position: tuple[int, int]) -> None:
        self.is_white = is_white
        self.position = position

    @abstractmethod
    def get_psuedo_moves(self, board: Board) -> list[Move]:
        """Returns a list of all possible moves this piece can make."""
        pass


class Pawn(Piece):
    def __init__(
        self, is_white: bool, position: tuple[int, int], is_at_start: bool = True
    ) -> None:
        super().__init__(is_white, position)
        self.is_at_start = is_at_start

    def get_psuedo_moves(self, board: Board) -> list[Move]:
        return super().get_psuedo_moves(board)


class Rook(Piece):
    def __init__(self, is_white: bool, position: tuple[int, int]) -> None:
        super().__init__(is_white, position)

    def get_psuedo_moves(self, board: Board) -> list[str]:
        return super().get_psuedo_moves(board)


class Knight(Piece):
    def __init__(self, is_white: bool, position: tuple[int, int]) -> None:
        super().__init__(is_white, position)

    def get_psuedo_moves(self, board: Board) -> list[str]:
        return super().get_psuedo_moves(board)


class Bishop(Piece):
    def __init__(self, is_white: bool, position: tuple[int, int]) -> None:
        super().__init__(is_white, position)

    def get_psuedo_moves(self, board: Board) -> list[str]:
        return super().get_psuedo_moves(board)


class Queen(Piece):
    def __init__(self, is_white: bool, position: tuple[int, int]) -> None:
        super().__init__(is_white, position)

    def get_psuedo_moves(self, board: Board) -> list[str]:
        return super().get_psuedo_moves(board)


class King(Piece):
    def __init__(self, is_white: bool, position: tuple[int, int]) -> None:
        super().__init__(is_white, position)

    def get_psuedo_moves(self, board: Board) -> list[str]:
        return super().get_psuedo_moves(board)
