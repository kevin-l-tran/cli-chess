from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

from src.application.session_types import SessionConfig, Snapshot
from src.ui.models.setup_models import SetupSelection


class GameSidePanel(Vertical):
    DEFAULT_CSS = """
    GameSidePanel {
        width: 1fr;
        height: 1fr;
    }

    GameSidePanel .panel {
        height: auto;
        margin-bottom: 1;
    }

    GameSidePanel .frame {
        border: ascii $border;
        padding: 0 1;
    }

    GameSidePanel .frame_title {
        height: 1;
        color: $accent;
        text-style: bold;
    }

    GameSidePanel .panel_body {
        height: auto;
        margin-bottom: 1;
    }

    GameSidePanel #moves_panel {
        height: 1fr;
        min-height: 8;
        margin-bottom: 0;
    }

    GameSidePanel #moves_list {
        height: auto;
    }

    GameSidePanel #feedback.error {
        color: $error;
        text-style: bold;
    }

    GameSidePanel #feedback.action,
    GameSidePanel #feedback.info {
        color: $success;
        text-style: bold;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._text_cache: dict[str, str] = {}
        self._status: Static | None = None
        self._draft_status: Static | None = None
        self._autocomplete: Static | None = None
        self._feedback: Static | None = None
        self._clock: Static | None = None
        self._move_list: Static | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="frame panel", id="status_panel"):
            yield Static("Status", classes="frame_title", markup=False)
            self._status = Static("", id="status", classes="panel_body", markup=False)
            yield self._status

        with Vertical(classes="frame panel", id="draft_panel"):
            yield Static("Draft", classes="frame_title", markup=False)
            self._draft_status = Static(
                "", id="draft-status", classes="panel_body", markup=False
            )
            yield self._draft_status
            self._autocomplete = Static(
                "", id="autocomplete", classes="panel_body", markup=False
            )
            yield self._autocomplete
            self._feedback = Static(
                "", id="feedback", classes="panel_body", markup=False
            )
            yield self._feedback

        with Vertical(classes="frame panel", id="clock_panel"):
            yield Static("Clocks", classes="frame_title", markup=False)
            self._clock = Static("", id="clock", classes="panel_body", markup=False)
            yield self._clock

        with Vertical(classes="frame panel", id="moves_panel"):
            yield Static("Moves", classes="frame_title", markup=False)
            with VerticalScroll(id="moves_list"):
                self._move_list = Static("", id="move-list", markup=False)
                yield self._move_list

    def sync(
        self,
        snapshot: Snapshot,
        *,
        selection: SetupSelection,
        config: SessionConfig,
        offer_draw: bool,
    ) -> None:
        side = self._title_case(snapshot.side_to_move or "-")
        opponent = selection.opponent
        bot_note = f" (level {selection.bot_level})" if opponent == "bot" else ""
        check_note = "Check" if snapshot.is_player_checked else "Active"
        if snapshot.is_game_over:
            check_note = "Game over"

        draw_line = (
            f"Draw: offered by {snapshot.draw_offered_by}"
            if snapshot.draw_offered_by
            else "Draw: -"
        )
        offer_line = "Offer: next move offers draw" if offer_draw else "Offer: -"

        self._update_text(
            "status",
            self._status_widget(),
            f"Turn: {side}\n"
            f"State: {check_note}\n"
            f"Mode: {self._title_case(opponent)}{bot_note}\n"
            f"Orientation: {self._title_case(config.player_side)}\n"
            f"{draw_line}\n"
            f"{offer_line}",
        )

        draft = snapshot.move_draft
        canonical = f" -> {draft.canonical_text}" if draft.canonical_text else ""
        self._update_text(
            "draft-status",
            self._draft_status_widget(),
            f"Text: {draft.text or '-'}\nStatus: {draft.status}{canonical}",
        )

        completions = ", ".join(snapshot.move_autocompletions[:10])
        self._update_text(
            "autocomplete",
            self._autocomplete_widget(),
            f"Completions: {completions or '-'}",
        )

        feedback = self._feedback_widget()
        for css_class in ("error", "action", "info"):
            feedback.remove_class(css_class)

        if snapshot.outcome is not None:
            feedback_text = snapshot.outcome.banner
            feedback.add_class("info")
        elif snapshot.feedback is not None:
            feedback_text = f"{snapshot.feedback.kind}: {snapshot.feedback.text}"
            feedback.add_class(snapshot.feedback.kind)
        else:
            feedback_text = ""
        self._update_text("feedback", feedback, feedback_text)

        if snapshot.timed_game is None:
            clock_text = "Black: -\nWhite: -\nIncrement: -"
        else:
            timed = snapshot.timed_game
            w_active = " *" if timed.white.is_active else ""
            b_active = " *" if timed.black.is_active else ""
            increment = getattr(timed, "increment_seconds", None)
            increment_line = (
                f"Increment: +{increment}s" if increment is not None else "Increment: -"
            )
            clock_text = (
                f"Black: {timed.black.display_text}{b_active}\n"
                f"White: {timed.white.display_text}{w_active}\n"
                f"{increment_line}"
            )
        self._update_text("clock", self._clock_widget(), clock_text)

        self._update_text(
            "move-list",
            self._move_list_widget(),
            self._format_moves(snapshot) or "No moves yet.",
        )

    def _update_text(self, cache_key: str, widget: Static, text: str) -> None:
        if self._text_cache.get(cache_key) == text:
            return
        self._text_cache[cache_key] = text
        widget.update(text)

    def _format_moves(self, snapshot: Snapshot) -> str:
        rows: dict[int, list[str]] = {}
        for item in snapshot.move_list[-80:]:
            move_number = max(1, (item.ply + 1) // 2)
            cells = rows.setdefault(move_number, ["", ""])
            if item.ply % 2 == 1:
                cells[0] = item.notation
            else:
                cells[1] = item.notation

        return "\n".join(
            f"{move_number}. {moves[0]:<8} {moves[1]}".rstrip()
            for move_number, moves in rows.items()
        )

    def _title_case(self, value: str) -> str:
        return value[:1].upper() + value[1:] if value else value

    def _status_widget(self) -> Static:
        if self._status is None:
            self._status = self.query_one("#status", Static)
        return self._status

    def _draft_status_widget(self) -> Static:
        if self._draft_status is None:
            self._draft_status = self.query_one("#draft-status", Static)
        return self._draft_status

    def _autocomplete_widget(self) -> Static:
        if self._autocomplete is None:
            self._autocomplete = self.query_one("#autocomplete", Static)
        return self._autocomplete

    def _feedback_widget(self) -> Static:
        if self._feedback is None:
            self._feedback = self.query_one("#feedback", Static)
        return self._feedback

    def _clock_widget(self) -> Static:
        if self._clock is None:
            self._clock = self.query_one("#clock", Static)
        return self._clock

    def _move_list_widget(self) -> Static:
        if self._move_list is None:
            self._move_list = self.query_one("#move-list", Static)
        return self._move_list
