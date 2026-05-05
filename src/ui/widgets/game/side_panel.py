from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

from src.application.session_types import SessionConfig, Snapshot
from src.ui.models.setup_models import SetupSelection


class GameSidePanel(Vertical):
    DEFAULT_CSS = """
    GameSidePanel {
        width: 50;
        height: 1fr;
    }

    GameSidePanel #status,
    GameSidePanel #draft-status,
    GameSidePanel #clock,
    GameSidePanel #feedback,
    GameSidePanel #autocomplete {
        height: auto;
        margin-bottom: 1;
    }

    GameSidePanel #move-list {
        height: 1fr;
        border: solid $border;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="status")
        yield Static("", id="draft-status")
        yield Static("", id="clock")
        yield Static("", id="autocomplete")
        yield Static("", id="feedback")
        yield VerticalScroll(Static("", id="move-list"))

    def sync(
        self,
        snapshot: Snapshot,
        *,
        selection: SetupSelection,
        config: SessionConfig,
        offer_draw: bool,
    ) -> None:
        side = snapshot.side_to_move or "-"
        opponent = selection.opponent
        bot_note = f" | bot level: {selection.bot_level}" if opponent == "bot" else ""
        check_note = " | check" if snapshot.is_player_checked else ""
        draw_note = (
            f" | draw offered by {snapshot.draw_offered_by}"
            if snapshot.draw_offered_by
            else ""
        )
        offer_note = " | next move offers draw" if offer_draw else ""

        self.query_one("#status", Static).update(
            f"Mode: {opponent}{bot_note}\n"
            f"Orientation: {config.player_side}\n"
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
