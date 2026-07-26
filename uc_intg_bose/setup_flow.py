"""Setup flow: Bose account sign-in -> discover devices -> pick one."""

import asyncio
import logging
import re
from typing import Any

from ucapi import RequestUserInput
from ucapi_framework import BaseSetupFlow

from uc_intg_bose import client as bose_client
from uc_intg_bose.config import BoseConfig

_LOG = logging.getLogger(__name__)


class BoseSetupFlow(BaseSetupFlow[BoseConfig]):
    """Collect Bose credentials, discover devices, and add the chosen one."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._email = ""
        self._password = ""
        self._tokens: dict[str, str] = {}
        self._auth = None
        self._devices: list[dict[str, str]] = []

    def get_manual_entry_form(self) -> RequestUserInput:
        return RequestUserInput(
            {"en": "Bose Account Sign-In"},
            [
                {
                    "id": "info",
                    "label": {"en": "Bose account"},
                    "field": {"label": {"value": {"en": "Sign in with your Bose account (same as the Bose app). Your speakers are discovered automatically. Credentials are stored on the Remote so the connection survives reboots and standby."}}},
                },
                {"id": "email", "label": {"en": "Bose Account Email"}, "field": {"text": {"value": ""}}},
                {"id": "password", "label": {"en": "Bose Account Password"}, "field": {"password": {"value": ""}}},
            ],
        )

    async def query_device(self, input_values: dict[str, Any]) -> BoseConfig | RequestUserInput:
        email = input_values.get("email", "").strip()
        password = input_values.get("password", "").strip()
        if not email or not password:
            raise ValueError("Bose account email and password are required")

        try:
            self._auth, self._tokens = await bose_client.authenticate(email, password, {})
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("Bose sign-in failed: %s", err)
            raise ValueError("Bose sign-in failed. Check your email and password.") from err

        self._email = email
        self._password = password

        self._devices = await bose_client.discover(timeout=5)
        if not self._devices:
            raise ValueError(
                "Signed in successfully, but no Bose devices were found on the network. "
                "Make sure the speaker is powered on and on the same network as the Remote."
            )

        if len(self._devices) == 1:
            return await self._build_config(self._devices[0])

        items = []
        for dev in self._devices:
            name, _ = await self._probe(dev["IP"], dev["GUID"])
            items.append({"id": dev["GUID"], "label": {"en": f"{name} ({dev['IP']})"}})
        return RequestUserInput(
            {"en": "Select Bose Device"},
            [{
                "id": "device",
                "label": {"en": "Device"},
                "field": {"dropdown": {"value": items[0]["id"], "items": items}},
            }],
        )

    async def handle_additional_configuration_response(self, msg: Any) -> BoseConfig | None:
        guid = msg.input_values.get("device", "")
        dev = next((d for d in self._devices if d["GUID"] == guid), None)
        if not dev:
            raise ValueError("Selected device not found")
        self._pending_device_config = await self._build_config(dev)
        return None

    async def _build_config(self, dev: dict[str, str]) -> BoseConfig:
        name, has_battery = await self._probe(dev["IP"], dev["GUID"])
        guid = dev["GUID"]
        identifier = f"bose_{re.sub(r'[^A-Za-z0-9]', '_', guid)}"
        return BoseConfig(
            identifier=identifier,
            name=name,
            host=dev["IP"],
            guid=guid,
            has_battery=has_battery,
            email=self._email,
            password=self._password,
            access_token=self._tokens.get("access_token", ""),
            refresh_token=self._tokens.get("refresh_token", ""),
            azure_refresh_token=self._tokens.get("azure_refresh_token", ""),
            bose_person_id=self._tokens.get("bose_person_id", ""),
        )

    async def _probe(self, ip: str, guid: str) -> tuple[str, bool]:
        """Best-effort (friendly name, has_battery) via a short connect."""
        speaker = bose_client.make_speaker(ip, guid, self._auth)
        try:
            await asyncio.wait_for(speaker.connect(), timeout=6)
            info = await asyncio.wait_for(speaker.get_system_info(), timeout=6)
            name = (info.get("name") or "").strip() or f"Bose ({ip})"
            has_battery = bool(speaker.has_capability("/system/battery"))
            return name, has_battery
        except Exception:  # pylint: disable=broad-exception-caught
            return f"Bose ({ip})", False
        finally:
            try:
                await speaker.disconnect()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
