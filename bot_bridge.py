"""Subprocess adapter: run the user's existing bot with its own interpreter/environment."""
import importlib.util, json, sys, threading, time, traceback
from pathlib import Path

def main():
    if len(sys.argv) != 4: raise SystemExit("Usage: bot_bridge.py BOT_SOURCE CONFIG_JSON run|login")
    source, config_file, mode = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), sys.argv[3]
    if not source.is_file(): raise SystemExit(f"Bot file not found: {source}")
    config = json.loads(config_file.read_text(encoding="utf-8"))
    sys.path.insert(0, str(source.parent))
    spec = importlib.util.spec_from_file_location("streak_existing_bot", source)
    if not spec or not spec.loader: raise SystemExit("Could not load bot module")
    bot = importlib.util.module_from_spec(spec); spec.loader.exec_module(bot)
    if mode == "login":
        if not hasattr(bot, "open_tiktok"): raise SystemExit("This bot version does not expose open_tiktok(config, wait_for_login=True)")
        bot.open_tiktok(config, wait_for_login=True); return
    if not hasattr(bot, "bot_worker"):
        raise SystemExit("This bot version doesn't expose bot_worker(config, stop_event); cannot safely control it through this adapter")
    stop_event = threading.Event()
    def listen():
        try:
            for line in sys.stdin:
                if line.strip().upper() == "STOP": stop_event.set(); break
        except Exception: pass
    threading.Thread(target=listen, daemon=True).start()
    print("Adapter connected to existing bot; stop command listener ready", flush=True)
    bot.bot_worker(config, stop_event)

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(f"BOT ERROR: {exc}", flush=True); traceback.print_exc(); raise
