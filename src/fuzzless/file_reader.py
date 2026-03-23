"""Lazy file reader with LRU caching for efficient handling of large files."""

from pathlib import Path
from typing import Optional, Literal

from textual.color import Color as TextualColor
from rich.color import Color as RichColor
from rich.segment import Segment
from rich.style import Style
import time

from dataclasses import dataclass

import edlib
from functools import lru_cache

from fuzzless.io import FastxIo, Record


@dataclass
class ReadLineLocation:
    read: Optional[int] = None
    line: Optional[int] = None
    type: Literal["data", "eof", "start"] = "data"


FileEOF = Literal["eof"]
revcomp_lookup = str.maketrans("ACGTacgt", "TGCAtgca")

# fmt: off
_IUPAC_EQUALITIES = [
    ("R", "A"), ("R", "G"),
    ("K", "G"), ("K", "T"),
    ("S", "G"), ("S", "C"),
    ("Y", "C"), ("Y", "T"),
    ("M", "A"), ("M", "C"),
    ("W", "A"), ("W", "T"),
    ("B", "C"), ("B", "G"), ("B", "T"),
    ("H", "A"), ("H", "C"), ("H", "T"),
    ("?", "A"), ("?", "C"), ("?", "G"), ("?", "T"),
    ("D", "A"), ("D", "G"), ("D", "T"),
    ("V", "A"), ("V", "C"), ("V", "G"),
]
# fmt: on


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

    def __init__(self, app, filepath: str, cache_size: int = 1000, readahead: int = 50):
        """Initialize the file reader.

        Args:
            filepath: Path to the file to read
            cache_size: Maximum number of lines to keep in cache
            readahead: Number of lines to read ahead when accessing a line
        """
        self.app = app
        self.filepath = Path(filepath)

        self._io = FastxIo(str(self.filepath))

        self.width = 80

        self.read_types = {}
        self.segment_cache = {}

        self.pattern_time = time.time()

        self.show_info = False

        self._manual_revcomp: set[int] = set()

    @property
    def total_reads(self) -> Optional[int]:
        return self._io.total_reads

    def rerender(self, new_width: int):
        """Rerender the file with a new width."""
        self.width = new_width - 9
        self.clear_cache()

    def render_read(self, read_id: int) -> list[list[Segment]]:
        """Render a specific read ID into segments."""

        # add to cache if not already present
        if read_id not in self.segment_cache:
            # do we need to check if the patterns have changed?
            rec = self._io.get_read_from_idx(read_id)

            # Re-apply manual revcomp if record was evicted and reloaded from disk
            if read_id in self._manual_revcomp and rec.direction == "fwd":
                self.revcomp_read(read_id, _manual=False)

            if rec.last_checked_direction != self.pattern_time:
                rec.last_checked_direction = self.pattern_time
                fw, rv = self.count_matches(rec)

                # reverse complement is a better match, take the revcomp
                if fw is not None and rv is not None:
                    if len(rv) > len(fw) or (len(rv) == len(fw) and sum(rv) < sum(fw)):
                        self.revcomp_read(read_id)

            seq_id = soft_wrap_line(
                [Segment(("@" + rec.id).expandtabs(8), Style(color="grey62", underline=True))],
                self.width,
            )

            fwd_rev_segment = Segment(
                " " + ("→" if rec.direction == "fwd" else "←") + " ",
                Style(color="green" if rec.direction == "fwd" else "deep_pink3"),
            )

            padded_seqid = [[fwd_rev_segment] + line for line in seq_id]

            highlighted_read = self.highlight_read(rec.seq)

            seq_read = soft_wrap_line(highlighted_read, self.width - 1)
            padded_seq = [[fwd_rev_segment, Segment(" ")] + line for line in seq_read]

            lines = [*padded_seqid, *padded_seq]
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
        """Ensure the read at to_read_id is indexable.

        Args:
            to_read_id: 0-indexed read ID to scan up to
        """
        if to_read_id < 0:
            raise IndexError("Read ID cannot be negative.")
        if self.total_reads is not None and to_read_id >= self.total_reads:
            raise IndexError("No more reads left in file")
        self._io.scan_to(to_read_id)

    def revcomp_read(self, read_id: int, _manual: bool = True) -> None:
        rec = self._io.get_read_from_idx(read_id)
        rec.seq = revcomp(rec.seq)
        rec.qual = rec.qual[::-1]
        rec.direction = "rev" if rec.direction == "fwd" else "fwd"
        if _manual:
            if read_id in self._manual_revcomp:
                self._manual_revcomp.discard(read_id)
            else:
                self._manual_revcomp.add(read_id)
        self.segment_cache.pop(read_id, None)

    def close(self) -> None:
        """Close the file handle."""
        self._io.close()

    @lru_cache(maxsize=50000)
    def search(self, pattern: tuple[str, int], text: str) -> Optional[dict]:
        pattern_str, max_edit_dist = pattern

        result = edlib.align(
            pattern_str.upper(),
            text.upper(),
            mode="HW",
            task="locations",
            k=max_edit_dist,
            additionalEqualities=_IUPAC_EQUALITIES,
        )

        if result["editDistance"] == -1:
            return None

        start, end = result["locations"][0]
        return {
            "start": start,
            "end": end + 1,  # edlib end is inclusive; convert to exclusive
            "edit_dist": result["editDistance"],
        }

    def highlight_read(self, read: str) -> list[Segment]:
        patterns = self.app.patterns.patterns

        length = len(read)

        if self.show_info:
            base_style = Style(color="bright_black", bgcolor="black")
        else:
            base_style = Style(color="bright_white", bgcolor="black")

        line = [Segment(read, base_style)]
        if not patterns:
            return line

        info_labels: list[tuple[int, Segment]] = []

        for pattern in reversed(patterns):
            pattern_seq = pattern["pattern"]
            pattern_label = pattern["label"]

            to_search = (
                [(True, pattern_seq)] + [(False, revcomp(pattern_seq))]
                if pattern["revcomp"]
                else [(True, pattern_seq)]
            )

            for fwd, pattern_seq in to_search:
                match = self.search((pattern_seq, pattern["max_edit_dist"]), read)
                if match is not None:
                    start = match["start"]
                    end = match["end"]
                    edit_dist = match["edit_dist"]

                    if self.show_info:
                        info_label_segment = Segment(
                            ("→" if fwd else "←") + f"{pattern_label}:{edit_dist}:",
                            Style(color="black", bgcolor="bright_white"),
                        )
                        info_labels.append((start, info_label_segment))

                    [a, h, b] = Segment.divide(line, [start, end, length])

                    colour_textual = TextualColor.parse(pattern["colour"])
                    colour_rich = RichColor.from_rgb(
                        colour_textual.r, colour_textual.g, colour_textual.b
                    )

                    h_new = Segment.apply_style(
                        h,
                        post_style=Style(
                            color=colour_rich,
                            reverse=fwd,
                        ),
                    )

                    line = [*a, *h_new, *b]

        # add information labels - start with earliest label
        offset = 0
        info_labels.sort(key=lambda x: x[0])
        for pos, label in info_labels:
            [a, b] = Segment.divide(line, [pos + offset, Segment.get_line_length(line)])

            line = [*a, label, *b]
            offset += label.cell_length

        return line

    def count_matches(self, rec: Record) -> Optional[tuple[list, list]]:
        patterns = self.app.patterns.patterns
        if not patterns:
            return None

        # always start with the forward sequence
        read = rec.seq if rec.direction == "fwd" else revcomp(rec.seq)

        fwd_edit_dists = []
        rev_edit_dists = []

        for pattern in patterns:
            pattern_seq = pattern["pattern"]
            max_dist = pattern["max_edit_dist"]

            match_fwd = self.search((pattern_seq, max_dist), read)
            match_rev = self.search((revcomp(pattern_seq), max_dist), read)

            if match_fwd is not None:
                fwd_edit_dists.append(match_fwd["edit_dist"])

            if match_rev is not None:
                rev_edit_dists.append(match_rev["edit_dist"])

        return fwd_edit_dists, rev_edit_dists

    def __del__(self):
        """Ensure file is closed when object is garbage collected."""
        self.close()

    def patterns_changed(self):
        self.pattern_time = time.time()
        self.clear_cache()

    def clear_cache(self):
        self.segment_cache.clear()


def revcomp(seq: str) -> str:
    return seq.translate(revcomp_lookup)[::-1]
