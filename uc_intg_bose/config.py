"""Configuration dataclass and manager for the Bose integration.

Credentials (email/password) are stored so the integration can silently
re-authenticate on every connect — the Remote is offline by design and cannot
rely on keeping a token refresh chain alive. This follows the same plaintext
credential pattern used across the other account-based integrations (e.g. HEOS).
Cached tokens are also stored to avoid a full cloud login on each reconnect.
"""

from dataclasses import dataclass


@dataclass
class BoseConfig:
    """Configuration for a single Bose (Bose Music line) device."""

    identifier: str = ""
    name: str = ""
    host: str = ""
    guid: str = ""
    has_battery: bool = False
    email: str = ""
    password: str = ""
    # Cached tokens (refreshed at runtime, persisted immediately on change)
    access_token: str = ""
    refresh_token: str = ""
    azure_refresh_token: str = ""
    bose_person_id: str = ""


from ucapi_framework import BaseConfigManager  # noqa: E402


class BoseConfigManager(BaseConfigManager[BoseConfig]):
    """Config manager bound to :class:`BoseConfig`."""
