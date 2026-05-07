from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static

from src.application.session_types import SessionConfig, Snapshot
from src.ui.models.setup_models import SetupSelection


class GameSidePanel(Vertical):
    """Right rail for committed game state.

    Draft text, completions, and feedback are rendered beside the move input in
    GameScreen. This widget owns only committed/read-only game data: clocks,
    game status, and move history.

    Widths are intentionally protected by CSS min-widths. When the terminal is
    too narrow, the screen-level horizontal scroll wrapper should scroll instead
    of squeezing these panels until labels wrap.
    """

    DEFAULT_CSS = (Path(__file__).parent / "css" / "side_panel.tcss").read_text()

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._text_cache: dict[str, str] = {}
        self._clock: Static | None = None
        self._status: Static | None = None
        self._move_list: Static | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="side-panel-scroll"):
            with Horizontal(id="game_header_row"):
                clock_panel = Vertical(classes="frame panel titled-frame", id="clock_panel")
                clock_panel.border_title = "Clocks"
                with clock_panel:
                    self._clock = Static(
                        "",
                        id="clock",
                        classes="panel_body",
                        markup=False,
                    )
                    yield self._clock

                status_panel = Vertical(classes="frame panel titled-frame", id="status_panel")
                status_panel.border_title = "Game"
                with status_panel:
                    self._status = Static(
                        "",
                        id="status",
                        classes="panel_body",
                        markup=False,
                    )
                    yield self._status

            moves_panel = Vertical(classes="frame panel titled-frame", id="moves_panel")
            moves_panel.border_title = "Moves"
            with moves_panel:
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
        self._update_text("clock", self._clock_widget(), self._format_clock(snapshot))
        self._update_text(
            "status",
            self._status_widget(),
            self._format_status(
                snapshot,
                selection=selection,
                config=config,
                offer_draw=offer_draw,
            ),
        )
        self._update_text(
            "move-list",
            self._move_list_widget(),
            self._format_moves(snapshot) or "No moves yet.",
        )

    def _format_clock(self, snapshot: Snapshot) -> str:
        if snapshot.timed_game is None:
            return "Black: -\nWhite: -\nIncrement: -"

        timed = snapshot.timed_game
        w_active = " *" if timed.white.is_active else ""
        b_active = " *" if timed.black.is_active else ""
        increment = getattr(timed, "increment_seconds", None)
        increment_line = (
            f"Increment: +{increment}s" if increment is not None else "Increment: -"
        )
        return (
            f"Black: {timed.black.display_text}{b_active}\n"
            f"White: {timed.white.display_text}{w_active}\n"
            f"{increment_line}"
        )

    def _format_status(
        self,
        snapshot: Snapshot,
        *,
        selection: SetupSelection,
        config: SessionConfig,
        offer_draw: bool,
    ) -> str:
        side = self._title_case(snapshot.side_to_move or "-")
        opponent = selection.opponent
        bot_note = f" (level {selection.bot_level})" if opponent == "bot" else ""
        state = "Check" if snapshot.is_player_checked else "Active"
        if snapshot.is_game_over:
            state = "Game over"

        draw_line = (
            f"Draw: offered by {snapshot.draw_offered_by}"
            if snapshot.draw_offered_by
            else "Draw: -"
        )
        offer_line = "Offer: next move offers draw" if offer_draw else "Offer: -"

        return (
            f"Turn: {side}\n"
            f"State: {state}\n"
            f"Mode: {self._title_case(opponent)}{bot_note}\n"
            f"View: {self._title_case(config.player_side)}\n"
            f"{draw_line}\n"
            f"{offer_line}"
        )

    def _format_moves(self, snapshot: Snapshot) -> str:
        rows: dict[int, list[str]] = {}
        for item in snapshot.move_list[-120:]:
            move_number = max(1, (item.ply + 1) // 2)
            cells = rows.setdefault(move_number, ["", ""])
            if item.ply % 2 == 1:
                cells[0] = item.notation
            else:
                cells[1] = item.notation

        return "\n".join(
            f"{move_number}. {moves[0]:<10} {moves[1]}".rstrip()
            for move_number, moves in rows.items()
        )

    def _update_text(self, cache_key: str, widget: Static, text: str) -> None:
        if self._text_cache.get(cache_key) == text:
            return
        self._text_cache[cache_key] = text
        widget.update(text)

    def _title_case(self, value: str) -> str:
        return value[:1].upper() + value[1:] if value else value

    def _clock_widget(self) -> Static:
        if self._clock is None:
            self._clock = self.query_one("#clock", Static)
        return self._clock

    def _status_widget(self) -> Static:
        if self._status is None:
            self._status = self.query_one("#status", Static)
        return self._status

    def _move_list_widget(self) -> Static:
        if self._move_list is None:
            self._move_list = self.query_one("#move-list", Static)
        return self._move_list
