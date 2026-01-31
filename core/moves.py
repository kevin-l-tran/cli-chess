from dataclasses import dataclass


@dataclass
class Move:
    """
    Represents a chess move.
    """

    piece: str
    "The character representing the moved piece."
    initialPosition: tuple[str, int]
    "The initial position of the moved piece."
    finalPosition: tuple[str, int]
    "The final position of the moved piece."
    capture: bool
    "Whether a piece was captured during the move."
    en_passant: bool
    "Whether the move was an en passant."
    check: bool
    "Whether the move resulted in a check."
    checkmate: bool
    "Whether the move resulted in a checkmate."
    promotion: str | None
    "The character representing the promotion piece, if a promotion occurred."
    annotation: str | None
    "The rating of the move, if it has any."

    def to_standard(self) -> str:
        """Returns the standard algebraic representation of the move."""
        return "not implemented"

    def to_extended(self) -> str:
        """Returns the extended algebraic representation of the move."""
        return "not implemented"

    def to_full(self) -> str:
        """Returns the complete representation of the move."""
        return "not implemented"
