from textual.app import ComposeResult
from textual.widgets import Input, Button, Checkbox, Label
from textual.containers import Grid, Horizontal, Vertical
from textual.events import Key
from textual.screen import ModalScreen

from fuzzless.file_reader import FileReader, ReadLineLocation


class GoToReadModal(ModalScreen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Pop screen"),
    ]

    DEFAULT_CSS = """
    GoToReadModal {
        align: left bottom;
    }

    #dialog {
        padding: 0 2;
        width: 59;
        height: 5;
        margin: 1 5;
        border: thick lightseagreen 80%;
        background: darkslategray;

        align: left middle;
        content-align: left middle;
    }

    #read_number {
        width: 20;
    }

    .inline-label {
        height: 3;
        padding: 1 0;
    }

    Button {
        width: 10 !important;
        min-width: 10 !important;
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        self.line_input = Input(id="read_number", type="number")

        yield Horizontal(
            Label("Read number:", classes="inline-label"),
            self.line_input,
            Button("Go", variant="primary", id="go"),
            Button("Cancel", variant="error", id="cancel"),
            id="dialog",
        )

    def on_screen_resume(self) -> None:
        self.line_input.value = "1"
        self.line_input.select_all()
        self.line_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "go":
            self.go_to_provided_read()
        else:
            self.app.pop_screen()

    def go_to_provided_read(self) -> None:
        read_number_str = self.line_input.value
        if not read_number_str:
            return

        read_number = int(read_number_str) - 1  # convert to 0-indexed

        file_reader: FileReader = self.app.file_reader
        file_reader.fill_read_buf(to_read_id=read_number)

        # was EOF reached?
        if file_reader.total_reads is not None:
            if read_number >= file_reader.total_reads:
                self.app.notify(
                    f"Reached end of file: only {file_reader.total_reads} reads available.",
                    severity="error",
                    timeout=5.0,
                )
                return

        self.app.pager.viewport_loc = ReadLineLocation(read_number, 0)
        self.app.pager.cursor_loc = 0
        self.app.pager.refresh()

        self.app.pop_screen()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.go_to_provided_read()
