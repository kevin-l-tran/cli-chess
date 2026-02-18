from itertools import cycle

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

TITLE = r"""
________/\\\\\\\\\__/\\\________/\\\__/\\\\\\\\\\\\\\\_____/\\\\\\\\\\\_______/\\\\\\\\\\\___        
 _____/\\\////////__\/\\\_______\/\\\_\/\\\///////////____/\\\/////////\\\___/\\\/////////\\\_       
  ___/\\\/___________\/\\\_______\/\\\_\/\\\______________\//\\\______\///___\//\\\______\///__      
   __/\\\_____________\/\\\\\\\\\\\\\\\_\/\\\\\\\\\\\_______\////\\\___________\////\\\_________     
    _\/\\\_____________\/\\\/////////\\\_\/\\\///////___________\////\\\___________\////\\\______    
     _\//\\\____________\/\\\_______\/\\\_\/\\\_____________________\////\\\___________\////\\\___   
      __\///\\\__________\/\\\_______\/\\\_\/\\\______________/\\\______\//\\\___/\\\______\//\\\__  
       ____\////\\\\\\\\\_\/\\\_______\/\\\_\/\\\\\\\\\\\\\\\_\///\\\\\\\\\\\/___\///\\\\\\\\\\\/___ 
        _______\/////////__\///________\///__\///////////////____\///////////_______\///////////_____
"""

TIPS = cycle(
    [
        "Tip: Checks, captures, threats.",
        "Tip: Develop pieces, then attack.",
        "Tip: Castle early.",
        "Tip: Undefended pieces are targets.",
        "Tip: Trade when ahead.",
        "Tip: Activate rooks on open files.",
        "Tip: Improve your worst piece.",
        "Tip: King activity wins endgames.",
        "Tip: Two threats beat one defense.",
        "Tip: Count attackers vs defenders.",
    ]
)


def styled_title(title: str) -> Text:
    t = Text(title)
    for i, ch in enumerate(t.plain):
        if ch in "/\\":
            t.stylize("rgb(0,255,215)", i, i + 1)
    return t


class Tips(Static):
    def on_mount(self) -> None:
        self.update(next(TIPS))
        self.set_interval(5, self.action_next_word)

    def action_next_word(self) -> None:
        tip = next(TIPS)
        self.update(tip)


class MenuScreen(Screen[None]):
    CSS = """
    MenuScreen {
        align: center middle;
    }

    #panel {
        width: 120;
        height: auto;
        padding: 1 2;
        border: rgb(0,255,215);
    }

    #title {
        text-align: center;
    }

    #tagline {
        text-align: center;
        margin: 1 0 1 0;
    }

    #menu {
        align: center middle;
        height: auto;
        margin-top: 1;
    }

    #menu Button {
        width: 28;
        height: 3;
        padding: 0 1;

        background: transparent;
        color: rgb(0,255,215);

        border: ascii rgb(0,255,215);
        content-align: center middle;
        text-style: bold;
    }

    #menu Button:hover {
        border: ascii white;
    }

    #menu Button:focus {
        color: white;
        border: ascii white;
    }
    """

    BINDINGS = [
        Binding("enter", "start", "Start"),
        Binding("s", "settings", "Settings"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(styled_title(TITLE), id="title"),
            Tips(id="tagline"),
            Vertical(
                Button("Start Game", id="start"),
                Button("Settings", id="settings"),
                Button("Quit", id="quit"),
                id="menu",
            ),
            id="panel",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Terminal Chess"
        self.query_one("#start", Button).focus()
