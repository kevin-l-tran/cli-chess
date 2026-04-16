from src.engine import moves

Move = moves.Move


def sq(name: str) -> tuple[int, int]:
    """Convert algebraic square like 'e4' to engine coordinates (file, rank)."""
    assert len(name) == 2
    file = ord(name[0]) - ord("a")
    rank = int(name[1]) - 1
    return (file, rank)


def make(
    piece: str,
    start: str,
    end: str,
    *,
    capture: str | None = None,
    en_passant: bool = False,
    promotion: str | None = None,
) -> Move:
    return moves.make_move(
        piece_name=piece,
        initial_position=sq(start),
        final_position=sq(end),
        capture_name=capture,
        en_passant=en_passant,
        promotion=promotion,
    )
