from __future__ import annotations
import json, os, secrets, socket, subprocess, sys, threading, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
DEFAULTS = {
    "version": "2.0.0", "pc_port": 8765, "phone_port": 8766,
    "bot_source": "", "usernames": [], "message": "", "interval_hours": 12,
    "debug_port": 9222, "profile_dir": "", "wait_after_profile_load_seconds": 3,
    "wait_after_message_click_seconds": 5, "auth_password": ""
}

def discover_bot():
    candidates = [
        ROOT / "bot" / "bot.py",                      # bundled bot (default)
        HOME / "tiktok-streak-dashboard" / "bot.py",  # optional: your own bot elsewhere
        HOME / "tiktok-python-bot" / "bot.py",
    ]
    for path in candidates:
        if path.is_file(): return str(path.resolve())
    return ""

class Backend:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.config_path = self.root / "config.json"
        self.lock = threading.RLock()
        self.worker = None
        self.stop_requested = False
        self.process = None
        if self.config_path.exists():
            try: loaded = json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception: loaded = {}
        else: loaded = {}
        self.config = DEFAULTS.copy(); self.config.update(loaded)
        detected = discover_bot()
        if not self.config.get("bot_source") or not Path(str(self.config["bot_source"])).expanduser().is_file():
            self.config["bot_source"] = detected
        # Seed a brand-new control-center config from the existing bot config, read-only.
        if detected and not loaded.get("usernames") and not loaded.get("message"):
            try:
                old_cfg = json.loads((Path(detected).parent / "config.json").read_text(encoding="utf-8"))
                for key in ("usernames", "message", "interval_hours", "debug_port", "profile_dir", "wait_after_profile_load_seconds", "wait_after_message_click_seconds"):
                    if key in old_cfg: self.config[key] = old_cfg[key]
            except (OSError, ValueError): pass
        if not self.config.get("auth_password"): self.config["auth_password"] = secrets.token_urlsafe(12)
        self.state = {"status":"stopped", "started_at":None, "last_finished":None, "last_error":"", "logs":[], "servers":{}}
        self.save()
    def save(self):
        self.config_path.write_text(json.dumps(self.config, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
        try: self.config_path.chmod(0o600)
        except OSError: pass
    def public_config(self): return {k:v for k,v in self.config.items() if k != "auth_password"}
    def log(self, message):
        with self.lock:
            self.state["logs"].append({"time":datetime.now().strftime("%H:%M:%S"), "message":str(message).replace("Press X to stop.", "Use [4] Stop bot to end.")[:500]})
            self.state["logs"] = self.state["logs"][-100:]
    def snapshot(self):
        with self.lock:
            return {"state": {**self.state, "logs":list(self.state["logs"]), "servers":dict(self.state["servers"])},
                    "config":self.public_config(), "bot_integrated":bool(self.config.get("bot_source") and Path(self.config["bot_source"]).expanduser().is_file())}
    def save_config(self, values):
        with self.lock:
            for key in ("usernames", "message", "interval_hours", "wait_after_profile_load_seconds", "wait_after_message_click_seconds", "debug_port", "profile_dir"):
                if key in values: self.config[key] = values[key]
            self.config["usernames"] = list(dict.fromkeys(str(x).strip().removeprefix("@").strip() for x in self.config.get("usernames", []) if str(x).strip()))
            self.config["interval_hours"] = float(self.config["interval_hours"])
            if self.config["interval_hours"] < 1: raise ValueError("Repeat interval must be at least 1 hour")
            for k in ("wait_after_profile_load_seconds", "wait_after_message_click_seconds"):
                self.config[k] = float(self.config[k])
                if not 0 <= self.config[k] <= 120: raise ValueError(f"{k} must be between 0 and 120 seconds")
            self.save()
        self.log("Configuration saved")
    def _bot_python(self, source):
        folder = Path(source).resolve().parent
        for candidate in (folder/".venv/bin/python", folder/"venv/bin/python"):
            if candidate.is_file() and os.access(candidate, os.X_OK): return str(candidate)
        return sys.executable
    def start_bot(self):
        with self.lock:
            if self.process and self.process.poll() is None: return False, "Bot is already running"
            source = str(self.config.get("bot_source", "")).strip()
            if not source or not Path(source).expanduser().is_file():
                source = discover_bot()
                if source: self.config["bot_source"] = source; self.save()
            if not source: return False, "Couldn't auto-detect bot.py. Expected ~/tiktok-streak-dashboard/bot.py or ~/tiktok-python-bot/bot.py"
            if not self.config.get("usernames"): return False, "Add at least one username in configuration before starting"
            if not str(self.config.get("message", "")).strip(): return False, "Set a message in configuration before starting"
            source = str(Path(source).expanduser().resolve())
            payload = {k:v for k,v in self.config.items() if k not in ("auth_password", "bot_source", "pc_port", "phone_port", "version")}
            payload_path = self.root / ".bot-runtime-config.json"
            payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8"); payload_path.chmod(0o600)
            py = self._bot_python(source)
            self.stop_requested = False
            cmd = [py, str(self.root/"bot_bridge.py"), source, str(payload_path), "run"]
            try:
                self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=str(Path(source).parent), env={**os.environ, 'PYTHONUNBUFFERED':'1'})
            except Exception as exc:
                self.state.update(status="error", last_error=str(exc)); return False, f"Couldn't launch bot: {exc}"
            self.state.update(status="running", started_at=datetime.now().isoformat(timespec="seconds"), last_error="")
            self.log(f"Bot launched with its own Python environment: {py}")
            self.worker = threading.Thread(target=self._watch_process, daemon=True); self.worker.start()
            return True, "Bot started"
    def _watch_process(self):
        proc = self.process
        if not proc: return
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if line: self.log(line)
            code = proc.wait()
            with self.lock:
                if self.state["status"] not in ("stopping", "error"):
                    self.state["status"] = "stopped" if code == 0 else "error"
                    if code: self.state["last_error"] = f"Bot process exited with code {code}; see logs"
                self.state["last_finished"] = datetime.now().isoformat(timespec="seconds")
            self.log(f"Bot process ended (exit {code})")
        except Exception as exc:
            self.log(f"Bot output reader error: {exc}")
    def stop_bot(self):
        proc = self.process
        if not proc or proc.poll() is not None:
            self.state["status"] = "stopped"; return "stopped"
        self.state["status"] = "stopping"
        try:
            if proc.stdin: proc.stdin.write("STOP\n"); proc.stdin.flush()
            proc.wait(timeout=4)
        except Exception:
            proc.terminate()
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: proc.kill()
        if proc.poll() is not None: self.state["status"] = "stopped"
        self.log("Stop requested")
        return self.state["status"]
    def open_tiktok(self):
        source = str(self.config.get("bot_source", "")).strip() or discover_bot()
        if not source or not Path(source).is_file(): return False, "Couldn't auto-detect the existing bot.py"
        payload = {k:v for k,v in self.config.items() if k not in ("auth_password", "bot_source", "pc_port", "phone_port", "version")}
        p = self.root/".bot-runtime-config.json"; p.write_text(json.dumps(payload), encoding="utf-8"); p.chmod(0o600)
        cmd = [self._bot_python(source), str(self.root/"bot_bridge.py"), str(Path(source).resolve()), str(p), "login"]
        try:
            subprocess.Popen(cmd, cwd=str(Path(source).resolve().parent), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            self.log("Browser/login launch requested")
            return True, "Browser launch requested; authenticate manually if prompted"
        except Exception as exc: return False, str(exc)
    def port_status(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(.25); return s.connect_ex(("127.0.0.1", int(port))) == 0
