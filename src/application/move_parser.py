from dataclasses import dataclass
from typing import Literal

from src.engine.moves import (
    Move,
    get_captured_piece,
    get_final_position,
    get_initial_position,
    get_piece,
    get_promotion
)


Square = tuple[int, int]
ParseStatus = Literal["empty", "no_match", "ambiguous", "resolved"]

FILES = "abcdefgh"
PROMOTION_PIECES = set({"Q", "R", "B", "N"})


@dataclass(frozen=True)
class ParseResult:
    raw_text: str
    normalized_text: str
    status: ParseStatus
    matching_moves: list[Move]
    source_highlights: list[Square]
    target_highlights: list[Square]
    resolved_move: Move | None
    canonical_text: str | None


def normalize_move_text(text: str) -> str:
    """Trim surrounding whitespace and remove all internal spaces."""
    return "".join(text.strip().split())


def get_square_name(s: Square) -> str:
    """Takes a Square object and returns a string representation of it."""
    return chr(ord("a") + s[0]) + str(s[1] + 1)


def canonical_text_for_move(
    move: Move,
) -> str:
    """
    Canonical application-facing spelling.
    """
    piece = get_piece(move)
    from_sq = get_square_name(get_initial_position(move))
    to_sq = get_square_name(get_final_position(move))
    divider = "x" if get_captured_piece(move) is not None else "-"
    text = f"{piece}{from_sq}{divider}{to_sq}"

    promotion = get_promotion(move)
    if promotion is not None:
        text += f"={promotion}"

    return text
