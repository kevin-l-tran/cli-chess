from dataclasses import dataclass


@dataclass(frozen=True)
class GameSettings:
    """
    Represents the settings of a chess game.

    Attributes:
        opponent (str): String indicating the opponent (currently "bot" or "local").
        side (str): String representing the player's side. Will refer to Player 1's side if the opponent is local.
        time (tuple[int, int]): Tuple representing the timer (starting time (min), increment time (sec)), if any. Otherwise defaults to (0,0).
        bot_level (int): The difficulty of the chess bot, if the opponent is a bot. Otherwise defaults to 0.
    """

    opponent: str
    side: str
    time: tuple[int, int]
    bot_level: int
