"""Fuzzless - A pager application for viewing large text files using Textual's Line API."""

__version__ = "0.1.0"

from fuzzless.app import FuzzlessApp, main
from fuzzless.file_reader import FileReader
from fuzzless.pager_widget import PagerWidget

__all__ = ["FuzzlessApp", "FileReader", "PagerWidget", "main"]
