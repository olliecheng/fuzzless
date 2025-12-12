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
                [Segment("         ~ EOF ~", Style(color="red3", italic=True))]
            ).adjust_cell_length(self.size.width)

        content_segments = self.file_reader.render_segment(line_loc)
        if content_segments is None:
            return Strip.blank(self.size.width)

        cursor_pos = self.file_reader.virtual_loc_change(
            self.viewport_loc, self.cursor_loc
        )

        is_active = (
            line_loc.read == cursor_pos.read and line_loc.line == cursor_pos.line
        )

        direction = "fwd"

        fwd_rev_segment = Segment(
            " " + ("→" if direction == "fwd" else "←") + " ",
            Style(color="green" if direction == "fwd" else "red"),
        )

        if is_active:
            line_style = Style(color="grey0", bold="true", bgcolor="deep_sky_blue3")
        else:
            line_style = Style(
                color="bright_white" if line_loc.read % 2 else "pale_turquoise1",
                bold=line_loc.read % 2,
                italic=not (line_loc.read % 2),
                # bgcolor="grey0" if line_loc.read % 2 else "grey11",
                bgcolor="grey0",
            )

        line_number_segment = Segment(f"{line_loc.read:>6}", line_style)

        return Strip([line_number_segment, fwd_rev_segment, *content_segments])

        if self._total_lines is None:
            self._total_lines = self.file_reader.get_total_lines()

        total_lines = self._total_lines

        if y >= total_lines:
            return Strip.blank(self.size.width)

        # Check if this is the selected line
        is_selected = y == self.selected_line

        # Get the line content from file reader
        line_content = self.file_reader.fill_read_buf(y)

        # Determine styles
        line_num_style = (
            Style(color="blue", bold=True) if is_selected else Style(color="gray60")
        )
        content_style = Style(bgcolor="blue", color="white") if is_selected else Style()

        # Format line number with padding
        line_num_str = f"{y + 1:>{self.line_number_width}}"
        line_num_segment = Segment(line_num_str, line_num_style)
        separator_segment = Segment(" ", Style())

        # Get horizontal offset for this line (only if selected)
        h_offset = self.horizontal_offsets.get(y, 0) if is_selected else 0

        # Slice the content based on horizontal offset
        visible_content = line_content[h_offset:]

        # Build the content segment - let Strip handle width management
        content_segment = Segment(visible_content, content_style)

        # Build the strip with all segments
        segments = [line_num_segment, separator_segment, content_segment]
        return Strip(segments)

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
