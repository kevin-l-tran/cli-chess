from dataclasses import replace
from time import monotonic

from src.application.viewer_types import ClockView, ViewerSessionView
from src.shared.protocol_types import PlayerSide


class ClientClockProjector:
    """
    A small projector that holds a locally hosted clock. It takes a
    ViewerSessionView and updates it based on the internal clock.
    """

    def __init__(self) -> None:
        self._base_time = monotonic()

    def reset_anchor(self) -> None:
        self._base_time = monotonic()

    def project(self, view: ViewerSessionView) -> ViewerSessionView:
        elapsed_ms = int((monotonic() - self._base_time) * 1000)
        return self._project_view(view, elapsed_ms)

    def _project_view(
        self, view: ViewerSessionView, elapsed_ms: int
    ) -> ViewerSessionView:
        snapshot = view.snapshot
        timed = snapshot.timed_game

        if (
            timed is None
            or timed.active_side is None
            or timed.timeout_side is not None
            or snapshot.is_game_over
        ):
            return view

        if timed.active_side == "white":
            white = self._decrement_clock(timed.white, elapsed_ms)
            black = timed.black
        else:
            white = timed.white
            black = self._decrement_clock(timed.black, elapsed_ms)

        timeout_side: PlayerSide | None = None
        if white.is_flagged:
            timeout_side = "white"
        elif black.is_flagged:
            timeout_side = "black"

        return replace(
            view,
            snapshot=replace(
                snapshot,
                timed_game=replace(
                    timed,
                    white=white,
                    black=black,
                    timeout_side=timeout_side,
                ),
            ),
        )

    def _decrement_clock(self, clock: ClockView, elapsed_ms: int) -> ClockView:
        remaining_ms = max(0, clock.remaining_ms - elapsed_ms)
        return replace(
            clock,
            remaining_ms=remaining_ms,
            display_text=_format_clock(remaining_ms),
            is_flagged=remaining_ms == 0,
        )


def _format_clock(ms: int) -> str:
    total_seconds = max(0, ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"
