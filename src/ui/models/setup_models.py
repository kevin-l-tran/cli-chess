from dataclasses import dataclass
from random import choice
from typing import Literal, cast

from src.application.session_types import (
    OpponentType,
    PlayerSide,
    SessionConfig,
    TimeControl,
)

SideChoice = Literal["random", "white", "black"]


@dataclass(frozen=True)
class SetupSelection:
    opponent: OpponentType
    side_choice: SideChoice
    time_control: TimeControl | None
    bot_level: int | None = None

    def to_session_config(self) -> SessionConfig:
        player_side: PlayerSide

        if self.side_choice == "random":
            player_side = choice(("white", "black"))
        else:
            player_side = cast(PlayerSide, self.side_choice)

        return SessionConfig(
            player_side=player_side,
            opponent=self.opponent,
            time_control=self.time_control,
        )