from src.engine.moves import Move, get_final_position, get_initial_position, get_piece
from .move_parser import ParseResult, get_canonical
from .session_types import Square


def click_to_move_text(
    parse_result: ParseResult,
    legal_moves: set[Move],
    square: Square,
) -> str:
    legal = sorted(legal_moves, key=get_canonical)
    matched = sorted(parse_result.matching_moves, key=get_canonical)

    # Empty draft: start a source selection if possible.
    if parse_result.status == "empty":
        by_source = _moves_from(legal, square)
        return _source_prefix(square, by_source) if by_source else ""

    # Invalid draft: replace it if the click is on a movable source; else clear.
    if parse_result.status == "no_match":
        by_source = _moves_from(legal, square)
        return _source_prefix(square, by_source) if by_source else ""

    # Non-empty valid draft:
    # 1) Prefer destination refinement within the currently matched moves.
    by_target = _moves_to(matched, square)
    if by_target:
        return _canonical_prefix(by_target)

    # 2) Otherwise allow source replacement from all legal moves.
    by_source = _moves_from(legal, square)
    if by_source:
        return _source_prefix(square, by_source)

    # 3) Dead-end click self-clears.
    return ""


def _moves_from(moves: list[Move], square: Square) -> list[Move]:
    return [move for move in moves if get_initial_position(move) == square]


def _moves_to(moves: list[Move], square: Square) -> list[Move]:
    return [move for move in moves if get_final_position(move) == square]


def _square_name(square: Square) -> str:
    file, rank = square
    return chr(ord("a") + file) + str(rank + 1)


def _source_prefix(square: Square, moves: list[Move]) -> str:
    return f"{get_piece(moves[0])}{_square_name(square)}"


def _canonical_prefix(moves: list[Move]) -> str:
    texts = [get_canonical(move) for move in moves]
    prefix = texts[0]
    for text in texts[1:]:
        i = 0
        while i < len(prefix) and i < len(text) and prefix[i] == text[i]:
            i += 1
        prefix = prefix[:i]
    return prefix
