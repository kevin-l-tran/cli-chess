from dataclasses import dataclass

from src.application.viewer_types import ViewerSessionView
from src.shared.protocol_types import CommandStatus


@dataclass(frozen=True)
class CommandResult:
    """Represents the result of a handled game command."""

    ok: bool
    status: CommandStatus
    message: str | None = None
    view: ViewerSessionView | None = None
