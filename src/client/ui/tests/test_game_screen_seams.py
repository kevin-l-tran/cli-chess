from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from src.application.command_types import CommandResult
from src.application.viewer_types import (
    AuthoritativeSnapshot,
    LocalDraftView,
    ViewerSessionView,
)
from src.client.ui.models.setup_models import SetupSelection
from src.client.ui.screens import game as game_screen_module
from src.client.ui.screens.game import GameScreen
from src.shared.ids import LobbyId, PlayerId, RequestId
from src.shared.protocol_types import PlayerSide


def make_selection() -> SetupSelection:
    return SetupSelection(
        opponent="local",
        side_choice="white",
        time_control=None,
        bot_level=None,
        player_side="white",
    )


def make_snapshot(
    *, is_game_over: bool = False, side_to_move: PlayerSide | None = "white"
) -> AuthoritativeSnapshot:
    return AuthoritativeSnapshot(
        board_glyphs=[["." for _ in range(8)] for _ in range(8)],
        board_squares=None,
        side_to_move=side_to_move,
        last_move_from=None,
        last_move_to=None,
        check_square=None,
        move_list=[],
        draw_offered_by=None,
        is_player_checked=False,
        is_game_over=is_game_over,
        timed_game=None,
        outcome=None,
        feedback=None,
    )


def make_view(
    *,
    current_ply: int = 0,
    last_event_seq: int | None = None,
    can_submit_move: bool = True,
    can_accept_draw: bool = False,
    can_resign: bool = True,
    can_request_undo: bool = False,
    side_to_move: PlayerSide | None = "white",
) -> ViewerSessionView:
    return ViewerSessionView(
        lobby_id=LobbyId("test-lobby"),
        viewer_id=PlayerId("test-viewer"),
        viewer_role="local_controller",
        viewer_side=None,
        current_ply=current_ply,
        last_event_seq=current_ply if last_event_seq is None else last_event_seq,
        connection_state="connected",
        can_submit_move=can_submit_move,
        can_submit_for_side=side_to_move if can_submit_move else None,
        can_offer_draw=can_submit_move,
        can_accept_draw=can_accept_draw,
        can_resign=can_resign,
        can_request_undo=can_request_undo,
        can_spectate=False,
        status_text=None,
        snapshot=make_snapshot(
            is_game_over=not can_submit_move and side_to_move is None,
            side_to_move=side_to_move,
        ),
        preview_hints=None,
    )


def make_draft(
    *,
    text: str = "",
    status: str = "empty",
    canonical_text: str | None = None,
    base_ply: int | None = 0,
    is_promotion_pending: bool = False,
    submit_text: str | None = None,
) -> LocalDraftView:
    return LocalDraftView(
        text=text,
        status=status,  # type: ignore[arg-type]
        canonical_text=canonical_text,
        base_ply=base_ply,
        candidate_moves=set(),
        autocompletions=[],
        promotion_prompt_position=None,
        is_promotion_pending=is_promotion_pending,
        submit_text=submit_text,
    )


class FakeClient:
    def __init__(self, view: ViewerSessionView) -> None:
        self.view = view
        self.submit_result: CommandResult | None = None
        self.submit_calls: list[dict[str, Any]] = []
        self.accept_draw_calls: list[dict[str, Any]] = []
        self.resign_calls: list[dict[str, Any]] = []
        self.undo_calls: list[dict[str, Any]] = []
        self.tick_calls = 0

    def get_view(self) -> ViewerSessionView:
        return self.view

    def submit_move(
        self,
        move_text: str,
        *,
        request_id: RequestId,
        expected_ply: int,
        offer_draw: bool = False,
    ) -> CommandResult:
        self.submit_calls.append(
            {
                "move_text": move_text,
                "request_id": request_id,
                "expected_ply": expected_ply,
                "offer_draw": offer_draw,
            }
        )
        assert self.submit_result is not None, (
            "Set FakeClient.submit_result before confirming."
        )
        if self.submit_result.view is not None:
            self.view = self.submit_result.view
        return self.submit_result

    def accept_draw_offer(
        self, *, request_id: RequestId, expected_ply: int
    ) -> CommandResult:
        self.accept_draw_calls.append(
            {"request_id": request_id, "expected_ply": expected_ply}
        )
        return CommandResult(ok=True, status="accepted", view=self.view)

    def resign(self, *, request_id: RequestId) -> CommandResult:
        self.resign_calls.append({"request_id": request_id})
        return CommandResult(ok=True, status="accepted", view=self.view)

    def request_undo(self, *, request_id: RequestId) -> CommandResult:
        self.undo_calls.append({"request_id": request_id})
        return CommandResult(ok=True, status="accepted", view=self.view)

    def events_since(self, last_seen_seq: int) -> list[Any]:
        return []

    def tick(self) -> None:
        self.tick_calls += 1


class FakeDraft:
    def __init__(self, initial: LocalDraftView | None = None) -> None:
        self.current = initial or make_draft()
        self.sync_calls: list[ViewerSessionView] = []
        self.set_text_calls: list[str] = []
        self.click_square_calls: list[Any] = []
        self.select_promotion_piece_calls: list[str] = []
        self.clear_calls = 0

    def sync_to_view(self, view: ViewerSessionView) -> None:
        self.sync_calls.append(view)
        if self.current.base_ply is None or self.current.base_ply != view.current_ply:
            self.current = replace(self.current, base_ply=view.current_ply)

    def set_text(self, text: str) -> LocalDraftView:
        self.set_text_calls.append(text)
        self.current = make_draft(
            text=text,
            status="unvalidated" if text else "empty",
            base_ply=self.current.base_ply,
            submit_text=text or None,
        )
        return self.current

    def clear(self) -> LocalDraftView:
        self.clear_calls += 1
        self.current = make_draft(base_ply=self.current.base_ply)
        return self.current

    def click_square(self, square: Any) -> LocalDraftView:
        self.click_square_calls.append(square)
        self.current = make_draft(
            text="e2",
            status="ambiguous",
            base_ply=self.current.base_ply,
            submit_text=None,
        )
        return self.current

    def select_promotion_piece(self, piece: str) -> LocalDraftView:
        self.select_promotion_piece_calls.append(piece)
        self.current = make_draft(
            text="e8=Q",
            status="resolved",
            canonical_text="e8=Q",
            base_ply=self.current.base_ply,
            submit_text="e8=Q",
        )
        return self.current

    def view(self) -> LocalDraftView:
        return self.current


class FocusTarget:
    def __init__(self) -> None:
        self.focus_calls = 0

    def focus(self) -> None:
        self.focus_calls += 1


@pytest.fixture
def screen_harness(monkeypatch: pytest.MonkeyPatch):
    view = make_view(current_ply=3)
    client = FakeClient(view)
    draft = FakeDraft(make_draft(base_ply=3))
    screen = GameScreen(client=client, draft=draft, selection=make_selection())

    refresh_calls: list[None] = []
    focus_target = FocusTarget()

    monkeypatch.setattr(screen, "_refresh_view", lambda: refresh_calls.append(None))
    monkeypatch.setattr(screen, "_move_input_widget", lambda: focus_target)
    monkeypatch.setattr(
        screen,
        "set_timer",
        lambda _delay, callback: callback(),
    )
    monkeypatch.setattr(
        game_screen_module,
        "new_request_id",
        lambda: RequestId("fixed-request-id"),
    )

    return SimpleNamespace(
        screen=screen,
        client=client,
        draft=draft,
        refresh_calls=refresh_calls,
        focus_target=focus_target,
        initial_view=view,
    )


def test_typing_only_updates_local_draft(screen_harness: SimpleNamespace) -> None:
    event = SimpleNamespace(input=SimpleNamespace(id="move-input"), value="Nf3")

    screen_harness.screen.on_input_changed(event)

    assert screen_harness.draft.set_text_calls == ["Nf3"]
    assert screen_harness.draft.click_square_calls == []
    assert screen_harness.draft.select_promotion_piece_calls == []
    assert screen_harness.client.submit_calls == []
    assert len(screen_harness.refresh_calls) == 1


def test_typing_ignores_non_move_input(screen_harness: SimpleNamespace) -> None:
    event = SimpleNamespace(input=SimpleNamespace(id="other-input"), value="Nf3")

    screen_harness.screen.on_input_changed(event)

    assert screen_harness.draft.set_text_calls == []
    assert screen_harness.client.submit_calls == []
    assert screen_harness.refresh_calls == []


def test_board_click_only_updates_local_draft(
    screen_harness: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        screen_harness.screen, "_should_auto_confirm_click", lambda: False
    )
    square = (6, 4)

    screen_harness.screen.on_chess_board_square_pressed(SimpleNamespace(square=square))

    assert screen_harness.draft.click_square_calls == [square]
    assert screen_harness.draft.set_text_calls == []
    assert screen_harness.client.submit_calls == []
    assert len(screen_harness.refresh_calls) == 1
    assert screen_harness.focus_target.focus_calls == 1


def test_promotion_selection_only_updates_local_draft(
    screen_harness: SimpleNamespace,
) -> None:
    screen_harness.screen.on_promotion_picker_piece_selected(SimpleNamespace(piece="Q"))

    assert screen_harness.draft.select_promotion_piece_calls == ["Q"]
    assert screen_harness.draft.set_text_calls == []
    assert screen_harness.draft.click_square_calls == []
    assert screen_harness.client.submit_calls == []
    assert len(screen_harness.refresh_calls) == 1
    assert screen_harness.focus_target.focus_calls == 1


def test_confirm_move_calls_game_client_submit_move(
    screen_harness: SimpleNamespace,
) -> None:
    screen_harness.screen.state.latest_draft_view = make_draft(
        text="e2e4",
        status="resolved",
        canonical_text="e2e4",
        base_ply=3,
        submit_text="e2e4",
    )
    screen_harness.client.submit_result = CommandResult(
        ok=False,
        status="invalid_move",
        message="No legal move matches the current draft.",
        view=screen_harness.initial_view,
    )

    screen_harness.screen._confirm_move()

    assert screen_harness.client.submit_calls == [
        {
            "move_text": "e2e4",
            "request_id": RequestId("fixed-request-id"),
            "expected_ply": 3,
            "offer_draw": False,
        }
    ]
    assert screen_harness.draft.clear_calls == 0
    assert len(screen_harness.refresh_calls) == 1
    assert screen_harness.focus_target.focus_calls == 1


def test_confirm_uses_offer_draw_and_accepted_submit_clears_draft(
    screen_harness: SimpleNamespace,
) -> None:
    new_view = make_view(current_ply=4, last_event_seq=4, side_to_move="black")
    screen_harness.screen.state.offer_draw = True
    screen_harness.screen.state.latest_draft_view = make_draft(
        text="e2e4",
        status="resolved",
        canonical_text="e2e4",
        base_ply=3,
        submit_text="e2e4",
    )
    screen_harness.client.submit_result = CommandResult(
        ok=True,
        status="accepted",
        event_seq=4,
        view=new_view,
    )

    screen_harness.screen._confirm_move()

    assert screen_harness.client.submit_calls == [
        {
            "move_text": "e2e4",
            "request_id": RequestId("fixed-request-id"),
            "expected_ply": 3,
            "offer_draw": True,
        }
    ]
    assert screen_harness.screen.state.latest_view is new_view
    assert screen_harness.screen.state.last_event_seq == 4
    assert screen_harness.draft.sync_calls[-1] is new_view
    assert screen_harness.draft.clear_calls == 1
    assert screen_harness.screen.state.latest_draft_view.text == ""
    assert screen_harness.screen.state.offer_draw is False


def test_rejected_submit_with_view_resyncs_but_does_not_clear_draft(
    screen_harness: SimpleNamespace,
) -> None:
    screen_harness.draft.current = make_draft(
        text="bad",
        status="unvalidated",
        base_ply=3,
        submit_text="bad",
    )
    screen_harness.screen.state.latest_draft_view = screen_harness.draft.current
    result_view = make_view(current_ply=3, last_event_seq=3)
    screen_harness.client.submit_result = CommandResult(
        ok=False,
        status="invalid_move",
        message="Invalid move.",
        view=result_view,
    )

    screen_harness.screen._confirm_move()

    assert screen_harness.client.submit_calls[0]["move_text"] == "bad"
    assert screen_harness.screen.state.latest_view is result_view
    assert screen_harness.draft.sync_calls[-1] is result_view
    assert screen_harness.draft.clear_calls == 0
    assert screen_harness.screen.state.latest_draft_view.text == "bad"


def test_replace_view_syncs_local_draft_to_new_authoritative_view(
    screen_harness: SimpleNamespace,
) -> None:
    new_view = make_view(current_ply=8, last_event_seq=12, side_to_move="black")

    screen_harness.screen._replace_view(new_view)

    assert screen_harness.screen.state.latest_view is new_view
    assert screen_harness.screen.state.last_event_seq == 12
    assert screen_harness.draft.sync_calls == [screen_harness.initial_view, new_view]
    assert screen_harness.screen.state.latest_draft_view is screen_harness.draft.view()
