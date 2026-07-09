"""Autonomous QA audit runner for AI Sales Manager.

The runner is intentionally safe by default:
- it does not start real campaigns,
- it does not send Telegram messages,
- it uses the dialogue lab for inbound conversation behavior,
- it writes a local markdown report under scripts/.qa-audit/.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path(__file__).resolve().parent / ".qa-audit" / "latest.md"


@dataclass
class CheckResult:
    name: str
    status: str
    duration_s: float
    details: str = ""
    command: str | None = None
    artifacts: list[str] = field(default_factory=list)


def _tail(text: str, max_chars: int = 5000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _format_cmd(cmd: list[str]) -> str:
    return " ".join(cmd)


def run_cmd(
    name: str,
    cmd: list[str],
    *,
    timeout: int = 120,
    warn_only: bool = False,
    pass_patterns: list[str] | None = None,
) -> CheckResult:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        output = "\n".join(
            part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
        )
        status = "PASS" if completed.returncode == 0 else "WARN" if warn_only else "FAIL"
        if completed.returncode == 0 and pass_patterns:
            missing = [pattern for pattern in pass_patterns if pattern not in output]
            if missing:
                status = "WARN" if warn_only else "FAIL"
                output = f"Missing expected output: {missing}\n\n{output}"
        return CheckResult(
            name=name,
            status=status,
            duration_s=time.monotonic() - started,
            details=_tail(output),
            command=_format_cmd(cmd),
        )
    except FileNotFoundError as exc:
        return CheckResult(
            name=name,
            status="SKIP" if warn_only else "FAIL",
            duration_s=time.monotonic() - started,
            details=str(exc),
            command=_format_cmd(cmd),
        )
    except subprocess.TimeoutExpired as exc:
        output = "\n".join(
            part for part in ((exc.stdout or "").strip(), (exc.stderr or "").strip()) if part
        )
        return CheckResult(
            name=name,
            status="WARN" if warn_only else "FAIL",
            duration_s=time.monotonic() - started,
            details=f"Timed out after {timeout}s\n\n{_tail(output)}",
            command=_format_cmd(cmd),
        )


def http_request(method: str, url: str, body: bytes | None = None) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def check_health(base_url: str) -> CheckResult:
    started = time.monotonic()
    try:
        status, text = http_request("GET", f"{base_url}/health")
        payload = json.loads(text)
        ok = status == 200 and payload.get("status") == "ok"
        return CheckResult(
            name="live health endpoint",
            status="PASS" if ok else "FAIL",
            duration_s=time.monotonic() - started,
            details=json.dumps(payload, ensure_ascii=False),
        )
    except Exception as exc:
        return CheckResult(
            name="live health endpoint",
            status="FAIL",
            duration_s=time.monotonic() - started,
            details=str(exc),
        )


def check_live_api_probe(base_url: str) -> CheckResult:
    started = time.monotonic()
    probes = [
        ("GET", "/", {200}),
        ("GET", "/scripts", {200}),
        ("GET", "/contacts", {200}),
        ("GET", "/campaigns", {200}),
        ("GET", "/analytics/dashboard", {200}),
        ("GET", "/campaigns/not-a-uuid", {400, 422}),
        ("POST", "/contacts", {400, 422}),
    ]
    rows = []
    failures = []
    for method, path, expected in probes:
        body = b"{bad json" if method == "POST" else None
        status, text = http_request(method, f"{base_url}{path}", body=body)
        rows.append(f"{method} {path}: {status}")
        if status not in expected:
            failures.append(f"{method} {path}: expected {sorted(expected)}, got {status}")
            rows.append(_tail(text, 1000))

    return CheckResult(
        name="live API smoke and validation probe",
        status="PASS" if not failures else "FAIL",
        duration_s=time.monotonic() - started,
        details="\n".join(rows + failures),
    )


def check_docker_logs(since: str) -> CheckResult:
    started = time.monotonic()
    cmd = ["docker", "compose", "logs", f"--since={since}", "api"]
    completed = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    output = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    )
    if completed.returncode != 0:
        return CheckResult(
            name="Docker API log scan",
            status="SKIP",
            duration_s=time.monotonic() - started,
            details=_tail(output),
            command=_format_cmd(cmd),
        )

    severe_patterns = [
        "Traceback",
        "MissingGreenlet",
        "process_campaigns job failed",
        "ERROR |",
    ]
    warning_patterns = [
        "PEER_ID_INVALID",
        "Unable to connect due to network issues",
    ]
    severe_hits = [line for line in output.splitlines() if any(p in line for p in severe_patterns)]
    warning_hits = [line for line in output.splitlines() if any(p in line for p in warning_patterns)]
    details = [
        f"Scanned logs since {since}",
        f"Severe hits: {len(severe_hits)}",
        f"Warning hits: {len(warning_hits)}",
    ]
    if severe_hits:
        details.extend(["", "Severe log lines:", *_tail("\n".join(severe_hits)).splitlines()])
    if warning_hits:
        details.extend(["", "Warning log lines:", *_tail("\n".join(warning_hits), 2500).splitlines()])

    return CheckResult(
        name="Docker API log scan",
        status="FAIL" if severe_hits else "WARN" if warning_hits else "PASS",
        duration_s=time.monotonic() - started,
        details="\n".join(details),
        command=_format_cmd(cmd),
    )


def check_db_snapshot() -> CheckResult:
    sql = (
        "select 'telegram_accounts' as metric, count(*)::text as value from telegram_accounts "
        "union all select 'ready_accounts', count(*)::text from telegram_accounts "
        "where status in ('ready','active') and session_string is not null "
        "union all select 'running_campaigns', count(*)::text from campaigns where status='running' "
        "union all select 'pending_campaign_contacts', count(*)::text from campaign_contacts where status='pending' "
        "union all select 'invalid_peer_campaign_contacts', count(*)::text "
        "from campaign_contacts where status='invalid_peer';"
    )
    return run_cmd(
        "live DB campaign/account snapshot",
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "sales",
            "-d",
            "ai_sales",
            "-c",
            sql,
        ],
        timeout=60,
        warn_only=True,
    )


def run_dialogue_lab(lead_id: int) -> CheckResult:
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "api",
        "python",
        "scripts/dialogue_lab.py",
        "--lead-id",
        str(lead_id),
    ]
    result = run_cmd(
        "autonomous dialogue lab",
        cmd,
        timeout=240,
        pass_patterns=["Dialogue lab finished:", "0 with issues"],
    )
    result.artifacts.append("scripts/.dialogue-lab/latest.md")
    return result


def run_targeted_pytest() -> CheckResult:
    return run_cmd(
        "targeted behavioral pytest suite",
        [
            ".venv/bin/pytest",
            "tests/test_bots_admin_bot.py",
            "tests/test_bots_inbound_listener.py",
            "tests/test_inbound_fallback.py",
            "tests/test_core_scheduler.py",
            "tests/test_flood_wait.py",
            "-q",
        ],
        timeout=180,
    )


def run_static_checks() -> CheckResult:
    cmd = (
        ".venv/bin/flake8 app/ scripts/dialogue_lab.py scripts/qa_audit.py "
        "--max-line-length=120 --extend-ignore=E203,W503"
    )
    return run_cmd(
        "static QA checks",
        ["bash", "-lc", cmd],
        timeout=120,
    )


def run_full_pytest() -> CheckResult:
    return run_cmd("full pytest suite", [".venv/bin/pytest", "tests/", "-q"], timeout=360)


def write_report(results: list[CheckResult], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1

    lines = [
        "# Autonomous QA Audit",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
        f"- PASS: {counts.get('PASS', 0)}",
        f"- WARN: {counts.get('WARN', 0)}",
        f"- FAIL: {counts.get('FAIL', 0)}",
        f"- SKIP: {counts.get('SKIP', 0)}",
        "",
    ]

    for result in results:
        lines.extend(
            [
                f"## {result.status}: {result.name}",
                "",
                f"Duration: {result.duration_s:.1f}s",
            ]
        )
        if result.command:
            lines.extend(["", "Command:", "", "```bash", result.command, "```"])
        if result.artifacts:
            lines.extend(["", "Artifacts:"])
            lines.extend(f"- {artifact}" for artifact in result.artifacts)
        if result.details:
            lines.extend(["", "Details:", "", "```text", result.details, "```"])
        lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run safe autonomous QA audit checks.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--lead-id", type=int, default=1018688845)
    parser.add_argument("--logs-since", default="15m")
    parser.add_argument("--full", action="store_true", help="Also run the full pytest suite.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = [
        run_cmd(
            "Docker Compose availability",
            ["docker", "compose", "ps"],
            timeout=30,
            warn_only=True,
        ),
        check_health(args.base_url),
        check_live_api_probe(args.base_url),
        check_db_snapshot(),
        check_docker_logs(args.logs_since),
        run_dialogue_lab(args.lead_id),
        run_targeted_pytest(),
        run_static_checks(),
    ]
    if args.full:
        results.append(run_full_pytest())

    write_report(results, args.output)
    print(f"QA audit finished. Report: {args.output}")
    for result in results:
        print(f"{result.status:4} {result.name} ({result.duration_s:.1f}s)")

    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
