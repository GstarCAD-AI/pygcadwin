"""Small utility helpers matching pyautocad functionality."""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from typing import Any

from .tables import (
    mtext_to_string,
    string_to_mtext,
    suppress_regeneration,
    text_width,
    unformat_mtext,
)

suppressed_regeneration_of = suppress_regeneration


@contextmanager
def timing(message: str = "Elapsed"):
    """Print elapsed time for a block."""
    begin = time.time()
    try:
        yield begin
    finally:
        elapsed = time.time() - begin
        print(f"{message}: {elapsed:.3f} s")


def dynamic_print(text: Any) -> None:
    """Print text in-place on the current console line."""
    sys.stdout.write(f"\r{text}")
    sys.stdout.flush()

