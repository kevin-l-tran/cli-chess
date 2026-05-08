from pathlib import Path
from typing import cast

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from src.application.session_types import OpponentType, TimeControl
from src.ui.models.setup_models import SetupSelection, SideChoice
from src.ui.widgets.setup.inputs import CustomTimeInput, TerminalOption, TerminalStep


class SetupForm(Vertical):
    DEFAULT_CSS = (Path(__file__).parent / "css" / "form.tcss").read_text()

    _SIDES: tuple[tuple[SideChoice, str], ...] = (
        ("random", "Random"),
        ("white", "White"),
        ("black", "Black"),
    )

    _TIMES: tuple[tuple[str, str], ...] = (
        ("none", "No clock"),
        ("3+2", "3+2"),
        ("5+0", "5+0"),
        ("10+0", "10+0"),
        ("15+10", "15+10"),
        ("custom", "Custom"),
    )

    opponent: reactive[OpponentType] = reactive("local")
    side_choice: reactive[SideChoice] = reactive("random")
    time_choice: reactive[str] = reactive("5+0")
    bot_level: reactive[int] = reactive(4)
    custom_time_value: reactive[tuple[int, int] | None] = reactive((5, 0))

    class SettingsChanged(Message):
        bubble = True

        def __init__(self, selection: SetupSelection) -> None:
            super().__init__()
            self.selection = selection
            # Compatibility with existing SetupScreen code that expects msg.settings.
            self.settings = selection

    def compose(self) -> ComposeResult:
        with Vertical(classes="setup-section", id="opponent-section"):
            yield Static(
                self._section_title("Opponent"),
                classes="section-title",
                markup=False,
            )
            with Horizontal(classes="option-row", id="opponent-row"):
                yield Static("Opponent:", classes="field-label", markup=False)
                yield TerminalOption(
                    "Local (2P)",
                    control_id="local",
                    selected=self.opponent == "local",
                    id="local",
                )
                yield TerminalOption(
                    "Bot",
                    control_id="bot",
                    selected=self.opponent == "bot",
                    id="bot",
                )

        with Vertical(classes="setup-section", id="bot-section"):
            yield Static(
                self._section_title("Bot"),
                classes="section-title",
                id="bot-section-title",
                markup=False,
            )
            with Horizontal(classes="level-row", id="bot-level-row"):
                yield Static(
                    "Level:",
                    classes="field-label",
                    id="bot-level-label",
                    markup=False,
                )
                yield TerminalStep("[ - ]", control_id="level-minus", id="level-minus")
                yield Static("", id="bot-level-display", markup=False)
                yield TerminalStep("[ + ]", control_id="level-plus", id="level-plus")
            yield Static("", id="bot-level-track", markup=True)

        with Vertical(classes="setup-section", id="game-section"):
            yield Static(
                self._section_title("Game"),
                classes="section-title",
                markup=False,
            )

            with Horizontal(classes="field-row", id="side-row"):
                yield Static(
                    "Side:",
                    classes="field-label",
                    id="side-label",
                    markup=False,
                )
                for value, label in self._SIDES:
                    yield TerminalOption(
                        label,
                        control_id=f"side-{value}",
                        selected=self.side_choice == value,
                        id=f"side-{value}",
                    )

            with Horizontal(classes="field-row", id="time-row-main"):
                yield Static("Time:", classes="field-label", markup=False)
                for value, label in self._TIMES[:4]:
                    yield TerminalOption(
                        label,
                        control_id=self._time_button_id(value),
                        selected=self.time_choice == value,
                        id=self._time_button_id(value),
                    )

            with Horizontal(classes="field-row", id="time-row-extra"):
                yield Static("", classes="field-label", markup=False)
                for value, label in self._TIMES[4:]:
                    yield TerminalOption(
                        label,
                        control_id=self._time_button_id(value),
                        selected=self.time_choice == value,
                        id=self._time_button_id(value),
                    )

            yield CustomTimeInput(id="custom-time-input")

    def on_mount(self) -> None:
        self._sync_rows()
        self._sync_controls()
        self._emit()

    def settings(self) -> SetupSelection:
        bot_level = self.bot_level if self.opponent == "bot" else None
        return SetupSelection(
            opponent=self.opponent,
            side_choice=self.side_choice,
            time_control=self._selected_time_control(),
            bot_level=bot_level,
        )

    @property
    def is_valid(self) -> bool:
        return self.time_choice != "custom" or self.custom_time_value is not None

    def cycle_opponent(self) -> None:
        self.opponent = "bot" if self.opponent == "local" else "local"

    def increment_bot_level(self) -> None:
        self.bot_level = min(10, self.bot_level + 1)

    def cycle_time(self) -> None:
        values = [value for value, _label in self._TIMES]
        index = values.index(self.time_choice)
        self.time_choice = values[(index + 1) % len(values)]

    def watch_opponent(self, _: OpponentType) -> None:
        self._sync_after_state_change(rows=True, controls=True)

    def watch_side_choice(self, _: SideChoice) -> None:
        self._sync_after_state_change(controls=True)

    def watch_time_choice(self, _: str) -> None:
        self._sync_after_state_change(rows=True, controls=True)

    def watch_bot_level(self, _: int) -> None:
        self._sync_after_state_change(controls=True)

    def watch_custom_time_value(self, _: tuple[int, int] | None) -> None:
        if self.is_mounted and self.time_choice == "custom":
            self._emit()

    def on_terminal_option_pressed(self, event: TerminalOption.Pressed) -> None:
        self._handle_control(event.control_id)

    def on_terminal_step_pressed(self, event: TerminalStep.Pressed) -> None:
        self._handle_control(event.control_id)

    def on_custom_time_input_changed(self, event: CustomTimeInput.Changed) -> None:
        self.custom_time_value = event.value

    def _handle_control(self, control_id: str) -> None:
        if control_id == "local":
            self.opponent = "local"
        elif control_id == "bot":
            self.opponent = "bot"
        elif control_id == "level-minus":
            self.bot_level = max(1, self.bot_level - 1)
        elif control_id == "level-plus":
            self.bot_level = min(10, self.bot_level + 1)
        elif control_id.startswith("side-"):
            self.side_choice = cast(SideChoice, control_id.removeprefix("side-"))
        elif control_id.startswith("time-"):
            self.time_choice = self._time_value_from_button_id(control_id)

    def _sync_after_state_change(
        self,
        *,
        rows: bool = False,
        controls: bool = False,
    ) -> None:
        if not self.is_mounted:
            return

        if rows:
            self._sync_rows()
        if controls:
            self._sync_controls()

        self._emit()

    def _selected_time_control(self) -> TimeControl | None:
        if self.time_choice == "none":
            return None

        if self.time_choice == "custom":
            if self.custom_time_value is None:
                return None

            mins, inc = self.custom_time_value
            return TimeControl(
                initial_seconds=mins * 60,
                increment_seconds=inc,
            )

        mins_s, inc_s = self.time_choice.split("+")
        return TimeControl(
            initial_seconds=int(mins_s) * 60,
            increment_seconds=int(inc_s),
        )

    def _sync_rows(self) -> None:
        bot_selected = self.opponent == "bot"

        self.query_one("#bot-section", Vertical).display = bot_selected
        self.query_one("#side-label", Static).update(
            "Side:" if bot_selected else "Player 1 Side:"
        )
        self.query_one("#custom-time-input", CustomTimeInput).display = (
            self.time_choice == "custom"
        )

    def _sync_controls(self) -> None:
        self._set_option("#local", "Local (2P)", self.opponent == "local")
        self._set_option("#bot", "Bot", self.opponent == "bot")

        for value, label in self._SIDES:
            self._set_option(f"#side-{value}", label, self.side_choice == value)

        for value, label in self._TIMES:
            self._set_option(
                f"#{self._time_button_id(value)}",
                label,
                self.time_choice == value,
            )

        self.query_one("#bot-level-display", Static).update(
            f"{self.bot_level} ({self._format_bot_level(self.bot_level)})"
        )
        self.query_one("#bot-level-track", Static).update(self._format_level_track())

    def _set_option(self, selector: str, label: str, selected: bool) -> None:
        option = self.query_one(selector, TerminalOption)
        option.update_state(label, selected=selected)

    def _emit(self) -> None:
        self.post_message(self.SettingsChanged(self.settings()))

    def _section_title(self, label: str) -> str:
        width = 76
        prefix = f"-- {label} "
        return prefix + "-" * max(0, width - len(prefix))

    def _format_bot_level(self, value: int) -> str:
        if value <= 2:
            return "easy"
        if value <= 5:
            return "medium"
        if value <= 8:
            return "hard"
        return "expert"

    def _format_level_track(self) -> str:
        cells: list[str] = []
        for value in range(1, 11):
            if value == self.bot_level:
                cells.append(f"[bold][{value}][/bold]")
            else:
                cells.append(f" {value} ")
        return " ".join(cells)

    def _time_button_id(self, value: str) -> str:
        return f"time-{value.replace('+', '-')}"

    def _time_value_from_button_id(self, button_id: str) -> str:
        value = button_id.removeprefix("time-")
        if value in {"3-2", "5-0", "10-0", "15-10"}:
            return value.replace("-", "+", 1)
        return value
