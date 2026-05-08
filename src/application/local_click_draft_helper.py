from src.application import viewer_types as vt
from src.shared.protocol_types import Square


def click_to_move_text(
    *,
    current_status: vt.DraftStatus,
    matching_candidates: list[vt.MovePreviewCandidate],
    hints: vt.MovePreviewHints,
    square: Square,
) -> str:
    """
    Derive the next local move-draft text from a board-square click.

    Behavior:
    - empty draft: clicking a movable source starts a source draft, e.g. "Pe2"
    - no-match/stale/unvalidated draft: clicking a movable source replaces it
    - valid draft: clicking a legal destination refines the current match set
    - otherwise: clicking a movable source replaces the draft
    - dead-end click: clears the draft by returning ""
    """
    legal = sorted(
        hints.legal_moves,
        key=lambda candidate: candidate.canonical_text,
    )
    matched = sorted(
        matching_candidates,
        key=lambda candidate: candidate.canonical_text,
    )

    if current_status == "empty":
        by_source = _candidates_from(legal, square)
        return _source_prefix(square, by_source) if by_source else ""

    if current_status in {"no_match", "stale", "unvalidated"}:
        by_source = _candidates_from(legal, square)
        return _source_prefix(square, by_source) if by_source else ""

    by_target = _candidates_to(matched, square)
    if by_target:
        return _canonical_prefix(by_target)

    by_source = _candidates_from(legal, square)
    if by_source:
        return _source_prefix(square, by_source)

    return ""


def _candidates_from(
    candidates: list[vt.MovePreviewCandidate],
    square: Square,
) -> list[vt.MovePreviewCandidate]:
    return [candidate for candidate in candidates if candidate.from_square == square]


def _candidates_to(
    candidates: list[vt.MovePreviewCandidate],
    square: Square,
) -> list[vt.MovePreviewCandidate]:
    return [candidate for candidate in candidates if candidate.to_square == square]


def _source_prefix(
    square: Square,
    candidates: list[vt.MovePreviewCandidate],
) -> str:
    """
    Return a parser-compatible source prefix.
    """
    if not candidates:
        return ""

    square_name = _square_name(square)

    for candidate in candidates:
        for spelling in _candidate_spellings(candidate):
            normalized = _normalize(spelling)
            source_index = normalized.find(square_name.upper())

            # For canonical/full move spellings, this finds "Pe2".
            if source_index > 0:
                return spelling[: source_index + len(square_name)]

    first = candidates[0].canonical_text
    if len(first) >= 3:
        return first[:3]

    return square_name


def _canonical_prefix(
    candidates: list[vt.MovePreviewCandidate],
) -> str:
    if not candidates:
        return ""

    texts = [candidate.canonical_text for candidate in candidates]
    prefix = texts[0]

    for text in texts[1:]:
        i = 0
        while i < len(prefix) and i < len(text) and prefix[i] == text[i]:
            i += 1
        prefix = prefix[:i]

    return prefix


def _candidate_spellings(
    candidate: vt.MovePreviewCandidate,
) -> tuple[str, ...]:
    values = {candidate.canonical_text}
    values.update(candidate.aliases)
    return tuple(sorted(value for value in values if value))


def _square_name(square: Square) -> str:
    file, rank = square
    return chr(ord("a") + file) + str(rank + 1)


def _normalize(text: str) -> str:
    return "".join(text.strip().split()).replace("0", "O").upper()
