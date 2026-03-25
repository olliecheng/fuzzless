import csv

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.events import Key
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView

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


class PresetsWidget(Widget):
    BINDINGS = [
        ("q", "quit", "quit"),
        Binding("space", "load_preset", "load preset"),
    ]

    DEFAULT_CSS = """
    PresetsWidget {
        background: black !important;
    }

    PresetsWidget ListView {
        background: black;
        height: 1fr;
        border: round royalblue;
        padding: 0 1;
        margin-bottom: 1;
    }

    PresetsWidget ListView:focus {
        border: heavy white;
    }

    PresetsWidget ListItem {
        background: black !important;
        border: blank;

        &.-highlight {
            background: black !important;
            text-style: none !important;
            border: blank;
        }
    }

    PresetsWidget ListView:focus ListItem.-highlight {
        border: heavy lightseagreen;
    }

    PresetsWidget Label {
        padding: 0 2;
    }

    PresetsWidget .column-header {
        text-style: bold;
        width: 1fr;
        padding: 0 1;
    }

    PresetsWidget .preset-actions {
        height: auto;
        background: black;
    }

    PresetsWidget Button {
        # height: 1;
        # min-width: 1;
        width: 1fr;
        margin: 0 1 1 1;
        # border: none;
        # padding: 0 1;
    }
    
    PresetsWidget Button:focus {
        outline: hkey white;
    }
    """

    def __init__(self):
        super().__init__()
        self.presets_list = None
        self._preset_names: list[str] = []

    def compose(self) -> ComposeResult:
        self.presets_list = ListView()

        with Vertical():
            yield Label("Presets", classes="column-header")
            yield self.presets_list
            with Vertical(classes="preset-actions"):
                with Horizontal(classes="preset-actions"):
                    yield Button("Import CSV", variant="warning", id="btn-import")
                    yield Button("Export CSV", variant="success", id="btn-export")
                yield Button("Save as preset", variant="primary", id="btn-save")

    def on_mount(self) -> None:
        self.refresh_presets()

    def on_screen_resume(self) -> None:
        self.refresh_presets()

    def _on_show(self, event) -> None:
        out = super()._on_show(event)
        self.presets_list.focus()
        return out

    def on_key(self, event: Key) -> None:
        if event.key not in ("tab", "shift+tab"):
            return
        focused = self.app.focused
        chain = [
            self.presets_list,
            self.query_one("#btn-import"),
            self.query_one("#btn-export"),
            self.query_one("#btn-save"),
        ]
        if focused not in chain:
            return
        event.stop()
        idx = chain.index(focused)
        if event.key == "tab":
            if idx < len(chain) - 1:
                chain[idx + 1].focus()
            else:
                self.app.patterns.patterns_list.focus()
        else:
            if idx > 0:
                chain[idx - 1].focus()
            else:
                self.app.patterns.patterns_list.focus()

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

        if self._preset_names:
            self.presets_list.index = 0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-import":
            self.app.push_screen("import_csv")
        elif event.button.id == "btn-export":
            self.app.push_screen("export_csv")
        elif event.button.id == "btn-save":
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
