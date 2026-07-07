# AssignCase

Python CLI app to assign support/work cases from CSV input across SEs as evenly and fairly as possible.

## Requirements

- Python 3.9+
- No external Python packages are required

## Setup

Clone the repository and move into it:

```bash
cd /home/runner/work/AssignCase/AssignCase
```

Optional: create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Sample input files

Ready-to-use sample CSV files are included in `/home/runner/work/AssignCase/AssignCase/samples`:

- `/home/runner/work/AssignCase/AssignCase/samples/cases.csv`
- `/home/runner/work/AssignCase/AssignCase/samples/se.csv`

## How to run the project

Run the main script from the repository root:

```bash
cd /home/runner/work/AssignCase/AssignCase
python assign_cases.py \
  --cases samples/cases.csv \
  --se samples/se.csv \
  --output samples/assigned.csv
```

For deterministic scoring, pass `--now`:

```bash
python assign_cases.py \
  --cases samples/cases.csv \
  --se samples/se.csv \
  --output samples/assigned.csv \
  --now 2026-07-07T00:00:00Z
```

The command writes a new CSV to the `--output` path with all original case columns plus:

- `assigned_se`

## Input CSV format

### Cases CSV

Required columns:

- `id`
- `created time`

Optional column:

- `first response time`

If `first response time` exists but a row value is blank, it is treated as `now - created time`.
If `first response time` is absent, first-response scoring is not used.

Example:

```csv
id,created time,first response time
C-001,2026-07-01T10:00:00,2026-07-01T10:45:00
C-002,2026-07-02T09:30:00,
C-003,2026-07-03T15:10:00,2026-07-03T16:00:00
```

### SE CSV

Provide one SE name per row. The first column is used, and a header row such as `name` is allowed:

```csv
name
Alice
Bob
Charlie
```

## How to test the project

Run the existing unit tests from the repository root:

```bash
cd /home/runner/work/AssignCase/AssignCase
python -m unittest -v
```

Current tests cover:

- balanced assignment counts
- output CSV generation
- missing first-response handling
- invalid input validation