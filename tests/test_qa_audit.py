from __future__ import annotations

import subprocess
import urllib.error
from types import SimpleNamespace

import pytest
from scripts import qa_audit


def _fake_log_run(stdout: str):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=stdout, stderr="")

    return run


def test_docker_log_scan_treats_transient_telegram_timeout_as_warning(monkeypatch):
    log_output = (
        "ai-sales-api  | 2026-07-10 11:21:19 | ERROR | aiogram.dispatcher | "
        "Failed to fetch updates - TelegramNetworkError: HTTP Client says - Request timeout error\n"
        "ai-sales-api  | 2026-07-10 11:21:31 | INFO | aiogram.dispatcher | "
        "Connection established (tryings = 1, bot id = 123)"
    )
    monkeypatch.setattr(qa_audit.subprocess, "run", _fake_log_run(log_output))

    result = qa_audit.check_docker_logs("5m")

    assert result.status == "WARN"
    assert "Severe hits: 0" in result.details
    assert "Warning hits: 1" in result.details


def test_docker_log_scan_fails_on_application_errors(monkeypatch):
    log_output = (
        "ai-sales-api  | 2026-07-10 11:21:19 | ERROR | app.core.scheduler | "
        "process_campaigns job failed"
    )
    monkeypatch.setattr(qa_audit.subprocess, "run", _fake_log_run(log_output))

    result = qa_audit.check_docker_logs("5m")

    assert result.status == "FAIL"
    assert "Severe hits: 1" in result.details


def test_qa_audit_small_helpers():
    assert qa_audit._tail("abcdef", max_chars=3) == "def"
    assert qa_audit._decode_output(None) == ""
    assert qa_audit._decode_output(b"\xd0\xbf") == "п"
    assert qa_audit._decode_output("text") == "text"
    assert qa_audit._format_cmd(["pytest", "-q"]) == "pytest -q"

    qa_audit._require_http_url("http://localhost:8000")
    qa_audit._require_http_url("https://example.test")
    with pytest.raises(ValueError, match="Only absolute"):
        qa_audit._require_http_url("file:///etc/passwd")


def test_run_cmd_handles_success_failure_missing_patterns_and_missing_binary(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(qa_audit.subprocess, "run", fake_run)
    result = qa_audit.run_cmd("cmd", ["tool"], pass_patterns=["ok"])
    assert result.status == "PASS"
    assert result.command == "tool"

    result = qa_audit.run_cmd("cmd", ["tool"], pass_patterns=["missing"])
    assert result.status == "FAIL"
    assert "Missing expected output" in result.details

    def failing_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 2, stdout="", stderr="bad")

    monkeypatch.setattr(qa_audit.subprocess, "run", failing_run)
    assert qa_audit.run_cmd("cmd", ["tool"]).status == "FAIL"
    assert qa_audit.run_cmd("cmd", ["tool"], warn_only=True).status == "WARN"

    def missing_run(*args, **kwargs):
        raise FileNotFoundError("no such tool")

    monkeypatch.setattr(qa_audit.subprocess, "run", missing_run)
    assert qa_audit.run_cmd("cmd", ["tool"], warn_only=True).status == "SKIP"


def test_run_cmd_handles_timeout(monkeypatch):
    def timeout_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=1,
            output=b"stdout",
            stderr=b"stderr",
        )

    monkeypatch.setattr(qa_audit.subprocess, "run", timeout_run)

    result = qa_audit.run_cmd("cmd", ["tool"], timeout=1)

    assert result.status == "FAIL"
    assert "Timed out after 1s" in result.details
    assert "stdout" in result.details
    assert "stderr" in result.details


def test_http_request_and_health_checks(monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"status":"ok"}'

    monkeypatch.setattr(qa_audit.urllib.request, "urlopen", lambda request, timeout: FakeResponse())

    assert qa_audit.http_request("GET", "http://localhost/health") == (
        200,
        '{"status":"ok"}',
    )
    assert qa_audit.check_health("http://localhost").status == "PASS"

    class FakeHTTPError(urllib.error.HTTPError):
        def read(self):
            return b'{"detail":"bad"}'

    def raise_http_error(request, timeout):
        raise FakeHTTPError(request.full_url, 400, "Bad", hdrs=None, fp=None)

    monkeypatch.setattr(qa_audit.urllib.request, "urlopen", raise_http_error)
    assert qa_audit.http_request("GET", "http://localhost/bad") == (
        400,
        '{"detail":"bad"}',
    )

    monkeypatch.setattr(qa_audit, "http_request", lambda *_args, **_kwargs: (500, "{}"))
    assert qa_audit.check_health("http://localhost").status == "FAIL"


def test_live_api_probe_marks_unexpected_status_as_failure(monkeypatch):
    statuses = {
        ("GET", "http://localhost/"): (200, "ok"),
        ("GET", "http://localhost/scripts"): (200, "ok"),
        ("GET", "http://localhost/contacts"): (500, "boom"),
        ("GET", "http://localhost/campaigns"): (200, "ok"),
        ("GET", "http://localhost/analytics/dashboard"): (200, "ok"),
        ("GET", "http://localhost/campaigns/not-a-uuid"): (422, "ok"),
        ("POST", "http://localhost/contacts"): (400, "ok"),
    }

    def fake_http(method, url, body=None):
        return statuses[(method, url)]

    monkeypatch.setattr(qa_audit, "http_request", fake_http)

    result = qa_audit.check_live_api_probe("http://localhost")

    assert result.status == "FAIL"
    assert "GET /contacts: expected [200], got 500" in result.details


def test_db_and_lab_wrappers_attach_commands_and_artifacts(monkeypatch):
    calls = []

    def fake_run_cmd(name, cmd, **kwargs):
        calls.append((name, cmd, kwargs))
        return qa_audit.CheckResult(name=name, status="PASS", duration_s=0.1)

    monkeypatch.setattr(qa_audit, "run_cmd", fake_run_cmd)

    assert qa_audit.check_db_snapshot().status == "PASS"
    dialogue = qa_audit.run_dialogue_lab(123)
    admin = qa_audit.run_admin_ux_lab()
    targeted = qa_audit.run_targeted_pytest()
    static = qa_audit.run_static_checks()
    full = qa_audit.run_full_pytest()

    assert "scripts/.dialogue-lab/latest.md" in dialogue.artifacts
    assert "scripts/.admin-ux-lab/latest.md" in admin.artifacts
    assert targeted.name == "targeted behavioral pytest suite"
    assert static.name == "static QA checks"
    assert full.name == "full pytest suite"
    assert any(call[0] == "live DB campaign/account snapshot" for call in calls)


def test_write_report_and_parse_args(tmp_path, monkeypatch):
    output = tmp_path / "qa.md"
    qa_audit.write_report(
        [
            qa_audit.CheckResult(
                name="check",
                status="PASS",
                duration_s=1.23,
                details="details",
                command="pytest",
                artifacts=["artifact.md"],
            )
        ],
        output,
    )

    text = output.read_text(encoding="utf-8")
    assert "# Autonomous QA Audit" in text
    assert "PASS: check" in text
    assert "artifact.md" in text

    monkeypatch.setattr(
        "sys.argv",
        [
            "qa_audit.py",
            "--base-url",
            "http://api.test",
            "--lead-id",
            "42",
            "--logs-since",
            "1h",
            "--full",
            "--output",
            str(output),
        ],
    )
    args = qa_audit.parse_args()
    assert args.base_url == "http://api.test"
    assert args.lead_id == 42
    assert args.logs_since == "1h"
    assert args.full is True
    assert args.output == output


def test_main_writes_report_and_returns_failure_when_any_check_fails(tmp_path, monkeypatch):
    output = tmp_path / "qa.md"
    monkeypatch.setattr(
        qa_audit,
        "parse_args",
        lambda: SimpleNamespace(
            base_url="http://localhost",
            lead_id=1,
            logs_since="5m",
            full=True,
            output=output,
        ),
    )
    monkeypatch.setattr(
        qa_audit,
        "run_cmd",
        lambda name, cmd, **kwargs: qa_audit.CheckResult(name=name, status="PASS", duration_s=0),
    )
    monkeypatch.setattr(
        qa_audit,
        "check_health",
        lambda _base_url: qa_audit.CheckResult("health", "PASS", 0),
    )
    monkeypatch.setattr(
        qa_audit,
        "check_live_api_probe",
        lambda _base_url: qa_audit.CheckResult("probe", "PASS", 0),
    )
    monkeypatch.setattr(
        qa_audit,
        "check_db_snapshot",
        lambda: qa_audit.CheckResult("db", "WARN", 0),
    )
    monkeypatch.setattr(
        qa_audit,
        "check_docker_logs",
        lambda _since: qa_audit.CheckResult("logs", "PASS", 0),
    )
    monkeypatch.setattr(
        qa_audit,
        "run_dialogue_lab",
        lambda _lead_id: qa_audit.CheckResult("dialogue", "PASS", 0),
    )
    monkeypatch.setattr(
        qa_audit,
        "run_admin_ux_lab",
        lambda: qa_audit.CheckResult("admin", "PASS", 0),
    )
    monkeypatch.setattr(
        qa_audit,
        "run_targeted_pytest",
        lambda: qa_audit.CheckResult("targeted", "FAIL", 0),
    )
    monkeypatch.setattr(
        qa_audit,
        "run_static_checks",
        lambda: qa_audit.CheckResult("static", "PASS", 0),
    )
    monkeypatch.setattr(
        qa_audit,
        "run_full_pytest",
        lambda: qa_audit.CheckResult("full", "PASS", 0),
    )

    assert qa_audit.main() == 1
    assert "FAIL: targeted" in output.read_text(encoding="utf-8")
