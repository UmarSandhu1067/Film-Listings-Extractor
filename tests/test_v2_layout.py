from pathlib import Path

from src.pdf_reader import read_pdf
from src.v2.layout import detect_sheet_d, iter_sheet_d_lines

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHEET_D = PROJECT_ROOT / "input" / "sheet_d_two_column_grid.pdf"


def test_detects_sheet_d_without_changing_existing_sheet_detectors():
    assert detect_sheet_d(read_pdf(SHEET_D))


def test_sheet_d_lines_follow_column_order_and_exclude_page_furniture():
    lines = list(iter_sheet_d_lines(read_pdf(SHEET_D)))
    texts = [line.text for line in lines]

    assert texts.index("LOW TIDE") < texts.index("NINE MILE ROAD")
    assert texts.index("SECOND SHIFT (continued)") < texts.index("KEYS TO THE VAN")
    assert not any("FERNBROOK & VALE AGENCY" in text for text in texts)
    assert not any("Fictional practice data" in text for text in texts)
    assert not any(text.startswith("KEY:") for text in texts)
