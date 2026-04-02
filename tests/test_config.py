"""Tests for config read/write operations."""

import pytest

from buddy_picker import config


@pytest.fixture()
def fake_claude_json(tmp_path, monkeypatch):
    """Redirect CLAUDE_JSON to a temp file."""
    path = tmp_path / ".claude.json"
    monkeypatch.setattr(config, "CLAUDE_JSON", path)
    return path


class TestReadWrite:
    def test_round_trip(self, fake_claude_json):
        data = {"userID": "abc123", "foo": "bar"}
        config.write_config(data)
        assert config.read_config() == data

    def test_read_missing_file(self, fake_claude_json):
        assert config.read_config() == {}


class TestApplyUid:
    def test_creates_backup(self, fake_claude_json):
        original = {"userID": "original-id", "companion": {"name": "TestPet"}}
        config.write_config(original)

        config.apply_uid("new-id")

        cfg = config.read_config()
        assert cfg["userID"] == "new-id"
        assert cfg[config.BACKUP_KEY] == "original-id"
        assert "companion" not in cfg

    def test_does_not_overwrite_backup(self, fake_claude_json):
        original = {
            "userID": "second-id",
            config.BACKUP_KEY: "first-id",
        }
        config.write_config(original)

        config.apply_uid("third-id")

        cfg = config.read_config()
        assert cfg["userID"] == "third-id"
        assert cfg[config.BACKUP_KEY] == "first-id"  # preserved


class TestRestoreUid:
    def test_restores_original(self, fake_claude_json, capsys):
        data = {
            "userID": "modified-id",
            config.BACKUP_KEY: "original-id",
            "companion": {"name": "X"},
        }
        config.write_config(data)

        config.restore_uid()

        cfg = config.read_config()
        assert cfg["userID"] == "original-id"
        assert config.BACKUP_KEY not in cfg
        assert "companion" not in cfg

    def test_no_backup(self, fake_claude_json, capsys):
        config.write_config({"userID": "whatever"})
        config.restore_uid()
        out = capsys.readouterr().out
        assert "No backup" in out
