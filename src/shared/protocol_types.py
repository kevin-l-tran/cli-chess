from typing import Literal

Square = tuple[int, int]

PlayerSide = Literal["white", "black"]
GameMode = Literal["local", "bot", "online"]

ParticipantRole = Literal[
    "white",
    "black",
    "spectator",
    "local_controller",
]

ConnectionState = Literal[
    "disconnected",
    "connecting",
    "connected",
    "reconnecting",
    "error",
]

CommandStatus = Literal[
    "accepted",
    "duplicate",
    "duplicate_conflict",
    "unauthorized",
    "not_player",
    "not_your_turn",
    "stale_position",
    "invalid_move",
    "ambiguous_move",
    "game_over",
    "draw_unavailable",
    "undo_unavailable",
    "bot_pending",
    "connection_error",
    "error",
]

GameEventKind = Literal[
    "game_started",
    "move_applied",
    "draw_offered",
    "draw_accepted",
    "draw_declined",
    "resigned",
    "timeout",
    "game_concluded",
    "bot_turn_started",
    "bot_move_applied",
    "player_connected",
    "player_disconnected",
    "spectator_joined",
    "spectator_left",
    "sync_error",
]
