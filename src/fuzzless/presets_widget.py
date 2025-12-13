from textual.app import RenderResult
from textual.widget import Widget


class PresetsWidget(Widget, can_focus=True):
    """Display a greeting."""

    BINDINGS = [("q", "quit", "quit"), ("tab", "next_tab", "next tab")]

    def __init__(self, next_tab):
        super().__init__()
        self.action_next_tab = next_tab

    def render(self) -> RenderResult:
        return "Hello, [b]World[/b]!"
