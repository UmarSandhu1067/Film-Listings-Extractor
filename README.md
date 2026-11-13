# Film Listings Extractor

Extract film and television project listings with V1 and V2. V1 retains its
original parser and API behavior; V2 adds the new extraction flow and runs
alongside V1 in the same FastAPI server.

For the full walkthrough of setup, extraction, output fields, API endpoints,
testing, and current limitations, see the [Project Guide](./PROJECT_GUIDE.md).
For quick side-by-side manual testing steps, see the
[V1/V2 Testing Guide](./TESTING_V1_V2.md).

## V2 Extraction and API

V2 is isolated under `src.v2`; V1's parser, models, CLI, and API routes are
unchanged. Run the combined APIs on one port:

```powershell
uvicorn src.api:app --reload --port 8000
```

V1 remains available at `http://127.0.0.1:8000/projects` and `/health`.
V2 is available under the `/v2` prefix: `/v2/projects`, `/v2/people`,
`/v2/companies`, and `/v2/health`. The APIs keep separate in-memory data.
V2 loads its bundled sample data when the server starts, so no POST is needed
to see the initial V2 results. Use `/docs` for V1 and `/v2/docs` for V2.

For API testing, you do not need to run the V2 CLI or supply a file path.
The combined API extracts its bundled V2 sample data when it starts. The CLI
is only needed when you separately want to export V2 results to a JSON file;
it takes the original PDF as input, not a JSON file.

V2 text is read top-to-bottom in the left column, then the right column,
before advancing to the next page. The repeated page header, footer, and final
credit key are excluded. Section bands apply to following projects; a continued
project keeps its current state across columns and pages. Printed project,
role, credit, contact, and alias text remains alongside its cleaned value.
Credits with combined codes produce one record per code. Unknown codes remain
visible and flagged. People are merged using a case-, spacing-, and
punctuation-insensitive key; the company heuristic uses the suffixes specified
in the task guide.

Known limits: V2 reads text PDFs only, assumes two columns split at the page
midpoint, and does not infer a missing project title or an unknown credit-code
meaning. OCR, three-column layouts, and source bounding boxes are not included.
With another week, I would add stored page coordinates and a configurable
column-boundary detector, then validate those additions against more varied
layouts.

## Setup (Python 3.12)

In PowerShell from the repository root:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e .
```

`requirements.txt` lists the runtime, test, lint, and type-checking dependencies.

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

JSON includes a `pages` array with each PDF page's number, dimensions, complete
extractable text, and positioned words. This preserves page headings, printed
page labels, and punctuation without splitting words into individual
characters, even when content is not mapped to a project field. The `projects`
array retains printed text in fields such as `genre`, `location`, and
`start_date`. Cleaned values are separate: `genres`, `locations`,
`studios`, `start_date_cleaned`, `start_date_precision`, and the corresponding
`*_cleaned` text fields. Sheet C `Shoot:` text is emitted as `location`, like
the other layouts. Unknown genre/location terms are retained; tentative
locations and dates are flagged, unsupported dates have no normalized date,
and `TBD` dates remain empty.

Project and role records generally include only fields extracted from that
PDF's layout; other fields are omitted rather than emitted as `null`. Cleaned
and normalized values are included only for source fields that were extracted.
Sheet A also includes `title_alias` to preserve parenthetical `fka`/`aka`
title notes; it is `null` for Sheet A projects without such a note. Other
layouts do not include this field.

Page text is extracted from the PDF's text layer. Text embedded only in scanned
images requires OCR and is not included by this reader.

The fixed genre vocabulary includes Action, Adventure, Comedy, Crime, Drama,
Horror, Romance, Science Fiction, Sports, Thriller, War, and Young Adult;
unrecognized labels are retained as printed. Known compound labels such as
`Dramedy`, `Sci-Fi`, and `Action-Adventure` are mapped explicitly. Descriptive
qualifiers such as `Psychological` and parenthetical notes do not prevent
recognition of a known genre.

Month and season dates use the first day of their known month, with precision
recorded separately. `Early`, `Mid`, and `Late` month dates use representative
days 5, 15, and 25 and `part_of_month` precision. Seasons map to March, June,
September, and December; quarter dates map to the first month of the quarter.
For a recognized date range, the cleaned date is its first endpoint and its
precision stays at that endpoint's granularity (`day`, `month`, or `quarter`).
Slash-form dates with two-digit years interpret the year as 2000–2099, so
`10/24/25` normalizes to 2025-10-24.

Locations drop comma-suffixed state, province, and country text, normalize
`NY` and `NYC` to `New York`, and split parenthetical alternatives into
separate locations. Studio names separated by `/`, `;`, or `+` are available in
`studios`; the original `studio` text remains unchanged. All-caps role names
are title-cased in `role_name_cleaned`, while `role_name` retains the printed
form. A `TBD ROLE` receives a `role_flag`.

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
mypy src tests
```

The tests cover all three supplied PDFs, layout detection, parsing, cleaning
rules, Pydantic validation, and JSON output.

## API

Start the service from the repository root:

```powershell
uvicorn src.api:app --reload
```

`POST /projects` accepts up to 20 project records per request. A request with
21 or more records returns HTTP 413. Records are validated independently:
valid records are stored, while invalid records appear in the `rejected` list.
A repeated project title (ignoring surrounding whitespace and case) is accepted
and updates the existing record rather than creating a duplicate.
An empty `projects` list returns HTTP 422. For example:

```json
{
  "projects": [
    {"project_title": "Quiet Hours"},
    {"studio": "North Star"}
  ]
}
```

```json
{
  "accepted": 1,
  "rejected": [
    {"index": 1, "errors": ["project_title: Field required"]}
  ]
}
```

`GET /projects` returns records held in the running API process; it does not
read JSON files from disk, and the in-memory records are cleared when the
process restarts. To load or refresh records from an extractor result, send it
to the API with:

```powershell
python scripts\send_batches.py result.json --url http://127.0.0.1:8000
```

## Design choices

1. **Why preserve the printed value beside normalized values?** Source text
   remains available for auditability; uncertain dates and tentative locations
   are flagged instead of being silently rewritten.
2. **How are date precision and two-digit years handled?** Mid- and late-month
   dates use representative dates (the 15th and 25th) marked
   `part_of_month`; ranges retain the precision of their first endpoint.
   Two-digit years are interpreted in the 2000s, so `10/24/25` means
   2025-10-24.
3. **How are location, genre, and company variations normalized?** Known
   modifiers and qualifiers are reduced to canonical genres; comma-suffixed
   administrative regions are dropped from place names; listed alternatives
   and slash-separated studios become arrays. The printed field remains
   intact.
4. **How are records kept consistent across layouts and API requests?** All
   `Shoot:` values use the shared `location` field, page-continuation state is
   retained by the parsers, and duplicate API titles update the existing
   record after case-insensitive, whitespace-trimmed comparison. Invalid API
   records are rejected independently.
