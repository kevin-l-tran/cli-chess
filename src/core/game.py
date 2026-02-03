from core.board import Board
from core.moves import get_piece


class Game:
    """
    Represents a chess game.

    Attributes:
        board (Board): The game board object.
        encountered_positions (dict[str, int]): A hashmap of encountered board positions to number of encounters.
        stale_moves (int): Number of moves since the last capture or pawn movement.
        is_white_turn (bool): Whether it is the white player's turn.
        outcome (str): String indicating the game outcome. It is empty if the game is ongoing.
    """

    def __init__(self) -> None:
        self.board = Board()
        self.encountered_positions: dict[str, int] = {}
        self.stale_moves = 0
        self.is_white_turn = True
        self.outcome = ""

        self.encountered_positions[self._get_position_hash()] = 1

    def _get_position_hash(self):
        hash = ""

        for r in self.board.board:
            for p in r:
                if p is None:
                    hash += "."
                else:
                    hash += get_piece(p)

        return hash
