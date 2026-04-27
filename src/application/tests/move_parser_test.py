import pytest

from helpers import make, sq

from src.engine import moves
from src.application import move_parser

Move = moves.Move


def pairset(
    result: move_parser.ParseResult,
) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    return set(result.source_to_target_highlights)


def test_normalize_move_text_trims_and_removes_internal_spaces() -> None:
    assert move_parser._normalize_move_text("  N b1 - c 3  ") == "Nb1-c3"
    assert move_parser._normalize_move_text(" O - O ") == "O-O"


@pytest.mark.parametrize(
    "square, expected",
    [
        ((0, 0), "a1"),
        ((4, 1), "e2"),
        ((7, 7), "h8"),
    ],
)
def test_get_square_name_uses_file_rank_coordinates(
    square: tuple[int, int], expected: str
) -> None:
    assert move_parser._get_square_name(square) == expected


def test_get_spellings_for_unique_piece_move_are_san_and_full_forms_only() -> None:
    move = make("N", "b1", "c3")
    spellings = move_parser.get_spellings(move, {move})

    assert spellings == {"Nc3", "Nb1-c3", "Nb1c3"}


def test_get_spellings_for_pawn_capture_promotion_include_san_and_full_forms() -> None:
    move = make("P", "f7", "e8", capture="R", promotion="N")
    spellings = move_parser.get_spellings(move, {move})

    assert spellings == {"fxe8=N", "Pf7xe8=N", "Pf7e8=N"}


def test_parse_empty_input_is_inert() -> None:
    legal_moves = {make("N", "b1", "c3")}
    result = move_parser.parse("   ", legal_moves)

    assert result.status == "empty"
    assert result.normalized_text == ""
    assert result.matching_moves == []
    assert result.source_to_target_highlights == []
    assert result.resolved_move is None
    assert result.canonical_text is None


def test_parse_whitespace_normalization_resolves_move() -> None:
    target = make("N", "b1", "c3")
    result = move_parser.parse("  N c 3  ", {target})

    assert result.status == "resolved"
    assert result.normalized_text == "Nc3"
    assert result.resolved_move == target
    assert result.canonical_text == "Nb1-c3"


def test_parse_rejects_wrong_case() -> None:
    legal_moves = {make("N", "b1", "c3")}
    result = move_parser.parse("nc3", legal_moves)

    assert result.status == "no_match"
    assert result.matching_moves == []


def test_parse_knight_prefix_from_initial_position_like_set_is_ambiguous() -> None:
    legal_moves = {
        make("N", "b1", "a3"),
        make("N", "b1", "c3"),
        make("N", "g1", "f3"),
        make("N", "g1", "h3"),
    }

    result = move_parser.parse("N", legal_moves)

    assert result.status == "ambiguous"
    assert set(result.matching_moves) == legal_moves
    assert pairset(result) == {
        (sq("b1"), sq("a3")),
        (sq("b1"), sq("c3")),
        (sq("g1"), sq("f3")),
        (sq("g1"), sq("h3")),
    }
    assert result.resolved_move is None
    assert result.canonical_text is None


def test_parse_resolves_san_knight_move() -> None:
    legal_moves = {
        make("N", "b1", "a3"),
        make("N", "b1", "c3"),
        make("N", "g1", "f3"),
        make("N", "g1", "h3"),
    }

    target = make("N", "b1", "c3")
    result = move_parser.parse("Nc3", legal_moves)

    assert result.status == "resolved"
    assert result.resolved_move == target
    assert result.canonical_text == "Nb1-c3"
    assert pairset(result) == {(sq("b1"), sq("c3"))}


def test_parse_pawn_prefix_is_ambiguous_and_full_form_resolves() -> None:
    legal_moves = {
        make("P", "e2", "e3"),
        make("P", "e2", "e4"),
    }

    ambiguous = move_parser.parse("e", legal_moves)
    resolved = move_parser.parse("Pe2e4", legal_moves)

    assert ambiguous.status == "ambiguous"
    assert set(ambiguous.matching_moves) == legal_moves
    assert pairset(ambiguous) == {(sq("e2"), sq("e3")), (sq("e2"), sq("e4"))}

    assert resolved.status == "resolved"
    assert resolved.resolved_move == make("P", "e2", "e4")
    assert resolved.canonical_text == "Pe2-e4"


def test_parse_castling_aliases_work_when_only_one_castle_move_is_legal() -> None:
    kingside = make("K", "e1", "g1")

    for text in ["O-O", "0-0", "o-o"]:
        result = move_parser.parse(text, {kingside})
        assert result.status == "resolved"
        assert result.resolved_move == kingside
        assert result.canonical_text == "O-O"


def test_parse_castling_token_is_ambiguous_when_both_castles_are_legal() -> None:
    legal_moves = {
        make("K", "e1", "g1"),
        make("K", "e1", "c1"),
    }

    # Current parser uses prefix matching even when the text is a complete token,
    # so O-O also matches O-O-O.
    result = move_parser.parse("O-O", legal_moves)

    assert result.status == "ambiguous"
    assert set(result.matching_moves) == legal_moves


def test_parse_uses_minimal_rank_disambiguation_when_two_same_file_pieces_share_destination() -> (
    None
):
    q4 = make("Q", "d4", "d5")
    q6 = make("Q", "d6", "d5")
    legal_moves = {q4, q6}

    assert move_parser._get_sans(q4, legal_moves) == "Q4d5"
    assert move_parser._get_sans(q6, legal_moves) == "Q6d5"

    no_match = move_parser.parse("Qd5", legal_moves)
    resolved = move_parser.parse("Q4d5", legal_moves)

    assert no_match.status == "no_match"
    assert resolved.status == "resolved"
    assert resolved.resolved_move == q4
    assert resolved.canonical_text == "Qd4-d5"


def test_parse_requires_full_square_when_file_and_rank_each_conflict() -> None:
    n_b1 = make("N", "b1", "d2")
    n_b5 = make("N", "b5", "d2")
    n_f1 = make("N", "f1", "d2")
    legal_moves = {n_b1, n_b5, n_f1}

    assert move_parser._get_sans(n_b1, legal_moves) == "Nb1d2"

    # Current parser only accepts the minimal SAN form, not additional
    # overspecified SAN-compatible disambiguators.
    assert move_parser.parse("Nbd2", legal_moves).status == "no_match"
    assert move_parser.parse("N1d2", legal_moves).status == "no_match"

    resolved = move_parser.parse("Nb1d2", legal_moves)
    assert resolved.status == "resolved"
    assert resolved.resolved_move == n_b1
    assert resolved.canonical_text == "Nb1-d2"


def test_parse_capture_canonical_text_uses_x() -> None:
    move = make("Q", "d1", "h5", capture="P")
    result = move_parser.parse("Qxh5", {move})

    assert result.status == "resolved"
    assert result.canonical_text == "Qd1xh5"


def test_parse_returns_no_match_for_unrelated_text() -> None:
    legal_moves = {
        make("N", "b1", "c3"),
        make("P", "e2", "e4"),
    }

    result = move_parser.parse("Zc3", legal_moves)
    assert result.status == "no_match"
    assert result.matching_moves == []
    assert result.source_to_target_highlights == []
