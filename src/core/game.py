from typing import Callable
from .board import Board
from .moves import Move, get_captured_piece, get_piece


class Game:
    """
    Represents a chess game.

    Attributes:
        board (Board): The game board object.
        moves_list (list[Move]): List of moves played.
        commands_list (list[tuple[Callable[[Board], None], Callable[[Board], None]]]): List of apply/undo move commands.
        encountered_positions (dict[str, int]): A hashmap of encountered board positions to number of encounters.
        is_white_turn (bool): Whether it is the white player's turn.
        outcome (str): String indicating the game outcome. It is empty if the game is ongoing.
    """

    def __init__(self) -> None:
        self.board = Board()
        self.moves_list: list[Move] = []
        self.commands_list: list[tuple[Callable[[
            Board], None], Callable[[Board], None]]] = []
        self.encountered_positions: dict[str, int] = {}
        self.is_white_turn = True
        self.outcome = ""

        self.encountered_positions[self._get_position_hash()] = 1

    def get_moves(self) -> set[Move]:
        return self.board.get_moves(self.is_white_turn)

    def make_move(self, move: Move) -> None:
        if self.outcome != "":
            raise Exception(
                f"The game has already been concluded: {self.outcome}")
        if move not in self.get_moves():
            raise Exception(f"This is not a legal move: {move}")

        commands = self.board.get_move_command(move)
        self.commands_list.append(commands)
        self.moves_list.append(move)

        self.commands_list[-1][0](self.board)  # apply move

        position = self._get_position_hash()
        if self.encountered_positions.get(position) is not None:
            self.encountered_positions[position] += 1
        else:
            self.encountered_positions[position] = 1

        self.is_white_turn = not self.is_white_turn

        # verify win/draw conditions
        if self._get_num_stale_moves() >= 50:
            self.outcome = "1/2-1/2"
        elif self.encountered_positions[position] >= 3:
            self.outcome = "1/2-1/2"
        # stalemate
        elif not self.board.get_moves(self.is_white_turn) and not self.board.is_checked(self.is_white_turn):
            self.outcome = "1/2-1/2"
        elif not self.board.get_moves(self.is_white_turn):
            self.outcome = "1-0" if not self.is_white_turn else "0-1"

    def _get_num_stale_moves(self) -> int:
        stale_moves = 0

        for move in self.moves_list:
            if get_piece(move) == "P":
                stale_moves = 0
            elif get_captured_piece(move) is not None:
                stale_moves = 0
            else:
                stale_moves += 1

        return stale_moves

    def _get_position_hash(self):
        hash = ""

        for r in self.board.board:
            for p in r:
                if p is None:
                    hash += "."
                else:
                    hash += get_piece(p)

        return hash
