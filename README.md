# Film Listings Extractor

Week 1 project for extracting film and television project listings from three
PDF layouts and returning a common Python data structure.

## Project structure

```text
input/                 Supplied Sheet A, B, and C PDFs
src/
  main.py              End-to-end extraction workflow
  pdf_reader.py        Word and coordinate extraction with pdfplumber
  detector.py          Content-based first-page layout detection
  parsers/             One parser per PDF layout
tests/                 Tests using the supplied PDFs
requirements.txt       Runtime and development dependencies
```

The three PDFs are included in `input/`. Each parser returns a list of project
dictionaries with the same project and role keys. Unavailable fields are `None`;
the parsers do not normalize values or invent missing information.

## Python environment

Create and activate a Python 3.12 environment in PowerShell:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Dependencies:

- `pdfplumber`: extract PDF text and word coordinates.
- `pydantic`: included for the project setup; Week 1 output uses dictionaries.
- `pytest`: run automated tests.
- `ruff`: lint Python code.

## Run the extractor

From the project root, activate the environment and run:

```powershell
.\.venv312\Scripts\Activate.ps1
python -m src.main input\sheet_a_labelled_fields.pdf
python -m src.main input\sheet_b_table.pdf
python -m src.main input\sheet_c_messy_text.pdf
```

To print every extracted word with its coordinates, call the reusable reader
from Python:

```python
from src.pdf_reader import print_pdf_words

print_pdf_words("input/sheet_a_labelled_fields.pdf")
```

The `x0`/`x1` coordinates show where a word sits horizontally; `top`/`bottom`
show its vertical position. Words with similar vertical positions form a text
line, while repeated horizontal starts reveal table columns. These positions
help distinguish a grid from labelled or free-form text.

## Run tests and lint

```powershell
pytest -v
ruff check .
```

Week 1 uses ordinary dictionaries and lists. Pydantic validation, value
normalization, API endpoints, and JSON export are intentionally out of scope.

## Git

The project is stored in a local Git repository with small commits for setup,
the reader, detector, each parser, and the workflow/tests. Review them with:

```powershell
git log --oneline
git status
```

For future changes, stage only the files for that change and use a descriptive
commit message, for example:

```powershell
git add src\pdf_reader.py
git commit -m "Improve PDF coordinate reporting"
```
```
