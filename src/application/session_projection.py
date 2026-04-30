from dataclasses import dataclass

from src.engine.board import Piece, get_name, is_white
from src.engine.game import Game
from src.engine.moves import get_final_position, get_initial_position, get_promotion

from .move_parser import ParseResult, Square, get_canonical
from .session_policy import SessionCapabilities
from .session_types import (
    ClockView,
    MoveDraftView,
    MoveListItem,
    OutcomeView,
    Snapshot,
    TerminalState,
    TimedGameView,
)
from .clock import ClockState


@dataclass(frozen=True)
class TimingProjectionInputs:
    clock_state: ClockState | None
    increment_seconds: int | None


@dataclass(frozen=True)
class SessionProjectionInputs:
    move_text: str
    parse_result: ParseResult
    last_move_from: Square | None
    last_move_to: Square | None
    terminal: TerminalState | None
    last_error_message: str | None
    last_action_message: str | None
    is_game_over: bool
    capabilities: SessionCapabilities
    timing: TimingProjectionInputs | None


class SessionProjection:
    @staticmethod
    def build(game: Game, inputs: SessionProjectionInputs) -> Snapshot:
        """
        Build a render-ready session snapshot from engine state and session inputs.

        Parameters:
            game (Game):
                The active engine game supplying board state, side to move, move
                history, and check information.

            inputs (SessionProjectionInputs):
                Session-owned UI state needed to project the current view, including
                move draft state, parser results, last-move highlights, user-facing
                feedback messages, outcome state, and opponent type.

        Returns:
            Snapshot:
                An immutable view-model containing board glyphs, turn state,
                candidate-move highlights, move history, draft/autocompletion state,
                promotion-picker anchor state, check state, opponent-sensitive undo
                availability flags, and user-facing banners and messages.

        Behavior:
            - converts the current board into render glyphs
            - projects parser-derived candidate moves, canonical draft state, and
            autocompletions into the snapshot
            - includes the last applied move highlights and move list
            - derives the promotion prompt anchor square when the remaining ambiguity
            corresponds only to a promotion-piece choice
            - derives UI capability flags such as move confirmation, undo availability,
            resignation availability, game-over state, and promotion-pending state
            - includes current check, outcome, and user-facing message state
        """
        parse_result = inputs.parse_result
        check_square = game.checked_king_position()
        move_list = _build_move_list(game)
        promotion_prompt_position = _get_promotion_prompt_position(parse_result)
        timed_game = _build_timed_game(inputs.timing)
        outcome = _build_outcome(inputs.terminal)

        caps = inputs.capabilities
        is_promotion_pending = promotion_prompt_position is not None

        return Snapshot(
            board_glyphs=_build_board_glyphs(game),
            side_to_move="white" if game.is_white_turn else "black",
            candidate_moves=set(parse_result.source_to_target_highlights),
            last_move_from=inputs.last_move_from,
            last_move_to=inputs.last_move_to,
            move_list=move_list,
            move_draft=MoveDraftView(
                text=inputs.move_text,
                status=parse_result.status,
                canonical_text=parse_result.canonical_text,
            ),
            move_autocompletions=parse_result.matching_spellings,
            promotion_prompt_position=promotion_prompt_position,
            check_square=check_square,
            is_player_checked=check_square is not None,
            is_game_over=inputs.is_game_over,
            can_confirm_move=caps.can_confirm_move,
            can_resign=caps.can_resign,
            is_promotion_pending=is_promotion_pending,
            can_undo_fullmove=caps.can_undo_fullmove,
            can_undo_halfmove=caps.can_undo_halfmove,
            timed_game=timed_game,
            outcome=outcome,
            last_error_message=inputs.last_error_message,
            last_action_message=inputs.last_action_message,
        )


def _build_outcome(terminal: TerminalState | None) -> OutcomeView | None:
    if terminal is None:
        return None

    if terminal.reason == "timeout":
        banner = (
            "Black wins on time."
            if terminal.winner == "black"
            else "White wins on time."
        )
    elif terminal.reason == "resignation":
        banner = (
            "White resigns. Black wins."
            if terminal.winner == "black"
            else "Black resigns. White wins."
        )
    elif terminal.reason == "draw":
        banner = "Draw."
    else:
        banner = (
            "White wins by checkmate."
            if terminal.winner == "white"
            else "Black wins by checkmate."
        )

    return OutcomeView(
        winner=terminal.winner,
        reason=terminal.reason,
        banner=banner,
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


def _format_clock(ms: int) -> str:
    total_seconds = max(0, ms) // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


def _build_timed_game(timing: TimingProjectionInputs | None) -> TimedGameView | None:
    if timing is None or timing.clock_state is None or timing.increment_seconds is None:
        return None

    clock = timing.clock_state

    return TimedGameView(
        white=ClockView(
            remaining_ms=clock.white_remaining_ms,
            display_text=_format_clock(clock.white_remaining_ms),
            is_active=clock.active_side == "white",
            is_flagged=clock.timeout_side == "white",
        ),
        black=ClockView(
            remaining_ms=clock.black_remaining_ms,
            display_text=_format_clock(clock.black_remaining_ms),
            is_active=clock.active_side == "black",
            is_flagged=clock.timeout_side == "black",
        ),
        active_side=clock.active_side,
        timeout_side=clock.timeout_side,
        increment_seconds=timing.increment_seconds,
    )


def _get_promotion_prompt_position(parse_result: ParseResult) -> Square | None:
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
