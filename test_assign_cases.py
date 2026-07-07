import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from assign_cases import read_cases, read_ses, run


class AssignCasesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)
        self.now = datetime(2026, 7, 7, 0, 0, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_file(self, name: str, contents: str) -> Path:
        path = self.base_path / name
        path.write_text(contents, encoding="utf-8")
        return path

    def test_balanced_distribution_and_output_column(self) -> None:
        cases = self._write_file(
            "cases.csv",
            "\n".join(
                [
                    "id,created time,first response time",
                    "C1,2026-07-01T00:00:00,2026-07-01T02:00:00",
                    "C2,2026-07-02T00:00:00,",
                    "C3,2026-07-03T00:00:00,2026-07-03T01:00:00",
                    "C4,2026-07-04T00:00:00,2026-07-04T03:00:00",
                    "C5,2026-07-05T00:00:00,",
                ]
            ),
        )
        ses = self._write_file("se.csv", "name\nAlice\nBob\n")
        output = self.base_path / "output.csv"

        run(str(cases), str(ses), str(output), self.now)

        with output.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))

        self.assertEqual(5, len(rows))
        counts = {}
        for row in rows:
            self.assertIn("assigned_se", row)
            counts[row["assigned_se"]] = counts.get(row["assigned_se"], 0) + 1
        self.assertEqual({"Alice", "Bob"}, set(counts.keys()))
        self.assertEqual(1, abs(counts["Alice"] - counts["Bob"]))

    def test_missing_first_response_value_uses_now_minus_created(self) -> None:
        cases_csv = self._write_file(
            "cases.csv",
            "\n".join(
                [
                    "id,created time,first response time",
                    "C1,2026-07-06T00:00:00,",
                ]
            ),
        )
        cases, include_first = read_cases(str(cases_csv), self.now)
        self.assertTrue(include_first)
        self.assertEqual(24 * 3600, cases[0].first_response_delay_seconds)

    def test_missing_created_time_column_errors(self) -> None:
        cases_csv = self._write_file("cases.csv", "id,first response time\nC1,2026-07-06T01:00:00\n")
        with self.assertRaises(ValueError) as ctx:
            read_cases(str(cases_csv), self.now)
        self.assertIn("created time", str(ctx.exception))

    def test_se_csv_without_names_errors(self) -> None:
        se_csv = self._write_file("se.csv", "name\n\n")
        with self.assertRaises(ValueError):
            read_ses(str(se_csv))


if __name__ == "__main__":
    unittest.main()
