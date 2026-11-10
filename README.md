# Film Listings Extractor

Extract film and television project listings from the supplied Sheet A
labelled fields, Sheet B table, and Sheet C free-text PDFs. Each parser produces
the same project/role structure; Pydantic validates it and adds cleaned values
without changing the original extracted text.

## Setup (Python 3.12)

In PowerShell from the repository root:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

`requirements.txt` pins `pdfplumber`, `pydantic`, `pytest`, and `ruff`.

## Extract to JSON

After installation, run the command-line tool:

```powershell
extract input\sheet_a_labelled_fields.pdf --out result.json
```

The same command works without installing the package entry point:

```powershell
python -m src.main extract input\sheet_a_labelled_fields.pdf --out result.json
```

The earlier print-only invocation remains available:

```powershell
python -m src.main input\sheet_a_labelled_fields.pdf
```

JSON retains printed text in fields such as `genre`, `location`, and
`start_date`. Cleaned values are separate: `genres`, `locations`,
`start_date_cleaned`, `start_date_precision`, and the corresponding
`*_cleaned` text fields. Unknown genre/location terms are retained; tentative
locations and dates are flagged, ambiguous dates are left without a normalized
date, and `TBD` dates remain empty.

The fixed genre vocabulary includes Action, Adventure, Comedy, Crime, Drama,
Horror, Romance, Science Fiction, Sports, Thriller, War, and Young Adult;
unrecognized labels are retained as printed. Known compound labels such as
`Dramedy`, `Sci-Fi`, and `Action-Adventure` are mapped explicitly. Month and
season dates use the first day of their known month, with precision recorded
separately. Seasons map to March, June, September, and December; quarter dates
map to the first month of the quarter. For a recognized date range, the cleaned
date is its first endpoint and its precision is `range`. Unsupported or
ambiguous dates (including two-digit years) have no cleaned date.

## Inspect PDF word coordinates

Print every extracted word and its page position with:

```powershell
python -c "from src.pdf_reader import print_pdf_words; print_pdf_words(r'input\sheet_b_table.pdf')"
```

The reader reports `x0`, `x1`, `top`, and `bottom` in PDF points. Similar
vertical positions form lines; repeated horizontal starts reveal the table
columns used by Sheet B.

## Tests and lint

```powershell
pytest -v
ruff check .
```

The tests cover all three supplied PDFs, layout detection, parsing, cleaning
rules, Pydantic validation, and JSON output.