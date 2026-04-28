from src.engine.moves import Move, get_final_position, get_initial_position
from .move_parser import ParseResult, get_canonical
from .session_types import Square


def click_to_move_text(
    current_text: str,
    parse_result: ParseResult,
    legal_moves: set[Move],
    square: Square,
) -> str:
    """
    Derive the next move-draft text from a click on a board square.

    Parameters:
        current_text (str):
            The current raw draft text before the click.

        parse_result (ParseResult):
            The current parse result for `current_text`, used as the active
            click context.

        legal_moves (set[Move]):
            The legal moves in the current position.

        square (Square):
            The clicked board square.

    Returns:
        str:
            The next draft text to store.

    Behavior:
        - starts from the parser-implied candidate move set for the current
          draft, or from all legal moves when the draft is empty
        - if the current draft implies a unique source square, clicking that
          same source clears the draft
        - if the current draft implies a unique source square, clicking a
          legal target refines the draft toward moves to that target
        - otherwise, clicking a candidate source refines the draft toward
          moves from that source
        - if refinement fails, clicking a movable square replaces the draft
          with a new source-based canonical prefix
        - if the click does not correspond to any useful refinement or
          replacement, the current draft text is returned unchanged
    """
    active = _active_candidates(parse_result, legal_moves)

    # First try to refine the current draft.
    if active:
        unique_source = _unique_source(active)

        # If current draft already implies one source, a click on that source clears.
        if unique_source is not None and square == unique_source:
            return ""

        # If current draft already implies one source, prefer destination refinement.
        if unique_source is not None:
            by_target = _moves_to(active, square)
            if by_target:
                return _canonical_prefix(by_target)

        # Otherwise try source refinement inside the current candidate set.
        by_source = _moves_from(active, square)
        if by_source:
            return _canonical_prefix(by_source)

    # If refinement failed, try replacing the draft with a new source selection.
    replacement = _moves_from(sorted(legal_moves, key=get_canonical), square)
    if replacement:
        return _canonical_prefix(replacement)

    # Dead-end click: keep current text unchanged.
    return current_text


def _common_prefix(texts: list[str]) -> str:
    if not texts:
        return ""

    prefix = texts[0]
    for text in texts[1:]:
        i = 0
        while i < len(prefix) and i < len(text) and prefix[i] == text[i]:
            i += 1
        prefix = prefix[:i]
    return prefix


def _canonical_prefix(moves: list[Move]) -> str:
    return _common_prefix(sorted(get_canonical(move) for move in moves))


def _moves_from(moves: list[Move], square: Square) -> list[Move]:
    return [move for move in moves if get_initial_position(move) == square]


def _moves_to(moves: list[Move], square: Square) -> list[Move]:
    return [move for move in moves if get_final_position(move) == square]


def _unique_source(moves: list[Move]) -> Square | None:
    sources = {get_initial_position(move) for move in moves}
    if len(sources) == 1:
        return next(iter(sources))
    return None


def _active_candidates(parse_result: ParseResult, legal_moves: set[Move]) -> list[Move]:
    if parse_result.status == "empty":
        return sorted(legal_moves, key=get_canonical)

    if parse_result.status == "no_match":
        return []

    return list(parse_result.matching_moves)
