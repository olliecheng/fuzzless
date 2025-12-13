from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Tabs, Static, TabbedContent, TabPane, ContentSwitcher
from textual.widgets._tabs import Underline
from textual.widgets._tabbed_content import ContentTab, ContentTabs
from itertools import zip_longest

from rich.segment import Segment

from textual.app import ComposeResult


class UpsideDownTabs(Tabs):
    def compose(self) -> ComposeResult:
        with Container(id="tabs-scroll"):
            with Vertical(id="tabs-list-bar"):
                yield Underline()
                with Horizontal(id="tabs-list"):
                    yield from self._tabs
                    # yield Static("    fuzzless v1", expand=True)


class BottomTabbedContent(TabbedContent, can_focus=False):
    DEFAULT_CSS = """
    BottomTabbedContent {
        height: auto;
        background: midnightblue;

        &> ContentTabs {
            dock: bottom;
        }
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.can_focus = False
        self.can_focus_children = False

    def on_mount(self):
        ct = self.query_one(ContentTabs)
        ct.can_focus = False
        ct.can_focus_children = False

    def _on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        print("activate")
        super()._on_tabs_tab_activated(event)
        print(self.active_pane)
        print(self.active_pane.size)
        self.active_pane.children[0].focus()

    def next_tab(self) -> None:
        """Switch to the next tab."""
        ct = self.query_one(ContentTabs)
        ct.action_next_tab()
        self.active_pane.children[0].focus()
