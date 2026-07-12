"""Regression tests for local utility scripts.

The scripts are mostly operator-facing entry points, so tests keep external
systems mocked and verify parsing, branching, and object construction.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import MockResult


class AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, result=None):
        self.result = result or MockResult([])
        self.add = MagicMock()
        self.commit = AsyncMock()
        self.flush = AsyncMock()
        self.execute = AsyncMock(return_value=self.result)


@pytest.mark.asyncio
async def test_admin_ux_lab_main_writes_report(tmp_path, monkeypatch):
    from scripts import admin_ux_lab

    output = tmp_path / "admin-ux-lab.md"
    monkeypatch.setattr(admin_ux_lab, "OUTPUT", output)

    exit_code = await admin_ux_lab.main()

    assert exit_code == 0
    report = output.read_text(encoding="utf-8")
    assert "# Admin UX Lab" in report
    assert "PASS: start screen asks for language" in report
    assert "FAIL:" not in report


def test_generate_session_string_reads_cli_env_and_prompt_values(monkeypatch):
    from scripts import generate_session_string as script

    monkeypatch.setattr("sys.argv", ["generate_session_string.py", "--api-id", "123"])
    assert script.parse_args().api_id == 123

    monkeypatch.setenv("TELEGRAM_API_ID", "456")
    assert script._read_api_id(None) == 456

    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt: "789")
    assert script._read_api_id(None) == 789

    assert script._read_api_hash("hash-from-arg") == "hash-from-arg"
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash-from-env")
    assert script._read_api_hash(None) == "hash-from-env"

    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "hash-from-prompt")
    assert script._read_api_hash(None) == "hash-from-prompt"


@pytest.mark.asyncio
async def test_generate_session_wait_for_file_reads_value_and_removes_file(
    tmp_path, monkeypatch
):
    from scripts import generate_session

    code_file = tmp_path / "telegram_code.txt"
    code_file.write_text("12345\n", encoding="utf-8")
    monkeypatch.setattr(generate_session, "INPUT_DIR", tmp_path)
    monkeypatch.setattr(generate_session, "TIMEOUT", 1)

    value = await generate_session.wait_for_file(code_file, "code")

    assert value == "12345"
    assert not code_file.exists()


@pytest.mark.asyncio
async def test_generate_session_patched_ainput_routes_code_and_password(monkeypatch):
    from scripts import generate_session

    calls = []

    async def fake_wait(path, label):
        calls.append((path, label))
        return label

    monkeypatch.setattr(generate_session, "wait_for_file", fake_wait)

    assert await generate_session.patched_ainput("Code:") == "код подтверждения Telegram"
    assert await generate_session.patched_ainput("Password:", hide=True) == "пароль 2FA"
    assert calls[0][0] == generate_session.CODE_FILE
    assert calls[1][0] == generate_session.TWOFA_FILE


@pytest.mark.asyncio
async def test_generate_session_main_exits_when_required_env_is_missing(monkeypatch):
    from scripts import generate_session

    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    monkeypatch.delenv("SELLER_PHONE", raising=False)

    with pytest.raises(SystemExit) as exc:
        await generate_session.main()

    assert exc.value.code == 1


@pytest.mark.asyncio
async def test_generate_session_main_exports_session_string(monkeypatch):
    from scripts import generate_session

    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("SELLER_PHONE", "+79990000000")

    fake_app = AsyncMock()
    fake_app.export_session_string = AsyncMock(return_value="session-string")

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return fake_app

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(generate_session, "Client", FakeClient)

    await generate_session.main()

    fake_app.export_session_string.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_contacts_imports_csv_records(tmp_path, monkeypatch):
    from scripts import import_contacts

    csv_file = tmp_path / "contacts.csv"
    csv_file.write_text("first_name,telegram_user_id\nAlice,123\n", encoding="utf-8")
    session = FakeSession()

    monkeypatch.setattr(
        import_contacts,
        "parse_csv",
        lambda data: [{"first_name": "Alice", "telegram_user_id": 123}],
    )
    monkeypatch.setattr(import_contacts, "AsyncSessionLocal", lambda: AsyncContext(session))

    await import_contacts.import_file(str(csv_file))

    assert session.add.call_count == 1
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_contacts_imports_excel_and_rejects_other_suffix(
    tmp_path, monkeypatch
):
    from scripts import import_contacts

    excel_file = tmp_path / "contacts.xlsx"
    excel_file.write_bytes(b"excel")
    session = FakeSession()
    monkeypatch.setattr(import_contacts, "parse_excel", lambda data: [])
    monkeypatch.setattr(import_contacts, "AsyncSessionLocal", lambda: AsyncContext(session))

    await import_contacts.import_file(str(excel_file))
    session.commit.assert_awaited_once()

    txt_file = tmp_path / "contacts.txt"
    txt_file.write_text("bad", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        await import_contacts.import_file(str(txt_file))
    assert exc.value.code == 1


def test_seed_demo_data_factories_create_consistent_demo_objects(monkeypatch):
    from scripts import seed_demo_data

    monkeypatch.setattr(seed_demo_data.random, "randint", lambda low, high: 77)

    script = seed_demo_data._make_demo_script()
    contacts = seed_demo_data._make_demo_contacts()
    campaign = seed_demo_data._make_demo_campaign(script, contacts)

    assert script.name == "Demo B2B Outreach Script"
    assert len(contacts) == len(seed_demo_data.DEMO_COMPANIES)
    assert {contact.icp_score for contact in contacts} == {77}
    assert campaign.name == "Demo Campaign"
    assert campaign.total_contacts == len(contacts)


@pytest.mark.asyncio
async def test_warmup_account_rejects_invalid_uuid(caplog):
    from scripts import warmup_accounts

    with caplog.at_level("ERROR"):
        await warmup_accounts.warmup_account("not-a-uuid")

    assert "Invalid UUID" in caplog.text


@pytest.mark.asyncio
async def test_warmup_account_handles_missing_and_existing_account(monkeypatch, caplog):
    from scripts import warmup_accounts

    missing_session = FakeSession(MockResult([]))
    monkeypatch.setattr(
        warmup_accounts,
        "AsyncSessionLocal",
        lambda: AsyncContext(missing_session),
    )

    with caplog.at_level("ERROR"):
        await warmup_accounts.warmup_account("00000000-0000-0000-0000-000000000001")
    assert "not found" in caplog.text

    account = SimpleNamespace(status="ready")
    existing_session = FakeSession(MockResult([account]))
    monkeypatch.setattr(
        warmup_accounts,
        "AsyncSessionLocal",
        lambda: AsyncContext(existing_session),
    )

    await warmup_accounts.warmup_account("00000000-0000-0000-0000-000000000001")

    assert account.status == "warming"
    existing_session.commit.assert_awaited_once()
