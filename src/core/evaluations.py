Evaluation = str
"""
Contains game-related evaluations that cannot be derived from a single move. The complete representation of an evaluation has the form:
    [C, M, D, A]
where:
    C = whether the move resulted in a check,
    M = whether the move resulted in a checkmate,
    D = whether a draw was offered,
    A = annotation symbols if any, "_" otherwise.
"""


def make_evaluation(
    check: bool,
    checkmate: bool,
    draw_offer: bool,
    annotation: str | None = None
) -> Evaluation:
    evaluation: Evaluation = ""

    evaluation += "T" if check else "F"
    evaluation += "T" if checkmate else "F"
    evaluation += "T" if draw_offer else "F"
    if annotation:
        evaluation += annotation

    return NotImplemented
