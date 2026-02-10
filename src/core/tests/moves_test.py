from __future__ import annotations

from typing import Any, Mapping

import pytest

from src.core import moves


def test_make_move_encodes_correctly_all_fields() -> None:
    m: str = moves.make_move(
        piece_name="N",
        initial_position=(1, 0),  # b1
        final_position=(2, 2),  # c3
        capture_name="P",
        en_passant=False,
        promotion=None,
    )
    assert m == "N10P22F_"


@pytest.mark.parametrize(
    "kwargs, expected_move",
    [
        (
            dict(
                piece_name="P",
                initial_position=(0, 1),  # a2
                final_position=(0, 3),  # a4
                capture_name=None,
                en_passant=False,
                promotion=None,
            ),
            "P01-03F_",
        ),
        (
            dict(
                piece_name="P",
                initial_position=(4, 6),  # e7
                final_position=(4, 7),  # e8
                capture_name="R",
                en_passant=False,
                promotion="Q",
            ),
            "P46R47FQ",
        ),
        (
            dict(
                piece_name="P",
                initial_position=(3, 4),  # d5
                final_position=(4, 5),  # e6
                capture_name="B",
                en_passant=True,
                promotion=None,
            ),
            "P34B45T_",
        ),
    ],
)
def test_make_move_various_cases(kwargs: Mapping[str, Any], expected_move: str) -> None:
    m: str = moves.make_move(**kwargs)
    assert m == expected_move


def test_getters_round_trip_for_basic_move() -> None:
    m: str = moves.make_move(
        piece_name="B",
        initial_position=(2, 0),  # c1
        final_position=(5, 3),  # f4
        capture_name="P",
        en_passant=False,
        promotion=None,
    )

    assert moves.get_piece(m) == "B"
    assert moves.get_initial_position(m) == (2, 0)
    assert moves.get_captured_piece(m) == "P"
    assert moves.get_final_position(m) == (5, 3)
    assert moves.is_en_passant(m) is False
    assert moves.get_promotion(m) is None


def test_get_promotion() -> None:
    m: str = moves.make_move(
        piece_name="P",
        initial_position=(6, 6),  # g7
        final_position=(7, 7),  # h8
        capture_name=None,
        en_passant=False,
        promotion="N",
    )
    assert moves.get_promotion(m) == "N"


@pytest.mark.parametrize(
    "bad_piece",
    ["", "p", "X", "KK", "1", None],
)
def test_make_move_rejects_invalid_piece(bad_piece: Any) -> None:
    with pytest.raises(AssertionError):
        moves.make_move(
            piece_name=bad_piece,
            initial_position=(1, 2),
            final_position=(1, 3),
            capture_name=None,
            en_passant=False,
            promotion=None,
        )


@pytest.mark.parametrize(
    "bad_position",
    [
        (-1, 0),
        (0, -1),
        (8, 0),
        (0, 8),
        (0,),
        (0, 1, 2),
        ("a", 1),
    ],
)
def test_make_move_rejects_invalid_positions(bad_position: Any) -> None:
    with pytest.raises(AssertionError):
        moves.make_move(
            piece_name="P",
            initial_position=bad_position,
            final_position=(1, 3),
            capture_name=None,
            en_passant=False,
            promotion=None,
        )

    with pytest.raises(AssertionError):
        moves.make_move(
            piece_name="P",
            initial_position=(1, 2),
            final_position=bad_position,
            capture_name=None,
            en_passant=False,
            promotion=None,
        )


@pytest.mark.parametrize("bad_promotion", ["", "p", "X", "A", "9"])
def test_make_move_rejects_invalid_promotion(bad_promotion: str) -> None:
    with pytest.raises(AssertionError):
        moves.make_move(
            piece_name="P",
            initial_position=(0, 6),
            final_position=(0, 7),
            capture_name=None,
            en_passant=False,
            promotion=bad_promotion,
        )
