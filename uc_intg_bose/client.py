"""Async helpers around pybose (BoseAuth / BoseSpeaker / BoseDiscovery).

pybose's auth and discovery are synchronous (``requests`` / blocking mDNS), so
they are run in a thread executor. ``authenticate()`` performs the layered
cached -> refresh -> full-login flow built into ``getControlToken`` and returns
the seeded ``BoseAuth`` plus the (possibly rotated) tokens to persist.
"""

import asyncio
import logging
from typing import Any

from pybose import BoseAuth, BoseDiscovery, BoseSpeaker

_LOG = logging.getLogger(__name__)


def _authenticate_sync(email: str, password: str, tokens: dict[str, str]) -> tuple[BoseAuth, dict]:
    auth = BoseAuth()
    if tokens.get("access_token"):
        auth.set_access_token(
            tokens.get("access_token", ""),
            tokens.get("refresh_token", ""),
            tokens.get("bose_person_id", ""),
        )
    if tokens.get("azure_refresh_token"):
        auth.set_azure_refresh_token(tokens["azure_refresh_token"])

    # getControlToken: returns cached token if valid, else refreshes via the
    # Azure refresh token, else performs a full login with email/password.
    control = auth.getControlToken(email or None, password or None)
    new_tokens = {
        "access_token": control.get("access_token", ""),
        "refresh_token": control.get("refresh_token", ""),
        "bose_person_id": control.get("bose_person_id", ""),
        "azure_refresh_token": auth.get_azure_refresh_token() or "",
    }
    return auth, new_tokens


async def authenticate(email: str, password: str, tokens: dict[str, str]) -> tuple[BoseAuth, dict]:
    """Authenticate (executor). Returns (seeded BoseAuth, tokens-to-persist)."""
    return await asyncio.to_thread(_authenticate_sync, email, password, tokens)


def _discover_sync(timeout: int) -> list[dict[str, str]]:
    return BoseDiscovery().discover_devices(timeout=timeout)


async def discover(timeout: int = 4) -> list[dict[str, str]]:
    """Discover Bose devices via mDNS (executor). Returns [{'GUID','IP'}, ...]."""
    return await asyncio.to_thread(_discover_sync, timeout)


async def resolve_ip(guid: str, fallback: str, timeout: int = 4) -> str:
    """Return the current IP for a device GUID, falling back to the stored IP."""
    try:
        for dev in await discover(timeout):
            if dev.get("GUID") == guid and dev.get("IP"):
                return dev["IP"]
    except Exception as err:  # pylint: disable=broad-exception-caught
        _LOG.debug("Bose discovery failed: %s", err)
    return fallback


def make_speaker(host: str, guid: str, auth: BoseAuth) -> BoseSpeaker:
    return BoseSpeaker(host=host, device_id=guid or None, bose_auth=auth, auto_reconnect=True)


# -- response parsers (defensive; every field is optional) -----------------
def parse_now_playing(body: dict[str, Any]) -> dict[str, Any]:
    body = body or {}
    metadata = body.get("metadata") or {}
    state = body.get("state") or {}
    container = body.get("container") or {}
    content_item = container.get("contentItem") or {}
    source = body.get("source") or {}
    return {
        "title": metadata.get("trackName", ""),
        "artist": metadata.get("artist", ""),
        "album": metadata.get("album", ""),
        "duration": metadata.get("duration", 0),
        "art": content_item.get("containerArt", ""),
        "status": state.get("status", ""),
        "position": state.get("timeIntoTrack", 0),
        "source": source.get("sourceDisplayName", "") or content_item.get("source", ""),
        "source_id": source.get("sourceID", ""),
    }


def parse_volume(body: dict[str, Any]) -> dict[str, Any]:
    body = body or {}
    return {
        "value": int(body.get("value", 0) or 0),
        "muted": bool(body.get("muted", False)),
        "min": int(body.get("min", 0) or 0),
        "max": int(body.get("max", 100) or 100),
    }


def parse_power(body: dict[str, Any]) -> bool:
    return (body or {}).get("power", "").upper() == "ON"


def parse_sources(body: dict[str, Any]) -> list[dict[str, Any]]:
    items = (body or {}).get("sources", []) or []
    out: list[dict[str, Any]] = []
    for s in items:
        if not s.get("visible", True):
            continue
        out.append({
            "source": s.get("sourceName", ""),
            "account": s.get("sourceAccountName", ""),
            "display_name": s.get("displayName", "") or s.get("sourceName", ""),
            "status": s.get("status", ""),
        })
    return out
