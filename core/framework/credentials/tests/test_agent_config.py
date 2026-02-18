"""Tests for agent-level credential configuration."""

from pathlib import Path
import json
import tempfile

import pytest

from framework.credentials.agent_config import (
    AgentCredentialConfig,
    get_integration_id_for_agent,
    set_integration_id_for_agent,
)


class TestAgentCredentialConfig:
    """Tests for AgentCredentialConfig class."""

    def test_load_empty_config(self, tmp_path: Path):
        """Load config from directory with no credentials.json."""
        config = AgentCredentialConfig.load(tmp_path)

        assert config.agent_path == tmp_path
        assert config.mappings == {}

    def test_load_existing_config(self, tmp_path: Path):
        """Load config from directory with existing credentials.json."""
        config_data = {
            "mappings": {
                "google": "Z29vZ2xlOmV4YW1wbGVAZ21haWwuY29t",
                "hubspot": "aHVic3BvdDp3b3JrQGNvbXBhbnkuY29t",
            }
        }
        config_path = tmp_path / "credentials.json"
        config_path.write_text(json.dumps(config_data))

        config = AgentCredentialConfig.load(tmp_path)

        assert config.mappings == config_data["mappings"]
        assert config.get_integration_id("google") == "Z29vZ2xlOmV4YW1wbGVAZ21haWwuY29t"
        assert config.get_integration_id("hubspot") == "aHVic3BvdDp3b3JrQGNvbXBhbnkuY29t"

    def test_save_config(self, tmp_path: Path):
        """Save config to credentials.json."""
        config = AgentCredentialConfig(agent_path=tmp_path)
        config.set_integration_id("google", "test-integration-id")
        config.save()

        config_path = tmp_path / "credentials.json"
        assert config_path.exists()

        saved_data = json.loads(config_path.read_text())
        assert saved_data == {"mappings": {"google": "test-integration-id"}}

    def test_get_integration_id_not_found(self, tmp_path: Path):
        """get_integration_id returns None for unmapped provider."""
        config = AgentCredentialConfig.load(tmp_path)

        assert config.get_integration_id("nonexistent") is None

    def test_set_integration_id(self, tmp_path: Path):
        """set_integration_id updates mapping."""
        config = AgentCredentialConfig.load(tmp_path)

        config.set_integration_id("google", "new-integration-id")

        assert config.get_integration_id("google") == "new-integration-id"

    def test_remove_integration(self, tmp_path: Path):
        """remove_integration removes a mapping."""
        config = AgentCredentialConfig.load(tmp_path)
        config.set_integration_id("google", "test-id")

        result = config.remove_integration("google")

        assert result is True
        assert config.get_integration_id("google") is None

    def test_remove_integration_not_found(self, tmp_path: Path):
        """remove_integration returns False for unmapped provider."""
        config = AgentCredentialConfig.load(tmp_path)

        result = config.remove_integration("nonexistent")

        assert result is False

    def test_list_mappings(self, tmp_path: Path):
        """list_mappings returns a copy of all mappings."""
        config = AgentCredentialConfig.load(tmp_path)
        config.set_integration_id("google", "g-id")
        config.set_integration_id("hubspot", "h-id")

        mappings = config.list_mappings()

        assert mappings == {"google": "g-id", "hubspot": "h-id"}
        # Verify it's a copy
        mappings["new"] = "value"
        assert "new" not in config.mappings

    def test_has_mapping(self, tmp_path: Path):
        """has_mapping checks if provider is mapped."""
        config = AgentCredentialConfig.load(tmp_path)
        config.set_integration_id("google", "test-id")

        assert config.has_mapping("google") is True
        assert config.has_mapping("hubspot") is False

    def test_handles_invalid_json(self, tmp_path: Path):
        """Handles invalid JSON in credentials.json gracefully."""
        config_path = tmp_path / "credentials.json"
        config_path.write_text("not valid json")

        config = AgentCredentialConfig.load(tmp_path)

        assert config.mappings == {}


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_integration_id_for_agent(self, tmp_path: Path):
        """get_integration_id_for_agent loads and returns mapping."""
        config_data = {"mappings": {"google": "g-id"}}
        config_path = tmp_path / "credentials.json"
        config_path.write_text(json.dumps(config_data))

        result = get_integration_id_for_agent(tmp_path, "google")

        assert result == "g-id"

    def test_set_integration_id_for_agent(self, tmp_path: Path):
        """set_integration_id_for_agent saves mapping to file."""
        set_integration_id_for_agent(tmp_path, "hubspot", "h-id")

        config_path = tmp_path / "credentials.json"
        assert config_path.exists()

        saved_data = json.loads(config_path.read_text())
        assert saved_data["mappings"]["hubspot"] == "h-id"
