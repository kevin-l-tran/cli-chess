from dataclasses import dataclass, replace
from random import choice
from typing import Literal, cast

from src.shared.protocol_types import PlayerSide


OpponentChoice = Literal["local", "bot", "online"]
SideChoice = Literal["random", "white", "black"]


@dataclass(frozen=True)
class SetupTimeControl:
    initial_seconds: int
    increment_seconds: int = 0


@dataclass(frozen=True)
class SetupSelection:
    """UI-owned setup selection."""

    opponent: OpponentChoice
    side_choice: SideChoice
    time_control: SetupTimeControl | None
    bot_level: int | None = None
    player_side: PlayerSide | None = None

    def with_resolved_player_side(self) -> "SetupSelection":
        if self.player_side is not None:
            return self

        if self.side_choice == "random":
            player_side = choice(("white", "black"))
        else:
            player_side = cast(PlayerSide, self.side_choice)

        return replace(self, player_side=player_side)

    def require_player_side(self) -> PlayerSide:
        if self.player_side is None:
            raise ValueError("SetupSelection must be resolved before starting a game.")
        return self.player_side
