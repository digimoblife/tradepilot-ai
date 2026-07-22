"""Tests for shell backup/restore scripts (TP-1603).

Uses temporary directories and fake pg_dump/pg_restore binaries to
verify invocation, timestamping, configurable destinations, error
handling, and secret isolation.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterator

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scripts"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_home() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def fake_pg_dump(tmp_home: Path) -> Path:
    """Create a fake pg_dump that records its invocation and creates the output file."""
    path = tmp_home / "pg_dump"
    path.write_text(
        "#!/usr/bin/env bash\n"
        'echo "FAKE_DUMP $@"\n'
        'for arg in "$@"; do\n'
        '    case "$arg" in\n'
        "        --file=*)\n"
        '            touch "${arg#--file=}"\n'
        "            ;;\n"
        "    esac\n"
        "done\n"
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture
def fake_pg_restore(tmp_home: Path) -> Path:
    """Create a fake pg_restore that records its invocation and succeeds."""
    path = tmp_home / "pg_restore"
    path.write_text('#!/usr/bin/env bash\necho "FAKE_RESTORE $@"\n')
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture
def fake_pg_dump_fail(tmp_home: Path) -> Path:
    """Create a fake pg_dump that always fails."""
    path = tmp_home / "pg_dump"
    path.write_text('#!/usr/bin/env bash\necho "FAKE_DUMP_FAILED" >&2\nexit 1\n')
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture
def fake_pg_restore_fail(tmp_home: Path) -> Path:
    """Create a fake pg_restore that always fails."""
    path = tmp_home / "pg_restore"
    path.write_text('#!/usr/bin/env bash\necho "FAKE_RESTORE_FAILED" >&2\nexit 1\n')
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture
def env(tmp_home: Path, fake_pg_dump: Path, fake_pg_restore: Path) -> dict[str, str]:
    """Environment with PATH pointing at the fake binaries."""
    new_env = {
        **os.environ,
        "PATH": f"{tmp_home}:/bin:/usr/bin",
        "BACKUP_DIR": str(tmp_home / "backups"),
    }
    return new_env


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


# ===================================================================
# 1. Database backup
# ===================================================================


class TestDatabaseBackup:
    def test_timestamped_filename(self, env: dict[str, str]) -> None:
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "backup_database.sh")],
            env=env,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        backup_dir = Path(env["BACKUP_DIR"])
        files = list(backup_dir.glob("tradepilot_db_*.dump"))
        assert len(files) >= 1
        name = files[0].name
        assert name.startswith("tradepilot_db_")
        assert name.endswith(".dump")
        # YYYYMMDD_HHMMSS
        assert len(name) == len("tradepilot_db_YYYYMMDD_HHMMSS.dump")

    def test_configurable_destination(self, env: dict[str, str]) -> None:
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "backup_database.sh")],
            env=env,
        )
        assert result.returncode == 0
        assert Path(env["BACKUP_DIR"]).exists()

    def test_pg_dump_invocation(self, env: dict[str, str]) -> None:
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "backup_database.sh")],
            env=env,
        )
        assert result.returncode == 0
        assert "FAKE_DUMP" in result.stdout
        # Must contain --format=custom
        assert "--format=custom" in result.stdout

    def test_pg_dump_failure_propagates(self, tmp_home: Path, fake_pg_dump_fail: Path) -> None:
        env = {
            **os.environ,
            "PATH": f"{tmp_home}:/bin:/usr/bin",
            "BACKUP_DIR": str(tmp_home / "backups"),
        }
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "backup_database.sh")],
            env=env,
        )
        assert result.returncode != 0

    def test_no_embedded_credentials(self) -> None:
        content = (Path(_SCRIPTS_DIR) / "backup_database.sh").read_text()
        assert "PGPASSWORD=" not in content

    def test_datetime_url_support(self, env: dict[str, str]) -> None:
        env["DATABASE_URL"] = "postgresql://u:p@h:9999/db"
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "backup_database.sh")],
            env=env,
        )
        assert result.returncode == 0
        # The DATABASE_URL should appear in the pg_dump args
        assert "postgresql://u:p@h:9999/db" in result.stdout


# ===================================================================
# 2. Storage backup
# ===================================================================


class TestStorageBackup:
    def test_timestamped_archive(self, env: dict[str, str], tmp_home: Path) -> None:
        storage_dir = tmp_home / "storage" / "evidence"
        storage_dir.mkdir(parents=True)
        (storage_dir / "test.png").write_text("fake-png")
        env["STORAGE_DIR"] = str(storage_dir)
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "backup_storage.sh")],
            env=env,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        files = list(Path(env["BACKUP_DIR"]).glob("tradepilot_storage_*.tar.gz"))
        assert len(files) >= 1
        name = files[0].name
        assert name.startswith("tradepilot_storage_")
        assert name.endswith(".tar.gz")

    def test_missing_source_fails(self, env: dict[str, str]) -> None:
        env["STORAGE_DIR"] = "/nonexistent/directory"
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "backup_storage.sh")],
            env=env,
        )
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_configurable_destination(self, env: dict[str, str], tmp_home: Path) -> None:
        storage_dir = tmp_home / "storage" / "evidence"
        storage_dir.mkdir(parents=True)
        (storage_dir / "a.png").write_text("png")
        env["STORAGE_DIR"] = str(storage_dir)
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "backup_storage.sh")],
            env=env,
        )
        assert result.returncode == 0
        assert Path(env["BACKUP_DIR"]).exists()

    def test_no_embedded_credentials(self) -> None:
        content = (Path(_SCRIPTS_DIR) / "backup_storage.sh").read_text()
        assert "PGPASSWORD=" not in content


# ===================================================================
# 3. Database restore
# ===================================================================


class TestDatabaseRestore:
    def test_restore_succeeds(self, env: dict[str, str], tmp_home: Path) -> None:
        backup_file = tmp_home / "test.dump"
        backup_file.write_text("fake-dump-content")
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "restore_database.sh"), str(backup_file)],
            env=env,
        )
        assert result.returncode == 0
        assert "FAKE_RESTORE" in result.stdout

    def test_missing_backup_file_rejected(self, env: dict[str, str]) -> None:
        result = _run(
            [
                "bash",
                str(_SCRIPTS_DIR / "restore_database.sh"),
                "/nonexistent/backup.dump",
            ],
            env=env,
        )
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_empty_backup_file_rejected(self, env: dict[str, str], tmp_home: Path) -> None:
        backup_file = tmp_home / "empty.dump"
        backup_file.write_text("")
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "restore_database.sh"), str(backup_file)],
            env=env,
        )
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_restore_failure_propagates(self, tmp_home: Path, fake_pg_restore_fail: Path) -> None:
        backup_file = tmp_home / "test.dump"
        backup_file.write_text("content")
        env = {
            **os.environ,
            "PATH": f"{tmp_home}:/bin:/usr/bin",
            "BACKUP_DIR": str(tmp_home / "backups"),
        }
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "restore_database.sh"), str(backup_file)],
            env=env,
        )
        assert result.returncode != 0

    def test_missing_argument(self, env: dict[str, str]) -> None:
        result = _run(
            ["bash", str(_SCRIPTS_DIR / "restore_database.sh")],
            env=env,
        )
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_no_embedded_credentials(self) -> None:
        content = (Path(_SCRIPTS_DIR) / "restore_database.sh").read_text()
        assert "PGPASSWORD=" not in content
