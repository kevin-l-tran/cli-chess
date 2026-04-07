from dataclasses import dataclass
from typing import Literal

from src.engine.moves import (
    Move,
    get_captured_piece,
    get_castle,
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


def _normalize_move_text(text: str) -> str:
    """Trim surrounding whitespace and remove all internal spaces."""
    return "".join(text.strip().split())


def _get_square_name(s: Square) -> str:
    """Takes a Square object and returns a string representation of it."""
    return chr(ord("a") + s[0]) + str(s[1] + 1)


def _ambiguous_siblings(move: Move, legal_moves: set[Move]) -> list[Move]:
    """Takes a move and a set of legal moves and returns legal moves with the same piece type and destination square."""
    piece = get_piece(move)
    to_sq = get_final_position(move)

    siblings = []
    for other in legal_moves:
        if other == move:
            continue
        if get_piece(other) != piece:
            continue
        if get_final_position(other) != to_sq:
            continue
        siblings.append(other)

    return siblings


def _san_disambiguator(
    move: Move,
    legal_moves: set[Move],
) -> Literal["none", "file", "rank", "full"]:
    """Returns the minimal square representation needed to distinguish a move from its siblings."""
    siblings = _ambiguous_siblings(move, legal_moves)
    if not siblings:
        return "none"

    from_sq = _get_square_name(get_initial_position(move))
    from_file = from_sq[0]
    from_rank = from_sq[1]

    file_conflict = any(
        _get_square_name(get_initial_position(other))[0] == from_file
        for other in siblings
    )
    rank_conflict = any(
        _get_square_name(get_initial_position(other))[1] == from_rank
        for other in siblings
    )

    # if file alone distinguishes, use file
    # else if rank alone distinguishes, use rank
    # else use full square
    if not file_conflict:
        return "file"
    if not rank_conflict:
        return "rank"
    return "full"


def _get_san_compatible(
    move: Move,
    legal_moves: set[Move]
) -> list[str]:
    """Returns the SAN/SAN-compatible representations of a move."""
    sans = []

    castle = get_castle(move)
    if castle == "0-0":
        sans.append("O-O")
    if castle == "0-0-0":
        sans.append("O-O-O")

    piece = get_piece(move)
    from_sq = _get_square_name(get_initial_position(move))
    to_sq = _get_square_name(get_final_position(move))
    is_capture = get_captured_piece(move) is not None
    promotion = get_promotion(move)

    if piece == "P":
        if is_capture:
            san = f"{from_sq[0]}x{to_sq}"
        else:
            san = to_sq
        if promotion is not None:
            san += f"={promotion}"
        sans.append(san)
    
    from_file = from_sq[0]
    from_rank = from_sq[1]

    disambiguator = _san_disambiguator(move, legal_moves)
    divider = "x" if is_capture is not None else "-"
    if disambiguator is "none":
        sans.append(f"{piece}{from_file}{divider}{to_sq}")
        sans.append(f"{piece}{from_rank}{divider}{to_sq}")
    elif disambiguator is "file":
        sans.append(f"{piece}{from_file}{divider}{to_sq}")
    elif disambiguator is "rank":
        sans.append(f"{piece}{from_rank}{divider}{to_sq}")
    sans.append(f"{piece}{from_sq}{divider}{to_sq}")

    return sans


def _get_canonical(
    move: Move,
) -> str:
    """
    Returns the canonical representation of a move.
    """
    piece = get_piece(move)
    from_sq = _get_square_name(get_initial_position(move))
    to_sq = _get_square_name(get_final_position(move))
    divider = "x" if get_captured_piece(move) is not None else "-"
    text = f"{piece}{from_sq}{divider}{to_sq}"

    promotion = get_promotion(move)
    if promotion is not None:
        text += f"={promotion}"

    return text


