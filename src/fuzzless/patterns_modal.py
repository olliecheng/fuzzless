from textual.app import ComposeResult
from textual.widgets import Input, Button, Checkbox, Label
from textual.containers import Grid
from textual.events import Key
from textual.screen import ModalScreen


class ConfigurePatternModal(ModalScreen):
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    DEFAULT_CSS = """
    ConfigurePatternModal {
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
            Label("Pattern label", classes="inline-label"),
            self.label_input,
            Label("Pattern colour", classes="inline-label"),
            self.colour_input,
            Label("Max edit distance", classes="inline-label"),
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

        patterns_list = self.app.patterns.patterns_list
        if patterns_list.index is None:
            self.app.pop_screen()
            return

        selected_pattern = self.app.patterns.patterns[patterns_list.index]

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
        patterns_list = self.app.patterns.patterns_list
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


class ExportCSVModal(ModalScreen):
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    DEFAULT_CSS = """
    ExportCSVModal {
        align: center middle;
    }

    #dialog {
        padding: 0 1;
        width: 45;
        height: 13;
        border: thick lightseagreen 80%;
        background: darkslategray;

        grid-size: 2;
        grid-columns: 15 30;
        grid-rows: 3 4 3;

        content-align: center top;
    }

    Label {
        padding: 1 1;
        text-style: bold;
        column-span: 2;
    }

    Input {
        margin: 0;
        width: 41 !important;
        padding: 0;
        column-span: 2;
    }

    Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        self.filepath_input = Input(
            id="filepath", value="patterns.csv", placeholder="~/patterns.csv"
        )
        self.filepath_input.on_key = self.on_key

        yield Grid(
            Label("Export to CSV file"),
            self.filepath_input,
            Button("Export", variant="primary", id="export"),
            Button("Cancel", variant="error", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        if event.button.id == "export":
            self.export_to_csv()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.export_to_csv()

    def export_to_csv(self):
        patterns = self.app.patterns.patterns

        # Check if there are patterns to export
        if not patterns:
            self.app.pop_screen()
            self.app.notify("No patterns to export", severity="warning", timeout=3.0)
            return

        # Get and resolve file path
        filepath_str = self.filepath_input.value.strip()
        if not filepath_str:
            self.app.pop_screen()
            self.app.notify("Please enter a file path", severity="error", timeout=3.0)
            return

        try:
            from pathlib import Path
            import csv

            # Expand ~ and resolve relative paths
            filepath = Path(filepath_str).expanduser().resolve()

            # Write CSV with proper encoding
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "label",
                        "pattern",
                        "colour",
                        "max_edit_dist",
                        "revcomp",
                    ],
                )
                writer.writeheader()
                writer.writerows(patterns)

            # Success notification and close modal
            count = len(patterns)
            self.app.pop_screen()
            self.app.notify(
                f"Exported {count} pattern{'s' if count != 1 else ''} to {filepath}",
                severity="information",
                timeout=3.0,
            )
        except Exception as e:
            self.app.pop_screen()
            self.app.notify(f"Export failed: {str(e)}", severity="error", timeout=5.0)


class ImportCSVModal(ModalScreen):
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    DEFAULT_CSS = """
    ImportCSVModal {
        align: center middle;
    }

    #dialog {
        padding: 0 1;
        width: 45;
        height: 15;
        border: thick lightseagreen 80%;
        background: darkslategray;

        grid-size: 2;
        grid-columns: 15 30;
        grid-rows: 3 3 4 3;

        content-align: center top;
    }

    Label {
        padding: 1 1;
        text-style: bold;
        column-span: 2;
    }

    .warning-label {
        padding: 1 1;
        color: coral;
        text-style: bold;
        column-span: 2;
    }

    Input {
        margin: 0;
        width: 41 !important;
        padding: 0 1;
        column-span: 2;
    }

    Button {
        margin-left: 1;
    }
    """

    def compose(self) -> ComposeResult:
        self.filepath_input = Input(
            id="filepath", value="patterns.csv", placeholder="patterns.csv"
        )
        self.filepath_input.on_key = self.on_key

        yield Grid(
            Label("Import from CSV file"),
            self.filepath_input,
            Label(
                "WARNING: This will replace ALL existing patterns",
                classes="warning-label",
            ),
            Button("Import", variant="primary", id="import"),
            Button("Cancel", variant="error", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
        if event.button.id == "import":
            self.import_from_csv()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.import_from_csv()

    def import_from_csv(self):
        import csv

        self.app.pop_screen()

        try:
            # Validate filepath input
            filepath = self.filepath_input.value.strip()
            if not filepath:
                raise Exception("No file path provided")
            required_fields = {"label", "pattern", "colour", "max_edit_dist", "revcomp"}
            imported_patterns = 0

            with open(filepath, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                missing_fields = required_fields - set(reader.fieldnames)
                if missing_fields:
                    raise Exception("Missing column(s):", ", ".join(missing_fields))

                self.app.patterns.clear_patterns()

                # Parse rows
                for _row_num, row in enumerate(
                    reader, start=2
                ):  # start=2 to account for header
                    row["revcomp"] = row["revcomp"].strip().lower()

                    if row["revcomp"] not in ["true", "false"]:
                        raise Exception("revcomp must be true or false")

                    print("R", row)

                    pattern = {
                        "label": row["label"],
                        "pattern": row["pattern"],
                        "colour": row["colour"],
                        "max_edit_dist": int(row["max_edit_dist"]),
                        "revcomp": row["revcomp"] == "true",
                    }

                    self.app.patterns.append_pattern(pattern)
                    imported_patterns += 1

                # Check if we got any patterns
                if not imported_patterns:
                    raise Exception("CSV file contains no patterns")

            self.app.notify(
                f"Imported {imported_patterns} pattern{'s' if imported_patterns != 1 else ''}",
                severity="information",
                timeout=3.0,
            )
        except Exception as e:
            self.app.notify(f"Import failed: {str(e)}", severity="error", timeout=10.0)
