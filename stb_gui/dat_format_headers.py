"""Re-export aligned .dat headers from classes.dat_format."""

from __future__ import annotations

import os
import sys

_CLASSES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "classes")
if _CLASSES not in sys.path:
    sys.path.insert(0, _CLASSES)

from dat_format import (  # noqa: E402
    SECTION_HEADERS,
    example_line,
    new_model_template,
    record_line,
    reformat_record_line,
)

__all__ = [
    "SECTION_HEADERS",
    "example_line",
    "new_model_template",
    "record_line",
    "reformat_record_line",
]
