"""Lazy file reader with LRU caching for efficient handling of large files."""

from collections import OrderedDict
import itertools
from pathlib import Path
from typing import Optional, Literal

from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip

import math
from dataclasses import dataclass


@dataclass
class ReadLineLocation:
    read: Optional[int] = None
    line: Optional[int] = None
    type: Literal["data", "eof", "start"] = "data"


@dataclass
class Record:
    seq: str
    qual: list[int]
    id: str
    direction: Literal["fwd", "rev"]


FileEOF = Literal["eof"]


def soft_wrap_line(line: list[Segment], width: int) -> list[list[Segment]]:
    segments = []

    line_length = sum(x.cell_length for x in line)
    if line_length > width:
        cut_points = list(range(width, line_length - 1, width))
        cut_points.append(line_length)

        segments.extend(Segment.divide(line, cut_points))
    else:
        segments.append(line)

    return [
        Segment.adjust_line_length(s, width, Style(bgcolor="gray0")) for s in segments
    ]


class FileReader:
    """Reads lines from a file on-demand with LRU caching and read-ahead buffering."""

    def __init__(self, filepath: str, cache_size: int = 1000, readahead: int = 50):
        """Initialize the file reader.

        Args:
            filepath: Path to the file to read
            cache_size: Maximum number of lines to keep in cache
            readahead: Number of lines to read ahead when accessing a line
        """
        self.filepath = Path(filepath)
        # self._file = open(self.filepath, "r", encoding="utf-8", errors="replace")

        # self.line_buffer = self._file.read().splitlines()
        self._file = open(self.filepath, "r")
        self.read_buffer: list[Record] = []

        self.width = 80

        self.read_types = {}
        self.segment_cache = {}

        self.total_reads: Optional[int] = None

    def rerender(self, new_width: int):
        """Rerender the file with a new width."""
        self.width = new_width - 9
        self.segment_cache.clear()

    def render_read(self, read_id: int) -> list[list[Segment]]:
        """Render a specific read ID into segments."""

        # add to cache if not already present
        if read_id not in self.segment_cache:
            # self.fill_read_buf(read_id)
            rec = self.read_buffer[read_id]

            seq_id = soft_wrap_line(
                [
                    Segment(
                        "@" + rec.id, Style(color="grey62", italic=True, underline=True)
                    )
                ],
                self.width,
            )
            seq = soft_wrap_line([Segment(rec.seq)], self.width - 1)
            padded_seq = [[Segment(" ")] + line for line in seq]

            lines = [*seq_id, *padded_seq]
            # print(lines)
            self.segment_cache[read_id] = lines

        return self.segment_cache[read_id]

    def render_segment(self, loc: ReadLineLocation) -> list[Segment]:
        read = self.render_read(loc.read)
        return read[loc.line]

    def virtual_loc_change(
        self, loc: ReadLineLocation, relative_change: int
    ) -> ReadLineLocation:
        """Get the virtual line at a given cursor location with a relative change.

        Args:
            loc: Current cursor location
            relative_change: Change in line number (can be negative)

        Returns:
            A tuple of (new CursorLocation, list of Segments for the line)
        """
        self.fill_read_buf(loc.read)
        if self.beyond_eof(loc):
            return ReadLineLocation(type="eof")
        if loc.read < 0:
            return ReadLineLocation(type="start")

        lines_in_current_read = len(self.render_read(loc.read))

        if relative_change == 0:
            return loc

        new_line = loc.line + relative_change
        if new_line < 0:
            # can't get smaller than this!
            if loc.read == 0:
                return ReadLineLocation(type="start")

            new_read = self.render_read(loc.read - 1)
            new_loc = ReadLineLocation(loc.read - 1, len(new_read) - 1)

            return self.virtual_loc_change(new_loc, new_line + 1)
        if new_line >= lines_in_current_read:
            # can't get bigger than this!
            if self.beyond_eof(ReadLineLocation(loc.read + 1, 0)):
                return ReadLineLocation(type="eof")

            new_loc = ReadLineLocation(loc.read + 1, 0)
            return self.virtual_loc_change(new_loc, new_line - lines_in_current_read)

        return ReadLineLocation(loc.read, new_line)

    def beyond_eof(self, loc: ReadLineLocation) -> bool:
        return self.total_reads is not None and loc.read >= self.total_reads

    def fill_read_buf(self, to_read_id: int) -> None:
        """Get a line by its 0-indexed read ID.

        Returns cached line if available, otherwise reads from file.

        Args:
            line_num: 0-indexed line number

        Returns:
            The line content (without trailing newline)
        """

        if to_read_id < 0:
            raise IndexError("Read ID cannot be negative.")
        if to_read_id > 100000:
            raise IndexError("File size limit reached")
        if self.total_reads is not None and to_read_id >= self.total_reads:
            raise IndexError("No more reads left in file")

        for _ in range(to_read_id - len(self.read_buffer) + 1):
            id = self._file.readline().rstrip("\n")[1:]

            # empty string = EOF
            if not id:
                self.total_reads = len(self.read_buffer)
                return

            seq = self._file.readline().rstrip("\n")
            self._file.readline()
            qual = self._file.readline().rstrip("\n")

            rec = Record(seq, qual, id, "fwd")
            self.read_buffer.append(rec)

    def close(self) -> None:
        """Close the file handle."""
        if self._file and not self._file.closed:
            self._file.close()

    def __del__(self):
        """Ensure file is closed when object is garbage collected."""
        self.close()
