"""
Statement parsing package for the Expense Tracker.

This package provides a modular architecture for parsing various
financial statement formats including PDF, CSV, Excel, OFX, and QIF.
"""

from .base import BaseParser, ParseResult, ParserRegistry
from .registry import parser_registry

__all__ = [
    "BaseParser",
    "ParseResult", 
    "ParserRegistry",
    "parser_registry",
]