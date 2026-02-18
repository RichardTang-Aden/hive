"""
Agent-level credential configuration.

Each agent can have its own credential mappings, allowing different agents
to use different OAuth accounts (e.g., work vs personal Google account).

The config is stored in `{agent_path}/credentials.json`:
{
    "mappings": {
        "google": "Z29vZ2xlOnJpY2hhcmRAYWNoby5pbzo3MDIwOjEwMzgz",
        "hubspot": "aHVic3BvdDp3b3JrQGNvbXBhbnkuY29t"
    }
}

Usage:
    config = AgentCredentialConfig.load("exports/my-agent")

    # Get the integration_id for a provider
    integration_id = config.get_integration_id("google")

    # Set a mapping
    config.set_integration_id("google", "Z29vZ2xlOnJpY2hhcmRAYWNoby5pbw==")
    config.save()
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_FILENAME = "credentials.json"


@dataclass
class AgentCredentialConfig:
    """Agent-level credential configuration."""

    agent_path: Path
    """Path to the agent directory."""

    mappings: dict[str, str] = field(default_factory=dict)
    """Provider -> integration_id mappings."""

    @classmethod
    def load(cls, agent_path: str | Path) -> AgentCredentialConfig:
        """Load config from agent directory.

        Args:
            agent_path: Path to agent directory (e.g., 'exports/my-agent')

        Returns:
            AgentCredentialConfig instance
        """
        agent_path = Path(agent_path)
        config_path = agent_path / CONFIG_FILENAME

        mappings: dict[str, str] = {}
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                mappings = data.get("mappings", {})
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load agent credential config: {e}")

        return cls(agent_path=agent_path, mappings=mappings)

    def save(self) -> None:
        """Save config to agent directory."""
        config_path = self.agent_path / CONFIG_FILENAME

        data = {"mappings": self.mappings}

        try:
            config_path.write_text(json.dumps(data, indent=2))
            logger.info(f"Saved agent credential config to {config_path}")
        except OSError as e:
            logger.error(f"Failed to save agent credential config: {e}")
            raise

    def get_integration_id(self, provider: str) -> str | None:
        """Get the integration_id for a provider.

        Args:
            provider: Provider name (e.g., 'google', 'hubspot')

        Returns:
            integration_id if mapped, None otherwise
        """
        return self.mappings.get(provider)

    def set_integration_id(self, provider: str, integration_id: str) -> None:
        """Set the integration_id for a provider.

        Args:
            provider: Provider name (e.g., 'google', 'hubspot')
            integration_id: The integration ID to use
        """
        self.mappings[provider] = integration_id

    def remove_integration(self, provider: str) -> bool:
        """Remove a provider mapping.

        Args:
            provider: Provider name to remove

        Returns:
            True if removed, False if not found
        """
        if provider in self.mappings:
            del self.mappings[provider]
            return True
        return False

    def list_mappings(self) -> dict[str, str]:
        """Get all provider -> integration_id mappings."""
        return dict(self.mappings)

    def has_mapping(self, provider: str) -> bool:
        """Check if a provider has a mapping."""
        return provider in self.mappings


def get_integration_id_for_agent(
    agent_path: str | Path,
    provider: str,
) -> str | None:
    """Convenience function to get integration_id for a provider.

    Args:
        agent_path: Path to agent directory
        provider: Provider name (e.g., 'google')

    Returns:
        integration_id if configured, None otherwise
    """
    config = AgentCredentialConfig.load(agent_path)
    return config.get_integration_id(provider)


def set_integration_id_for_agent(
    agent_path: str | Path,
    provider: str,
    integration_id: str,
) -> None:
    """Convenience function to set integration_id for a provider.

    Args:
        agent_path: Path to agent directory
        provider: Provider name (e.g., 'google')
        integration_id: The integration ID to use
    """
    config = AgentCredentialConfig.load(agent_path)
    config.set_integration_id(provider, integration_id)
    config.save()
