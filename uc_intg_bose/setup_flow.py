"""Setup flow: Bose account sign-in -> discover devices -> pick one.

Setup deliberately does NOT open a connection to the speaker (that is done at
runtime). Connecting to the speaker during setup risks blocking past the
Remote's ~60s setup timeout, so we build the device config from the cloud
sign-in + mDNS discovery only. The friendly name and battery capability are
filled in at runtime on the first successful connect.
"""

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

        _LOG.info("Signing in to Bose account...")
        try:
            _, self._tokens = await bose_client.authenticate(email, password, {})
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("Bose sign-in failed: %s", err)
            raise ValueError("Bose sign-in failed. Check your email and password.") from err

        self._email = email
        self._password = password
        _LOG.info("Bose sign-in OK. Discovering devices on the network...")

        self._devices = await bose_client.discover(timeout=5)
        _LOG.info("Discovered %d Bose device(s)", len(self._devices))
        if not self._devices:
            raise ValueError(
                "Signed in successfully, but no Bose devices were found on the network. "
                "Make sure the speaker is powered on and on the same network as the Remote."
            )

        if len(self._devices) == 1:
            return self._build_config(self._devices[0])

        items = [{"id": d["GUID"], "label": {"en": f"Bose ({d['IP']})"}} for d in self._devices]
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
        self._pending_device_config = self._build_config(dev)
        return None

    def _build_config(self, dev: dict[str, str]) -> BoseConfig:
        guid = dev["GUID"]
        ip = dev["IP"]
        identifier = f"bose_{re.sub(r'[^A-Za-z0-9]', '_', guid)}"
        return BoseConfig(
            identifier=identifier,
            name=f"Bose ({ip})",  # real name filled in at runtime on first connect
            host=ip,
            guid=guid,
            has_battery=False,  # detected at runtime
            email=self._email,
            password=self._password,
            access_token=self._tokens.get("access_token", ""),
            refresh_token=self._tokens.get("refresh_token", ""),
            azure_refresh_token=self._tokens.get("azure_refresh_token", ""),
            bose_person_id=self._tokens.get("bose_person_id", ""),
        )
