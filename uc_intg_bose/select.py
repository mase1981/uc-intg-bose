"""Bose source Select entity."""

import logging
from typing import Any

from ucapi import StatusCodes, select
from ucapi_framework import SelectEntity

from uc_intg_bose.config import BoseConfig
from uc_intg_bose.device import BoseDevice

_LOG = logging.getLogger(__name__)


class BoseSourceSelect(SelectEntity):
    """Selects the active input/source on the device."""

    def __init__(self, device_config: BoseConfig, device: BoseDevice) -> None:
        self._device = device
        entity_id = f"select.{device_config.identifier}.source"
        super().__init__(
            entity_id,
            f"{device_config.name} Source",
            {
                select.Attributes.STATE: select.States.UNKNOWN,
                select.Attributes.OPTIONS: [],
                select.Attributes.CURRENT_OPTION: "",
            },
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({select.Attributes.STATE: select.States.UNAVAILABLE})
            return
        self.update({
            select.Attributes.STATE: select.States.ON,
            select.Attributes.OPTIONS: self._device.source_list,
            select.Attributes.CURRENT_OPTION: self._device.source,
        })

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            if cmd_id != select.Commands.SELECT_OPTION:
                return StatusCodes.NOT_IMPLEMENTED
            option = (params or {}).get("option", "")
            if not option:
                return StatusCodes.BAD_REQUEST
            if await self._device.select_source(option):
                return StatusCodes.OK
            return StatusCodes.BAD_REQUEST
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Source select error: %s", entity.id, err)
            return StatusCodes.SERVER_ERROR


def create_selects(device_config: BoseConfig, device: BoseDevice) -> list[BoseSourceSelect]:
    return [BoseSourceSelect(device_config, device)]
