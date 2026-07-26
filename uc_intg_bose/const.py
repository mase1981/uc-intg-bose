"""Constants for the Bose integration."""

STATE_ON = "ON"
STATE_OFF = "OFF"
STATE_PLAYING = "PLAYING"
STATE_PAUSED = "PAUSED"
STATE_BUFFERING = "BUFFERING"
STATE_UNAVAILABLE = "UNAVAILABLE"

# pybose resource paths pushed as NOTIFY events (header.resource)
RES_NOW_PLAYING = "/content/nowPlaying"
RES_VOLUME = "/audio/volume"
RES_POWER = "/system/power/control"

VOLUME_STEP = 5

# now_playing state.status -> integration state
PLAY_STATUS_MAP = {
    "PLAY": STATE_PLAYING,
    "PLAYING": STATE_PLAYING,
    "BUFFERING": STATE_BUFFERING,
    "PAUSED": STATE_PAUSED,
    "PAUSE": STATE_PAUSED,
    "STOPPED": STATE_ON,
    "STOP": STATE_ON,
    "INVALID": STATE_ON,
}

# TV / product source shortcut
SOURCE_PRODUCT = "PRODUCT"
SOURCE_TV_ACCOUNT = "TV"
