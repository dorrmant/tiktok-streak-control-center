[![Streak Control Center – visual guide](https://github.com/dorrmant/tiktok-streak-control-center/raw/main/docs/tutorial/intro.svg)](https://github.com/dorrmant/tiktok-streak-control-center/blob/main/docs/tutorial/intro.svg)

# ✦ Streak Control Center

**A neon control panel for a TikTok streak bot — terminal menu, PC dashboard and phone dashboard, all sharing one backend.**

Made by **Dorrmant** · MIT licensed

---

## Table of contents

- [Features](#features)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Disclaimer](#disclaimer)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Three ways to control one bot:** an interactive terminal menu, a PC/LAN web dashboard (`:8765`) and a phone-friendly dashboard (`:8766`).
- **Live logs everywhere:** the terminal and both dashboards stream what the bot is doing, color-coded (errors, waits, successes).
- **Password-protected dashboards**, generated on first run.
- **Resilient navigation:** retries with back-off when TikTok answers with a `403`, and keeps the browser session alive between runs.
- **No file editing needed:** start / stop the bot, open TikTok to log in, and edit usernames, message and timings from the menu or dashboard.

---

# 📦 Installation

Installation takes three steps. Everything below was tested on a clean copy of the project.

## 1. Check requirements

| Requirement | Details |
|---|---|
| Operating system | **Linux** (tested on Linux Mint), **Windows 10/11** (added, lightly tested), macOS (should work) |
| Python | 3.9 or newer. Linux: `sudo apt install python3-venv`. Windows: install from python.org and tick *Add to PATH* |
| Browser | Google Chrome or Chromium installed |

## 2. Download the project

- **Windows:** on GitHub choose **Code → Download ZIP**, then unzip it.
- **Linux / macOS:**

  ```bash
  git clone https://github.com/dorrmant/tiktok-streak-control-center.git
  cd tiktok-streak-control-center
  ```

## 3. Install and run it

- **Windows:** double-click **`install.bat`**, then **`run.bat`**. Use Windows Terminal or PowerShell for the best colors.
- **Linux / macOS:**

  ```bash
  bash install.sh
  bash run.sh
  ```

The first run creates `config.json` with a random dashboard password. It is shown in the terminal menu.

---

# 🚀 Usage

From first launch to controlling the bot from your phone.

## Quick start

1. **Start the app** with `run.bat` (Windows) or `bash run.sh` (Linux / macOS). The terminal menu appears.
2. **Log in to TikTok once.** Choose **5 · Open TikTok / login** and sign in by hand. The session is saved in a local browser profile, so you only need to do this once.
3. **Configure the bot.** Choose **8** (or use the web dashboard) to set your usernames, message, timing and repeat interval, then save.
4. **Start the bot.** Choose **3 · Start bot**. Watch progress in **9 · Live logs** or on the dashboard.
5. **Stop the bot** any time with **4 · Stop bot**.
6. **Open a dashboard:**
   - PC: `http://127.0.0.1:8765`
   - Phone (same Wi-Fi): `http://<your-LAN-IP>:8766`

   Log in with the dashboard password shown in the terminal menu. Use option **6 · Show web URLs** to see your exact addresses.

## Menu reference

| Key | Action              | Key | Action                             |
|-----|---------------------|-----|------------------------------------|
| 1   | Bot status          | 6   | Show web URLs                      |
| 2   | View configuration  | 7   | Check ports                        |
| 3   | Start bot           | 8   | Edit message / interval / users    |
| 4   | Stop bot            | 9   | Live logs (`x` + Enter to go back) |
| 5   | Open TikTok / login | 0   | Exit                               |

---

## Configuration

`config.json` is created automatically, so there is nothing to copy by hand. See [`config.example.json`](config.example.json) for the available fields.

> **Warning:** `config.json` holds your dashboard password and is git-ignored. **Never commit it.**

**Using your own bot:** put its path in `bot_source`. It must expose:

- `bot_worker(config, stop_event)`
- `open_tiktok(config, wait_for_login=True)`

## Troubleshooting

| Problem | What to do |
|---|---|
| **HTTP 403 / "Access denied" on profiles** | This is TikTok's anti-bot layer. Log in first (option 5), disable any VPN, raise "Profile-load wait" to 8–10 s, and avoid very short intervals. The bot retries automatically, but it cannot bypass a blocked IP. |
| **"Could not connect to Chromium"** | Close other Chrome windows that use the bot profile, or check `debug_port` (default `9222`). |
| **Phone can't open the dashboard** | Use the LAN IP from the menu (option 6) and allow ports 8765 and 8766 in your firewall. |

## Security

- Dashboards listen on your local network. **Do not port-forward them to the internet.**
- The bot never asks for or stores your TikTok password; you log in manually in the browser.

## Disclaimer

This is an independent hobby project, **not affiliated with or endorsed by TikTok / ByteDance**. Automating a TikTok account may violate TikTok's Terms of Service and can lead to rate limits or account restrictions. Use it only with your own account and with people who expect your messages, send responsibly, and at your own risk. The authors accept no liability.

## Contributing

Issues and pull requests are welcome. Please keep personal data (usernames, passwords, `config.json`) out of commits.

## License

[MIT](LICENSE) © 2026 Dorrmant
