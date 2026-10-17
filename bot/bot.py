import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

APP_NAME = "TikTok Streak Bot"
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
DEFAULT_CONFIG = {
    "usernames": [],
    "message": "",
    "interval_hours": 12,
    "debug_port": 9222,
    "profile_dir": "",
    "wait_after_profile_load_seconds": 3,
    "wait_after_message_click_seconds": 5,
}


def default_profile_dir():
    return Path.home() / "tiktok-streak-bot" / "browser-data"


def profile_dir(config):
    configured = str(config.get("profile_dir", "")).strip()
    return Path(configured).expanduser() if configured else default_profile_dir()


def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


def load_config():
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG.copy())
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Cannot read {CONFIG_PATH}: {exc}") from exc
    merged = DEFAULT_CONFIG.copy()
    merged.update(config)
    if not isinstance(merged.get("usernames"), list):
        merged["usernames"] = DEFAULT_CONFIG["usernames"].copy()
    return merged


def clean_username(value):
    value = value.strip()
    if not value:
        return ""
    if "tiktok.com/" in value.lower():
        parsed = urlparse(value if "://" in value else "https://" + value)
        path = parsed.path.strip("/")
        value = path[1:] if path.startswith("@") else path
    else:
        value = value.removeprefix("@").strip().strip("/")
    if not value or any(ch.isspace() for ch in value) or "/" in value:
        return ""
    return value


def print_header():
    print("\n" + "=" * 52)
    print(f"                 {APP_NAME}")
    print("=" * 52)


def pause():
    input("\nPress Enter to return to the menu...")


def add_usernames(config):
    print("Enter usernames/profile links separated by commas.")
    print("Example: @username, https://www.tiktok.com/@another_user")
    raw = input("> ").strip()
    additions = [clean_username(item) for item in raw.split(",")]
    additions = [name for name in additions if name]
    existing = {name.casefold() for name in config["usernames"]}
    added = []
    for name in additions:
        if name.casefold() not in existing:
            config["usernames"].append(name)
            existing.add(name.casefold())
            added.append(name)
    save_config(config)
    if added:
        print("Added: " + ", ".join("@" + name for name in added))
    else:
        print("No new valid usernames were added.")


def edit_wait(config, key, title):
    try:
        value = float(input(f"{title} (0–120 seconds): ").strip())
        if not 0 <= value <= 120:
            raise ValueError
        config[key] = value
        save_config(config)
        print("Saved.")
    except ValueError:
        print("Please enter a number from 0 to 120; no change made.")


def edit_config(config):
    while True:
        print_header()
        print("EDIT CONFIGURATION")
        print("1. Edit message")
        print(f"2. Edit repeat interval (currently {config['interval_hours']} hour(s))")
        print(f"3. Profile-load wait (currently {config['wait_after_profile_load_seconds']} sec)")
        print(f"4. DM-open wait (currently {config['wait_after_message_click_seconds']} sec)")
        print("5. Replace username list")
        print("6. Remove a username")
        print("X. Back")
        choice = input("\nChoose: ").strip().lower()
        if choice == "1":
            value = input("New message (blank cancels): ")
            if value:
                config["message"] = value
                save_config(config)
                print("Message saved.")
        elif choice == "2":
            try:
                value = float(input("Repeat interval in hours (minimum 1): ").strip())
                if value < 1:
                    raise ValueError
                config["interval_hours"] = value
                save_config(config)
                print("Interval saved.")
            except ValueError:
                print("Enter a number greater than or equal to 1.")
        elif choice == "3":
            edit_wait(config, "wait_after_profile_load_seconds", "Wait after profile loads")
        elif choice == "4":
            edit_wait(config, "wait_after_message_click_seconds", "Wait after clicking Message")
        elif choice == "5":
            raw = input("Enter complete username list, separated by commas: ").strip()
            result, seen = [], set()
            for item in raw.split(","):
                name = clean_username(item)
                if name and name.casefold() not in seen:
                    result.append(name)
                    seen.add(name.casefold())
            if result:
                config["usernames"] = result
                save_config(config)
                print(f"Saved {len(result)} username(s).")
            else:
                print("No valid usernames; existing list kept.")
        elif choice == "6":
            for index, name in enumerate(config["usernames"], 1):
                print(f"{index}. @{name}")
            raw = input("Number to remove (blank cancels): ").strip()
            if raw:
                try:
                    removed = config["usernames"].pop(int(raw) - 1)
                    save_config(config)
                    print(f"Removed @{removed}.")
                except (ValueError, IndexError):
                    print("Invalid number.")
        elif choice in ("x", "b", "q"):
            return
        else:
            print("Choose one of the listed options.")
        input("\nPress Enter to continue...")


def show_config(config):
    print_header()
    print("CURRENT CONFIGURATION")
    print(f"Message: {config['message']}")
    print(f"Repeat interval: {config['interval_hours']} hour(s)")
    print(f"Wait after profile loads: {config['wait_after_profile_load_seconds']} sec")
    print(f"Wait after clicking Message: {config['wait_after_message_click_seconds']} sec")
    print(f"Browser profile: {profile_dir(config)}")
    print(f"Config file: {CONFIG_PATH}")
    print(f"\nUsernames ({len(config['usernames'])}):")
    for index, name in enumerate(config["usernames"], 1):
        print(f"  {index:>2}. @{name}")


def find_chromium(playwright):
    explicit = os.environ.get("TIKTOK_CHROMIUM", "").strip()
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.exists():
            return str(candidate)
        raise RuntimeError(f"TIKTOK_CHROMIUM does not exist: {candidate}")
    if platform.system() == "Linux":
        candidates = [shutil.which("chromium"), shutil.which("chromium-browser"),
                      shutil.which("google-chrome"), shutil.which("google-chrome-stable")]
    elif platform.system() == "Windows":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        pf = Path(os.environ.get("PROGRAMFILES", ""))
        pfx86 = Path(os.environ.get("PROGRAMFILES(X86)", ""))
        candidates = [local / "Google/Chrome/Application/chrome.exe",
                      pf / "Google/Chrome/Application/chrome.exe",
                      pfx86 / "Google/Chrome/Application/chrome.exe",
                      local / "Chromium/Application/chrome.exe"]
    else:
        candidates = []
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return playwright.chromium.executable_path


def port_is_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0


def start_chromium(executable, config):
    port = int(config["debug_port"])
    if port_is_open(port):
        print(f"Chromium debug port {port} is already open; reusing it.")
        return None
    prof = profile_dir(config)
    prof.mkdir(parents=True, exist_ok=True)
    command = [executable, f"--user-data-dir={prof}", f"--remote-debugging-port={port}",
               "--no-first-run", "--no-default-browser-check"]
    try:
        extra = {"creationflags": 0x00000200} if platform.system() == "Windows" else {"start_new_session": True}
        return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **extra)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Chromium executable not found: {executable}") from exc


def connect_to_chromium(playwright, config):
    port = int(config["debug_port"])
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            return playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Could not connect to Chromium on port {port}. Close any browser using the bot profile and retry.")


def open_tiktok(config, wait_for_login=False):
    with sync_playwright() as playwright:
        executable = find_chromium(playwright)
        process = start_chromium(executable, config)
        browser = connect_to_chromium(playwright, config)
        if not browser.contexts:
            raise RuntimeError("No Chromium context is available.")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.tiktok.com/", wait_until="domcontentloaded", timeout=30_000)
        page.bring_to_front()
        if wait_for_login:
            print("\nTikTok is open; log in manually if needed. The bot never asks for your password.")
            input("When finished, press Enter here to return to the menu...")
        # Deliberately leave the browser open to preserve the session.
        _ = process


def find_message_button(page):
    try:
        buttons = page.get_by_role("button", name="Message", exact=True)
        for index in range(buttons.count()):
            button = buttons.nth(index)
            try:
                if button.is_visible():
                    return button
            except Exception:
                pass
    except Exception:
        pass
    return None


def interruptible_wait(seconds, stop_event):
    deadline = time.monotonic() + max(0, float(seconds))
    while time.monotonic() < deadline:
        if stop_event.is_set():
            return False
        stop_event.wait(min(0.15, deadline - time.monotonic()))
    return not stop_event.is_set()


def is_blocked(page, response):
    try:
        if response is not None and response.status == 403:
            return True
        title = (page.title() or "").lower()
        return "access denied" in title
    except Exception:
        return False


def warm_up(page, stop_event):
    """Visit the homepage first so TikTok sets its session cookies. Never raises."""
    try:
        page.goto("https://www.tiktok.com/", wait_until="domcontentloaded", timeout=30_000)
        page.bring_to_front()
        print("  Homepage OK.")
    except Exception as exc:
        print(f"  Homepage visit failed ({str(exc).splitlines()[0]}); continuing.")
    interruptible_wait(6, stop_event)


def try_open(page, url, how):
    """Open url; return True if TikTok blocked it (403 / empty error page). Logs what happened."""
    try:
        if how == "click":
            with page.expect_navigation(wait_until="domcontentloaded", timeout=30_000) as nav:
                page.evaluate(
                    "u => { const a = document.createElement('a'); a.href = u; document.body.appendChild(a); a.click(); }",
                    url)
            response = nav.value
        else:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30_000,
                                 referer="https://www.tiktok.com/")
        status = response.status if response else "?"
        title = page.title()
        print(f"  [{how}] HTTP {status} | title: {title!r}")
        return is_blocked(page, response)
    except Exception as exc:
        # Chrome raises ERR_HTTP_RESPONSE_CODE_FAILURE for an empty 403 body instead of returning a response.
        msg = str(exc).splitlines()[0]
        print(f"  [{how}] navigation error: {msg}")
        return "ERR_HTTP_RESPONSE_CODE_FAILURE" in str(exc) or "403" in str(exc)


def open_profile_and_dm(page, username, config, stop_event):
    if stop_event.is_set():
        return False
    print(f"\nOpening profile: @{username}")
    url = f"https://www.tiktok.com/@{username}"
    for attempt, delay in enumerate((0, 20, 45, 90), 1):
        if delay:
            print(f"  Blocked/unreachable. Waiting {delay}s, then attempt {attempt}/4...")
            if not interruptible_wait(delay, stop_event):
                return False
            warm_up(page, stop_event)
            if stop_event.is_set():
                return False
        if not try_open(page, url, "click" if attempt % 2 == 0 else "direct"):
            break
    else:
        raise RuntimeError(f"TikTok kept blocking @{username} after 4 attempts (intermittent 403 = IP/network reputation). Skipping.")
    if not interruptible_wait(config["wait_after_profile_load_seconds"], stop_event):
        return False
    button, deadline = None, time.time() + 20
    while time.time() < deadline and not stop_event.is_set():
        button = find_message_button(page)
        if button is not None:
            break
        time.sleep(0.25)
    if stop_event.is_set():
        return False
    if button is None:
        raise RuntimeError(f"Profile Message button not found for @{username}")
    print(f"Clicking profile Message button for @{username}...")
    button.click()
    print(f"Waiting {config['wait_after_message_click_seconds']} second(s) for DM...")
    return interruptible_wait(config["wait_after_message_click_seconds"], stop_event)


def send_message(page, username, config, stop_event):
    if stop_event.is_set():
        return False
    print(f"Typing message for @{username}...")
    page.bring_to_front()
    # Matches the previously working method: Playwright keyboard.type(), then Enter.
    page.keyboard.type(config["message"])
    if stop_event.is_set():
        print("Cancellation requested; message left unsent in the composer.")
        return False
    page.keyboard.press("Enter")
    print(f"Enter pressed for @{username}; moving to the next username.")
    return True


def run_once(browser, config, stop_event):
    if not browser.contexts:
        raise RuntimeError("No Chromium context was found.")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    total = len(config["usernames"])
    if not stop_event.is_set():
        try:
            warm_up(page, stop_event)
        except Exception as exc:
            print(f"Warm-up failed (continuing anyway): {exc}")
    for index, username in enumerate(config["usernames"], 1):
        if stop_event.is_set():
            break
        print(f"\n[{index}/{total}] Processing @{username}")
        try:
            if not open_profile_and_dm(page, username, config, stop_event):
                break
            if not send_message(page, username, config, stop_event):
                break
        except PlaywrightTimeoutError as exc:
            print(f"TIMEOUT @{username}: {exc}")
        except Exception as exc:
            print(f"ERROR @{username}: {exc}")


def bot_worker(config, stop_event):
    try:
        with sync_playwright() as playwright:
            executable = find_chromium(playwright)
            print(f"Using Chromium: {executable}")
            _process = start_chromium(executable, config)
            browser = connect_to_chromium(playwright, config)
            while not stop_event.is_set():
                print("\nStarting bot run...")
                run_once(browser, config, stop_event)
                if stop_event.is_set():
                    break
                seconds = float(config["interval_hours"]) * 3600
                print(f"\nRun finished. Next run in {config['interval_hours']} hour(s). Press X to stop.")
                stop_event.wait(seconds)
    except Exception as exc:
        print(f"\nBOT ERROR: {exc}")


def read_key_nonblocking():
    """Read one key without Enter on supported Windows/Linux interactive terminals."""
    if platform.system() == "Windows":
        import msvcrt
        return msvcrt.getwch() if msvcrt.kbhit() else None
    if not sys.stdin.isatty():
        return None
    import select
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        return sys.stdin.read(1) if ready else None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def start_bot_menu(config):
    if not config["usernames"]:
        print("No usernames configured; add at least one first.")
        pause()
        return
    print_header()
    print(f"This will submit the configured message to {len(config['usernames'])} username(s).")
    print(f"Message: {config['message']!r}")
    print(f"Repeat interval: {config['interval_hours']} hour(s)")
    if input("Start now? [y/N]: ").strip().lower() != "y":
        print("Start cancelled.")
        pause()
        return
    stop_event = threading.Event()
    worker = threading.Thread(target=bot_worker, args=(config.copy(), stop_event), daemon=True)
    worker.start()
    print("\nBOT RUNNING — press X (no Enter required) to stop and return to menu.")
    try:
        while worker.is_alive():
            key = read_key_nonblocking()
            if key and key.lower() == "x":
                print("\nX pressed; stopping at the next safe checkpoint...")
                stop_event.set()
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nCtrl+C pressed; requesting stop...")
        stop_event.set()
    worker.join()
    print("\nBot stopped. Returning to the menu.")
    pause()


def main():
    try:
        config = load_config()
    except RuntimeError as exc:
        print(exc)
        return
    while True:
        print_header()
        print(f"Configured users: {len(config['usernames'])} | Repeat: every {config['interval_hours']} hour(s)")
        print("\n1. Add username(s)")
        print("2. Edit configuration")
        print("3. Start bot")
        print("4. Open TikTok / log in")
        print("5. View configuration")
        print("X. Exit")
        choice = input("\nChoose an option: ").strip().lower()
        if choice == "1":
            add_usernames(config)
            pause()
            config = load_config()
        elif choice == "2":
            edit_config(config)
            config = load_config()
        elif choice == "3":
            start_bot_menu(config)
            config = load_config()
        elif choice == "4":
            try:
                print("Opening TikTok using the bot's saved browser profile...")
                open_tiktok(config, wait_for_login=True)
                print("Login/session step finished.")
            except Exception as exc:
                print(f"Could not open TikTok: {exc}")
            pause()
            config = load_config()
        elif choice == "5":
            show_config(config)
            pause()
        elif choice in ("x", "q", "exit"):
            print("Goodbye.")
            break
        else:
            print("Invalid option.")
            time.sleep(1)


if __name__ == "__main__":
    main()
