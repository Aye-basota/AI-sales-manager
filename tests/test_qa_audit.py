from __future__ import annotations

import subprocess

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
