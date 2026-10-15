"""Unit tests. Run with: python -m unittest -v"""

import json
import tempfile
import unittest
from pathlib import Path

from analyzer import analyze, load_events


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.events = load_events(Path(__file__).with_name("sample_logs.jsonl"))

    def test_sample_totals(self):
        report = analyze(self.events)
        self.assertEqual(report["total_calls"], 10)
        self.assertEqual(report["successful_calls"], 7)
        self.assertEqual(report["failed_calls"], 3)
        self.assertEqual(report["failure_rate_pct"], 30.0)
        self.assertEqual(report["total_tokens"], 7110)

    def test_detects_repeats_within_sessions(self):
        report = analyze(self.events)
        self.assertEqual(report["repeated_calls"], 3)
        self.assertEqual([item["line"] for item in report["repeats"]], [3, 4, 7])
        # The same web search in another session (line 9) is NOT a repeat.
        self.assertNotIn(9, [item["line"] for item in report["repeats"]])

    def test_slow_threshold_and_tool_breakdown(self):
        report = analyze(self.events, slow_threshold_ms=1200)
        self.assertEqual(report["slow_calls_count"], 3)
        self.assertEqual(report["tools"]["fetch_page"]["failures"], 2)
        self.assertEqual(report["tools"]["run_python"]["calls"], 3)

    def test_empty_file(self):
        self.assertEqual(analyze([])["failure_rate_pct"], 0)
        self.assertEqual(analyze([])["avg_duration_ms"], 0)

    def test_key_order_does_not_change_repeat_detection(self):
        first = {"session_id": "a", "tool": "search", "input": {"a": 1, "b": 2},
                 "status": "success", "duration_ms": 10, "tokens": 0, "line": 1}
        second = {**first, "input": {"b": 2, "a": 1}, "line": 2}
        self.assertEqual(analyze([first, second])["repeated_calls"], 1)

    def test_invalid_json_has_line_number(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.jsonl"
            path.write_text('{"session_id": "ok"}\nnot json\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Line 1: missing fields"):
                load_events(path)
            path.write_text('\nnot json\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Line 2: invalid JSON"):
                load_events(path)

    def test_negative_duration_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.jsonl"
            event = {"session_id": "s", "tool": "t", "input": {},
                     "status": "success", "duration_ms": -1}
            path.write_text(json.dumps(event), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duration_ms"):
                load_events(path)


if __name__ == "__main__":
    unittest.main()
