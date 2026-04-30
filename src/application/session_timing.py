from dataclasses import dataclass

from .session_types import PlayerSide, TimeControl
from .clock import ClockFrame, ClockState, TimeSource, advance_clock, freeze_clock


@dataclass
class SessionTiming:
    clock_state: ClockState | None
    time_control: TimeControl | None
    time_source: TimeSource

    def sync(self, engine_game_over: bool) -> bool:
        return advance_clock(
            self.clock_state,
            now_ms=self.time_source(),
            is_game_over=engine_game_over,
        )

    def is_timed(self) -> bool:
        return self.clock_state is not None

    def timeout_side(self) -> PlayerSide | None:
        if self.clock_state is None:
            return None
        return self.clock_state.timeout_side

    def is_session_over(self, *, engine_game_over: bool) -> bool:
        return engine_game_over or self.timeout_side() is not None

    def freeze(self) -> None:
        freeze_clock(self.clock_state)

    def push_frame(self) -> None:
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
        clock = self.clock_state
        if clock is None or not clock.history:
            return
        frame = clock.history.pop()
        clock.white_remaining_ms = frame.white_remaining_ms
        clock.black_remaining_ms = frame.black_remaining_ms
        clock.active_side = frame.active_side
        clock.timeout_side = frame.timeout_side
        clock.last_updated_ms = frame.last_updated_ms

    def on_move_committed(self, next_side: PlayerSide) -> None:
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
        clock = self.clock_state
        if clock is None:
            return

        if engine_game_over or clock.timeout_side is not None:
            self.freeze()
            return

        clock.active_side = side_to_move
        if clock.last_updated_ms is None:
            clock.last_updated_ms = self.time_source()
