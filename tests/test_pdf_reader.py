from pathlib import Path

from src.pdf_reader import print_word_coordinates, read_pdf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHEET_A = PROJECT_ROOT / "input" / "sheet_a_labelled_fields.pdf"


def test_reader_extracts_every_page_and_word_coordinates():
    pages = read_pdf(SHEET_A)

    assert len(pages) == 2
    assert pages[0]["page_number"] == 1
    assert pages[0]["words"]
    first_word = pages[0]["words"][0]
    assert first_word["text"] == "STUDIO"
    assert set(first_word) == {"text", "x0", "x1", "top", "bottom"}
    assert first_word["x0"] < first_word["x1"]
    assert first_word["top"] < first_word["bottom"]


def test_coordinate_printer_includes_word_and_all_positions(capsys):
    print_word_coordinates(
        [
            {
                "page_number": 1,
                "width": 100.0,
                "height": 200.0,
                "words": [{"text": "Test", "x0": 1.0, "x1": 20.0, "top": 2.0, "bottom": 10.0}],
            }
        ]
    )

    output = capsys.readouterr().out
    assert "Test" in output
    assert all(name in output for name in ("x0=", "x1=", "top=", "bottom="))
