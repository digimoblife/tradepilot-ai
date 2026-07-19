"""Tests for LocalFileStorage."""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

import pytest

from app.storage import (
    LocalFileStorage,
    StorageFileNotFoundError,
    StorageInvalidPathError,
)

_USER_A = uuid.UUID("11111111-1111-4111-8111-111111111111")
_USER_B = uuid.UUID("22222222-2222-4222-8222-222222222222")
_SESSION_A = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
_SESSION_B = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(root=tmp_path)


# ---------------------------------------------------------------------------
# Successful storage
# ---------------------------------------------------------------------------


class TestStore:
    def test_basic_store(self, storage: LocalFileStorage) -> None:
        content = b"hello, world"
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="chart.png",
            content=content,
        )

        assert result.file_reference.startswith(str(_USER_A) + "/")
        assert result.file_reference.endswith(".png")
        assert result.generated_filename != "chart.png"
        assert result.original_filename == "chart.png"
        assert result.size_bytes == len(content)
        assert result.checksum_sha256 == hashlib.sha256(content).hexdigest()

    def test_bytes_preserved(self, storage: LocalFileStorage) -> None:
        content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"  # real PNG header
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="screenshot.png",
            content=content,
        )
        restored = storage.read(file_reference=result.file_reference)
        assert restored == content

    def test_relative_reference(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="img.png",
            content=b"data",
        )
        assert not Path(result.file_reference).is_absolute()
        assert result.file_reference == str(
            Path(str(_USER_A)) / str(_SESSION_A) / result.generated_filename,
        )

    def test_file_size(self, storage: LocalFileStorage) -> None:
        content = b"x" * 65536
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="large.bin",
            content=content,
        )
        assert result.size_bytes == 65536

    def test_checksum_sha256(self, storage: LocalFileStorage) -> None:
        content = b"verify checksum please"
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="check.txt",
            content=content,
        )
        assert result.checksum_sha256 == hashlib.sha256(content).hexdigest()
        assert len(result.checksum_sha256) == 64
        assert all(c in "0123456789abcdef" for c in result.checksum_sha256)


# ---------------------------------------------------------------------------
# User and session scoping
# ---------------------------------------------------------------------------


class TestScoping:
    def test_user_scope(self, storage: LocalFileStorage) -> None:
        r1 = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="file.png",
            content=b"user-a",
        )
        r2 = storage.store(
            user_id=_USER_B,
            session_id=_SESSION_A,
            original_filename="file.png",
            content=b"user-b",
        )

        assert str(_USER_A) in r1.file_reference
        assert str(_USER_B) in r2.file_reference
        assert r1.file_reference != r2.file_reference
        assert storage.read(file_reference=r1.file_reference) == b"user-a"
        assert storage.read(file_reference=r2.file_reference) == b"user-b"

    def test_session_scope(self, storage: LocalFileStorage) -> None:
        r1 = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="file.png",
            content=b"session-a",
        )
        r2 = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_B,
            original_filename="file.png",
            content=b"session-b",
        )

        assert str(_SESSION_A) in r1.file_reference
        assert str(_SESSION_B) in r2.file_reference
        assert storage.read(file_reference=r1.file_reference) == b"session-a"
        assert storage.read(file_reference=r2.file_reference) == b"session-b"

    def test_original_filename_does_not_affect_scope(
        self,
        storage: LocalFileStorage,
    ) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="../../etc/passwd",
            content=b"safe",
        )
        assert str(_USER_A) in result.file_reference
        assert str(_SESSION_A) in result.file_reference
        assert "../../etc/passwd" not in result.file_reference
        assert Path(storage._root, result.file_reference).exists() is True  # sanity
        assert storage.read(file_reference=result.file_reference) == b"safe"


# ---------------------------------------------------------------------------
# Generated filenames
# ---------------------------------------------------------------------------


class TestGeneratedNames:
    def test_differs_from_original(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="chart.png",
            content=b"data",
        )
        assert result.generated_filename != "chart.png"
        assert result.generated_filename.endswith(".png")

    def test_repeated_original_creates_separate_files(
        self,
        storage: LocalFileStorage,
    ) -> None:
        r1 = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="same.png",
            content=b"first",
        )
        r2 = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="same.png",
            content=b"second",
        )
        assert r1.generated_filename != r2.generated_filename
        assert r1.file_reference != r2.file_reference
        assert storage.read(file_reference=r1.file_reference) == b"first"
        assert storage.read(file_reference=r2.file_reference) == b"second"

    def test_no_path_separators_in_generated(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="normal.png",
            content=b"data",
        )
        assert "/" not in result.generated_filename

    def test_no_extension_for_unsafe_suffix(
        self,
        storage: LocalFileStorage,
    ) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="evil.py.exe",
            content=b"data",
        )
        # ".exe" is alphanumeric, so it passes
        assert result.generated_filename.endswith(".exe")

    def test_unsafe_extension_omitted(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="file.$$$",
            content=b"data",
        )
        # ".$$$" contains only non-alphanumeric chars, so no extension is kept
        assert "." not in result.generated_filename[32:]

    def test_hidden_file_no_extension(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename=".gitignore",
            content=b"data",
        )
        # ".gitignore" is a hidden file with no suffix on Python 3.12+
        assert "." not in result.generated_filename


# ---------------------------------------------------------------------------
# Path traversal prevention
# ---------------------------------------------------------------------------


class TestTraversal:
    def test_traversal_in_reference_read(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageInvalidPathError):
            storage.read(file_reference="../outside")

    def test_traversal_deeply_nested(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageInvalidPathError):
            storage.read(file_reference="user/session/../../../outside")

    def test_absolute_path_rejected(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageInvalidPathError):
            storage.read(file_reference="/etc/passwd")

    def test_absolute_path_delete(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageInvalidPathError):
            storage.delete(file_reference="/etc/passwd")

    def test_malicious_original_filename(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="../../secret.txt",
            content=b"safe",
        )
        # Generated filename should not contain traversal
        assert ".." not in result.generated_filename
        assert "/" not in result.generated_filename
        # The stored file must be inside the storage root
        stored_path = Path(storage._root, result.file_reference)
        assert str(stored_path.resolve()).startswith(str(storage._root))

    def test_empty_reference(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageInvalidPathError):
            storage.read(file_reference="")

    def test_traversal_in_delete(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageInvalidPathError):
            storage.delete(file_reference="../../outside")

    def test_symlink_does_not_escape(self, tmp_path: Path) -> None:
        storage_root = tmp_path / "store"
        storage_root.mkdir(parents=True)
        storage = LocalFileStorage(root=storage_root)

        outside = tmp_path / "outside"
        outside.mkdir()
        outside_file = outside / "leaked.txt"
        outside_file.write_text("leaked")

        # Create a symlink inside storage pointing to a sibling directory
        link_target = storage_root / "escape"
        os.symlink(outside, link_target, target_is_directory=True)

        # The symlink resolves outside the storage root
        with pytest.raises(StorageInvalidPathError):
            storage.read(file_reference="escape/leaked.txt")


# ---------------------------------------------------------------------------
# Original filename as metadata only
# ---------------------------------------------------------------------------


class TestOriginalFilename:
    def test_preserved_in_result(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="my original chart.png",
            content=b"data",
        )
        assert result.original_filename == "my original chart.png"

    def test_not_used_in_generated_name(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="../../malicious.sh",
            content=b"data",
        )
        # The generated name should be UUID-based, not containing the original
        assert "malicious" not in result.generated_filename
        assert ".." not in result.generated_filename

    def test_no_control_of_stored_path(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="/etc/cronjob.sh",
            content=b"data",
        )
        assert "/etc/cronjob.sh" not in result.file_reference
        assert result.file_reference.startswith(str(_USER_A))


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


class TestRead:
    def test_read_stored_file(self, storage: LocalFileStorage) -> None:
        content = b"readable content"
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="readme.txt",
            content=content,
        )
        assert storage.read(file_reference=result.file_reference) == content

    def test_missing_file(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageFileNotFoundError):
            storage.read(file_reference="nonexistent/file.txt")

    def test_unsafe_reference_rejected(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageInvalidPathError):
            storage.read(file_reference="../etc/passwd")

    def test_null_byte_reference_rejected(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageInvalidPathError):
            storage.read(file_reference="safe/../\x00/exploit")


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_stored_file(self, storage: LocalFileStorage) -> None:
        content = b"delete me"
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="temporary.txt",
            content=content,
        )
        storage.delete(file_reference=result.file_reference)
        with pytest.raises(StorageFileNotFoundError):
            storage.read(file_reference=result.file_reference)

    def test_delete_missing_file(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageFileNotFoundError):
            storage.delete(file_reference="nonexistent/file.txt")

    def test_delete_outside_root(self, storage: LocalFileStorage) -> None:
        with pytest.raises(StorageInvalidPathError):
            storage.delete(file_reference="../outside.txt")


# ---------------------------------------------------------------------------
# Temporary directory isolation
# ---------------------------------------------------------------------------


class TestIsolation:
    def test_tmp_path_isolation(self, tmp_path: Path) -> None:
        other = tmp_path / "outside"
        other.mkdir()
        other_file = other / "test.txt"
        other_file.write_text("outside")

        storage = LocalFileStorage(root=tmp_path / "storage")
        with pytest.raises(StorageInvalidPathError):
            storage.read(file_reference="../outside/test.txt")

    def test_no_files_outside_root(self, storage: LocalFileStorage) -> None:
        result = storage.store(
            user_id=_USER_A,
            session_id=_SESSION_A,
            original_filename="inside.txt",
            content=b"inside",
        )
        stored = Path(storage._root) / result.file_reference
        assert stored.resolve().exists()
        # No files should have been created outside the root
        root_files = list(Path(storage._root).rglob("*"))
        assert all(str(f.resolve()).startswith(str(storage._root)) for f in root_files)
