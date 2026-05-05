from dataclasses import dataclass
from typing import Literal, Protocol, cast

from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Input, Static

from src.application.session import GameSession
from src.application.session_types import SessionConfig, Snapshot, Square, UndoScope
from src.ui.models.setup_models import SetupSelection


PromotionPiece = Literal["Q", "R", "B", "N"]


class GameController(Protocol):
    """Small seam between the Textual screen and the application layer.

    Today this wraps the current GameSession API. When the application layer moves to
    GameClient + LocalDraftController, add a new adapter here and leave most of the
    screen unchanged.
    """

    def snapshot(self) -> Snapshot: ...

    def set_move_text(self, text: str) -> None: ...

    def click_square(self, square: Square) -> None: ...

    def select_promotion_piece(self, piece: PromotionPiece) -> None: ...

    def confirm_move(self, *, offer_draw: bool = False) -> None: ...

    def accept_draw_offer(self) -> None: ...

    def undo(self, scope: UndoScope) -> None: ...

    def resign(self) -> None: ...

    def restart_game(self) -> None: ...


@dataclass
class CurrentSessionController:
    """Adapter for the current pull-based GameSession."""

    session: GameSession

    def snapshot(self) -> Snapshot:
        return self.session.snapshot()

    def set_move_text(self, text: str) -> None:
        self.session.set_move_text(text)

    def click_square(self, square: Square) -> None:
        self.session.click_square(square)

    def select_promotion_piece(self, piece: PromotionPiece) -> None:
        self.session.select_promotion_piece(cast(PromotionPiece, piece))

    def confirm_move(self, *, offer_draw: bool = False) -> None:
        self.session.confirm_move_draft(offer_draw=offer_draw)

    def accept_draw_offer(self) -> None:
        self.session.accept_draw_offer()

    def undo(self, scope: UndoScope) -> None:
        self.session.undo(scope)

    def resign(self) -> None:
        self.session.resign()

    def restart_game(self) -> None:
        self.session.restart_game()


class ChessBoard(Widget):
    """Minimal clickable 8x8 board."""

    DEFAULT_CSS = """
    ChessBoard {
        width: auto;
        height: auto;
    }

    #board-grid {
        grid-size: 8;
        grid-columns: 4 4 4 4 4 4 4 4;
        grid-rows: 3 3 3 3 3 3 3 3;
        width: 32;
        height: 24;
    }

    ChessBoard Button.square {
        width: 4;
        height: 3;
        min-width: 4;
        margin: 0;
        padding: 0;
        border: none;
        content-align: center middle;
    }

    ChessBoard Button.last {
        text-style: bold;
    }

    ChessBoard Button.candidate {
        text-style: reverse;
    }

    ChessBoard Button.check {
        text-style: bold reverse;
    }
    """

    class SquarePressed(Message):
        bubble = True

        def __init__(self, square: Square) -> None:
            super().__init__()
            self.square = square

    def __init__(self, *, orientation: str = "white", id: str | None = None) -> None:
        super().__init__(id=id)
        self.orientation = orientation

    def compose(self) -> ComposeResult:
        with Grid(id="board-grid"):
            for row in range(8):
                for col in range(8):
                    yield Button("", id=f"sq-{row}-{col}", classes="square")

    def refresh_from_snapshot(self, snapshot: Snapshot) -> None:
        highlighted: dict[tuple[int, int], set[str]] = {}

        def add_highlight(square: Square | None, css_class: str) -> None:
            if square is None:
                return
            display_pos = self._square_to_display(square)
            highlighted.setdefault(display_pos, set()).add(css_class)

        for from_square, to_square in snapshot.candidate_moves:
            add_highlight(from_square, "candidate")
            add_highlight(to_square, "candidate")

        add_highlight(snapshot.last_move_from, "last")
        add_highlight(snapshot.last_move_to, "last")
        add_highlight(snapshot.check_square, "check")

        for display_row in range(8):
            for display_col in range(8):
                square = self._display_to_square(display_row, display_col)
                file, rank = square

                # board_glyphs is a board-render matrix, not the display matrix.
                # Convert display cell -> engine square -> board matrix indexes.
                glyph = snapshot.board_glyphs[7 - rank][file]

                button = self.query_one(f"#sq-{display_row}-{display_col}", Button)
                button.label = self._display_glyph(glyph)

                for css_class in ("candidate", "last", "check"):
                    button.remove_class(css_class)

                for css_class in highlighted.get((display_row, display_col), set()):
                    button.add_class(css_class)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if not button_id.startswith("sq-"):
            return

        _, row_s, col_s = button_id.split("-")
        square = self._display_to_square(int(row_s), int(col_s))
        event.stop()
        self.post_message(self.SquarePressed(square))

    def _display_to_square(self, display_row: int, display_col: int) -> Square:
        """Map a rendered board cell to an engine square: (file, rank)."""
        if self.orientation == "black":
            return 7 - display_col, display_row

        return display_col, 7 - display_row


    def _square_to_display(self, square: Square) -> tuple[int, int]:
        """Map an engine square: (file, rank) to a rendered board cell."""
        file, rank = square

        if self.orientation == "black":
            return rank, 7 - file

        return 7 - rank, file

    def _display_glyph(self, glyph: str) -> str:
        glyph = glyph.strip()
        return glyph if glyph else "·"


class GameScreen(Screen):
    """Minimal game board screen for exercising the current GameSession API."""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("ctrl+r", "restart", "Restart"),
        ("ctrl+u", "undo_fullmove", "Undo turn"),
        ("ctrl+h", "undo_halfmove", "Undo move"),
    ]

    CSS = """
    GameScreen {
        padding: 1 2;
    }

    #layout {
        height: 1fr;
    }

    #board-panel {
        width: auto;
        height: auto;
        margin-right: 2;
    }

    #side-panel {
        width: 50;
        height: 1fr;
    }

    #title {
        text-style: bold;
        height: auto;
        margin-bottom: 1;
    }

    #status, #draft-status, #clock, #feedback, #autocomplete {
        height: auto;
        margin-bottom: 1;
    }

    #move-list {
        height: 1fr;
        border: solid $border;
        padding: 1 2;
    }

    #move-input {
        margin-top: 1;
    }

    #controls, #promotion-row {
        height: auto;
        margin-top: 1;
    }

    #controls Button, #promotion-row Button {
        width: auto;
        min-width: 10;
        margin-right: 1;
    }
    """

    def __init__(
        self,
        selection: SetupSelection,
        controller: GameController | None = None,
    ) -> None:
        super().__init__()
        self.selection = selection
        self.config: SessionConfig = selection.to_session_config()
        self.controller = controller or CurrentSessionController(
            GameSession(self.config)
        )
        self.offer_draw = False
        self._syncing_input = False

    def compose(self) -> ComposeResult:
        yield Static("Chess", id="title")
        with Horizontal(id="layout"):
            with Vertical(id="board-panel"):
                yield ChessBoard(orientation=self.config.player_side, id="board")
                yield Input(placeholder="Move, e.g. e2e4 or Nc3", id="move-input")
                with Horizontal(id="promotion-row"):
                    yield Button("Queen", id="promote-q")
                    yield Button("Rook", id="promote-r")
                    yield Button("Bishop", id="promote-b")
                    yield Button("Knight", id="promote-n")
                with Horizontal(id="controls"):
                    yield Button("Confirm", id="confirm")
                    yield Button("Offer draw", id="offer-draw")
                    yield Button("Accept draw", id="accept-draw")
                    yield Button("Undo move", id="undo-half")
                    yield Button("Undo turn", id="undo-full")
                    yield Button("Resign", id="resign")
                    yield Button("Restart", id="restart")
                    yield Button("Back", id="back")
            with Vertical(id="side-panel"):
                yield Static("", id="status")
                yield Static("", id="draft-status")
                yield Static("", id="clock")
                yield Static("", id="autocomplete")
                yield Static("", id="feedback")
                yield VerticalScroll(Static("", id="move-list"))

    def on_mount(self) -> None:
        self._refresh_view()
        self.query_one("#move-input", Input).focus()
        self.set_interval(0.5, self._refresh_view)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "move-input" or self._syncing_input:
            return

        self.controller.set_move_text(event.value)
        self._refresh_view()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "move-input":
            self._confirm_move()

    def on_chess_board_square_pressed(self, msg: ChessBoard.SquarePressed) -> None:
        self.controller.click_square(msg.square)
        self._refresh_view()
        self.query_one("#move-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "confirm":
            self._confirm_move()
        elif button_id == "offer-draw":
            self.offer_draw = not self.offer_draw
            self._refresh_view()
        elif button_id == "accept-draw":
            self.controller.accept_draw_offer()
            self._refresh_view()
        elif button_id == "undo-half":
            self.controller.undo("halfmove")
            self._refresh_view()
        elif button_id == "undo-full":
            self.controller.undo("fullmove")
            self._refresh_view()
        elif button_id == "resign":
            self.controller.resign()
            self._refresh_view()
        elif button_id == "restart":
            self.controller.restart_game()
            self.offer_draw = False
            self._refresh_view()
        elif button_id == "back":
            self.app.pop_screen()
        elif button_id in {"promote-q", "promote-r", "promote-b", "promote-n"}:
            piece = cast(
                PromotionPiece,
                {
                    "promote-q": "Q",
                    "promote-r": "R",
                    "promote-b": "B",
                    "promote-n": "N",
                }[button_id],
            )
            self.controller.select_promotion_piece(piece)
            self._refresh_view()
            self.query_one("#move-input", Input).focus()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_restart(self) -> None:
        self.controller.restart_game()
        self.offer_draw = False
        self._refresh_view()

    def action_undo_fullmove(self) -> None:
        self.controller.undo("fullmove")
        self._refresh_view()

    def action_undo_halfmove(self) -> None:
        self.controller.undo("halfmove")
        self._refresh_view()

    def _confirm_move(self) -> None:
        self.controller.confirm_move(offer_draw=self.offer_draw)
        snapshot = self.controller.snapshot()
        if snapshot.feedback is None or snapshot.feedback.kind != "error":
            self.offer_draw = False
        self._refresh_view(snapshot)
        self.query_one("#move-input", Input).focus()

    def _refresh_view(self, snapshot: Snapshot | None = None) -> None:
        snapshot = self.controller.snapshot() if snapshot is None else snapshot

        self.query_one("#board", ChessBoard).refresh_from_snapshot(snapshot)
        self._sync_move_input(snapshot)
        self._sync_text_panels(snapshot)
        self._sync_controls(snapshot)

    def _sync_move_input(self, snapshot: Snapshot) -> None:
        move_input = self.query_one("#move-input", Input)
        move_input.disabled = snapshot.is_game_over

        if move_input.value != snapshot.move_draft.text:
            self._syncing_input = True
            move_input.value = snapshot.move_draft.text
            self._syncing_input = False

    def _sync_text_panels(self, snapshot: Snapshot) -> None:
        side = snapshot.side_to_move or "-"
        opponent = self.selection.opponent
        bot_note = ""
        if opponent == "bot":
            bot_note = f" | bot level: {self.selection.bot_level}"

        check_note = " | check" if snapshot.is_player_checked else ""
        draw_note = (
            f" | draw offered by {snapshot.draw_offered_by}"
            if snapshot.draw_offered_by
            else ""
        )
        offer_note = " | next move offers draw" if self.offer_draw else ""
        self.query_one("#status", Static).update(
            f"Mode: {opponent}{bot_note}\n"
            f"Orientation: {self.config.player_side}\n"
            f"Side to move: {side}{check_note}{draw_note}{offer_note}"
        )

        draft = snapshot.move_draft
        canonical = f" -> {draft.canonical_text}" if draft.canonical_text else ""
        self.query_one("#draft-status", Static).update(
            f"Draft: {draft.status}{canonical}"
        )

        if snapshot.timed_game is None:
            clock_text = "Clock: none"
        else:
            timed = snapshot.timed_game
            w_active = " *" if timed.white.is_active else ""
            b_active = " *" if timed.black.is_active else ""
            clock_text = (
                f"White: {timed.white.display_text}{w_active}\n"
                f"Black: {timed.black.display_text}{b_active}"
            )
        self.query_one("#clock", Static).update(clock_text)

        completions = ", ".join(snapshot.move_autocompletions[:10])
        self.query_one("#autocomplete", Static).update(
            f"Completions: {completions or '-'}"
        )

        if snapshot.outcome is not None:
            feedback_text = snapshot.outcome.banner
        elif snapshot.feedback is not None:
            feedback_text = f"{snapshot.feedback.kind}: {snapshot.feedback.text}"
        else:
            feedback_text = ""
        self.query_one("#feedback", Static).update(feedback_text)

        moves = "\n".join(
            f"{item.ply:>3}: {item.notation}" for item in snapshot.move_list[-80:]
        )
        self.query_one("#move-list", Static).update(moves or "No moves yet.")

    def _sync_controls(self, snapshot: Snapshot) -> None:
        self.query_one(
            "#promotion-row", Horizontal
        ).display = snapshot.is_promotion_pending

        self.query_one("#confirm", Button).disabled = not snapshot.can_confirm_move
        self.query_one("#offer-draw", Button).disabled = not snapshot.can_offer_draw
        self.query_one("#accept-draw", Button).disabled = (
            snapshot.draw_offered_by is None or snapshot.is_game_over
        )
        self.query_one("#undo-half", Button).disabled = not snapshot.can_undo_halfmove
        self.query_one("#undo-full", Button).disabled = not snapshot.can_undo_fullmove
        self.query_one("#resign", Button).disabled = not snapshot.can_resign

        self.query_one("#offer-draw", Button).label = (
            "Cancel draw" if self.offer_draw else "Offer draw"
        )
