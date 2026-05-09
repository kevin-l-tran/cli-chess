from fastapi import FastAPI

from src.server.services.lobby_service import LobbyService
from src.server.stores.memory_store import MemoryStore
from src.server.routes.games import make_game_router
from src.server.routes.lobbies import make_lobby_router
from src.server.services.game_service import ServerGameService


store = MemoryStore()
lobby_service = LobbyService(store)
game_service = ServerGameService(store)

app = FastAPI(title="Chess Server Dev API")

app.include_router(make_lobby_router(lobby_service))
app.include_router(make_game_router(game_service))


@app.get("/health")
def health():
    return {"ok": True}
