from dataclasses import dataclass

from src.engine.moves import (
    Move,
    get_captured_piece,
    get_castle,
    get_final_position,
    get_initial_position,
    get_piece,
    get_promotion,
)
from .session_types import ParseStatus, Square


@dataclass(frozen=True)
class ParseResult:
    """
    Represents the parse results of an arbitrary move string.

    Attributes:
        raw_text (str):
            The raw text being parsed.

        normalized_text (str):
            The raw text after being normalized according to the move string specifications.

        status (ParseStatus):
            The status of the parse. Parsing can resolve to `empty`, `no_match`, `ambiguous`, or `resolved`.

        matching_moves (list[Move]):
            A list of moves that match the normalized text according to the move string specifications.

        matching_spellings (list[str]):
            A list of move strings that match the normalized text according to the move string specifications.

        source_to_target_highlights (list[tuple[Square, Square]]):
            A list of `(Square, Square)` tuples representing the `(source square, destination square)` of each matched move.

        resolved_move (Move | None):
            The unique move that the normalized text resolves to, if any.

        canonical_text (str | None):
            The canonical text representation, according to the move string specifications, of the resolved move, if it exists.
    """

    raw_text: str
    normalized_text: str
    status: ParseStatus
    matching_moves: list[Move]
    matching_spellings: list[str]
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


def get_canonical(
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


def _get_spellings(move: Move, legal_moves: set[Move]) -> set[str]:
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
    spellings.extend(_get_full(move))

    return set(spellings)


def _collect_matches(
    text: str, legal_moves: set[Move]
) -> tuple[str, list[Move], list[str]]:
    normalized = _normalize_move_text(text)
    if normalized == "":
        return normalized, [], []

    move_to_spellings: list[tuple[Move, list[str]]] = []
    matched_spellings: set[str] = set()

    for move in sorted(legal_moves, key=get_canonical):
        spellings = sorted(_get_spellings(move, legal_moves))
        matched_for_move = [s for s in spellings if s.startswith(normalized)]
        if matched_for_move:
            move_to_spellings.append((move, matched_for_move))
            matched_spellings.update(matched_for_move)

    matching_moves = [move for move, _ in move_to_spellings]
    return normalized, matching_moves, sorted(matched_spellings)


def parse(text: str, legal_moves: set[Move]) -> ParseResult:
    """Takes a text string and converts it into a ParseResult"""
    normalized, matching_moves, matching_spellings = _collect_matches(text, legal_moves)

    # Deliberate special case: keep empty input inert.
    if normalized == "":
        return ParseResult(
            raw_text=text,
            normalized_text=normalized,
            status="empty",
            matching_moves=[],
            matching_spellings=[],
            source_to_target_highlights=[],
            resolved_move=None,
            canonical_text=None,
        )

    source_to_target_highlights = [
        (get_initial_position(move), get_final_position(move))
        for move in matching_moves
    ]

    if not matching_moves:
        status: ParseStatus = "no_match"
        resolved_move = None
        canonical_text = None
    elif len(matching_moves) == 1:
        status = "resolved"
        resolved_move = matching_moves[0]
        canonical_text = get_canonical(resolved_move)
    else:
        status = "ambiguous"
        resolved_move = None
        canonical_text = None

    return ParseResult(
        raw_text=text,
        normalized_text=normalized,
        status=status,
        matching_moves=matching_moves,
        matching_spellings=matching_spellings,
        source_to_target_highlights=source_to_target_highlights,
        resolved_move=resolved_move,
        canonical_text=canonical_text,
    )
