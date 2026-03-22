"""Memory-mapped FASTQ I/O with lazy sparse offset indexing and LRU record cache."""

import mmap
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

_MARKER_INTERVAL = 500  # Store one byte-offset marker per this many reads


@dataclass
class Record:
    seq: str
    qual: str
    id: str
    direction: Literal["fwd", "rev"]
    last_checked_direction: int
    folded: bool = False


class FastxIo:
    """Random-access FASTQ reader backed by mmap with a bounded LRU record cache.

    Builds a sparse byte-offset index lazily: one marker is stored per
    _MARKER_INTERVAL reads. To access an arbitrary read, the nearest lower-bound
    marker is located and the file is scanned forward from there.
    """

    def __init__(self, filepath: str):
        self._f = open(Path(filepath), "rb")
        self._mmap = mmap.mmap(self._f.fileno(), 0, access=mmap.ACCESS_READ)
        self._offsets: list[int] = []
        self._total_reads: Optional[int] = None

    @property
    def total_reads(self) -> Optional[int]:
        return self._total_reads

    def scan_to(self, read_idx: int) -> bool:
        """Ensure the byte offset for read_idx is known.

        Returns True if read_idx is within the file, False if EOF was reached first.
        """
        return self._scan_to_internal(read_idx)

    def _scan_to_internal(self, read_idx: int) -> bool:
        marker_needed = read_idx // _MARKER_INTERVAL

        while len(self._offsets) <= marker_needed:
            if self._total_reads is not None:
                return read_idx < self._total_reads
            if len(self._offsets) == 0:
                if len(self._mmap) == 0:
                    self._total_reads = 0
                    return False
                self._offsets.append(0)
                continue
            # Scan _MARKER_INTERVAL reads forward from the last marker
            last_marker_i = len(self._offsets) - 1
            pos = self._offsets[last_marker_i]
            base = last_marker_i * _MARKER_INTERVAL
            for i in range(_MARKER_INTERVAL):
                for _ in range(4):
                    nl = self._mmap.find(b"\n", pos)
                    if nl == -1:
                        self._total_reads = base + i
                        return read_idx < self._total_reads
                    pos = nl + 1
            if pos >= len(self._mmap):
                self._total_reads = base + _MARKER_INTERVAL
                return read_idx < self._total_reads
            self._offsets.append(pos)

        return True

    def _parse_record(self, read_idx: int) -> Record:
        marker_i = min(read_idx // _MARKER_INTERVAL, len(self._offsets) - 1)
        pos = self._offsets[marker_i]
        reads_to_skip = read_idx - marker_i * _MARKER_INTERVAL
        for _ in range(reads_to_skip):
            for _ in range(4):
                nl = self._mmap.find(b"\n", pos)
                pos = nl + 1
        self._mmap.seek(pos)
        header = self._mmap.readline().rstrip(b"\n").decode()[1:]  # strip leading @
        seq = self._mmap.readline().rstrip(b"\n").decode()
        self._mmap.readline()  # skip + separator
        qual = self._mmap.readline().rstrip(b"\n").decode()
        return Record(seq, qual, header, "fwd", last_checked_direction=0)

    @lru_cache(maxsize=500)
    def get_read_from_idx(self, read_idx: int) -> Record:
        """Return the Record at read_idx, using the cache when possible."""
        if read_idx < 0:
            raise IndexError("Read index cannot be negative.")
        if not self._scan_to_internal(read_idx):
            raise IndexError(f"Read index {read_idx} is beyond end of file.")
        return self._parse_record(read_idx)

    def close(self) -> None:
        if not self._mmap.closed:
            self._mmap.close()
        if not self._f.closed:
            self._f.close()

    def __del__(self) -> None:
        self.close()
