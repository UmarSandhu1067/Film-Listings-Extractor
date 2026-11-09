from pathlib import Path

import pytest

from src.detector import LayoutDetectionError, detect_layout
from src.pdf_reader import read_pdf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = PROJECT_ROOT / "input"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("sheet_a_labelled_fields.pdf", "A"),
        ("sheet_b_table.pdf", "B"),
        ("sheet_c_messy_text.pdf", "C"),
    ],
)
def test_detects_actual_pdf_layout_from_first_page(filename, expected):
    assert detect_layout(read_pdf(INPUT / filename)) == expected


def test_raises_clear_error_when_layout_evidence_is_missing():
    with pytest.raises(LayoutDetectionError, match="Could not confidently identify"):
        detect_layout(
            [
                {
                    "words": [
                        {"text": "Unrelated", "x0": 10, "x1": 60, "top": 10, "bottom": 20},
                    ]
                }
            ]
        )
