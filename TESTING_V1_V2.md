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

V2 supports Sheet D:

```powershell
python -m src.v2.main input\sheet_d_two_column_grid.pdf --out sheet_d_test.json
```

Expected V1 results: **A: 4 projects/9 roles, B: 5/12, C: 3/9** (12/30 total).
Expected V2 totals: **8 projects, 22 roles, 37 credits, 17 people, and 2 companies**.

Check the V2 JSON counts:

```powershell
$d = Get-Content .\sheet_d_test.json -Raw | ConvertFrom-Json
$d.projects.Count
($d.projects | ForEach-Object { $_.roles.Count } | Measure-Object -Sum).Sum
($d.projects | ForEach-Object { $_.credits.Count } | Measure-Object -Sum).Sum
$d.people.Count
$d.companies.Count
```

## 3. Run both APIs at the same time

Open two PowerShell terminals.

Terminal 1 — V1:

```powershell
python -m uvicorn src.api:app --reload --port 8000
```

Terminal 2 — V2:

```powershell
python -m uvicorn src.v2.api:app --reload --port 8001
```

Check that both are responding:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8001/health
```

Both APIs use `/projects`, but they run on different ports and keep separate
in-memory data. V2 also provides `/people` and `/companies`.

## 4. Load extracted projects into each API

V1 example:

```powershell
$d = Get-Content .\v1_sheet_a.json -Raw | ConvertFrom-Json
$body = @{ projects = $d.projects } | ConvertTo-Json -Depth 100
Invoke-RestMethod http://127.0.0.1:8000/projects -Method Post -ContentType "application/json" -Body $body
Invoke-RestMethod http://127.0.0.1:8000/projects
```

V2 example:

```powershell
$d = Get-Content .\sheet_d_test.json -Raw | ConvertFrom-Json
$body = @{ projects = $d.projects } | ConvertTo-Json -Depth 100
Invoke-RestMethod http://127.0.0.1:8001/projects -Method Post -ContentType "application/json" -Body $body
Invoke-RestMethod http://127.0.0.1:8001/people
Invoke-RestMethod http://127.0.0.1:8001/companies
```

The APIs store data in memory; restarting a service clears its records.

## 5. Run automated checks

```powershell
ruff check .
mypy src
pytest
```
