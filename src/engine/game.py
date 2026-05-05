from typing import Callable

from src.engine.evaluations import Evaluation, is_draw_offer, make_evaluation
from .board import Board
from .moves import Move, get_captured_piece, get_piece


class GameError(Exception):
    pass


class IllegalMoveError(GameError):
    pass


class GameConcludedError(GameError):
    pass


class NoDrawOfferError(GameError):
    pass


class NoMoveToUndoError(GameError):
    pass


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
            raise GameConcludedError(self.outcome)
        if move not in self.get_moves():
            raise IllegalMoveError(move)

        commands = self.board.get_move_command(move)
        self.commands_list.append(commands)

        commands[0](self.board)

        # Toggle before hashing. The position key includes side-to-move.
        self.is_white_turn = not self.is_white_turn

        position = self._get_position_hash()
        self.encountered_positions[position] = (
            self.encountered_positions.get(position, 0) + 1
        )

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
        self.moves_list.append((move, evaluation))

        if draw:
            self.outcome = "1/2-1/2"
        if checkmate:
            self.outcome = "1-0" if not self.is_white_turn else "0-1"

    def accept_draw(self) -> None:
        if self.outcome != "":
            raise GameConcludedError(self.outcome)

        if not self.moves_list:
            raise NoDrawOfferError(None)

        _, evaluation = self.moves_list[-1]
        if not is_draw_offer(evaluation):
            raise NoDrawOfferError(evaluation)

        self.outcome = "1/2-1/2"

    def pending_draw_offer_side_is_white(self) -> bool | None:
        if self.outcome != "":
            return None

        if not self.moves_list:
            return None

        _, evaluation = self.moves_list[-1]
        if not is_draw_offer(evaluation):
            return None

        return not self.is_white_turn

    def undo_halfmove(self) -> None:
        if not self.moves_list:
            raise NoMoveToUndoError()

        current_position = self._get_position_hash()
        commands = self.commands_list[-1]

        if current_position in self.encountered_positions:
            self.encountered_positions[current_position] -= 1
            if self.encountered_positions[current_position] <= 0:
                del self.encountered_positions[current_position]

        commands[1](self.board)

        self.commands_list.pop()
        self.moves_list.pop()
        self.is_white_turn = not self.is_white_turn
        self.outcome = ""

    def undo_fullmove(self) -> None:
        if len(self.moves_list) < 2:
            raise NoMoveToUndoError()

        self.undo_halfmove()
        self.undo_halfmove()

    def resign(self) -> None:
        if self.outcome != "":
            raise GameConcludedError(self.outcome)
        self.outcome = "0-1" if self.is_white_turn else "1-0"

    def checked_king_position(self) -> tuple[int, int] | None:
        if not self.board.is_checked(self.is_white_turn):
            return None
        return self.board.king_position(self.is_white_turn)

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
                    hash += p

        hash += "T" if self.is_white_turn else "F"
        if self.board.en_passant_pawn:
            hash += str(self.board.en_passant_pawn)

        return hash
