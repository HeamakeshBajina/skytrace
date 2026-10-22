
from pathlib import Path

import pytest

from scripts.fetch_satellites import save_data_pair


def test_save_data_pair_writes_both_files(tmp_path):
    tle_path = tmp_path / "data.tle"
    metadata_path = tmp_path / "data.json"

    save_data_pair(
        tle_path,
        metadata_path,
        "TLE test content\n",
        '{"record_count": 1}',
    )

    assert tle_path.read_text(encoding="utf-8") == "TLE test content\n"
    assert metadata_path.read_text(encoding="utf-8") == '{"record_count": 1}'
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob("*.bak"))


def test_failed_temporary_write_preserves_existing_destinations(
    tmp_path, monkeypatch
):
    tle_path = tmp_path / "data.tle"
    metadata_path = tmp_path / "data.json"

    tle_path.write_text("original TLE\n", encoding="utf-8")
    metadata_path.write_text("original metadata\n", encoding="utf-8")

    original_write_text = Path.write_text

    def fail_metadata_temp_write(self, *args, **kwargs):
        if self.name.startswith("data.json.") and self.name.endswith(".tmp"):
            raise OSError("simulated metadata write failure")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_metadata_temp_write)

    with pytest.raises(OSError, match="simulated metadata write failure"):
        save_data_pair(
            tle_path,
            metadata_path,
            "replacement TLE\n",
            "replacement metadata\n",
        )

    assert tle_path.read_text(encoding="utf-8") == "original TLE\n"
    assert metadata_path.read_text(encoding="utf-8") == "original metadata\n"
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob("*.bak"))


def test_second_replace_failure_restores_both_original_files(
    tmp_path, monkeypatch
):
    tle_path = tmp_path / "data.tle"
    metadata_path = tmp_path / "data.json"

    tle_path.write_text("original TLE\n", encoding="utf-8")
    metadata_path.write_text("original metadata\n", encoding="utf-8")

    original_replace = Path.replace

    def fail_metadata_install(self, target):
        if self.name.startswith("data.json.") and self.name.endswith(".tmp"):
            raise OSError("simulated second replacement failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_metadata_install)

    with pytest.raises(OSError, match="simulated second replacement failure"):
        save_data_pair(
            tle_path,
            metadata_path,
            "replacement TLE\n",
            "replacement metadata\n",
        )

    assert tle_path.read_text(encoding="utf-8") == "original TLE\n"
    assert metadata_path.read_text(encoding="utf-8") == "original metadata\n"
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob("*.bak"))


def test_second_replace_failure_removes_new_files_when_no_originals_exist(
    tmp_path, monkeypatch
):
    tle_path = tmp_path / "data.tle"
    metadata_path = tmp_path / "data.json"

    original_replace = Path.replace

    def fail_metadata_install(self, target):
        if self.name.startswith("data.json.") and self.name.endswith(".tmp"):
            raise OSError("simulated second replacement failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_metadata_install)

    with pytest.raises(OSError, match="simulated second replacement failure"):
        save_data_pair(
            tle_path,
            metadata_path,
            "new TLE\n",
            "new metadata\n",
        )

    assert not tle_path.exists()
    assert not metadata_path.exists()
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob("*.bak"))


def test_failed_rollback_reports_error_and_preserves_backup(
    tmp_path, monkeypatch
):
    tle_path = tmp_path / "data.tle"
    metadata_path = tmp_path / "data.json"

    tle_path.write_text("original TLE\n", encoding="utf-8")
    metadata_path.write_text("original metadata\n", encoding="utf-8")

    original_replace = Path.replace
    restore_failed = False

    def simulate_install_and_restore_failures(self, target):
        nonlocal restore_failed

        # Simulate failure installing the new metadata.
        if self.name.startswith("data.json.") and self.name.endswith(".tmp"):
            raise OSError("simulated metadata installation failure")

        # Simulate failure restoring the original TLE from its backup.
        if self.name.startswith("data.tle.") and self.name.endswith(".bak"):
            restore_failed = True
            raise OSError("simulated TLE restoration failure")

        return original_replace(self, target)

    monkeypatch.setattr(
        Path, "replace", simulate_install_and_restore_failures
    )

    with pytest.raises(RuntimeError, match="rollback was incomplete"):
        save_data_pair(
            tle_path,
            metadata_path,
            "replacement TLE\n",
            "replacement metadata\n",
        )

    assert restore_failed
    assert metadata_path.read_text(encoding="utf-8") == "original metadata\n"

    # The original TLE remains recoverable in the backup.
    backups = list(tmp_path.glob("data.tle.*.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "original TLE\n"