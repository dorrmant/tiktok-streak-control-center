import os, re, shutil, socket, sys, time

# ── Streak Control Center · terminal UI · made by Dorrmant ─────────────────────
USE_COLOR = sys.stdout.isatty() and not os.environ.get('NO_COLOR')
VIOLET, PINK, CYAN = (139, 92, 246), (236, 72, 153), (34, 211, 238)
GREEN, RED, YELLOW, MUTED, TEXT = (74, 222, 128), (251, 113, 133), (251, 191, 36), (155, 149, 184), (241, 238, 252)
ANSI = re.compile(r'\x1b\[[0-9;]*m')

def rgb(c, s, bold=False):
    if not USE_COLOR: return str(s)
    return f"\x1b[{'1;' if bold else ''}38;2;{c[0]};{c[1]};{c[2]}m{s}\x1b[0m"

def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def gradient(text, stops=(CYAN, VIOLET, PINK), bold=True):
    if not USE_COLOR or not text: return text
    n, out = max(len(text) - 1, 1), []
    for i, ch in enumerate(text):
        t = i / n * (len(stops) - 1); k = min(int(t), len(stops) - 2)
        out.append(rgb(lerp(stops[k], stops[k + 1], t - k), ch, bold))
    return ''.join(out)

def vis(s): return len(ANSI.sub('', s))
def pad(s, w): return s + ' ' * max(0, w - vis(s))
def clip(s, w): return s if len(s) <= w else s[:max(0, w - 1)] + '…'
def width(): return max(52, min(shutil.get_terminal_size((80, 24)).columns - 2, 84))

def lan_ips():
    ips = []
    try:  # most reliable: ask the OS which interface routes outward (no packets are sent)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(('10.255.255.255', 1)); ip = probe.getsockname()[0]
            if not ip.startswith('127.'): ips.append(ip)
    except OSError: pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith('127.') and ip not in ips: ips.append(ip)
    except OSError: pass
    return ips or ['LAN IP not detected']

def panel(title, lines, w, accent=VIOLET):
    inner = w - 4
    head = rgb(accent, '╭─ ') + rgb(TEXT, title.upper(), True) + ' ' + rgb(accent, '─' * max(0, w - 5 - len(title)) + '╮')
    print(head)
    for line in lines: print(rgb(accent, '│ ') + pad(line, inner) + rgb(accent, ' │'))
    print(rgb(accent, '╰' + '─' * (w - 2) + '╯'))

def pill(state):
    color = GREEN if state == 'running' else RED if state == 'error' else YELLOW
    return rgb(color, '● ' + state.upper(), True)

def log_color(msg):
    low = msg.lower()
    if re.search(r'error|failed|403|blocked|traceback', low): return RED
    if re.search(r'wait|cool|retry|warn', low): return YELLOW
    if re.search(r'clicking|enter pressed|started|connected|homepage ok', low): return GREEN
    return TEXT

def log_line(e, w):
    return rgb(MUTED, f"[{e['time']}] ") + rgb(log_color(e['message']), clip(e['message'], w - 14))

def banner(w):
    art = [" ✦  S T R E A K   C O N T R O L   C E N T E R  ✦"]
    print()
    print(rgb(VIOLET, '╭' + '─' * (w - 2) + '╮'))
    for a in art: print(rgb(VIOLET, '│') + ' ' * ((w - 2 - len(a)) // 2) + gradient(a) + ' ' * (w - 2 - len(a) - (w - 2 - len(a)) // 2) + rgb(VIOLET, '│'))
    sub = 'terminal · pc · phone   —   made by Dorrmant'
    left = (w - 2 - len(sub)) // 2
    styled = sub.replace('Dorrmant', rgb(CYAN, 'Dorrmant', True))
    print(rgb(VIOLET, '│') + ' ' * left + rgb(MUTED, '') + styled.replace('terminal · pc · phone   —   made by ', rgb(MUTED, 'terminal · pc · phone   —   made by ')) + ' ' * (w - 2 - len(sub) - left) + rgb(VIOLET, '│'))
    print(rgb(VIOLET, '╰' + '─' * (w - 2) + '╯'))

def footer(w):
    msg = '✦  designed & built with ♥ by Dorrmant  ✦'
    print(' ' * ((w - len(msg)) // 2) + gradient(msg))

def _typed_line():
    """Return a line typed by the user (after Enter) without blocking, or None."""
    try:
        if os.name == 'nt':
            import msvcrt
            if msvcrt.kbhit():
                return (msvcrt.getwch() + '').strip().lower() or 'x'
            return None
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            data = os.read(sys.stdin.fileno(), 1024).decode(errors='ignore').strip().lower()
            return (data.splitlines() or ['x'])[0] or 'x'
    except Exception: pass
    return None

def live_logs(backend):
    print(gradient('— live logs —') + rgb(MUTED, '  type ') + rgb(PINK, 'x', True) + rgb(MUTED, ' + Enter (or Ctrl+C) to go back · ') + rgb(PINK, '4', True) + rgb(MUTED, ' + Enter stops the bot'))
    last = None
    try:
        while True:
            logs = backend.snapshot()['state']['logs']
            new = logs[logs.index(last) + 1:] if last in logs else logs
            for e in new: print(log_line(e, 200))
            if logs: last = logs[-1]
            typed = _typed_line()
            if typed in ('x', 'q', 'b', '0'): break
            if typed == '4': print(rgb(YELLOW, 'Bot state: ' + backend.stop_bot(), True))
            time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    print()

def key(n, label, hint=''):
    return rgb(PINK, f'[{n}]', True) + ' ' + rgb(TEXT, label) + (rgb(MUTED, '  ' + hint) if hint else '')

def run(backend):
    while True:
        snap = backend.snapshot(); cfg = snap['config']; state = snap['state']; ips = lan_ips(); ip = ips[0]
        pw = backend.config['auth_password']; ports = state.get('servers', {}); w = width()
        os.system('clear' if os.name == 'posix' else 'cls')
        banner(w)
        pc_url = 'http://127.0.0.1:%s' % cfg['pc_port']; phone_url = 'http://%s:%s' % (ip, cfg['phone_port'])
        dot = lambda s: rgb(GREEN, '● online') if s == 'online' else rgb(YELLOW, '● ' + str(s))
        panel('Status', [
            f"{rgb(MUTED,'Bot        ')} {pill(state['status'])}   {rgb(MUTED,'integration')} " + (rgb(GREEN, 'READY') if snap['bot_integrated'] else rgb(RED, 'NOT FOUND')),
            f"{rgb(MUTED,'Users      ')} {rgb(CYAN, len(cfg['usernames']), True)}   {rgb(MUTED,'every')} {rgb(CYAN, str(cfg['interval_hours']) + 'h', True)}",
            f"{rgb(MUTED,'PC         ')} {rgb(TEXT, pc_url)}  {dot(ports.get('pc', {}).get('status', 'starting'))}",
            f"{rgb(MUTED,'Phone      ')} {rgb(TEXT, phone_url)}  {dot(ports.get('phone', {}).get('status', 'starting'))}",
            f"{rgb(MUTED,'Password   ')} {rgb(YELLOW, pw, True)}",
        ], w)
        panel('Menu', [
            key(1, 'Check bot status') + '      ' + key(5, 'Open TikTok / login'),
            key(2, 'View configuration') + '    ' + key(6, 'Show web URLs'),
            key(3, 'Start bot') + '             ' + key(7, 'Check ports'),
            key(4, 'Stop bot') + '              ' + key(8, 'Edit message / interval / users'),
            key(9, 'Live logs', '(x / Ctrl+C = back)') + '   ' + key(0, 'Exit'),
        ], w, PINK)
        recent = state.get('logs', [])[-8:]
        panel('Recent log', [log_line(e, w - 4) for e in recent] or [rgb(MUTED, 'No activity yet.')], w, CYAN)
        footer(w)
        try: choice = input('\n  ' + gradient('dorrmant') + rgb(MUTED, '@') + gradient('control') + rgb(PINK, ' ❯ ', True)).strip().lower()
        except (EOFError, OSError): print('\nTerminal input unavailable. Relaunch with ./run.sh in a real terminal.'); return
        try:
            if choice == '1':
                s = backend.snapshot(); print(f"Status: {s['state']['status']}"); print(f"Bot: {s['config'].get('bot_source') or 'not found'}"); print(f"Last error: {s['state'].get('last_error') or 'none'}")
            elif choice == '2':
                c = backend.public_config(); print(f"Bot source: {c.get('bot_source') or 'not found'}\nUsers: {', '.join('@' + u for u in c['usernames'])}\nMessage: {c['message']}\nInterval: {c['interval_hours']} hours\nBrowser profile: {c.get('profile_dir') or '(bot default)'}")
            elif choice == '3':
                ok, msg = backend.start_bot(); print(msg)
            elif choice == '4': print('Bot state:', backend.stop_bot())
            elif choice == '5':
                ok, msg = backend.open_tiktok(); print(msg)
            elif choice == '6': print(f"PC local: http://127.0.0.1:{cfg['pc_port']}\nPC/LAN: http://{ip}:{cfg['pc_port']}\nPhone: http://{ip}:{cfg['phone_port']}\nPassword: {pw}")
            elif choice == '7':
                for port in (cfg['pc_port'], cfg['phone_port']): print(f"Port {port}: {'IN USE' if backend.port_status(port) else 'available (not necessarily listening by this app)'}")
            elif choice == '8':
                msg = input('Message (blank keeps current): ')
                interval = input(f"Repeat interval hours [{cfg['interval_hours']}]: ").strip()
                users = input('Usernames comma-separated (blank keeps current): ').strip()
                values = {}
                if msg: values['message'] = msg
                if interval: values['interval_hours'] = float(interval)
                if users: values['usernames'] = [x.strip().removeprefix('@') for x in users.split(',') if x.strip()]
                backend.save_config(values); print('Configuration saved.')
            elif choice == '9':
                live_logs(backend); continue
            elif choice in ('0', 'q', 'x'):
                backend.stop_bot(); print(gradient('Stopping web servers… see you · made by Dorrmant')); return
            else: print('Choose one of the listed options.')
        except Exception as exc: print(f"ERROR: {exc}")
        try: input('\n' + rgb(MUTED, '↳ Press Enter to return to menu...'))
        except (EOFError, OSError): return
