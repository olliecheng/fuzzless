# CLAUDE.md - Fuzzless Codebase Guide

## Project Overview

**Fuzzless** is a terminal UI (TUI) application for bioinformatics professionals to interactively search and visualize DNA sequence patterns in FASTQ files. It supports fuzzy matching (edit distance tolerance) and automatic reverse complement detection.

- **Language:** Python 3.13+
- **UI Framework:** [Textual](https://textual.textualize.io/)
- **Fuzzy Matching:** [`regex`](https://pypi.org/project/regex/) library with edit distance syntax
- **Entry point:** `fuzzless <path_to_fastq_file>`

---

## Directory Structure

```
src/fuzzless/
├── app.py              # FuzzlessApp: main Textual App, layout, modal coordination
├── file_reader.py      # FileReader: FASTQ parsing, fuzzy search, rendering, caching
├── pager_widget.py     # PagerWidget: scrollable display of reads with navigation
├── pager_modal.py      # GoToReadModal: jump to a specific read by number
├── patterns_widget.py  # PatternsWidget: CRUD for search patterns
├── patterns_modal.py   # ConfigurePatternModal, ExportCSVModal, ImportCSVModal
├── presets_widget.py   # PresetsWidget: stub, not yet implemented
├── vertical_tabs.py    # BottomTabbedContent: custom tabs-at-bottom layout
└── __init__.py         # Package exports
```

---

## Architecture & Data Flow

### High-Level Flow

```
User input (keyboard)
       │
       ▼
PagerWidget / PatternsWidget   ←→   Modal screens (GoToRead, ConfigurePattern, CSV)
       │
       ▼
FileReader
  ├── fill_read_buf(read_id)    # lazy-load FASTQ records into read_buffer
  ├── render_read(read_id)      # render Record → list[list[Segment]] (cached)
  │     ├── count_matches()     # auto-select fwd vs. reverse complement
  │     ├── highlight_read()    # apply fuzzy pattern colors to sequence
  │     └── soft_wrap_line()    # break long sequences to terminal width
  └── segment_cache             # dict[read_id → segments], cleared on pattern change
```

### FASTQ Parsing

FASTQ files have 4 lines per read:
1. `@<id>` — read identifier
2. `<sequence>` — DNA sequence
3. `+` — separator (ignored)
4. `<quality>` — Phred quality string

`fill_read_buf(to_read_id)` reads from the file handle sequentially, appending `Record` objects to `read_buffer` until the requested read ID is buffered. On EOF, `total_reads` is set and no more reads are attempted.

### Pattern Matching

Patterns are stored as dicts in `PatternsWidget.patterns`:

```python
{
    "label": str,          # e.g. "R1"
    "pattern": str,        # DNA sequence, e.g. "CTACACGACGCTCTTCCGATCT"
    "colour": str,         # named color, e.g. "lawngreen"
    "max_edit_dist": int,  # fuzzy tolerance (0 = exact)
    "revcomp": bool,       # also search reverse complement of pattern
}
```

`FileReader.search(pattern_tuple, text)` compiles and caches the regex:
- Exact: `regex.compile(pattern_seq, IGNORECASE)`
- Fuzzy: `regex.compile("(?:PATTERN){e<=N}", BESTMATCH | IGNORECASE)`

Returns `{"start", "end", "edit_dist"}` or `None`.

`highlight_read(seq)` iterates patterns in reverse order, splits the sequence into `Segment` objects at match boundaries, and applies color styling. If `show_info` is enabled, it also prepends directional labels (e.g. `→R1:2:`) before each match.

### Automatic Orientation (fwd / rev)

Each `Record` has a `direction` (`"fwd"` or `"rev"`) and a `last_checked_direction` timestamp. When `pattern_time` changes (patterns updated), the next `render_read()` call triggers `count_matches()`:

- Counts how many patterns match forward vs. reverse complement
- Selects the orientation with **more matches**, or if equal, **fewer total edit distance mismatches**
- If reverse is better, `revcomp_read(read_id)` mutates the record in place and clears its segment cache entry

### Virtual Line Navigation

Reads are soft-wrapped to terminal width, so a single read may occupy multiple display lines. `ReadLineLocation(read, line)` tracks position as `(read_id, line_within_read)`.

`virtual_loc_change(loc, delta)` recursively navigates across read boundaries:
- Moving up past line 0 of a read → goes to the last line of the previous read
- Moving down past the last line → goes to line 0 of the next read
- Returns `ReadLineLocation(type="eof")` or `type="start"` at boundaries

---

## Key Keyboard Bindings

| Key | Widget | Action |
|-----|--------|--------|
| `q` / `Ctrl+C` | Global | Quit |
| `↑` / `k` | Pager | Move cursor up |
| `↓` / `j` | Pager | Move cursor down |
| `Ctrl+U` | Pager | Page up |
| `Ctrl+D` | Pager | Page down |
| `r` | Pager | Toggle reverse complement for current read |
| `g` | Pager | Go to specific read number |
| `i` | Pager | Toggle info mode (show pattern labels on matches) |
| `Space` | Patterns | Edit selected pattern |
| `Ctrl+A` | Patterns | Add new pattern |
| `Ctrl+D` | Patterns | Delete selected pattern |
| `Ctrl+E` | Patterns | Export patterns to CSV |
| `Ctrl+I` | Patterns | Import patterns from CSV |
| `Tab` | Global | Next tab |

---

## Coding Best Practices

### General

- **Follow existing patterns** before introducing new abstractions. The codebase has clear, consistent conventions — match them.
- **Avoid debug `print()` statements.** Use Textual's `self.notify()` for user-visible messages and `self.log()` for debug output.
- **Keep widgets focused.** Widgets should handle display and user input; delegate data logic to `FileReader` or the app layer.
- **Don't add features beyond what is asked.** The presets system and read folding are stubs — do not expand them unless explicitly requested.

### Textual-Specific

- Use `compose()` to declare child widgets declaratively.
- Use `on_mount()` for initialization that requires the DOM to be ready.
- Return `Strip` (wrapping `list[Segment]`) from `render_line(y)` in custom `Widget` subclasses using the Line API.
- Use `self.app` to access shared state (e.g. `self.app.patterns`, `self.app.file_reader`).
- Prefer `self.notify()` over bare `print()` for user feedback in modal screens.

### Caching

- `FileReader.segment_cache` is a plain `dict[int, list[list[Segment]]]` keyed by read ID. Clear it (via `clear_cache()` or `patterns_changed()`) whenever rendering output would change.
- `FileReader.search()` is decorated with `@lru_cache(maxsize=50000)`. Its arguments must be hashable — patterns are passed as `(str, int)` tuples, not dicts.
- Compiled regex objects are stored in the module-level `pattern_regex` dict to avoid recompilation.

### Pattern Data

- Always pass patterns as the dict format described above. Do not store patterns as objects — the list-of-dicts format is used directly by both `FileReader` and the CSV export/import logic.
- When modifying the pattern list, call `file_reader.patterns_changed()` to invalidate caches and trigger a re-render.

### File I/O

- `FileReader` reads the FASTQ file **sequentially and lazily** — it never seeks backward. Do not assume random access.
- `total_reads` is `None` until EOF is hit. Always check `beyond_eof(loc)` before assuming a read ID is valid.

### Reverse Complement

The `revcomp()` utility function at module level:
```python
revcomp_lookup = str.maketrans("ACGTacgt", "TGCAtgca")

def revcomp(seq: str) -> str:
    return seq.translate(revcomp_lookup)[::-1]
```
Use this function; do not reimplement it inline.

### CSV Import/Export

Pattern CSV format:
```
label,pattern,colour,max_edit_dist,revcomp
R1,CTACACGACGCTCTTCCGATCT,lawngreen,3,true
```
`revcomp` is a boolean stored as `"true"` / `"false"`. Validate all required columns on import and report per-row errors without aborting the full import.

---

## Things Not Yet Implemented

- **PresetsWidget** (`presets_widget.py`): Currently a placeholder. Intended for storing/loading common adapter sets.
- **Read folding**: `Record.folded` field exists but is unused.
- **Forward search** (`/` keybinding in pager): Binding is defined but has no handler.
- **Streaming search across file**: No global search; matching is per-read on render.
