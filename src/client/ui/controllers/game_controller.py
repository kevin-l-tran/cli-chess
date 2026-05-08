from dataclasses import dataclass
from typing import Literal, Protocol, cast

from src.application.session import GameSession
from src.application.session_types import Snapshot, Square, UndoScope


PromotionPiece = Literal["Q", "R", "B", "N"]


class GameController(Protocol):
    def snapshot(self) -> Snapshot: ...
    def set_move_text(self, text: str) -> None: ...
    def click_square(self, square: Square) -> None: ...
    def select_promotion_piece(self, piece: PromotionPiece) -> None: ...
    def confirm_move(self, *, offer_draw: bool = False) -> None: ...
    def accept_draw_offer(self) -> None: ...
    def undo(self, scope: UndoScope) -> None: ...
    def resign(self) -> None: ...
    def restart_game(self) -> None: ...


@dataclass
class CurrentSessionController:
    session: GameSession

    def snapshot(self) -> Snapshot:
        return self.session.snapshot()

    def set_move_text(self, text: str) -> None:
        self.session.set_move_text(text)

    def click_square(self, square: Square) -> None:
        self.session.click_square(square)

    def select_promotion_piece(self, piece: PromotionPiece) -> None:
        self.session.select_promotion_piece(cast(PromotionPiece, piece))

    def confirm_move(self, *, offer_draw: bool = False) -> None:
        self.session.confirm_move_draft(offer_draw=offer_draw)

    def accept_draw_offer(self) -> None:
        self.session.accept_draw_offer()

    def undo(self, scope: UndoScope) -> None:
        self.session.undo(scope)

    def resign(self) -> None:
        self.session.resign()

    def restart_game(self) -> None:
        self.session.restart_game()
