# Manual Testing: V1 and V2

Run these commands from the repository root in PowerShell.

## 1. Prepare the environment

```powershell
.\.venv312\Scripts\Activate.ps1
```

## 2. Test PDF extraction

V1 supports Sheets A, B, and C:

```powershell
python -m src.main extract input\sheet_a_labelled_fields.pdf --out v1_sheet_a.json
python -m src.main extract input\sheet_b_table.pdf --out v1_sheet_b.json
python -m src.main extract input\sheet_c_messy_text.pdf --out v1_sheet_c.json
```

Expected V1 results: **A: 4 projects/9 roles, B: 5/12, C: 3/9** (12/30 total).
Expected V2 totals: **8 projects, 22 roles, 37 credits, 17 people, and 2 companies**.

For API testing, you do not need to run V2 extraction or enter a PDF/JSON path.
The combined API loads V2 sample data when it starts.

## 3. Run both APIs on one port

Start the combined API once:

```powershell
python -m uvicorn src.api:app --reload --port 8000
```

Both versions use port 8000. V1 routes are unchanged; V2 routes use the `/v2`
prefix. Open `http://127.0.0.1:8000/docs` for V1 or
`http://127.0.0.1:8000/v2/docs` for V2.
V2 loads its sample projects, people, and companies automatically when the
server starts; you do not need to POST the V2 JSON first.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/v2/health
```

V1 uses `/projects`; V2 uses `/v2/projects`, `/v2/people`, and
`/v2/companies`. Their in-memory data remains separate.

## 4. Load V1 projects and check V2

V1 example (repeat for the other V1 JSON files if desired):

```powershell
$d = Get-Content .\v1_sheet_a.json -Raw | ConvertFrom-Json
$body = @{ projects = $d.projects } | ConvertTo-Json -Depth 100
Invoke-RestMethod http://127.0.0.1:8000/projects -Method Post -ContentType "application/json" -Body $body
Invoke-RestMethod http://127.0.0.1:8000/projects
```

Check the V2 data, which is already loaded:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v2/projects
Invoke-RestMethod http://127.0.0.1:8000/v2/people
Invoke-RestMethod http://127.0.0.1:8000/v2/companies
```

V2 reloads its sample data each time the server starts. V1 records are
in-memory and must be POSTed again after a restart.

## 5. Run automated checks

```powershell
ruff check .
mypy src
pytest
```
