from dataclasses import dataclass

from src.engine.board import Piece, get_name, is_white
from src.engine.game import Game
from src.engine.moves import get_final_position, get_initial_position, get_promotion

from .move_parser import ParseResult, Square, get_canonical
from .session_types import MoveDraftView, MoveListItem, Snapshot


@dataclass(frozen=True)
class SnapshotInputs:
    move_text: str
    parse_result: ParseResult

    last_move_from: Square | None
    last_move_to: Square | None

    outcome_banner: str | None
    last_error_message: str | None
    last_action_message: str | None


def build_snapshot(
    game: Game,
    inputs: SnapshotInputs,
) -> Snapshot:
    """
    Build a render-ready session snapshot from engine state and session inputs.

    Parameters:
        game (Game):
            The active engine game supplying board state, side to move, move
            history, and check information.

        inputs (SnapshotInputs):
            The session-owned UI state needed to project the current view,
            including move draft, parse result, last-move highlights, and 
            feedback messages.

    Returns:
        Snapshot:
            An immutable view-model containing board glyphs, turn state, 
            candidate-move highlights, move history, draft/autocompletion state, 
            promotion-popup anchor state, check state, and user-facing banners or errors.

    Behavior:
        - converts the current board into render glyphs
        - projects parser-derived candidate moves, canonical draft state, and
        autocompletions into the snapshot
        - includes the last applied move highlights and move list
        - derives the promotion prompt anchor square from the current parse
        result when the remaining ambiguity corresponds to a promotion choice
        - includes current check, outcome, and error-display state
    """
    parse_result = inputs.parse_result
    check_square = game.checked_king_position()

    return Snapshot(
        board_glyphs=_build_board_glyphs(game),
        side_to_move="white" if game.is_white_turn else "black",
        candidate_moves=set(parse_result.source_to_target_highlights),
        last_move_from=inputs.last_move_from,
        last_move_to=inputs.last_move_to,
        move_list=_build_move_list(game),
        move_draft=MoveDraftView(
            text=inputs.move_text,
            status=parse_result.status,
            canonical_text=parse_result.canonical_text,
        ),
        move_autocompletions=parse_result.matching_spellings,
        promotion_prompt_position=_get_promotion_prompt_square(parse_result),
        check_square=check_square,
        is_checked=check_square is not None,
        outcome_banner=inputs.outcome_banner,
        last_error_message=inputs.last_error_message,
        last_action_message=inputs.last_action_message,
    )


def _build_move_list(game: Game) -> list[MoveListItem]:
    items: list[MoveListItem] = []

    for ply, (move, _) in enumerate(game.moves_list, start=1):
        items.append(
            MoveListItem(
                ply=ply,
                notation=get_canonical(move),
            )
        )

    return items


def _build_board_glyphs(game: Game) -> list[list[str]]:
    def piece_to_glyph(piece: Piece | None) -> str:
        if piece is None:
            return "."
        name = get_name(piece)
        return name if is_white(piece) else name.lower()

    return [
        [piece_to_glyph(game.board.piece_at((file, rank))) for file in range(8)]
        for rank in range(7, -1, -1)
    ]


def _get_promotion_prompt_square(parse_result: ParseResult) -> Square | None:
    moves = parse_result.matching_moves

    if parse_result.status != "ambiguous" or not moves:
        return None

    if any(get_promotion(move) is None for move in moves):
        return None

    from_squares = {get_initial_position(move) for move in moves}
    to_squares = {get_final_position(move) for move in moves}
    if len(from_squares) != 1 or len(to_squares) != 1:
        return None

    texts = [get_canonical(move) for move in sorted(moves, key=get_canonical)]
    prefix = texts[0]
    for text in texts[1:]:
        i = 0
        while i < len(prefix) and i < len(text) and prefix[i] == text[i]:
            i += 1
        prefix = prefix[:i]

    if parse_result.normalized_text != prefix or not prefix.endswith("="):
        return None

    return next(iter(to_squares))
