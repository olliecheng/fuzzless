from textual.app import RenderResult
from textual.widget import Widget
from textual.widgets import (
    DataTable,
    Footer,
    TextArea,
    Input,
    ListView,
    Static,
    ListItem,
    Label,
    Checkbox,
    Button,
)
from textual.containers import Vertical, VerticalScroll, Grid
from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import Key
from textual.reactive import var, reactive
from textual.screen import ModalScreen

from rich.text import Text

import json

DEFAULT_COLOURS = [
    "lawngreen",
    "coral",
    "deepskyblue",
    "hotpink",
    "gold",
    "lightsteelblue",
    "palegoldenrod",
    "tan",
    "crimson",
    "darkcyan",
]


def get_default_colour(index: int) -> str:
    return DEFAULT_COLOURS[index % len(DEFAULT_COLOURS)]


class PatternsWidget(Widget, can_focus=True):
    """Display a greeting."""

    BINDINGS = [
        ("q", "quit", "quit   "),
        Binding("space", "edit_pattern", "edit   "),
        Binding("ctrl+a", "add_pattern", "add", priority=True),
        Binding("ctrl+d", "delete_pattern", "delete   ", priority=True),
        Binding("ctrl+e", "export", "export", priority=True),
        ("ctrl+i", "import", "import   "),
        ("tab", "next_tab", "next tab"),
    ]

    DEFAULT_CSS = """
    PatternsWidget {
        background: black;
    }

    ListView {
        background: black;
        border-bottom: blank;
    }

    ListItem {
        background: black !important;
        border: blank;

        &.-highlight {
            background: black !important;
            text-style: none !important;
            border: heavy lightseagreen;
        }
    }

    Label {
        padding: 0 2;
    }
    """

    def __init__(self, next_tab):
        super().__init__()
        self.action_next_tab = next_tab
        self.patterns_list = None

        self.patterns = []

    def on_resize(self) -> None:
        print(self.app.size.height)
        # if self.patterns_list is not None:
        # self.patterns_list.styles.height = self.app.size.height -
        self.styles.height = self.app.size.height - 2

    def render_pattern(self, pattern: dict) -> str:
        colour = pattern["colour"]
        return (
            f"[{colour}]"
            + f"{pattern['pattern']}\n"
            + f"[b]{pattern['label']}[/b], [i]{pattern['colour']}, edit dist: {pattern['max_edit_dist']}, "
            + ("fwd + rev" if pattern["revcomp"] else "fwd only")
            + f"[/i][/{colour}]"
        )

    def update_pattern(self, index: int, new_pattern: dict) -> None:
        self.patterns[index] = new_pattern
        print("child", self.patterns_list.children[index].children[0])
        self.patterns_list.children[index].children[0].update(
            self.render_pattern(new_pattern)
        )

        self.app.file_reader.patterns_changed()

    def append_pattern(self, pattern: dict) -> None:
        print("p1", self.patterns_list)
        if self.patterns_list is None or not self.patterns_list.is_mounted:
            return

        self.patterns = self.patterns + [pattern]

        item = ListItem(Label(self.render_pattern(pattern)))

        self.patterns_list.append(item)

        self.app.file_reader.patterns_changed()

    def remove_pattern(self, index: int) -> None:
        if self.patterns_list is None or not self.patterns_list.is_mounted:
            return

        del self.patterns[index]
        self.patterns_list.pop(index)

        self.app.file_reader.patterns_changed()

    def compose(self) -> ComposeResult:
        # self.datatable = DataTable(zebra_stripes=True, cell_padding=2)
        # self.textarea = TextArea(json.dumps(self.config, indent=1))
        self.patterns_list = ListView()
        for pattern in self.patterns:
            print(pattern)
            self.append_pattern(pattern)

        with Vertical():
            # yield self.textarea
            yield self.patterns_list
        yield Footer(show_command_palette=False, compact=True)

    def _on_show(self, event):
        out = super()._on_show(event)
        self.query_one(ListView).focus()
        return out

    def action_edit_pattern(self) -> None:
        """Edit the selected pattern."""
        self.app.push_screen("configure")

    def action_delete_pattern(self) -> None:
        """Delete the selected pattern."""
        patterns_list: ListView = self.patterns_list
        index = patterns_list.index
        if index is None:
            return

        self.remove_pattern(index)

    def action_add_pattern(self) -> None:
        """Add a new pattern."""
        new_index = len(self.patterns)
        self.append_pattern(
            {
                "label": "",
                "max_edit_dist": 2,
                "pattern": "",
                "colour": get_default_colour(new_index),
                "revcomp": True,
            }
        )
        self.patterns_list.index = new_index
        self.app.push_screen("configure")


class ConfigurePattern(ModalScreen):
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    DEFAULT_CSS = """
    ConfigurePattern {
        align: center middle;
    }

    #dialog {
        padding: 0 1;
        width: 60;
        height: 25;
        border: thick lightseagreen 80%;
        background: darkslategray;

        grid-size: 2;
        grid-columns: 20 36;
        grid-rows: 4 4 4 2 4 2 3;

        content-align: center top;
    }

    #question {
        # height: 3;
        # width: 1fr;
        content-align: right middle;
    }

    .inline-label {
        padding: 1 1 1 1;
        text-style: italic;
    }

    Input {
        margin: 0;
        width: 100%;
        padding: 0;
    }

    Button {
        width: 10;
    }
    
    #pattern {
        width: 58;
        column-span: 2;
        margin-bottom: 1;
    }

    .span-label {
        text-style: italic;
        padding: 1 1 0 1;
        column-span: 2;
    }

    #revcomp {
        column-span: 2;
        margin-bottom: 1;
        margin-left: 1;
        background: darkslategray;
        color: white;
    }
    """

    def compose(self) -> ComposeResult:
        self.label_input = Input(id="label")
        self.colour_input = Input(id="colour")
        self.edit_dist_input = Input(type="number", id="edit-dist")
        self.pattern_input = Input(id="pattern", placeholder="ATCG...")
        self.pattern_input.on_key = self.on_key

        self.revcomp_checkbox = Checkbox(
            id="revcomp", label="Also match reverse complement", compact=True
        )
        yield Grid(
            Label("[i]Pattern label[/i]", classes="inline-label"),
            self.label_input,
            Label("[i]Pattern colour[/i]", classes="inline-label"),
            self.colour_input,
            Label("[i]Max edit distance[/i]", classes="inline-label"),
            self.edit_dist_input,
            Label("Sequence pattern", classes="span-label"),
            self.pattern_input,
            self.revcomp_checkbox,
            Button("OK", variant="primary", id="ok"),
            Button("Cancel", variant="error", id="cancel"),
            id="dialog",
        )

    def on_screen_resume(self):
        if self.app.patterns is None or self.app.patterns.patterns_list is None:
            return

        patterns_list: ListView = self.app.patterns.patterns_list
        if patterns_list.index is None:
            self.app.pop_screen()
            return

        selected_pattern = self.app.patterns.patterns[patterns_list.index]
        print("index", patterns_list.index)
        print("selected", selected_pattern)
        print("all", self.app.patterns.patterns)

        self.label_input.value = selected_pattern["label"]
        self.colour_input.value = selected_pattern["colour"]
        self.edit_dist_input.value = str(selected_pattern["max_edit_dist"])
        self.pattern_input.value = selected_pattern["pattern"]
        self.revcomp_checkbox.value = selected_pattern["revcomp"]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        if event.button.id == "ok":
            self.save_changes()

    def on_key(self, event: Key) -> None:
        if event.key == "enter":
            self.save_changes()

    def save_changes(self):
        patterns_list: ListView = self.app.patterns.patterns_list
        print("launch")
        index = patterns_list.index

        self.app.patterns.update_pattern(
            index,
            {
                "label": self.label_input.value,
                "colour": self.colour_input.value,
                "max_edit_dist": int(self.edit_dist_input.value),
                "pattern": self.pattern_input.value,
                "revcomp": self.revcomp_checkbox.value,
            },
        )

        self.app.pop_screen()
