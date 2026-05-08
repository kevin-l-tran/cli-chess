from dataclasses import dataclass
import hashlib
import json
from typing import Any, Literal

from src.shared.ids import PlayerId, RequestId
from src.shared.protocol_types import CommandStatus

from .authoritative_session_types import CachedCommandResult


DuplicateKind = Literal["miss", "duplicate", "conflict"]


@dataclass(frozen=True)
class DuplicateCheck:
    kind: DuplicateKind
    cached: CachedCommandResult | None = None


class CommandIdempotencyCache:
    def __init__(
        self,
        backing: dict[tuple[PlayerId, RequestId], CachedCommandResult] | None = None,
    ) -> None:
        self._cache = {} if backing is None else backing

    @property
    def raw(self) -> dict[tuple[PlayerId, RequestId], CachedCommandResult]:
        return self._cache

    def check(
        self,
        *,
        player_id: PlayerId,
        request_id: RequestId,
        fingerprint: str,
    ) -> DuplicateCheck:
        cached = self._cache.get((player_id, request_id))
        if cached is None:
            return DuplicateCheck("miss")
        if cached.fingerprint != fingerprint:
            return DuplicateCheck("conflict", cached)
        return DuplicateCheck("duplicate", cached)

    def record(
        self,
        *,
        player_id: PlayerId,
        request_id: RequestId,
        fingerprint: str,
        ok: bool,
        status: CommandStatus,
        message: str | None,
    ) -> None:
        self._cache[(player_id, request_id)] = CachedCommandResult(
            fingerprint=fingerprint,
            ok=ok,
            status=status,
            message=message,
        )


def command_fingerprint(kind: str, payload: dict[str, Any]) -> str:
    body = json.dumps(
        {"kind": kind, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
