from textual.widget import Widget
from textual.widgets import (
    Footer,
    ListView,
    ListItem,
    Label,
)
from textual.containers import Vertical
from textual.app import ComposeResult
from textual.binding import Binding

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
        ("q", "quit", "quit"),
        Binding("space", "edit_pattern", "edit"),
        Binding("ctrl+a", "add_pattern", "add", priority=True),
        Binding("ctrl+d", "delete_pattern", "delete  │ ", priority=True),
        ("ctrl+i", "import", "import"),
        Binding("ctrl+e", "export", "export  │ "),
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
            + f"[b]{pattern['label']}[/b], {pattern['colour']}, edit dist: {pattern['max_edit_dist']}, "
            + ("fwd + rev" if pattern["revcomp"] else "fwd only")
            + f"[/{colour}]"
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

    def clear_patterns(self) -> None:
        self.patterns = []
        self.patterns_list.clear()

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

    def action_export(self) -> None:
        """Export patterns to CSV file."""
        self.app.push_screen("export_csv")

    def action_import(self) -> None:
        """Import patterns from CSV file."""
        self.app.push_screen("import_csv")
