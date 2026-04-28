from dataclasses import dataclass

from src.engine.board import Piece, get_name, is_white
from src.engine.game import Game

from .move_parser import ParseResult, Square, get_canonical
from .session_types import MoveDraftView, MoveListItem, PlayerSide, Snapshot


@dataclass(frozen=True)
class SnapshotInputs:
    player_side: PlayerSide
    orientation_override: bool

    cursor: Square | None
    move_text: str
    parse_result: ParseResult

    last_move_from: Square | None
    last_move_to: Square | None

    outcome_banner: str | None
    last_error_message: str | None


def build_snapshot(
    game: Game,
    inputs: SnapshotInputs,
) -> Snapshot:
    parse_result = inputs.parse_result
    check_square = game.checked_king_position()

    return Snapshot(
        board_glyphs=_build_board_glyphs(game),
        side_to_move="white" if game.is_white_turn else "black",
        flipped=_compute_flipped(
            player_side=inputs.player_side,
            orientation_override=inputs.orientation_override,
        ),
        cursor=inputs.cursor,
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
        check_square=check_square,
        is_checked=check_square is not None,
        outcome_banner=inputs.outcome_banner,
        last_error_message=inputs.last_error_message,
    )


def _compute_flipped(
    player_side: PlayerSide,
    orientation_override: bool,
) -> bool:
    default_flipped = player_side == "black"
    if orientation_override:
        return not default_flipped
    return default_flipped


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
