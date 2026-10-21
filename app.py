from __future__ import annotations
import threading, socket, sys
from pathlib import Path
from werkzeug.serving import make_server
from backend import Backend, ROOT
from web_dashboard import create_app
from terminal_ui import run, lan_ips

class ServerThread(threading.Thread):
    def __init__(self, backend, name, port, mobile):
        super().__init__(daemon=True, name=f"web-{name}"); self.backend=backend; self.name_key=name; self.port=port; self.mobile=mobile; self.server=None; self.error=None
    def run(self):
        try:
            self.server=make_server('0.0.0.0', self.port, create_app(self.backend,self.mobile), threaded=True)
            self.backend.state['servers'][self.name_key]={'status':'online','port':self.port,'address':f'0.0.0.0:{self.port}'}
            self.server.serve_forever()
        except OSError as exc:
            self.error=exc; self.backend.state['servers'][self.name_key]={'status':'conflict/error','port':self.port,'error':str(exc)}
            self.backend.log(f"SERVER {self.name_key.upper()} FAILED on port {self.port}: {exc}")
    def shutdown(self):
        if self.server:
            try: self.server.shutdown()
            except Exception: pass

def main():
    backend=Backend(ROOT)
    print('STREAK CONTROL CENTER v2.0.0')
    print('Dashboard password (keep private):', backend.config['auth_password'])
    print('Auto-detected bot:', backend.config.get('bot_source') or 'NOT FOUND — expected ~/tiktok-streak-dashboard/bot.py or ~/tiktok-python-bot/bot.py')
    servers=[]
    for name,port,mobile in [('pc',int(backend.config['pc_port']),False),('phone',int(backend.config['phone_port']),True)]:
        thread=ServerThread(backend,name,port,mobile); thread.start(); servers.append(thread)
    # Give bind attempts time to settle before presenting the actual status.
    for thread in servers: thread.join(timeout=.25)
    print('LAN IPs:', ', '.join(lan_ips()))
    print('PC URL:    http://127.0.0.1:%s' % backend.config['pc_port'])
    print('Phone URL: http://LAN-IP:%s' % backend.config['phone_port'])
    for t in servers:
        if t.error: print(f"ERROR: {t.name_key} dashboard could not bind port {t.port}: {t.error}")
        elif t.server: print(f"{t.name_key.upper()} dashboard listening on 0.0.0.0:{t.port}")
    try: run(backend)
    finally:
        backend.stop_bot()
        for t in servers: t.shutdown()
if __name__=='__main__': main()
