from typing import NewType
from uuid import uuid4

PlayerId = NewType("PlayerId", str)
LobbyId = NewType("LobbyId", str)
RequestId = NewType("RequestId", str)
EventSeq = NewType("EventSeq", int)


def new_request_id() -> RequestId:
    return RequestId(str(uuid4()))
