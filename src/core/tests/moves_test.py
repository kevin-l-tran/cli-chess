from __future__ import annotations

from typing import Any, Mapping

import pytest

from src.core import moves


def test_make_move_encodes_correctly_all_fields() -> None:
    m: str = moves.make_move(
        piece="N",
        initial_position=(2, 1),  # b1
        final_position=(3, 3),  # c3
        capture=True,
        en_passant=False,
        check=True,
        checkmate=False,
        promotion=None,
        annotation="!?",
    )
    assert m == "Nb1xc3FTF_!?"


@pytest.mark.parametrize(
    "kwargs, expected_move",
    [
        (
            dict(
                piece="P",
                initial_position=(1, 2),  # a2
                final_position=(1, 4),  # a4
                capture=False,
                en_passant=False,
                check=False,
                checkmate=False,
                promotion=None,
                annotation=None,
            ),
            "Pa2-a4FFF__",
        ),
        (
            dict(
                piece="P",
                initial_position=(5, 7),  # e7
                final_position=(5, 8),  # e8
                capture=True,
                en_passant=False,
                check=False,
                checkmate=True,
                promotion="Q",
                annotation="!!",
            ),
            "Pe7xe8FFTQ!!",
        ),
        (
            dict(
                piece="P",
                initial_position=(4, 5),  # d5
                final_position=(5, 6),  # e6
                capture=True,
                en_passant=True,
                check=False,
                checkmate=False,
                promotion=None,
                annotation="--",
            ),
            "Pd5xe6TFF_--",
        ),
    ],
)
def test_make_move_various_cases(kwargs: Mapping[str, Any], expected_move: str) -> None:
    m: str = moves.make_move(**kwargs)
    assert m == expected_move


def test_getters_round_trip_for_basic_move() -> None:
    m: str = moves.make_move(
        piece="B",
        initial_position=(3, 1),  # c1
        final_position=(6, 4),  # f4
        capture=False,
        en_passant=False,
        check=False,
        checkmate=False,
        promotion=None,
        annotation=None,
    )

    assert moves.get_piece(m) == "B"
    assert moves.get_initial_position(m) == (3, 1)
    assert moves.is_capture(m) is False
    assert moves.get_final_position(m) == (6, 4)
    assert moves.is_en_passant(m) is False
    assert moves.is_check(m) is False
    assert moves.is_checkmate(m) is False
    assert moves.get_promotion(m) is None
    assert moves.get_rating(m) is None


def test_get_promotion_and_rating_present() -> None:
    m: str = moves.make_move(
        piece="P",
        initial_position=(7, 7),  # g7
        final_position=(8, 8),  # h8
        capture=True,
        en_passant=False,
        check=True,
        checkmate=True,
        promotion="N",
        annotation="??",
    )
    assert moves.get_promotion(m) == "N"
    assert moves.get_rating(m) == "??"


@pytest.mark.parametrize(
    "bad_piece",
    ["", "p", "X", "KK", "1", None],
)
def test_make_move_rejects_invalid_piece(bad_piece: Any) -> None:
    with pytest.raises(AssertionError):
        moves.make_move(
            piece=bad_piece,
            initial_position=(1, 2),
            final_position=(1, 3),
            capture=False,
            en_passant=False,
            check=False,
            checkmate=False,
            promotion=None,
            annotation=None,
        )


@pytest.mark.parametrize(
    "bad_position",
    [
        (0, 1),
        (1, 0),
        (9, 1),
        (1, 9),
        (1,),
        (1, 2, 3),
        ("a", 2),
    ],
)
def test_make_move_rejects_invalid_positions(bad_position: Any) -> None:
    with pytest.raises(AssertionError):
        moves.make_move(
            piece="P",
            initial_position=bad_position,
            final_position=(1, 3),
            capture=False,
            en_passant=False,
            check=False,
            checkmate=False,
            promotion=None,
            annotation=None,
        )

    with pytest.raises(AssertionError):
        moves.make_move(
            piece="P",
            initial_position=(1, 2),
            final_position=bad_position,
            capture=False,
            en_passant=False,
            check=False,
            checkmate=False,
            promotion=None,
            annotation=None,
        )


@pytest.mark.parametrize("bad_promotion", ["", "p", "X", "A", "9"])
def test_make_move_rejects_invalid_promotion(bad_promotion: str) -> None:
    with pytest.raises(AssertionError):
        moves.make_move(
            piece="P",
            initial_position=(1, 7),
            final_position=(1, 8),
            capture=False,
            en_passant=False,
            check=False,
            checkmate=False,
            promotion=bad_promotion,
            annotation=None,
        )


@pytest.mark.parametrize(
    "bad_annotation", ["", "good", "+=", "??!", "!!!", " -", "x", "?? "]
)
def test_make_move_rejects_invalid_annotation(bad_annotation: str) -> None:
    with pytest.raises(AssertionError):
        moves.make_move(
            piece="P",
            initial_position=(1, 2),
            final_position=(1, 3),
            capture=False,
            en_passant=False,
            check=False,
            checkmate=False,
            promotion=None,
            annotation=bad_annotation,
        )
