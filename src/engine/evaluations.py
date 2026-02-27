Evaluation = str
"""
Contains game-related evaluations that cannot be derived from a single move. The complete representation of an evaluation has the form:
    [C, M, D, O, A]
where:
    C = whether the move resulted in a check,
    M = whether the move resulted in a checkmate,
    D = whether the move resulted in a draw,
    O = whether a draw was offered,
    A = annotation symbols if any, "_" otherwise.
"""


def make_evaluation(
    check: bool,
    checkmate: bool,
    draw: bool,
    draw_offer: bool,
    annotation: str | None = None,
) -> Evaluation:
    evaluation: Evaluation = ""

    evaluation += "T" if check else "F"
    evaluation += "T" if checkmate else "F"
    evaluation += "T" if draw else "F"
    evaluation += "T" if draw_offer else "F"
    if annotation:
        evaluation += annotation

    return evaluation


def is_check(e: Evaluation) -> bool:
    return e[0] == "T"


def is_checkmate(e: Evaluation) -> bool:
    return e[1] == "T"


def is_draw(e: Evaluation) -> bool:
    return e[2] == "T"


def is_draw_offer(e: Evaluation) -> bool:
    return e[3] == "T"


def get_annotation(e: Evaluation) -> str | None:
    if len(e) > 4:
        return e[4:]
    else:
        return None
