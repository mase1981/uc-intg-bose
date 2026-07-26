"""Bose remote entity (transport, power, TV shortcut) for activities."""

import logging
from typing import Any

from ucapi import StatusCodes, remote
from ucapi.ui import Buttons, Size, UiPage, create_btn_mapping, create_ui_icon, create_ui_text
from ucapi_framework import RemoteEntity

from uc_intg_bose.config import BoseConfig
from uc_intg_bose.device import BoseDevice

_LOG = logging.getLogger(__name__)

SIMPLE_COMMANDS = [
    "POWER", "POWER_ON", "POWER_OFF",
    "PLAY", "PAUSE", "PLAY_PAUSE", "NEXT", "PREVIOUS",
    "VOLUME_UP", "VOLUME_DOWN", "MUTE", "UNMUTE",
    "SOURCE_TV",
]


class BoseRemote(RemoteEntity):
    """Exposes Bose transport/power/TV as simple commands for activities."""

    def __init__(self, device_config: BoseConfig, device: BoseDevice) -> None:
        self._device = device
        entity_id = f"remote.{device_config.identifier}"
        super().__init__(
            entity_id,
            f"{device_config.name} Remote",
            [remote.Features.ON_OFF, remote.Features.TOGGLE, remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.UNKNOWN},
            simple_commands=SIMPLE_COMMANDS,
            button_mapping=[
                create_btn_mapping(Buttons.DPAD_MIDDLE, short="PLAY_PAUSE"),
                create_btn_mapping(Buttons.PLAY, short="PLAY_PAUSE"),
                create_btn_mapping(Buttons.PREV, short="PREVIOUS"),
                create_btn_mapping(Buttons.NEXT, short="NEXT"),
                create_btn_mapping(Buttons.VOLUME_UP, short="VOLUME_UP"),
                create_btn_mapping(Buttons.VOLUME_DOWN, short="VOLUME_DOWN"),
                create_btn_mapping(Buttons.MUTE, short="MUTE"),
                create_btn_mapping(Buttons.POWER, short="POWER"),
            ],
            ui_pages=[
                UiPage("main", "Bose", grid=Size(4, 6), items=[
                    create_ui_icon("uc:power-on", 0, 0, cmd="POWER_ON"),
                    create_ui_icon("uc:power-off", 1, 0, cmd="POWER_OFF"),
                    create_ui_text("TV", 2, 0, cmd="SOURCE_TV"),
                    create_ui_icon("uc:mute", 3, 0, cmd="MUTE"),
                    create_ui_icon("uc:bw", 0, 2, cmd="PREVIOUS"),
                    create_ui_icon("uc:play", 1, 2, cmd="PLAY_PAUSE"),
                    create_ui_icon("uc:ff", 2, 2, cmd="NEXT"),
                    create_ui_icon("uc:volume-up", 3, 3, cmd="VOLUME_UP"),
                    create_ui_icon("uc:volume-down", 3, 4, cmd="VOLUME_DOWN"),
                ]),
            ],
            cmd_handler=self._handle_command,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({remote.Attributes.STATE: remote.States.UNAVAILABLE})
            return
        self.update({
            remote.Attributes.STATE: remote.States.ON if self._device.power else remote.States.OFF,
        })

    async def _handle_command(self, entity: Any, cmd_id: str, params: dict | None = None, *_a: Any) -> StatusCodes:
        try:
            if cmd_id == remote.Commands.ON:
                await self._device.power_on()
                return StatusCodes.OK
            if cmd_id == remote.Commands.OFF:
                await self._device.power_off()
                return StatusCodes.OK
            if cmd_id == remote.Commands.TOGGLE:
                await self._device.toggle_power()
                return StatusCodes.OK
            if cmd_id != remote.Commands.SEND_CMD:
                return StatusCodes.NOT_IMPLEMENTED
            return await self._run((params or {}).get("command", ""))
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOG.error("[%s] Remote command error (%s): %s", entity.id, cmd_id, err)
            return StatusCodes.SERVER_ERROR

    async def _run(self, command: str) -> StatusCodes:
        actions = {
            "POWER": self._device.toggle_power,
            "POWER_ON": self._device.power_on,
            "POWER_OFF": self._device.power_off,
            "PLAY": self._device.play,
            "PAUSE": self._device.pause,
            "PLAY_PAUSE": self._device.play_pause,
            "NEXT": self._device.next_track,
            "PREVIOUS": self._device.previous_track,
            "VOLUME_UP": self._device.volume_up,
            "VOLUME_DOWN": self._device.volume_down,
            "MUTE": lambda: self._device.set_mute(True),
            "UNMUTE": lambda: self._device.set_mute(False),
            "SOURCE_TV": self._device.switch_tv,
        }
        action = actions.get(command)
        if not action:
            return StatusCodes.NOT_IMPLEMENTED
        await action()
        return StatusCodes.OK


def create_remote(device_config: BoseConfig, device: BoseDevice) -> list[BoseRemote]:
    return [BoseRemote(device_config, device)]
