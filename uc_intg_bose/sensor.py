"""Bose sensors: now-playing text and (for portables) battery level."""

import logging

from ucapi import sensor
from ucapi_framework import SensorEntity

from uc_intg_bose.config import BoseConfig
from uc_intg_bose.const import STATE_OFF
from uc_intg_bose.device import BoseDevice

_LOG = logging.getLogger(__name__)


class BoseNowPlayingSensor(SensorEntity):
    """Shows the current track / source text."""

    def __init__(self, device_config: BoseConfig, device: BoseDevice) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.now_playing"
        super().__init__(
            entity_id,
            f"{device_config.name} Now Playing",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: ""},
            device_class=sensor.DeviceClasses.CUSTOM,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available:
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        if self._device.state == STATE_OFF:
            value = "Off"
        else:
            title = self._device.media_title
            artist = self._device.media_artist
            value = f"{artist} - {title}" if artist and title else (
                title or self._device.source or "Idle"
            )
        self.update({sensor.Attributes.STATE: sensor.States.ON, sensor.Attributes.VALUE: value})


class BoseBatterySensor(SensorEntity):
    """Battery level for portable Bose speakers."""

    def __init__(self, device_config: BoseConfig, device: BoseDevice) -> None:
        self._device = device
        entity_id = f"sensor.{device_config.identifier}.battery"
        super().__init__(
            entity_id,
            f"{device_config.name} Battery",
            [],
            {sensor.Attributes.STATE: sensor.States.UNKNOWN, sensor.Attributes.VALUE: 0},
            device_class=sensor.DeviceClasses.BATTERY,
        )
        self.subscribe_to_device(device)

    async def sync_state(self) -> None:
        if not self._device.available or not self._device.has_battery:
            self.update({sensor.Attributes.STATE: sensor.States.UNAVAILABLE})
            return
        self.update({
            sensor.Attributes.STATE: sensor.States.ON,
            sensor.Attributes.VALUE: self._device.battery_percent,
        })


def create_sensors(device_config: BoseConfig, device: BoseDevice) -> list[SensorEntity]:
    sensors: list[SensorEntity] = [BoseNowPlayingSensor(device_config, device)]
    if device_config.has_battery:
        sensors.append(BoseBatterySensor(device_config, device))
    return sensors
