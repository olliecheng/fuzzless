"""Pager widget using Textual's Line API for efficient rendering."""

from dataclasses import dataclass
import itertools
from rich.segment import Segment
from rich.style import Style
from textual.geometry import Size, Offset, Region
from textual.scroll_view import ScrollView
from textual.widget import Widget
from textual.reactive import var
from textual.strip import Strip

from fuzzless.file_reader import FileReader, ReadLineLocation

import collections


class PagerWidget(Widget):
    """A pager widget that displays file contents with line selection and horizontal scrolling."""

    COMPONENT_CLASSES = {
        "scroll-line-active",
        "scroll-line-inactive",
        "scroll-number-active",
        "scroll-number-inactive",
    }

    DEFAULT_CSS = """
    PagerWidget > .scroll-line-active {
        background: black;
        color: white;
    }

    PagerWidget > .scroll-line-inactive {
        background: black;
        color: white;
    }

    PagerWidget > .scroll-number-active {
        background: lightblue;
        color: black;
        text-style: bold;
    }

    PagerWidget > .scroll-number-inactive {
        background: black;
        color: white;
    }
    """

    viewport_loc = var(ReadLineLocation(0, 0))
    cursor_loc = var(0)

    def __init__(self, file_reader: FileReader):
        """Initialize the pager widget.

        Args:
            file_reader: FileReader instance for reading lines
        """
        super().__init__()
        self.file_reader = file_reader

    def on_resize(self, event):
        # move cursor if window height has changed
        if self.cursor_loc >= self.size.height:
            self.cursor_loc = self.size.height - 1

        self.file_reader.rerender(self.size.width)
        self.refresh()

    def watch_cursor_coord(
        self, prev_coord: ReadLineLocation, coord: ReadLineLocation
    ) -> None:
        # self.refresh(Region(0, coord.y, self.size.width, 1))
        # self.refresh(Region(0, max(0, prev_coord.y - 1), self.size.width, 3))
        # old_y = prev_coord.pos
        # new_y = coord.pos

        self.refresh()

    def render_line(self, y: int) -> Strip:
        "Render a single line at position y"

        line_loc = self.file_reader.virtual_loc_change(self.viewport_loc, y)
        if line_loc.type == "start":
            return Strip.blank(self.size.width)
        if line_loc.type == "eof":
            return Strip(
                [Segment("       ~ EOF ~", Style(color="red3", italic=True))]
            ).adjust_cell_length(self.size.width)

        content_segments = self.file_reader.render_segment(line_loc)

        cursor_pos = self.file_reader.virtual_loc_change(
            self.viewport_loc, self.cursor_loc
        )

        is_active = (
            line_loc.read == cursor_pos.read and line_loc.line == cursor_pos.line
        )

        if is_active:
            line_style = Style(color="grey0", bold="true", bgcolor="deep_sky_blue3")
        else:
            line_style = Style(
                color="bright_white" if line_loc.read % 2 else "pale_turquoise1",
                bold=line_loc.read % 2,
                italic=not (line_loc.read % 2),
                bgcolor="grey0",
            )

        line_number_segment = Segment(f"{line_loc.read:>6}", line_style)

        return Strip([line_number_segment, *content_segments])

    def scroll_by(self, lines: int, move_cursor=True) -> None:
        """Move selection to the previous line."""

        is_at_top = self.cursor_loc == 0 and lines < 0
        is_at_bottom = self.cursor_loc >= self.size.height - 1 and lines > 0

        if is_at_top or is_at_bottom or not move_cursor:
            new_loc = self.file_reader.virtual_loc_change(self.viewport_loc, lines)
            if new_loc.type == "data":
                self.viewport_loc = new_loc

            # pgdn/pgup at edge of viewport: move cursor
            # in this case, we should move the cursor as far as we can
            elif not move_cursor:
                if lines < 0:
                    self.cursor_loc = 0
        else:
            # move cursor_loc, don't move viewport
            new_loc = self.file_reader.virtual_loc_change(
                self.viewport_loc, self.cursor_loc + lines
            )
            if not new_loc.type == "eof":
                self.cursor_loc += lines

        self.refresh()

    def refresh_lines(self, start: int, end: int) -> None:
        """Refresh a range of lines.

        Args:
            start: Start line number (inclusive)
            end: End line number (exclusive)
        """
        # Request a full refresh to update the display
        # This could be optimized in the future for better performance
        self.refresh()

    def revcomp(self) -> None:
        """Reverse complement the selected read."""
        cursor_pos = self.file_reader.virtual_loc_change(
            self.viewport_loc, self.cursor_loc
        )
        if cursor_pos.type == "data":
            self.file_reader.revcomp_read(cursor_pos.read)
            self.refresh()
