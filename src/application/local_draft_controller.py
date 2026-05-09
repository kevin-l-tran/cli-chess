from typing import Literal

from src.application import viewer_types as vt
from src.application.local_click_draft_helper import click_to_move_text
from src.application.viewer_types import LocalDraftView, ViewerSessionView
from src.shared.protocol_types import Square


class LocalDraftController:
    """
    Client-local draft controller.

    Owns only uncommitted draft state. All data is derived from 
    the ViewerSessionView passed down by the authoritative session 
    controller.
    """

    def __init__(self) -> None:
        self._current_ply: int | None = None
        self._draft_ply: int | None = None
        self._hints: vt.MovePreviewHints | None = None
        self._promotion_family: tuple[vt.MovePreviewCandidate, ...] = ()
        self._view = _empty_view()

    def sync_to_view(self, view: ViewerSessionView) -> None:
        """Synchronize draft state with the latest authoritative view."""
        old_ply = self._current_ply
        self._current_ply = view.current_ply

        if (
            view.preview_hints is not None
            and view.preview_hints.base_ply == view.current_ply
        ):
            self._hints = view.preview_hints
        else:
            self._hints = None

        if old_ply is None:
            self._draft_ply = view.current_ply
            return

        if not self._has_active_draft():
            self._draft_ply = view.current_ply
            return

        if self._draft_ply is not None and self._draft_ply != view.current_ply:
            self._promotion_family = ()

            if self._view.text:
                self._view = LocalDraftView(
                    text=self._view.text,
                    status="stale",
                    canonical_text=None,
                    candidate_moves=set(),
                    autocompletions=[],
                    promotion_prompt_position=None,
                    submit_text=None,
                )
            else:
                self._view = _empty_view()

            self._draft_ply = view.current_ply
            return

        # If a draft was created without hints, but hints later become
        # available for the same ply, re-evaluate it locally.
        if (
            self._view.text
            and self._view.status == "unvalidated"
            and self._hints is not None
        ):
            self.set_text(self._view.text)

    def set_text(self, text: str) -> LocalDraftView:
        """Update the draft text and return its local validation view."""
        self._draft_ply = self._current_ply
        self._promotion_family = ()

        if _normalize(text) == "":
            self._view = _empty_view()
            return self._view

        if self._hints is None:
            self._view = LocalDraftView(
                text=text,
                status="unvalidated",
                canonical_text=None,
                candidate_moves=set(),
                autocompletions=[],
                promotion_prompt_position=None,
                submit_text=text,
            )
            return self._view

        matches = self._matching_candidates(text)

        if not matches:
            self._view = LocalDraftView(
                text=text,
                status="no_match",
                canonical_text=None,
                candidate_moves=set(),
                autocompletions=[],
                promotion_prompt_position=None,
                submit_text=None,
            )
            return self._view

        if _is_promotion_family(matches):
            prompt_position = _get_promotion_prompt_position(text, matches)
            self._promotion_family = (
                tuple(matches) if prompt_position is not None else ()
            )

            self._view = LocalDraftView(
                text=text,
                status="ambiguous",
                canonical_text=None,
                candidate_moves=_candidate_edges(matches),
                autocompletions=_autocompletions(text, matches),
                promotion_prompt_position=prompt_position,
                submit_text=None,
            )
            return self._view

        if len(matches) == 1:
            self._view = _resolved_view(
                text=text,
                candidate=matches[0],
            )
            return self._view

        self._view = LocalDraftView(
            text=text,
            status="ambiguous",
            canonical_text=None,
            candidate_moves=_candidate_edges(matches),
            autocompletions=_autocompletions(text, matches),
            promotion_prompt_position=None,
            submit_text=None,
        )
        return self._view

    def clear(self) -> LocalDraftView:
        """Clear the active draft and return an empty draft view."""
        self._draft_ply = self._current_ply
        self._promotion_family = ()
        self._view = _empty_view()
        return self._view

    def click_square(self, square: Square) -> LocalDraftView:
        """Apply a board-square click to the current draft text."""
        self._draft_ply = self._current_ply

        if self._hints is None:
            # With no local hints, clicks cannot be interpreted. Typed drafts
            # can still be submitted as unvalidated text.
            return self._view

        matching_candidates = (
            self._matching_candidates(self._view.text) if self._view.text else []
        )

        next_text = click_to_move_text(
            current_status=self._view.status,
            matching_candidates=matching_candidates,
            hints=self._hints,
            square=square,
        )

        return self.set_text(next_text)

    def select_promotion_piece(
        self,
        piece: Literal["Q", "R", "B", "N"],
    ) -> LocalDraftView:
        """Resolve a pending promotion draft with the selected piece."""
        matching = next(
            (
                candidate
                for candidate in self._promotion_family
                if candidate.promotion_piece == piece
            ),
            None,
        )

        if matching is None:
            return self._view

        self._promotion_family = ()
        return self.set_text(matching.canonical_text)

    def view(self) -> LocalDraftView:
        """Return the current local draft view."""
        return self._view

    def _matching_candidates(
        self,
        text: str,
    ) -> list[vt.MovePreviewCandidate]:
        if self._hints is None:
            return []

        query = _normalize(text)

        matches = [
            candidate
            for candidate in self._hints.legal_moves
            if any(
                _normalize(spelling).startswith(query)
                for spelling in _candidate_spellings(candidate)
            )
        ]

        return sorted(matches, key=lambda candidate: candidate.canonical_text)

    def _has_active_draft(self) -> bool:
        return (
            bool(self._view.text)
            or bool(self._view.candidate_moves)
            or bool(self._promotion_family)
        )


def _empty_view() -> LocalDraftView:
    return LocalDraftView(
        text="",
        status="empty",
        canonical_text=None,
        candidate_moves=set(),
        autocompletions=[],
        promotion_prompt_position=None,
        submit_text=None,
    )


def _resolved_view(
    *,
    text: str,
    candidate: vt.MovePreviewCandidate,
) -> LocalDraftView:
    return LocalDraftView(
        text=text,
        status="resolved",
        canonical_text=candidate.canonical_text,
        candidate_moves={(candidate.from_square, candidate.to_square)},
        autocompletions=[],
        promotion_prompt_position=None,
        submit_text=candidate.canonical_text,
    )


def _candidate_spellings(
    candidate: vt.MovePreviewCandidate,
) -> tuple[str, ...]:
    values = {candidate.canonical_text}
    values.update(candidate.aliases)
    return tuple(sorted(value for value in values if value))


def _candidate_edges(
    candidates: list[vt.MovePreviewCandidate],
) -> set[tuple[Square, Square]]:
    return {(candidate.from_square, candidate.to_square) for candidate in candidates}


def _autocompletions(
    text: str,
    candidates: list[vt.MovePreviewCandidate],
    *,
    limit: int = 12,
) -> list[str]:
    query = _normalize(text)
    seen: set[str] = set()
    values: list[str] = []

    for candidate in sorted(candidates, key=lambda item: item.canonical_text):
        for spelling in _candidate_spellings(candidate):
            if not _normalize(spelling).startswith(query):
                continue
            if spelling in seen:
                continue

            seen.add(spelling)
            values.append(spelling)

            if len(values) >= limit:
                return values

    return values


def _is_promotion_family(
    candidates: list[vt.MovePreviewCandidate],
) -> bool:
    if len(candidates) < 2:
        return False

    first = candidates[0]

    if first.promotion_prompt_position is None:
        return False

    return all(
        candidate.from_square == first.from_square
        and candidate.to_square == first.to_square
        and candidate.promotion_piece is not None
        and candidate.promotion_prompt_position == first.promotion_prompt_position
        for candidate in candidates
    )


def _get_promotion_prompt_position(
    text: str,
    candidates: list[vt.MovePreviewCandidate],
) -> Square | None:
    if not _is_promotion_family(candidates):
        return None

    canonical_texts = [
        candidate.canonical_text
        for candidate in sorted(candidates, key=lambda item: item.canonical_text)
    ]
    prefix = _common_prefix(canonical_texts)

    if _normalize(text) != _normalize(prefix):
        return None
    if not prefix.endswith("="):
        return None

    positions = {
        candidate.promotion_prompt_position
        for candidate in candidates
        if candidate.promotion_prompt_position is not None
    }

    if len(positions) != 1:
        return None

    return next(iter(positions))


def _common_prefix(values: list[str]) -> str:
    if not values:
        return ""

    prefix = values[0]

    for value in values[1:]:
        i = 0
        while i < len(prefix) and i < len(value) and prefix[i] == value[i]:
            i += 1
        prefix = prefix[:i]

    return prefix


def _normalize(text: str) -> str:
    return "".join(text.strip().split()).replace("0", "O").upper()
