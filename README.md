# fuzzless

A simple Hello World Textual TUI application built with Python and uv.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Clone the repository
git clone <repository-url>
cd fuzzless

# Install dependencies (uv will create a virtual environment automatically)
uv sync
```

## Running the Application

There are several ways to run the application:

### Method 1: Using uv run (recommended)
```bash
uv run fuzzless
```

### Method 2: Direct script execution
```bash
uv run python -m fuzzless.app
```

### Method 3: After activating the virtual environment
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
fuzzless
```

## Usage

Once running:
- Press `q` to quit the application

## Development

This project uses:
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- [Textual](https://github.com/Textualize/textual) - Modern TUI framework for Python

## License

See LICENSE file for details.