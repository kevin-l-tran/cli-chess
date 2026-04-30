from dataclasses import dataclass, field
import time
from typing import Callable

from .session_types import PlayerSide

TimeSource = Callable[[], int]
"""Callable that returns the current monotonic time in milliseconds."""


def system_time_ms() -> int:
    """
    Return the current monotonic time in milliseconds.
    """
    return time.monotonic_ns() // 1_000_000


@dataclass(frozen=True)
class ClockFrame:
    """
    Immutable snapshot of clock state used for timing undo restoration.
    """
    white_remaining_ms: int
    black_remaining_ms: int
    active_side: PlayerSide | None
    timeout_side: PlayerSide | None
    last_updated_ms: int | None


@dataclass
class ClockState:
    """
    Mutable session-owned chess clock state.

    Attributes:
        white_remaining_ms:
            White's remaining clock time in milliseconds.

        black_remaining_ms:
            Black's remaining clock time in milliseconds.

        active_side:
            Which side's clock is currently running. `None` means no clock is
            active, such as after timeout or while frozen.

        timeout_side:
            Which side has lost on time, if any.

        last_updated_ms:
            Monotonic timestamp of the last clock synchronization point.

        history:
            Stack of prior timing frames used to restore timing state during
            undo operations.
    """
    white_remaining_ms: int
    black_remaining_ms: int
    active_side: PlayerSide | None
    timeout_side: PlayerSide | None
    last_updated_ms: int | None
    history: list[ClockFrame] = field(default_factory=list)


def freeze_clock(clock: ClockState | None) -> None:
    """
    Stop a clock from continuing to run.

    Parameters:
        clock (ClockState | None):
            The clock state to freeze. `None` is accepted so untimed sessions
            can reuse the same timing paths without extra branching.

    Behavior:
        - clears the active side
        - clears the last-updated timestamp
        - leaves remaining times and timeout state unchanged
    """
    if clock is None:
        return
    clock.active_side = None
    clock.last_updated_ms = None


def advance_clock(
    clock: ClockState | None,
    now_ms: int,
    is_game_over: bool,
) -> bool:
    """
    Advance the active clock to a target monotonic timestamp.

    Parameters:
        clock:
            The mutable clock state to update. `None` means the session is
            untimed.

        now_ms:
            The current monotonic time in milliseconds.

        is_game_over:
            Whether the engine has already reached a terminal outcome. When
            true, the clock is frozen instead of advanced.

    Returns:
        bool:
            `True` when this call newly causes a timeout, otherwise `False`.

    Behavior:
        - does nothing for untimed sessions or when no side is active
        - subtracts elapsed time from the active side
        - marks the timed-out side when remaining time reaches zero
        - freezes the clock after timeout or engine game over
    """
    if clock is None or clock.active_side is None:
        return False

    if is_game_over or clock.timeout_side is not None:
        freeze_clock(clock)
        return False

    last = clock.last_updated_ms
    if last is None:
        clock.last_updated_ms = now_ms
        return False

    elapsed_ms = max(0, now_ms - last)
    if elapsed_ms == 0:
        return False

    if clock.active_side == "white":
        clock.white_remaining_ms = max(0, clock.white_remaining_ms - elapsed_ms)
        timed_out = clock.white_remaining_ms == 0
        if timed_out:
            clock.timeout_side = "white"
    else:
        clock.black_remaining_ms = max(0, clock.black_remaining_ms - elapsed_ms)
        timed_out = clock.black_remaining_ms == 0
        if timed_out:
            clock.timeout_side = "black"

    if timed_out:
        clock.active_side = None
        clock.last_updated_ms = None
        return True

    clock.last_updated_ms = now_ms
    return False
