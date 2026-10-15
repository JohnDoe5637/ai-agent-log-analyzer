"""Analyze JSONL tool-call logs produced by an AI agent.

Uses only Python's standard library. Run:
    python analyzer.py sample_logs.jsonl
    python analyzer.py sample_logs.jsonl --json
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


REQUIRED_FIELDS = ("session_id", "tool", "input", "status", "duration_ms")
VALID_STATUSES = {"success", "error"}


def load_events(path):
    """Read JSONL events and validate them, reporting errors by line number."""
    events = []

    with Path(path).open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            if not raw_line.strip():
                continue  # Ignore blank lines.

            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {line_number}: invalid JSON ({exc.msg})") from exc

            if not isinstance(event, dict):
                raise ValueError(f"Line {line_number}: expected a JSON object")

            missing = [field for field in REQUIRED_FIELDS if field not in event]
            if missing:
                raise ValueError(f"Line {line_number}: missing fields: {', '.join(missing)}")

            for field in ("session_id", "tool"):
                if not isinstance(event[field], str) or not event[field].strip():
                    raise ValueError(f"Line {line_number}: '{field}' must be a nonempty string")

            if not isinstance(event["status"], str) or event["status"] not in VALID_STATUSES:
                raise ValueError(f"Line {line_number}: status must be 'success' or 'error'")

            duration = event["duration_ms"]
            if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not 0 <= duration < float("inf"):
                raise ValueError(f"Line {line_number}: duration_ms must be a finite nonnegative number")

            tokens = event.get("tokens", 0)
            if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
                raise ValueError(f"Line {line_number}: tokens must be a nonnegative integer")

            event["tokens"] = tokens
            event["line"] = line_number
            events.append(event)

    return events


def analyze(events, slow_threshold_ms=1000):
    """Compute totals, failures, slow calls, per-tool stats and repeated inputs."""
    per_tool = defaultdict(lambda: {"calls": 0, "failures": 0, "duration_ms": 0})
    first_seen = {}  # (session, tool, serialized input) -> first line number
    failures = []
    repeats = []
    slow_calls = []
    total_duration = 0
    total_tokens = 0

    for event in events:
        tool = event["tool"]
        duration = event["duration_ms"]
        per_tool[tool]["calls"] += 1
        per_tool[tool]["duration_ms"] += duration
        total_duration += duration
        total_tokens += event["tokens"]

        if event["status"] == "error":
            per_tool[tool]["failures"] += 1
            failures.append({
                "line": event["line"],
                "session_id": event["session_id"],
                "tool": tool,
                "message": event.get("error", "No error detail provided"),
            })

        if duration > slow_threshold_ms:
            slow_calls.append({"line": event["line"], "tool": tool, "duration_ms": duration})

        # Serialize inputs consistently; JSON object key order should not matter.
        input_key = json.dumps(event["input"], sort_keys=True, separators=(",", ":"))
        key = (event["session_id"], tool, input_key)
        if key in first_seen:
            repeats.append({
                "line": event["line"],
                "first_line": first_seen[key],
                "session_id": event["session_id"],
                "tool": tool,
            })
        else:
            first_seen[key] = event["line"]

    count = len(events)
    failure_count = len(failures)
    tool_stats = {}
    for tool, stats in sorted(per_tool.items()):
        tool_stats[tool] = {
            "calls": stats["calls"],
            "failures": stats["failures"],
            "avg_duration_ms": round(stats["duration_ms"] / stats["calls"], 1),
        }

    return {
        "total_calls": count,
        "successful_calls": count - failure_count,
        "failed_calls": failure_count,
        "failure_rate_pct": round(100 * failure_count / count, 1) if count else 0,
        "repeated_calls": len(repeats),
        "slow_calls_count": len(slow_calls),
        "avg_duration_ms": round(total_duration / count, 1) if count else 0,
        "total_tokens": total_tokens,
        "tools": tool_stats,
        "failures": failures,
        "repeats": repeats,
        "slow_calls": slow_calls,
    }


def print_report(report, slow_threshold_ms):
    """Print the same analysis in a human-readable terminal format."""
    print("\nAI AGENT LOG ANALYZER")
    print("=" * 44)
    print(f"Total tool calls : {report['total_calls']}")
    print(f"Successful calls : {report['successful_calls']}")
    print(f"Failed calls     : {report['failed_calls']} ({report['failure_rate_pct']}%)")
    print(f"Repeated calls   : {report['repeated_calls']}")
    print(f"Slow calls       : {report['slow_calls_count']} (> {slow_threshold_ms} ms)")
    print(f"Average duration : {report['avg_duration_ms']} ms")
    print(f"Total tokens     : {report['total_tokens']}")

    print("\nPER-TOOL SUMMARY")
    for tool, stats in report["tools"].items():
        print(f"  {tool}: {stats['calls']} calls, {stats['failures']} failures, "
              f"{stats['avg_duration_ms']} ms avg")

    print("\nFAILURES")
    if not report["failures"]:
        print("  None")
    for failed in report["failures"]:
        print(f"  Line {failed['line']}: {failed['tool']} — {failed['message']}")

    print("\nPOSSIBLE REDUNDANT CALLS")
    if not report["repeats"]:
        print("  None")
    for repeat in report["repeats"]:
        print(f"  Line {repeat['line']}: {repeat['tool']} repeated "
              f"input from line {repeat['first_line']} "
              f"(session {repeat['session_id']})")

    print("\nSLOW CALLS")
    if not report["slow_calls"]:
        print("  None")
    for slow in report["slow_calls"]:
        print(f"  Line {slow['line']}: {slow['tool']} took {slow['duration_ms']} ms")
    print("\nNote: A repeated call may be an intentional retry, not necessarily a bug.\n")


def main():
    parser = argparse.ArgumentParser(description="Find failures, repeated calls, and slow calls in AI agent JSONL logs")
    parser.add_argument("logfile", type=Path, help="Path to a .jsonl log file")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--slow-threshold-ms", type=float, default=1000,
                        help="Mark calls slower than this many milliseconds (default: 1000)")
    args = parser.parse_args()
    if not 0 <= args.slow_threshold_ms < float("inf"):
        parser.error("--slow-threshold-ms must be a finite nonnegative number")

    try:
        events = load_events(args.logfile)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    report = analyze(events, args.slow_threshold_ms)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report, args.slow_threshold_ms)


if __name__ == "__main__":
    main()
