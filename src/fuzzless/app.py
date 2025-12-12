"""Fuzzless pager application using Textual's Line API."""

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Tab, Tabs

from fuzzless.file_reader import FileReader
from fuzzless.pager_widget import PagerWidget


class FuzzlessApp(App):
    """A pager application for viewing large text files efficiently."""

    CSS = """
    PagerWidget {
        width: 100%;
        height: 1fr;
    }

    Footer {
        background: $boost;
    }
    """

    BINDINGS = [
        ("q", "quit", "quit"),
        ("up", "cursor_up", ""),
        ("down", "cursor_down", ""),
        ("ctrl+d", "pg_down", "↓↓"),
        ("ctrl+u", "pg_up", "↑↑"),
        Binding(
            "r", "revcomp", "→revcomp←", tooltip="reverse complement selected read"
        ),
        Binding("space", "toggle_fold", "fold"),
        Binding("ctrl+space", "toggle_all_folds", "fold all", show=False),
        Binding("tab", "next_tab", "next tab", show=True),
    ]

    def __init__(self, filepath: str):
        """Initialize the app with a file path.

        Args:
            filepath: Path to the file to display
        """
        super().__init__()
        self.filepath = filepath
        self.file_reader = FileReader(filepath)
        self.pager: PagerWidget | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.pager = PagerWidget(self.file_reader)
        yield self.pager
        yield Footer(show_command_palette=False, compact=True)
        yield Tabs(
            Tab("    reads    ", id="reads"),
            Tab(" patterns ", id="patterns"),
            Tab(" presets ", id="presets"),
        )

    def action_cursor_up(self) -> None:
        """Move selection up."""
        if self.pager:
            self.pager.scroll_by(-1)

    def action_cursor_down(self) -> None:
        """Move selection down."""
        if self.pager:
            self.pager.scroll_by(1)

    def action_pg_down(self) -> None:
        if self.pager:
            self.pager.scroll_by(self.pager.size.height // 2, move_cursor=False)

    def action_pg_up(self) -> None:
        if self.pager:
            self.pager.scroll_by(-(self.pager.size.height // 2), move_cursor=False)

    def on_unmount(self) -> None:
        """Clean up resources when app is closed."""
        self.file_reader.close()


def main():
    """Entry point for the application."""
    if len(sys.argv) < 2:
        print("Usage: fuzzless <filepath>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]

    # Validate file exists
    if not Path(filepath).exists():
        print(f"Error: File '{filepath}' not found", file=sys.stderr)
        sys.exit(1)

    if not Path(filepath).is_file():
        print(f"Error: '{filepath}' is not a file", file=sys.stderr)
        sys.exit(1)

    app = FuzzlessApp(filepath)
    app.run()


if __name__ == "__main__":
    main()
