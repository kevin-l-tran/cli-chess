from textual.app import ComposeResult
from textual.containers import Horizontal, HorizontalScroll, Vertical
from textual.widgets import Footer, Input, Static

from src.client.ui.widgets.game.chess_board import ChessBoard
from src.client.ui.widgets.game.controls import GameControls
from src.client.ui.widgets.game.game_over_panel import GameOverPanel
from src.client.ui.widgets.game.promotion_picker import PromotionPicker
from src.client.ui.widgets.game.side_panel import GameSidePanel


def compose_game_screen() -> ComposeResult:
    yield Static(
        "CLI Chess",
        id="topbar",
        markup=False,
    )

    with HorizontalScroll(id="game-scroll"):
        with Vertical(id="game-root"):
            with Horizontal(id="main"):
                board_panel = Vertical(id="left", classes="frame titled-frame")
                board_panel.border_title = "Board"
                with board_panel:
                    yield ChessBoard(orientation="white", id="board")
                    yield PromotionPicker(id="promotion-row")

                with Vertical(id="right"):
                    yield GameSidePanel(id="side-panel")

                    actions_panel = Vertical(
                        id="actions-panel",
                        classes="frame titled-frame",
                    )
                    actions_panel.border_title = "Actions"
                    with actions_panel:
                        yield GameControls(id="controls")
                        yield GameOverPanel(id="game-over-panel")

            move_composer = Vertical(
                id="move-composer",
                classes="frame titled-frame",
            )
            move_composer.border_title = "Move"
            with move_composer:
                yield Input(
                    placeholder="Enter move (e2e4 / Nf3) ...",
                    id="move-input",
                )
                with Horizontal(id="draft-row"):
                    yield Static(
                        "Status: empty",
                        id="draft-status",
                        classes="composer_meta",
                        markup=False,
                    )
                    yield Static(
                        "Completions: -",
                        id="autocomplete",
                        classes="composer_meta",
                        markup=False,
                    )
                yield Static(
                    "",
                    id="feedback",
                    classes="composer_feedback",
                    markup=False,
                )

    yield Footer()
