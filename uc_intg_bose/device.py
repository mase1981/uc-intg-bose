"""Bose (Bose Music line) device — wraps pybose.BoseSpeaker.

Self-healing auth: on every (re)connect we re-authenticate (cached token ->
refresh -> full login) and re-resolve the device IP via mDNS, so the entities
recover automatically whenever the Remote wakes and rejoins the network — even
if the cached token expired while it was asleep. Rotated tokens are persisted
immediately (update_config) so a reboot never loses the refresh chain.
"""

import asyncio
import logging
from typing import Any

from ucapi_framework import ExternalClientDevice

from uc_intg_bose import client as bose_client
from uc_intg_bose.config import BoseConfig
from uc_intg_bose.const import (
    PLAY_STATUS_MAP,
    RES_NOW_PLAYING,
    RES_POWER,
    RES_VOLUME,
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
    STATE_UNAVAILABLE,
    VOLUME_STEP,
)

_LOG = logging.getLogger(__name__)


class BoseDevice(ExternalClientDevice):
    """One Bose Music-line speaker/soundbar."""

    def __init__(self, device_config: BoseConfig, **kwargs: Any) -> None:
        super().__init__(device_config, watchdog_interval=30, reconnect_delay=5, **kwargs)
        self._device_config = device_config
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._receiver_id: int | None = None
        self._available: bool = False
        self._power: bool = False
        self._volume: dict[str, Any] = {"value": 0, "muted": False, "min": 0, "max": 100}
        self._now_playing: dict[str, Any] = {}
        self._sources: list[dict[str, Any]] = []
        self._system: dict[str, Any] = {}
        self._battery: dict[str, Any] = {}
        self._has_battery: bool = False

    # -- identity ------------------------------------------------------
    @property
    def identifier(self) -> str:
        return self._device_config.identifier

    @property
    def name(self) -> str:
        return self._device_config.name

    @property
    def address(self) -> str:
        return self._device_config.host

    @property
    def log_id(self) -> str:
        return f"{self.name} ({self.address})"

    @property
    def available(self) -> bool:
        return self._available

    @property
    def state(self) -> str:
        if not self._available:
            return STATE_UNAVAILABLE
        if not self._power:
            return STATE_OFF
        return PLAY_STATUS_MAP.get((self._now_playing.get("status") or "").upper(), STATE_ON)

    # -- state accessors ----------------------------------------------
    @property
    def power(self) -> bool:
        return self._power

    @property
    def volume(self) -> int:
        return int(self._volume.get("value", 0))

    @property
    def muted(self) -> bool:
        return bool(self._volume.get("muted", False))

    @property
    def media_title(self) -> str:
        return self._now_playing.get("title", "")

    @property
    def media_artist(self) -> str:
        return self._now_playing.get("artist", "")

    @property
    def media_album(self) -> str:
        return self._now_playing.get("album", "")

    @property
    def media_image_url(self) -> str:
        return self._now_playing.get("art", "")

    @property
    def media_duration(self) -> int:
        return int(self._now_playing.get("duration", 0) or 0)

    @property
    def media_position(self) -> int:
        return int(self._now_playing.get("position", 0) or 0)

    @property
    def source(self) -> str:
        current = self._now_playing.get("source", "")
        for s in self._sources:
            if s["source"] == current or s["display_name"] == current:
                return s["display_name"]
        return current

    @property
    def source_list(self) -> list[str]:
        return [s["display_name"] for s in self._sources]

    @property
    def has_battery(self) -> bool:
        return self._has_battery

    @property
    def battery_percent(self) -> int:
        return int(self._battery.get("percent", 0) or 0)

    @property
    def battery_charging(self) -> bool:
        return str(self._battery.get("chargerConnected", "")).upper() in ("CONNECTED", "TRUE")

    @property
    def model(self) -> str:
        return self._system.get("productName", "")

    def _source_lookup(self, display: str) -> tuple[str, str] | None:
        for s in self._sources:
            if display.lower() in (s["display_name"].lower(), s["source"].lower()):
                return s["source"], s["account"]
        return None

    # -- ExternalClientDevice lifecycle -------------------------------
    async def connect(self) -> bool:
        async with self._connect_lock:
            return await super().connect()

    async def disconnect(self) -> None:
        async with self._connect_lock:
            self._available = False
            await super().disconnect()

    async def create_client(self) -> Any:
        # Defensive teardown — the watchdog reconnect path bypasses connect().
        await self.disconnect_client()

        cfg = self._device_config
        # Re-resolve IP for this GUID (DHCP-safe) before connecting.
        if cfg.guid:
            new_ip = await bose_client.resolve_ip(cfg.guid, cfg.host)
            if new_ip and new_ip != cfg.host:
                _LOG.info("[%s] IP changed %s -> %s", self.log_id, cfg.host, new_ip)
                self.update_config(host=new_ip)

        # Layered auth: cached token -> refresh -> full login (email/password).
        auth, tokens = await bose_client.authenticate(
            cfg.email,
            cfg.password,
            {
                "access_token": cfg.access_token,
                "refresh_token": cfg.refresh_token,
                "azure_refresh_token": cfg.azure_refresh_token,
                "bose_person_id": cfg.bose_person_id,
            },
        )
        # Persist rotated tokens immediately (survives reboot).
        self.update_config(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            azure_refresh_token=tokens["azure_refresh_token"],
            bose_person_id=tokens["bose_person_id"],
        )
        return bose_client.make_speaker(cfg.host, cfg.guid, auth)

    async def connect_client(self) -> None:
        await self._client.connect()

        guid = self._client.get_device_id()
        if guid and guid != self._device_config.guid:
            self.update_config(guid=guid)

        self._receiver_id = self._client.attach_receiver(self._on_message)
        await self._client.subscribe()
        await self._seed_state()
        self._available = True
        self.push_update()

    async def disconnect_client(self) -> None:
        if self._client is not None:
            try:
                if self._receiver_id is not None:
                    self._client.detach_receiver(self._receiver_id)
                    self._receiver_id = None
                await self._client.disconnect()
            except Exception as err:  # pylint: disable=broad-exception-caught
                _LOG.debug("[%s] disconnect_client: %s", self.log_id, err)
        self._available = False

    def check_client_connected(self) -> bool:
        return self._client is not None and self._client.is_connected()

    # -- state seeding & live events ----------------------------------
    async def _seed_state(self) -> None:
        self._system = await self._client.get_system_info() or {}
        self._power = bose_client.parse_power(await self._client.get_power_state())
        self._volume = bose_client.parse_volume(await self._client.get_audio_volume())
        self._now_playing = bose_client.parse_now_playing(await self._client.get_now_playing())
        self._sources = bose_client.parse_sources(await self._client.get_sources())
        if self._client.has_capability("/system/battery"):
            try:
                self._battery = await self._client.get_battery_status() or {}
                self._has_battery = bool(self._battery)
            except Exception:  # pylint: disable=broad-exception-caught
                self._has_battery = False

    def _on_message(self, message: Any) -> None:
        """Sync NOTIFY callback from pybose's receiver loop (runs on our loop)."""
        try:
            header = message.get("header", {}) if isinstance(message, dict) else {}
            resource = header.get("resource", "")
            body = message.get("body", {}) if isinstance(message, dict) else {}
        except AttributeError:
            return
        changed = False
        if resource == RES_NOW_PLAYING:
            self._now_playing = bose_client.parse_now_playing(body)
            changed = True
        elif resource == RES_VOLUME:
            self._volume = bose_client.parse_volume(body)
            changed = True
        elif resource == RES_POWER:
            self._power = bose_client.parse_power(body)
            changed = True
        if changed:
            self.push_update()

    # -- commands ------------------------------------------------------
    async def power_on(self) -> None:
        await self._client.set_power_state(True)

    async def power_off(self) -> None:
        await self._client.set_power_state(False)

    async def toggle_power(self) -> None:
        await self._client.set_power_state(not self._power)

    async def play(self) -> None:
        await self._client.play()

    async def pause(self) -> None:
        await self._client.pause()

    async def play_pause(self) -> None:
        if self.state == STATE_PLAYING:
            await self._client.pause()
        else:
            await self._client.play()

    async def next_track(self) -> None:
        await self._client.skip_next()

    async def previous_track(self) -> None:
        await self._client.skip_previous()

    async def set_volume(self, level: int) -> None:
        level = max(0, min(100, int(level)))
        await self._client.set_audio_volume(level)

    async def volume_up(self) -> None:
        await self.set_volume(self.volume + VOLUME_STEP)

    async def volume_down(self) -> None:
        await self.set_volume(self.volume - VOLUME_STEP)

    async def set_mute(self, muted: bool) -> None:
        await self._client.set_audio_volume_muted(bool(muted))

    async def mute_toggle(self) -> None:
        await self._client.set_audio_volume_muted(not self.muted)

    async def select_source(self, display: str) -> bool:
        match = self._source_lookup(display)
        if not match:
            _LOG.warning("[%s] Unknown source: %s", self.log_id, display)
            return False
        await self._client.set_source(match[0], match[1])
        return True

    async def switch_tv(self) -> None:
        await self._client.switch_tv_source()
