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
    source_to_target_highlights: list[tuple[Square, Square]]
    resolved_move: Move | None
    canonical_text: str | None


def _normalize_move_text(text: str) -> str:
    """Trim surrounding whitespace and remove all internal spaces."""
    return "".join(text.strip().split())


def _get_square_name(s: Square) -> str:
    """Takes a Square object and returns a string representation of it."""
    return chr(ord("a") + s[0]) + str(s[1] + 1)


def _ambiguous_siblings(move: Move, legal_moves: set[Move]) -> list[Move]:
    """Takes a move and a set of legal moves and returns other legal moves with the same piece type and destination square."""
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
) -> str:
    """Returns the minimal square representation needed to distinguish a move from its siblings."""
    siblings = _ambiguous_siblings(move, legal_moves)
    if not siblings:
        return ""

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
        return from_file
    if not rank_conflict:
        return from_rank
    return from_sq


def _get_sans(
    move: Move,
    legal_moves: set[Move],
) -> str:
    """Returns the SAN representation of a move."""
    castle = get_castle(move)
    if castle == "0-0":
        return "O-O"
    if castle == "0-0-0":
        return "O-O-O"

    piece = get_piece(move)
    to_sq = _get_square_name(get_final_position(move))
    promotion = get_promotion(move)

    if piece == "P":
        if get_captured_piece(move) is not None:
            text = f"{_get_square_name(get_initial_position(move))[0]}x{to_sq}"
        else:
            text = to_sq
    else:
        divider = "x" if get_captured_piece(move) is not None else ""
        disambiguator = _san_disambiguator(move, legal_moves)
        text = f"{piece}{disambiguator}{divider}{to_sq}"

    if promotion is not None:
        text += f"={promotion}"

    return text


def _get_full(
    move: Move,
    legal_moves: set[Move],
) -> list[str]:
    """Returns the full representations of a move."""
    piece = get_piece(move)
    from_sq = _get_square_name(get_initial_position(move))
    to_sq = _get_square_name(get_final_position(move))
    divider = "x" if get_captured_piece(move) is not None else "-"

    divtext = f"{piece}{from_sq}{divider}{to_sq}"
    nodivtext = f"{piece}{from_sq}{to_sq}"

    promotion = get_promotion(move)
    if promotion is not None:
        divtext += f"={promotion}"
        nodivtext += f"={promotion}"

    return [divtext, nodivtext]


def _get_canonical(
    move: Move,
) -> str:
    """Returns the canonical move text of a move."""
    castle = get_castle(move)
    if castle == "0-0":
        return "O-O"
    if castle == "0-0-0":
        return "O-O-O"

    piece = get_piece(move)
    from_sq = _get_square_name(get_initial_position(move))
    to_sq = _get_square_name(get_final_position(move))
    divider = "x" if get_captured_piece(move) is not None else "-"
    text = f"{piece}{from_sq}{divider}{to_sq}"

    promotion = get_promotion(move)
    if promotion is not None:
        text += f"={promotion}"

    return text


def _get_spellings(
    move: Move,
    legal_moves: set[Move]
) -> set[str]:
    """Returns the SAN/SAN-compatible representations of a move."""
    spellings = []

    castle = get_castle(move)
    if castle == "0-0":
        spellings.append(castle)
        spellings.append("O-O")
        spellings.append("o-o")
    if castle == "0-0-0":
        spellings.append(castle)
        spellings.append("O-O-O")
        spellings.append("o-o-o")

    spellings.append(_get_sans(move, legal_moves))
    spellings.extend(_get_full(move, legal_moves))

    return set(spellings)


def parse(text: str, legal_moves: set[Move]) -> ParseResult:
    normalized = _normalize_move_text(text)

    # Deliberate special case: keep empty input inert.
    if normalized == "":
        return ParseResult(
            raw_text=text,
            normalized_text=normalized,
            status="empty",
            matching_moves=[],
            source_to_target_highlights=[],
            resolved_move=None,
            canonical_text=None,
        )

    matching_moves: list[Move] = []

    for move in legal_moves:
        spellings = _get_spellings(move, legal_moves)
        if any(spelling.startswith(normalized) for spelling in spellings):
            matching_moves.append(move)

    source_to_target_highlights = [
        (get_initial_position(move), get_final_position(move)) for move in matching_moves
    ]

    if not matching_moves:
        status: ParseStatus = "no_match"
        resolved_move = None
        canonical_text = None
    elif len(matching_moves) == 1:
        status = "resolved"
        resolved_move = matching_moves[0]
        canonical_text = _get_canonical(resolved_move)
    else:
        status = "ambiguous"
        resolved_move = None
        canonical_text = None

    return ParseResult(
        raw_text=text,
        normalized_text=normalized,
        status=status,
        matching_moves=matching_moves,
        source_to_target_highlights=source_to_target_highlights,
        resolved_move=resolved_move,
        canonical_text=canonical_text,
    )
