"""Fuzzless pager application using Textual's Line API."""

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import (
    Footer,
    Tab,
    Tabs,
    ContentSwitcher,
    TabbedContent,
    TabPane,
    Static,
)
from textual.containers import Vertical, VerticalGroup, HorizontalGroup

from fuzzless.file_reader import FileReader
from fuzzless.pager_widget import PagerWidget
from fuzzless.patterns_widget import PatternsWidget
from fuzzless.patterns_modal import (
    ConfigurePatternModal,
    ExportCSVModal,
    ImportCSVModal,
)
from fuzzless.pager_modal import GoToReadModal
from fuzzless.presets_widget import PresetsWidget
from fuzzless.vertical_tabs import UpsideDownTabs, BottomTabbedContent


class FuzzlessApp(App):
    """A pager application for viewing large text files efficiently."""

    CSS = """
    FuzzlessApp {
        background: black; 
    }
    PagerWidget {
        width: 100%;
        height: 1fr;
    }

    Footer {
        background: $boost;
    }

    #tabs-list {
        dock: bottom;
    }

    BottomTabbedContent {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "quit  │ ", priority=True),
        Binding("ctrl+c", "quit", show=False),
    ]

    SCREENS = {
        "configure": ConfigurePatternModal,
        "export_csv": ExportCSVModal,
        "import_csv": ImportCSVModal,
        "go_to_read": GoToReadModal,
    }

    def __init__(self, filepath: str):
        """Initialize the app with a file path.

        Args:
            filepath: Path to the file to display
        """
        super().__init__()
        self.filepath = filepath
        self.file_reader = FileReader(self, filepath)
        self.pager: PagerWidget | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.content_pane = BottomTabbedContent()

        next_tab_fn = self.content_pane.next_tab
        self.pager = PagerWidget(self.file_reader, next_tab_fn)
        self.patterns = PatternsWidget(next_tab_fn)
        self.presets = PresetsWidget(next_tab_fn)

        with self.content_pane:
            with TabPane("pager"):
                yield self.pager
            with TabPane("patterns"):
                yield self.patterns
            with TabPane("presets"):
                yield self.presets

        # yield UpsideDownTabs(
        #     Tab("    reads    ", id="pager"),
        #     Tab(" patterns ", id="patterns"),
        #     Tab(" presets ", id="presets"),
        # )

    def on_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab activation events to switch content.

        Args:
            event: The tab activated event
        """
        self.query_one(ContentSwitcher).switch_to(event.tab.id)

    def on_mount(self) -> None:
        self.screen.bindings_updated_signal.subscribe(self, self.bindings_changed)
        print("mount")

        patterns = [
            {
                "label": "R1",
                "max_edit_dist": 3,
                "pattern": "CTACACGACGCTCTTCCGATCT",
                "colour": "lawngreen",
                "revcomp": True,
            },
            {
                "label": "TSO",
                "max_edit_dist": 3,
                "pattern": "TGGTATCAACGCAGAGTACATGGG",
                "colour": "coral",
                "revcomp": True,
            },
            {
                "label": "PolyT",
                "max_edit_dist": 1,
                "pattern": "TTTTTTTTTTTT",
                "colour": "deepskyblue",
                "revcomp": True,
            },
        ]

        for pattern in patterns:
            self.patterns.append_pattern(pattern)

    def on_unmount(self) -> None:
        """Clean up resources when app is closed."""
        self.file_reader.close()

    def on_bottom_tabbed_content_focus(self, event: any) -> None:
        print("hello")

    def bindings_changed(self, _screen: any) -> None:
        # print("app")
        # self.query_one(BottomTabbedContent).active_pane.children[0].focus()
        pass


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
