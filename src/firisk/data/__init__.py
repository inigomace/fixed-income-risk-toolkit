# src/firisk/data/__init__.py

"""
Data loading and validation.

Provides functions and abstractions for working with yield history data.
"""

from .loaders import load_yield_history, validate_yield_table

__all__ = [
    "load_yield_history",
    "validate_yield_table",
]
