# AssignCase

Python CLI app to assign support/work cases from CSV input across SEs as evenly and fairly as possible.

## Requirements

- Python 3.9+

## Input CSV format

### Cases CSV

Required columns:

- `id`
- `created time`

Optional column:

- `first response time`

If `first response time` column exists but a row value is blank, it is treated as `now - created time`.
If `first response time` column is absent, first-response scoring is not used.

Example:

```csv
id,created time,first response time
C-001,2026-07-01T10:00:00,2026-07-01T10:45:00
C-002,2026-07-02T09:30:00,
C-003,2026-07-03T15:10:00,2026-07-03T16:00:00
```

### SE CSV

Provide one SE name per row (first column is used):

```csv
name
Alice
Bob
Charlie
```

## Usage

```bash
python /home/runner/work/AssignCase/AssignCase/assign_cases.py \
  --cases /absolute/path/cases.csv \
  --se /absolute/path/se.csv \
  --output /absolute/path/assigned.csv
```

Optional:

- `--now` ISO timestamp override for deterministic runs/tests.

## Output

Writes a CSV to `--output` with original case columns plus:

- `assigned_se`