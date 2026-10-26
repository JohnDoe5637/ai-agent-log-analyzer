# AI Agent Log Analyzer

A lightweight Python command-line tool that helps developers **debug AI agents** by analyzing logs of agent tool calls. It detects **failures, repeated tool calls, slow operations, and token usage**, with no API key or third-party packages required.

## Why this exists

AI agents may repeatedly call tools, retry failed requests, or spend too much time on a single operation. This project provides a simple observability starting point: inspect a `.jsonl` file to see where agent runs may need attention.

> **Note:** This is a rule-based log analyzer for AI-agent behavior, not a machine-learning model. Repeated calls may be intentional retries; they are flagged for review, not automatically classified as errors.

## Quick start

**Prerequisite:** Python 3.9 or newer.

```bash
# Clone your repo after uploading it (or open this folder locally).
python analyzer.py sample_logs.jsonl
```

### Example output

```text
AI AGENT LOG ANALYZER
============================================
Total tool calls : 10
Successful calls : 7
Failed calls     : 3 (30.0%)
Repeated calls   : 3
Slow calls       : 3 (> 1000 ms)
Average duration : 757.0 ms
Total tokens     : 7110
```

The complete terminal report also includes per-tool statistics, failed operations and their error messages, repeated input locations, and slow calls.

## Options

```bash
# JSON output, useful for piping into dashboards or other scripts
python analyzer.py sample_logs.jsonl --json

# Adjust slow-call cutoff to 500 milliseconds
python analyzer.py sample_logs.jsonl --slow-threshold-ms 500

# Run all automated tests
python -m unittest -v
```

## Input format

One JSON object per line (`.jsonl`), describing one **tool invocation**:

```json
{"session_id":"run-001","tool":"web_search","input":{"query":"AI news"},"status":"success","duration_ms":250,"tokens":120}
```

| Field | Type | Required? | Meaning |
| --- | --- | --- | --- |
| `session_id` | string | Yes | Agent run identifier (used to group repeated calls) |
| `tool` | string | Yes | Name of the tool being called |
| `input` | any JSON value | Yes | Tool arguments; used to detect identical requests |
| `status` | `success` or `error` | Yes | Call outcome |
| `duration_ms` | number >= 0 | Yes | Wall-clock time in milliseconds |
| `tokens` | integer >= 0 | No | Logged token count; defaults to 0 |
| `error` | string | No | Error message for failed calls |
| `timestamp` | string | No | Timestamp, for human reference |

### How repeated calls are detected

Calls are marked as repeated if they have **the same `session_id`, `tool`, and JSON `input`** as an earlier call in the same file. JSON object key order does not matter. The system reports the first occurrence and each later repetition. Calls from different sessions do not count as repeats. Slow calls have `duration_ms` **strictly greater than** the selected threshold.

## Files

```text
ai-agent-log-analyzer/
├── .github/workflows/tests.yml  # GitHub Actions tests
├── analyzer.py                  # CLI and analysis logic
├── sample_logs.jsonl            # Example agent activity
├── test_analyzer.py             # Unit tests
├── requirements.txt             # No external dependencies
└── README.md                    # Documentation
```

## Roadmap

- Detect repeated failures with exponential-backoff recommendations
- Add estimated dollar costs for popular AI models
- Parse OpenAI / Anthropic tool-call traces into a common format
- Generate HTML charts and dashboards
- Evaluate agent runs across sessions

## Tech stack

Python 3, `argparse`, `json`, `collections`, `unittest`. Designed to stay small, transparent, and easy to extend.

## Future Improvements



## Getting Started

### Running the Project
1. Clone the repository.
2. Open a terminal in the project folder.
3. Run:
   
### Requirements
- Python 3.10 or newer



```bash
python analyzer.py
```


