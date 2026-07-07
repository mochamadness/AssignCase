import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


def _normalize_header(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _find_column(fieldnames: List[str], options: List[str]) -> Optional[str]:
    normalized_map = {_normalize_header(name): name for name in fieldnames}
    for option in options:
        if option in normalized_map:
            return normalized_map[option]
    return None


def parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError("Timestamp value is empty.")

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: '{value}'. Use ISO format.") from exc

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass
class Case:
    row_index: int
    row_data: Dict[str, str]
    case_id: str
    created_time: datetime
    age_seconds: float
    first_response_delay_seconds: Optional[float]
    score: float = 0.0


def read_cases(path: str, now: datetime) -> Tuple[List[Case], bool]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            raise ValueError("Cases CSV is missing a header row.")

        id_col = _find_column(fieldnames, ["id"])
        created_col = _find_column(fieldnames, ["created time", "created_at", "created"])
        first_response_col = _find_column(
            fieldnames,
            ["first response time", "first_response_time", "first response", "first response at"],
        )

        if not id_col:
            raise ValueError("Cases CSV must include an 'id' column.")
        if not created_col:
            raise ValueError("Cases CSV must include a 'created time' column.")

        cases: List[Case] = []
        for index, row in enumerate(reader):
            case_id = (row.get(id_col) or "").strip()
            if not case_id:
                raise ValueError(f"Cases CSV row {index + 2} has empty id.")

            created_raw = (row.get(created_col) or "").strip()
            if not created_raw:
                raise ValueError(f"Cases CSV row {index + 2} has empty created time.")
            created_time = parse_timestamp(created_raw)

            age_seconds = (now - created_time).total_seconds()
            if age_seconds < 0:
                raise ValueError(f"Cases CSV row {index + 2} has created time in the future.")

            first_delay: Optional[float] = None
            if first_response_col:
                first_raw = (row.get(first_response_col) or "").strip()
                if first_raw:
                    first_response_time = parse_timestamp(first_raw)
                    first_delay = (first_response_time - created_time).total_seconds()
                    if first_delay < 0:
                        raise ValueError(
                            f"Cases CSV row {index + 2} has first response time before created time."
                        )
                else:
                    first_delay = age_seconds

            cases.append(
                Case(
                    row_index=index,
                    row_data=row,
                    case_id=case_id,
                    created_time=created_time,
                    age_seconds=age_seconds,
                    first_response_delay_seconds=first_delay,
                )
            )

    if not cases:
        raise ValueError("Cases CSV has no data rows.")

    return cases, bool(first_response_col)


def read_ses(path: str) -> List[str]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        rows = [row for row in reader if row]

    if not rows:
        raise ValueError("SE CSV is empty.")

    first_row_lower = [cell.strip().lower() for cell in rows[0]]
    start_index = 0
    if any(token in {"name", "se", "engineer"} for token in first_row_lower):
        start_index = 1

    ses = []
    for row in rows[start_index:]:
        if not row:
            continue
        name = row[0].strip()
        if name:
            ses.append(name)

    if not ses:
        raise ValueError("SE CSV does not contain any SE names.")

    return ses


def _normalize(values: List[float]) -> List[float]:
    max_value = max(values) if values else 0.0
    if max_value <= 0:
        return [0.0 for _ in values]
    return [value / max_value for value in values]


def assign_cases(cases: List[Case], se_names: List[str], include_first_response: bool) -> Dict[str, str]:
    base_count = len(cases) // len(se_names)
    extra = len(cases) % len(se_names)
    max_items = {
        se: base_count + (1 if idx < extra else 0)
        for idx, se in enumerate(se_names)
    }

    normalized_age = _normalize([case.age_seconds for case in cases])
    if include_first_response:
        normalized_first = _normalize(
            [case.first_response_delay_seconds or 0.0 for case in cases]
        )
    else:
        normalized_first = [0.0 for _ in cases]

    for idx, case in enumerate(cases):
        if include_first_response:
            case.score = 0.5 * normalized_age[idx] + 0.5 * normalized_first[idx]
        else:
            case.score = normalized_age[idx]

    cases_sorted = sorted(cases, key=lambda item: item.score, reverse=True)
    assigned_counts = {se: 0 for se in se_names}
    assigned_scores = {se: 0.0 for se in se_names}
    assignments: Dict[str, str] = {}

    for case in cases_sorted:
        eligible = [
            se for se in se_names if assigned_counts[se] < max_items[se]
        ]
        selected = min(eligible, key=lambda se: (assigned_scores[se], assigned_counts[se], se))
        assignments[case.case_id] = selected
        assigned_counts[selected] += 1
        assigned_scores[selected] += case.score

    return assignments


def write_output(path: str, cases: List[Case], assignments: Dict[str, str]) -> None:
    fieldnames = list(cases[0].row_data.keys())
    if "assigned_se" not in fieldnames:
        fieldnames.append("assigned_se")

    cases_in_input_order = sorted(cases, key=lambda item: item.row_index)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for case in cases_in_input_order:
            output_row = dict(case.row_data)
            output_row["assigned_se"] = assignments[case.case_id]
            writer.writerow(output_row)


def run(cases_path: str, se_path: str, output_path: str, now: datetime) -> None:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)

    cases, include_first_response = read_cases(cases_path, now)
    se_names = read_ses(se_path)
    assignments = assign_cases(cases, se_names, include_first_response)
    write_output(output_path, cases, assignments)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assign support/work cases from a CSV file to SEs fairly."
    )
    parser.add_argument("--cases", required=True, help="Path to cases CSV file.")
    parser.add_argument("--se", required=True, help="Path to SE CSV file.")
    parser.add_argument("--output", required=True, help="Path to output assigned CSV file.")
    parser.add_argument(
        "--now",
        help="Optional ISO timestamp for deterministic scoring (defaults to current UTC time).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        now = parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)
        run(args.cases, args.se, args.output, now)
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
