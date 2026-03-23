import csv

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Footer, Label, ListItem, ListView

from fuzzless.patterns_modal import PRESETS_DIR

DEFAULT_PRESETS: dict[str, list[dict]] = {
    "10x3v3": [
        {
            "label": "R1",
            "pattern": "CTACACGACGCTCTTCCGATCT",
            "colour": "lawngreen",
            "max_edit_dist": 2,
            "revcomp": True,
        },
        {
            "label": "PolyT",
            "pattern": "TTTTTTTTT",
            "colour": "deepskyblue",
            "max_edit_dist": 1,
            "revcomp": True,
        },
    ],
    "10x3v2": [
        {
            "label": "R1",
            "pattern": "CTACACGACGCTCTTCCGATCT",
            "colour": "lawngreen",
            "max_edit_dist": 2,
            "revcomp": True,
        },
        {
            "label": "PolyT",
            "pattern": "TTTTTTTTT",
            "colour": "deepskyblue",
            "max_edit_dist": 1,
            "revcomp": True,
        },
    ],
    "10x5v2": [
        {
            "label": "R1",
            "pattern": "CTACACGACGCTCTTCCGATCT",
            "colour": "lawngreen",
            "max_edit_dist": 2,
            "revcomp": True,
        },
        {
            "label": "TSO",
            "pattern": "TTTCTTATATGGG",
            "colour": "coral",
            "max_edit_dist": 2,
            "revcomp": True,
        },
    ],
    "10x_atac": [
        {
            "label": "Read1",
            "pattern": "ACCGAGATCTACAC",
            "colour": "lawngreen",
            "max_edit_dist": 2,
            "revcomp": True,
        },
        {
            "label": "Tn5",
            "pattern": "CGCGTCTGTCGTCGGCAGCGTCAGATGTGTATAAGAGACAG",
            "colour": "coral",
            "max_edit_dist": 2,
            "revcomp": True,
        },
    ],
}


class PresetsWidget(Widget, can_focus=True):
    BINDINGS = [
        ("q", "quit", "quit"),
        Binding("space", "load_preset", "load preset"),
        ("tab", "next_tab", "next tab"),
    ]

    DEFAULT_CSS = """
    PresetsWidget {
        background: black;
    }

    ListView {
        background: black;
        height: 1fr;
        border-bottom: blank;
        max-width: 30;
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

    ListItem.action-item {
        background: darkslategray !important;
        border: blank;

        &.-highlight {
            background: darkslategray !important;
            text-style: none !important;
            border: heavy lightseagreen;
        }
    }

    Label {
        padding: 0 2;
    }

    .config-path {
        color: gray;
        padding: 0 2;
        height: auto;
    }
    """

    def __init__(self, next_tab):
        super().__init__()
        self.action_next_tab = next_tab
        self.presets_list = None
        self._preset_names: list[str] = []

    def compose(self) -> ComposeResult:
        self.presets_list = ListView()

        with Vertical():
            yield self.presets_list
            yield Label(str(PRESETS_DIR), classes="config-path")
        yield Footer(show_command_palette=False, compact=True)

    def on_resize(self) -> None:
        self.styles.height = self.app.size.height - 2

    def on_mount(self) -> None:
        self.refresh_presets()

    def on_screen_resume(self) -> None:
        self.refresh_presets()

    def _on_show(self, event) -> None:
        out = super()._on_show(event)
        self.presets_list.focus()
        return out

    def refresh_presets(self) -> None:
        if self.presets_list is None or not self.presets_list.is_mounted:
            return

        self.presets_list.clear()
        self._preset_names = []

        # Built-in presets
        for name in sorted(DEFAULT_PRESETS.keys()):
            self.presets_list.append(ListItem(Label(f"{name} (built-in)")))
            self._preset_names.append(f"builtin:{name}")

        # Disk presets
        if PRESETS_DIR.exists():
            for csv_file in sorted(PRESETS_DIR.glob("*.csv")):
                self.presets_list.append(ListItem(Label(csv_file.stem)))
                self._preset_names.append(f"disk:{csv_file.stem}")

        self.presets_list.append(
            ListItem(Label("Import from CSV"), classes="action-item")
        )
        self.presets_list.append(
            ListItem(Label("Export to CSV"), classes="action-item")
        )
        self.presets_list.append(
            ListItem(Label("Save as preset"), classes="action-item")
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        index = self.presets_list.index
        if index is None:
            return
        action_index = index - len(self._preset_names)
        if action_index < 0:
            self._load_preset_at(index)
        elif action_index == 0:
            self.app.push_screen("import_csv")
        elif action_index == 1:
            self.app.push_screen("export_csv")
        elif action_index == 2:
            self.app.push_screen("save_preset")

    def action_load_preset(self) -> None:
        index = self.presets_list.index
        if index is None or index >= len(self._preset_names):
            return
        self._load_preset_at(index)

    def _load_preset_at(self, index: int) -> None:
        key = self._preset_names[index]
        source, name = key.split(":", 1)

        try:
            if source == "builtin":
                patterns = list(DEFAULT_PRESETS[name])
            else:
                patterns = self._load_from_disk(PRESETS_DIR / f"{name}.csv")

            self.app.patterns.clear_patterns()
            for pattern in patterns:
                self.app.patterns.append_pattern(pattern)

            self.app.notify(
                f"Loaded preset '{name}'",
                severity="information",
                timeout=3.0,
            )
        except Exception as e:
            self.app.notify(f"Load failed: {str(e)}", severity="error", timeout=5.0)

    def _load_from_disk(self, filepath) -> list[dict]:
        required_fields = {"label", "pattern", "colour", "max_edit_dist", "revcomp"}
        patterns = []

        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            missing_fields = required_fields - set(reader.fieldnames)
            if missing_fields:
                raise Exception(f"Missing columns: {', '.join(missing_fields)}")

            for row in reader:
                row["revcomp"] = row["revcomp"].strip().lower()
                if row["revcomp"] not in ["true", "false"]:
                    raise Exception("revcomp must be true or false")
                patterns.append(
                    {
                        "label": row["label"],
                        "pattern": row["pattern"],
                        "colour": row["colour"],
                        "max_edit_dist": int(row["max_edit_dist"]),
                        "revcomp": row["revcomp"] == "true",
                    }
                )

        if not patterns:
            raise Exception("Preset file contains no patterns")

        return patterns
