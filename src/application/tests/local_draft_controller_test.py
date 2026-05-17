import pytest

from src.application.local_draft_controller import (
    LocalDraftController,
)
from src.application.viewer_types import (
    AuthoritativeSnapshot,
    LocalDraftView,
    MovePreviewCandidate,
    MovePreviewHints,
    ViewerSessionView,
)
from src.shared.ids import LobbyId, PlayerId
from src.shared.protocol_types import PromotionPiece


E2 = (4, 1)
E3 = (4, 2)
E4 = (4, 3)

G1 = (6, 0)
F3 = (5, 2)
H3 = (7, 2)

E7 = (4, 6)
E8 = (4, 7)

A1 = (0, 0)


def candidate(
    canonical_text: str,
    from_square: tuple[int, int],
    to_square: tuple[int, int],
    aliases: set[str] = set(),
    promotion_piece: PromotionPiece | None = None,
    promotion_prompt_position: tuple[int, int] | None = None,
) -> MovePreviewCandidate:
    return MovePreviewCandidate(
        canonical_text=canonical_text,
        aliases=aliases,
        from_square=from_square,
        to_square=to_square,
        promotion_piece=promotion_piece,
        promotion_prompt_position=promotion_prompt_position,
    )


def snapshot() -> AuthoritativeSnapshot:
    return AuthoritativeSnapshot(
        board_glyphs=[["." for _ in range(8)] for _ in range(8)],
        side_to_move="white",
        last_move_from=None,
        last_move_to=None,
        check_square=None,
        move_list=[],
        draw_offered_by=None,
        is_player_checked=False,
        is_game_over=False,
        timed_game=None,
        outcome=None,
        feedback=None,
    )


def view(
    *,
    ply: int = 0,
    view_revision: int = 0,
    hints: MovePreviewHints | None = None,
) -> ViewerSessionView:
    return ViewerSessionView(
        lobby_id=LobbyId("lobby-1"),
        viewer_id=PlayerId("viewer-1"),
        viewer_role="local_controller",
        viewer_side=None,
        current_ply=ply,
        view_revision=view_revision,
        can_submit_for_side="white",
        can_offer_draw=True,
        can_accept_draw=False,
        can_resign=True,
        can_request_undo=True,
        status_text=None,
        snapshot=snapshot(),
        preview_hints=hints,
        connection_state="connected",
    )


@pytest.fixture
def opening_hints() -> MovePreviewHints:
    return MovePreviewHints(
        base_ply=0,
        legal_moves=[
            candidate(
                "Pe2-e3",
                E2,
                E3,
                aliases=set(["e3", "Pe2e3"]),
            ),
            candidate(
                "Pe2-e4",
                E2,
                E4,
                aliases=set(["e4", "Pe2e4"]),
            ),
            candidate(
                "Ng1-f3",
                G1,
                F3,
                aliases=set(["Nf3", "Ng1f3"]),
            ),
            candidate(
                "Ng1-h3",
                G1,
                H3,
                aliases=set(["Nh3", "Ng1h3"]),
            ),
        ],
    )


@pytest.fixture
def promotion_hints() -> MovePreviewHints:
    return MovePreviewHints(
        base_ply=0,
        legal_moves=[
            candidate(
                "Pe7-e8=B",
                E7,
                E8,
                aliases=set(["e8=B", "Pe7e8=B"]),
                promotion_piece="B",
                promotion_prompt_position=E8,
            ),
            candidate(
                "Pe7-e8=N",
                E7,
                E8,
                aliases=set(["e8=N", "Pe7e8=N"]),
                promotion_piece="N",
                promotion_prompt_position=E8,
            ),
            candidate(
                "Pe7-e8=Q",
                E7,
                E8,
                aliases=set(["e8=Q", "Pe7e8=Q"]),
                promotion_piece="Q",
                promotion_prompt_position=E8,
            ),
            candidate(
                "Pe7-e8=R",
                E7,
                E8,
                aliases=set(["e8=R", "Pe7e8=R"]),
                promotion_piece="R",
                promotion_prompt_position=E8,
            ),
        ],
    )


def synced_controller(hints: MovePreviewHints | None) -> LocalDraftController:
    controller = LocalDraftController()
    controller.sync_to_view(view(hints=hints))
    return controller


def assert_empty(draft: LocalDraftView) -> None:
    assert draft.text == ""
    assert draft.status == "empty"
    assert draft.canonical_text is None
    assert draft.candidate_moves == set()
    assert draft.autocompletions == []
    assert draft.promotion_prompt_position is None
    assert draft.submit_text is None


def test_initial_view_is_empty() -> None:
    controller = LocalDraftController()

    assert_empty(controller.view())


def test_clear_returns_empty_view(opening_hints: MovePreviewHints) -> None:
    controller = synced_controller(opening_hints)

    controller.set_text("Pe2-e4")
    draft = controller.clear()

    assert_empty(draft)
    assert_empty(controller.view())


def test_set_text_exact_legal_move_resolves(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    draft = controller.set_text("Pe2-e4")

    assert draft.text == "Pe2-e4"
    assert draft.status == "resolved"
    assert draft.canonical_text == "Pe2-e4"
    assert draft.candidate_moves == {(E2, E4)}
    assert draft.autocompletions == []
    assert draft.promotion_prompt_position is None
    assert draft.submit_text == "Pe2-e4"


def test_set_text_alias_resolves_to_canonical_submit_text(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    draft = controller.set_text("e4")

    assert draft.status == "resolved"
    assert draft.text == "e4"
    assert draft.canonical_text == "Pe2-e4"
    assert draft.candidate_moves == {(E2, E4)}
    assert draft.submit_text == "Pe2-e4"


def test_set_text_san_prefix_returns_san_autocompletions(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    draft = controller.set_text("N")

    assert draft.status == "ambiguous"
    assert draft.canonical_text is None
    assert draft.candidate_moves == {(G1, F3), (G1, H3)}
    assert draft.autocompletions == [
        "Nf3",
        "Ng1-f3",
        "Ng1f3",
        "Ng1-h3",
        "Ng1h3",
        "Nh3",
    ]
    assert draft.promotion_prompt_position is None
    assert draft.submit_text is None


def test_set_text_ambiguous_prefix_returns_candidates_and_autocomplete(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    draft = controller.set_text("Pe2")

    assert draft.status == "ambiguous"
    assert draft.canonical_text is None
    assert draft.candidate_moves == {(E2, E3), (E2, E4)}
    assert draft.autocompletions == [
        "Pe2-e3",
        "Pe2e3",
        "Pe2-e4",
        "Pe2e4",
    ]
    assert draft.promotion_prompt_position is None
    assert draft.submit_text is None


def test_set_text_no_match(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    draft = controller.set_text("bad")

    assert draft.text == "bad"
    assert draft.status == "no_match"
    assert draft.canonical_text is None
    assert draft.candidate_moves == set()
    assert draft.autocompletions == []
    assert draft.promotion_prompt_position is None
    assert draft.submit_text is None


def test_set_text_without_preview_hints_is_unvalidated() -> None:
    controller = synced_controller(None)

    draft = controller.set_text("e4")

    assert draft.text == "e4"
    assert draft.status == "unvalidated"
    assert draft.canonical_text is None
    assert draft.candidate_moves == set()
    assert draft.autocompletions == []
    assert draft.promotion_prompt_position is None
    assert draft.submit_text == "e4"


def test_click_without_preview_hints_does_not_change_draft() -> None:
    controller = synced_controller(None)

    draft = controller.click_square(E2)

    assert_empty(draft)


def test_click_source_square_creates_ambiguous_source_draft(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    draft = controller.click_square(E2)

    assert draft.status == "ambiguous"
    assert draft.text == "Pe2"
    assert draft.canonical_text is None
    assert draft.candidate_moves == {(E2, E3), (E2, E4)}
    assert draft.autocompletions == [
        "Pe2-e3",
        "Pe2e3",
        "Pe2-e4",
        "Pe2e4",
    ]
    assert draft.submit_text is None


def test_click_source_then_destination_resolves_move(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    controller.click_square(E2)
    draft = controller.click_square(E4)

    assert draft.status == "resolved"
    assert draft.text == "Pe2-e4"
    assert draft.canonical_text == "Pe2-e4"
    assert draft.candidate_moves == {(E2, E4)}
    assert draft.submit_text == "Pe2-e4"


def test_click_dead_square_from_empty_draft_keeps_empty(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    draft = controller.click_square(A1)

    assert_empty(draft)


def test_click_invalid_draft_on_movable_source_replaces_draft(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    controller.set_text("bad")
    draft = controller.click_square(E2)

    assert draft.status == "ambiguous"
    assert draft.text == "Pe2"
    assert draft.candidate_moves == {(E2, E3), (E2, E4)}
    assert draft.submit_text is None


def test_click_invalid_draft_on_dead_square_clears_draft(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    controller.set_text("bad")
    draft = controller.click_square(A1)

    assert_empty(draft)


def test_promotion_text_prefix_sets_promotion_prompt(
    promotion_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(promotion_hints)

    draft = controller.set_text("Pe7-e8=")

    assert draft.status == "ambiguous"
    assert draft.canonical_text is None
    assert draft.candidate_moves == {(E7, E8)}
    assert draft.autocompletions == [
        "Pe7-e8=B",
        "Pe7-e8=N",
        "Pe7-e8=Q",
        "Pe7-e8=R",
    ]
    assert draft.promotion_prompt_position == E8
    assert draft.submit_text is None


def test_click_promotion_source_then_destination_sets_promotion_prompt(
    promotion_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(promotion_hints)

    controller.click_square(E7)
    draft = controller.click_square(E8)

    assert draft.status == "ambiguous"
    assert draft.text == "Pe7-e8="
    assert draft.candidate_moves == {(E7, E8)}
    assert draft.promotion_prompt_position == E8
    assert draft.submit_text is None


def test_select_promotion_piece_resolves_submit_text(
    promotion_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(promotion_hints)

    controller.set_text("Pe7-e8=")
    draft = controller.select_promotion_piece("Q")

    assert draft.status == "resolved"
    assert draft.text == "Pe7-e8=Q"
    assert draft.canonical_text == "Pe7-e8=Q"
    assert draft.candidate_moves == {(E7, E8)}
    assert draft.promotion_prompt_position is None
    assert draft.submit_text == "Pe7-e8=Q"


def test_select_promotion_piece_without_pending_family_is_noop(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    before = controller.set_text("Pe2-e4")
    after = controller.select_promotion_piece("Q")

    assert after == before


def test_sync_to_new_ply_marks_text_draft_stale(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    controller.set_text("Pe2-e4")

    new_hints = MovePreviewHints(
        base_ply=1,
        legal_moves=[
            candidate(
                "Pe7-e5",
                E7,
                (4, 4),
                aliases=set(["e5", "Pe7e5"]),
            )
        ],
    )
    controller.sync_to_view(view(ply=1, hints=new_hints))

    draft = controller.view()

    assert draft.text == "Pe2-e4"
    assert draft.status == "stale"
    assert draft.canonical_text is None
    assert draft.candidate_moves == set()
    assert draft.autocompletions == []
    assert draft.promotion_prompt_position is None
    assert draft.submit_text is None


def test_sync_to_new_ply_marks_click_generated_text_stale(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    controller.click_square(E2)

    new_hints = MovePreviewHints(base_ply=1, legal_moves=[])
    controller.sync_to_view(view(ply=1, hints=new_hints))

    draft = controller.view()

    assert draft.text == "Pe2"
    assert draft.status == "stale"
    assert draft.canonical_text is None
    assert draft.candidate_moves == set()
    assert draft.autocompletions == []
    assert draft.promotion_prompt_position is None
    assert draft.submit_text is None


def test_unvalidated_text_reparses_when_hints_arrive() -> None:
    controller = synced_controller(None)

    draft = controller.set_text("e4")
    assert draft.status == "unvalidated"

    hints = MovePreviewHints(
        base_ply=0,
        legal_moves=[
            candidate(
                "Pe2-e4",
                E2,
                E4,
                aliases=set(["e4", "Pe2e4"]),
            )
        ],
    )
    controller.sync_to_view(view(ply=0, hints=hints))

    draft = controller.view()

    assert draft.status == "resolved"
    assert draft.canonical_text == "Pe2-e4"
    assert draft.submit_text == "Pe2-e4"


def test_click_new_movable_source_replaces_existing_partial_source_draft(
    opening_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(opening_hints)

    controller.click_square(E2)
    draft = controller.click_square(G1)

    assert draft.status == "ambiguous"
    assert draft.text == "Ng1"
    assert draft.canonical_text is None
    assert draft.candidate_moves == {(G1, F3), (G1, H3)}
    assert draft.autocompletions == [
        "Ng1-f3",
        "Ng1f3",
        "Ng1-h3",
        "Ng1h3",
    ]
    assert draft.promotion_prompt_position is None
    assert draft.submit_text is None


def test_click_promotion_source_only_does_not_show_prompt(
    promotion_hints: MovePreviewHints,
) -> None:
    controller = synced_controller(promotion_hints)

    draft = controller.click_square(E7)

    assert draft.status == "ambiguous"
    assert draft.text == "Pe7"
    assert draft.canonical_text is None
    assert draft.candidate_moves == {(E7, E8)}
    assert draft.autocompletions == [
        "Pe7-e8=B",
        "Pe7e8=B",
        "Pe7-e8=N",
        "Pe7e8=N",
        "Pe7-e8=Q",
        "Pe7e8=Q",
        "Pe7-e8=R",
        "Pe7e8=R",
    ]
    assert draft.promotion_prompt_position is None
    assert draft.submit_text is None
