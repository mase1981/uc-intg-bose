"""Integration driver for Bose (Bose Music line)."""

from ucapi_framework import BaseIntegrationDriver

from uc_intg_bose.config import BoseConfig
from uc_intg_bose.device import BoseDevice
from uc_intg_bose.media_player import create_media_player
from uc_intg_bose.remote import create_remote
from uc_intg_bose.select import create_selects
from uc_intg_bose.sensor import create_sensors


class BoseDriver(BaseIntegrationDriver[BoseDevice, BoseConfig]):
    """Builds a media_player, remote, source select, and sensors per device."""

    def __init__(self) -> None:
        super().__init__(
            device_class=BoseDevice,
            entity_classes=[
                create_media_player,
                create_remote,
                create_selects,
                create_sensors,
            ],
            driver_id="uc_intg_bose",
        )
