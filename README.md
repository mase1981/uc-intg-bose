# Bose Integration for Unfolded Circle Remote 2/3

Control your **Bose smart soundbars and speakers** (the **Bose Music app** line) directly from your Unfolded Circle Remote 2 or Remote 3. Power, volume, mute, transport, source switching, now-playing with album art, and battery level for portables — controlled **locally** after a one-time Bose account sign-in.

> **Which integration do I need?** This is for the **modern Bose (Bose Music app)** devices. For older **SoundTouch** speakers (SoundTouch app), use the separate [SoundTouch integration](https://github.com/mase1981/uc-intg-soundtouch). The quick test: if you set the device up in the **Bose** app → this integration; if the **SoundTouch** app → the other one.

![Bose](https://img.shields.io/badge/Bose-Music-blue)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-bose?style=flat-square)](https://github.com/mase1981/uc-intg-bose/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-bose?style=flat-square)](https://github.com/mase1981/uc-intg-bose/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-bose/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)

## Supported Devices

Bose Music-line devices, including: **Smart Ultra Soundbar**, **Soundbar 500 / 700 / 900**, **Home Speaker 300 / 500**, **Music Amplifier**, and **Portable Speaker**. (Older SoundTouch models are **not** supported here — see the note above.)

## Features

- **🎵 Full media player** - power on/off, volume, mute, play/pause, next/previous, and live **now-playing** metadata (track, artist, album, **album art**).
- **🔀 Source switching** - select any input the device exposes (TV, Bluetooth, aux, streaming, …).
- **🎛️ Remote entity** - transport, power on/off, and a TV shortcut as simple commands for Activities, plus a ready-made button page.
- **🔋 Battery sensor** - for portable models (added automatically only when the device has a battery).
- **📊 Now-playing sensor** - current track/source for use on any page or in automations.
- **⚡ Real-time local control** - after sign-in, everything runs over the speaker's local WebSocket with instant push updates.
- **Multi-device** - add each Bose device on your account.

---
## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

## How Authentication Works

Bose requires a one-time cloud sign-in to enable local control. During setup you enter your **Bose account email and password** (the same you use in the Bose app). After that:

- **All control is local** over the speaker's own network connection — the cloud is not in the loop for day-to-day use.
- The integration **re-authenticates automatically whenever it reconnects** (e.g. when the Remote wakes from standby), so your speakers recover on their own with **no periodic re-setup**.
- Your credentials are stored on the Remote so this recovery works across reboots and long offline periods. You only need to run setup again if you **change your Bose account password**.

> This integration uses an unofficial, community-maintained Bose API ([pybose](https://github.com/cavefire/pybose)). It is not affiliated with or endorsed by Bose, and Bose could change their API at any time.

## Requirements

- A Bose Music-line device on the same network as your Remote.
- A Bose account (email + password).
- Internet access at setup time (and for the occasional token refresh); day-to-day control is local.
- Unfolded Circle Remote 2 / 3 with firmware supporting custom integrations.

## Installation

### Option 1: Remote Web Interface (Recommended)

1. Download the latest `uc-intg-bose-<version>.tar.gz` from the [**Releases**](https://github.com/mase1981/uc-intg-bose/releases) page.
2. Open your Remote's web interface (`http://your-remote-ip`).
3. Go to **Settings -> Integrations -> Add Integration -> Install Custom** and upload the `.tar.gz`.

### Option 2: Docker (Advanced Users)

**Image**: `ghcr.io/mase1981/uc-intg-bose:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-bose:
    image: ghcr.io/mase1981/uc-intg-bose:latest
    container_name: uc-intg-bose
    network_mode: host
    volumes:
      - ./config:/config
    environment:
      - UC_CONFIG_HOME=/config
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-intg-bose --restart unless-stopped --network host -v $(pwd)/config:/config -e UC_CONFIG_HOME=/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-bose:latest
```

## Configuration

1. Start setup and **sign in with your Bose account** (email + password).
2. Your devices are discovered automatically; if you have more than one, pick the device to add.
3. Repeat setup to add additional Bose devices.

For each device the integration creates:

| Entity | Purpose |
|--------|---------|
| **Media player** (`<name>`) | Power, volume, mute, transport, source select, now-playing with album art. |
| **Remote** (`<name> Remote`) | Transport, power on/off, TV shortcut as simple commands for Activities. |
| **Select** (`<name> Source`) | Pick the active input/source. |
| **Sensors** (`<name> Now Playing`, `<name> Battery`) | Now-playing text; battery only on portables. |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Bose sign-in failed" | Double-check your Bose account email and password (the same used in the Bose app). |
| "No Bose devices were found" | Ensure the device is powered on and on the same network/subnet as the Remote. |
| Device unavailable after a password change | Changing your Bose password revokes the stored login — re-run setup to sign in again. |
| Device unavailable after a router reboot | The IP is re-resolved automatically on reconnect; give it a moment, or power-cycle the speaker. |
| Source switch does nothing | Only the sources the device actually exposes are selectable; some streaming sources are controlled from within their app. |

## Credits

- **Developer**: Meir Miyara
- **Bose local API**: [cavefire/pybose](https://github.com/cavefire/pybose) (unofficial, reverse-engineered).
- **Unfolded Circle**: Remote 2/3 integration framework ([ucapi](https://github.com/unfoldedcircle/integration-python-library) / [ucapi-framework](https://github.com/JackJPowell/ucapi-framework)).

## License

Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-bose/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)

---

**Made with ❤️ for the Unfolded Circle Community**

**Thank You**: Meir Miyara
