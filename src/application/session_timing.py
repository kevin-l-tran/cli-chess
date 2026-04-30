from dataclasses import dataclass

from .session_types import PlayerSide, TimeControl
from .clock import ClockFrame, ClockState, TimeSource, advance_clock, freeze_clock


@dataclass
class SessionTiming:
    """
    Timing coordinator for a `GameSession`.

    This helper centralizes session-level timing policy on top of `ClockState`,
    including clock synchronization, timeout detection, increment handling, and
    timing-history save/restore for undo.
    """
    clock_state: ClockState | None
    time_control: TimeControl | None
    time_source: TimeSource

    def sync(self, engine_game_over: bool) -> bool:
        """
        Synchronize the session clock to the current time source.

        Returns:
            bool:
                `True` when synchronization newly causes a timeout, otherwise
                `False`.
        """
        return advance_clock(
            self.clock_state,
            now_ms=self.time_source(),
            is_game_over=engine_game_over,
        )

    def is_timed(self) -> bool:
        """Return whether the session is using a chess clock."""
        return self.clock_state is not None

    def timeout_side(self) -> PlayerSide | None:
        """Return the side that has lost due to time, if any."""
        if self.clock_state is None:
            return None
        return self.clock_state.timeout_side

    def freeze(self) -> None:
        """Freeze the clock so no side is currently running."""
        freeze_clock(self.clock_state)

    def push_frame(self) -> None:
        """Save the current timing state for later undo restoration."""
        clock = self.clock_state
        if clock is None:
            return
        clock.history.append(
            ClockFrame(
                white_remaining_ms=clock.white_remaining_ms,
                black_remaining_ms=clock.black_remaining_ms,
                active_side=clock.active_side,
                timeout_side=clock.timeout_side,
                last_updated_ms=clock.last_updated_ms,
            )
        )

    def pop_frame(self) -> None:
        """Restore the most recently saved timing state, if available."""
        clock = self.clock_state
        if clock is None or not clock.history:
            return
        frame = clock.history.pop()
        clock.white_remaining_ms = frame.white_remaining_ms
        clock.black_remaining_ms = frame.black_remaining_ms
        clock.active_side = frame.active_side
        clock.timeout_side = frame.timeout_side
        clock.last_updated_ms = None

    def on_move_committed(self, next_side: PlayerSide) -> None:
        """
        Update timing state after a move has been successfully committed.

        This applies increment for the side that just moved, switches the active
        clock to `next_side`, clears any timeout marker, and starts the next clock
        from the current time source.
        """
        clock = self.clock_state
        tc = self.time_control
        if clock is None or tc is None:
            return

        mover = "black" if next_side == "white" else "white"
        increment_ms = tc.increment_seconds * 1000
        if mover == "white":
            clock.white_remaining_ms += increment_ms
        else:
            clock.black_remaining_ms += increment_ms

        clock.active_side = next_side
        clock.timeout_side = None
        clock.last_updated_ms = self.time_source()

    def on_position_ready(
        self, side_to_move: PlayerSide, engine_game_over: bool
    ) -> None:
        """
        Reconcile timing state with the current position after session refresh.

        This activates the clock for `side_to_move` when the session is still live,
        or freezes timing when the engine is already in a terminal state or a side
        has timed out.
        """
        clock = self.clock_state
        if clock is None:
            return

        if engine_game_over or clock.timeout_side is not None:
            self.freeze()
            return

        clock.active_side = side_to_move
        if clock.last_updated_ms is None:
            clock.last_updated_ms = self.time_source()
