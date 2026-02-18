from typing import Callable

from src.core.evaluations import Evaluation, is_draw_offer, make_evaluation
from .board import Board
from .moves import Move, get_captured_piece, get_piece


class Game:
    """
    Represents a chess game.

    Attributes:
        board (Board): The game board object.
        moves_list (list[tuple[Move, Evaluation]]): List of moves played and their evaluations.
        commands_list (list[tuple[Callable[[Board], None], Callable[[Board], None]]]): List of apply/undo move commands.
        encountered_positions (dict[str, int]): A hashmap of encountered board positions to number of encounters.
        is_white_turn (bool): Whether it is the white player's turn.
        outcome (str): String indicating the game outcome. It is empty if the game is ongoing.
    """

    def __init__(self) -> None:
        self.board = Board()
        self.moves_list: list[tuple[Move, Evaluation]] = []
        self.commands_list: list[
            tuple[Callable[[Board], None], Callable[[Board], None]]
        ] = []
        self.encountered_positions: dict[str, int] = {}
        self.is_white_turn = True
        self.outcome = ""

        self.encountered_positions[self._get_position_hash()] = 1

    def get_moves(self) -> set[Move]:
        return self.board.get_moves(self.is_white_turn)

    def make_move(self, move: Move, draw_offered: bool) -> None:
        if self.outcome != "":
            raise Exception("GAME_CONCLUDED")
        if move not in self.get_moves():
            raise Exception("ILLEGAL_MOVE")

        commands = self.board.get_move_command(move)
        self.commands_list.append(commands)  # append commands

        self.commands_list[-1][0](self.board)  # apply move

        position = self._get_position_hash()
        # append encountered position
        if self.encountered_positions.get(position) is not None:
            self.encountered_positions[position] += 1
        else:
            self.encountered_positions[position] = 1

        self.is_white_turn = not self.is_white_turn  # change player turn

        # get evaluation
        check = self.board.is_checked(self.is_white_turn)

        checkmate = check and not self.board.get_moves(self.is_white_turn)

        draw = False
        if self._get_num_stale_moves() >= 100:
            draw = True
        elif self.encountered_positions[position] >= 3:
            draw = True
        elif not self.board.get_moves(self.is_white_turn) and not self.board.is_checked(
            self.is_white_turn
        ):
            draw = True

        evaluation = make_evaluation(check, checkmate, draw, draw_offered)
        self.moves_list.append((move, evaluation))  # append moves

        # set outcomes
        if draw:
            self.outcome = "1/2-1/2"
        if checkmate:
            self.outcome = "1-0" if not self.is_white_turn else "0-1"

    def accept_draw(self) -> None:
        _, evaluation = self.moves_list[-1]
        if not is_draw_offer(evaluation):
            raise Exception("NO_DRAW_OFFER")
        else:
            self.outcome = "1/2-1/2"

    def undo_halfmove(self) -> None:
        if not self.moves_list:
            return
        
        self.moves_list.pop()
        self.encountered_positions[self._get_position_hash()] -= 1
        self.is_white_turn = not self.is_white_turn
        self.outcome = ""
        commands = self.commands_list.pop()

        commands[1](self.board)  # undo move

    def undo_fullmove(self) -> None:
        self.undo_halfmove()
        self.undo_halfmove()

    def _get_num_stale_moves(self) -> int:
        stale_moves = 0

        for move, _ in self.moves_list:
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
