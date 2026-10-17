from flask import Flask, request, session, redirect, url_for, render_template_string, jsonify, abort
import hmac, secrets

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#07060f"><title>Streak Control Center · Dorrmant</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet"><style>
:root{color-scheme:dark;--bg:#07060f;--card:rgba(255,255,255,.045);--line:rgba(255,255,255,.10);--text:#f1eefc;--muted:#9b95b8;--a:#8b5cf6;--b:#ec4899;--c:#22d3ee;--green:#4ade80;--red:#fb7185;--yellow:#fbbf24}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;min-height:100vh;color:var(--text);font:15px/1.55 'Space Grotesk',system-ui,sans-serif;background:var(--bg);position:relative;overflow-x:hidden}
body:before,body:after{content:"";position:fixed;z-index:-1;border-radius:50%;filter:blur(110px);opacity:.45;pointer-events:none}
body:before{width:520px;height:520px;background:var(--a);top:-160px;left:-120px}
body:after{width:480px;height:480px;background:var(--b);bottom:-180px;right:-120px;opacity:.30}
.wrap{max-width:1080px;margin:auto;padding:22px 16px 40px}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:22px}
.brand{display:flex;align-items:center;gap:14px}
.logo{width:46px;height:46px;border-radius:14px;display:grid;place-items:center;font-size:22px;background:linear-gradient(135deg,var(--a),var(--b));box-shadow:0 8px 30px rgba(139,92,246,.45)}
h1{margin:0;font-size:clamp(22px,4.5vw,32px);letter-spacing:-.02em;background:linear-gradient(90deg,#fff,#c4b5fd 60%,#f9a8d4);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--muted);font-size:13px;margin-top:2px}.sub b{color:var(--c);font-weight:600}
a{color:var(--muted);text-decoration:none}a:hover{color:var(--text)}
.out{border:1px solid var(--line);border-radius:99px;padding:7px 14px;font-size:13px;background:var(--card)}
.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:16px}
.card{grid-column:span 6;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:20px;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);min-width:0;transition:border-color .2s,transform .2s}
.card:hover{border-color:rgba(167,139,250,.35)}.wide{grid-column:1/-1}
h2{margin:0 0 14px;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);font-weight:700;display:flex;align-items:center;gap:8px}
h2:before{content:"";width:18px;height:2px;border-radius:2px;background:linear-gradient(90deg,var(--a),var(--b))}
.row{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.pill{display:inline-flex;align-items:center;gap:8px;border-radius:99px;padding:6px 14px;font-size:12px;font-weight:700;letter-spacing:.08em;border:1px solid currentColor;background:rgba(255,255,255,.04)}
.pill:before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor;box-shadow:0 0 10px currentColor}
.green{color:var(--green)}.red{color:var(--red)}.yellow{color:var(--yellow)}.green:before{animation:pulse 1.6s infinite}
@keyframes pulse{50%{opacity:.3}}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:6px 0 14px}
.stat{padding:14px;border-radius:14px;background:rgba(0,0,0,.28);border:1px solid var(--line);overflow-wrap:anywhere}
.stat strong{display:block;font-size:20px;background:linear-gradient(90deg,var(--c),#a78bfa);-webkit-background-clip:text;background-clip:text;color:transparent}
.stat span{font-size:12px;color:var(--muted)}
.muted{color:var(--muted)}p{margin:6px 0}.small{font-size:12px}
label{display:block;color:var(--muted);margin:14px 0 6px;font-size:12px;letter-spacing:.04em}
input,textarea{width:100%;padding:12px 14px;border-radius:12px;border:1px solid var(--line);background:rgba(0,0,0,.30);color:var(--text);font:inherit;outline:none;transition:border-color .15s,box-shadow .15s}
input:focus,textarea:focus{border-color:var(--a);box-shadow:0 0 0 3px rgba(139,92,246,.22)}textarea{min-height:80px;resize:vertical}
button{border:0;border-radius:12px;color:#fff;font:inherit;font-weight:700;padding:11px 18px;margin:12px 8px 0 0;cursor:pointer;background:linear-gradient(135deg,var(--a),var(--b));box-shadow:0 6px 22px rgba(139,92,246,.35);transition:transform .15s,filter .15s}
button:hover{transform:translateY(-2px);filter:brightness(1.1)}button:active{transform:none}
.ghost{background:rgba(255,255,255,.06);box-shadow:none;border:1px solid var(--line)}
.danger{background:linear-gradient(135deg,#e11d48,#fb7185);box-shadow:0 6px 22px rgba(244,63,94,.3)}
.log{height:340px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;background:rgba(0,0,0,.45);border:1px solid var(--line);padding:14px;border-radius:14px;font:12.5px/1.65 'JetBrains Mono',ui-monospace,monospace;color:#cfe9f2}
.log .e{color:var(--red)}.log .ok{color:var(--green)}.log .w{color:var(--yellow)}.log .t{color:#6e6890}
.flash{border:1px solid var(--b);background:rgba(236,72,153,.10);padding:12px 14px;border-radius:14px;margin-bottom:16px;overflow-wrap:anywhere}
footer{margin-top:34px;text-align:center;color:var(--muted);font-size:13px}
footer b{background:linear-gradient(90deg,var(--c),#a78bfa,var(--b));-webkit-background-clip:text;background-clip:text;color:transparent;font-size:15px;letter-spacing:.04em}
@media(max-width:820px){.card{grid-column:1/-1}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:480px){.wrap{padding:16px 12px 30px}.card{padding:16px;border-radius:16px}button{width:100%;margin-right:0}.log{height:260px}}
</style></head><body><div class="wrap">
<div class="top"><div class="brand"><div class="logo">✦</div><div><h1>Streak Control Center</h1><div class="sub">terminal · PC · phone &nbsp;—&nbsp; made by <b>Dorrmant</b></div></div></div><a href="/logout" class="out">Log out</a></div>
{% if error %}<div class="flash">{{ error }}</div>{% endif %}
<div class="grid">
<section class="card wide"><div class="row"><h2>Live status</h2><span class="pill {{ 'green' if state.status=='running' else 'red' if state.status=='error' else 'yellow' }}">{{ state.status|upper }}</span></div>
<div class="stats"><div class="stat"><strong>{{ config.usernames|length }}</strong><span>Configured users</span></div><div class="stat"><strong>{{ config.interval_hours }}h</strong><span>Repeat interval</span></div><div class="stat"><strong>{{ 'Detected' if integrated else 'Not found' }}</strong><span>Existing bot</span></div><div class="stat"><strong>{{ state.servers|length }}</strong><span>Web servers</span></div></div>
<p class="muted small">Bot: {{ bot_source or 'No bot found in the usual folders' }}</p><p class="muted small">Last error: {{ state.last_error or 'none' }}</p>
<form method="post" action="/action"><input type="hidden" name="csrf" value="{{ csrf }}"><button name="action" value="start">▶ Start bot</button><button class="danger" name="action" value="stop">■ Stop bot</button><button class="ghost" name="action" value="login">↗ Open TikTok / login</button></form></section>
<section class="card wide"><div class="row"><h2>Live log</h2><span class="muted small">auto-refreshing</span></div><div class="log" id="livelog">{% for e in logs[-35:] %}[{{ e.time }}] {{ e.message }}
{% else %}No activity yet.{% endfor %}</div></section>
<section class="card"><h2>Bot config</h2><form method="post" action="/config"><input type="hidden" name="csrf" value="{{ csrf }}"><label>Usernames (one per line)</label><textarea name="usernames">{{ config.usernames|join('\n') }}</textarea><label>Message</label><textarea name="message" required>{{ config.message }}</textarea><label>Repeat interval (hours; minimum 1)</label><input name="interval_hours" type="number" min="1" step="0.5" value="{{ config.interval_hours }}" required><label>Wait after profile opens (seconds)</label><input name="wait_after_profile_load_seconds" type="number" min="0" max="120" step="0.5" value="{{ config.wait_after_profile_load_seconds }}"><label>Wait after opening DM (seconds)</label><input name="wait_after_message_click_seconds" type="number" min="0" max="120" step="0.5" value="{{ config.wait_after_message_click_seconds }}"><label>Browser profile path (optional)</label><input name="profile_dir" value="{{ config.profile_dir }}"><button>Save configuration</button></form><p class="muted small" style="margin-top:14px">Bot path is auto-detected; original source/config/profile are not edited by this app.</p></section>
<section class="card"><h2>Network</h2><p>PC / LAN &nbsp;<b>:{{ config.pc_port }}</b> &nbsp;<span class="muted">{{ state.servers.get('pc',{}).get('status','offline') }}</span></p><p>Phone &nbsp;<b>:{{ config.phone_port }}</b> &nbsp;<span class="muted">{{ state.servers.get('phone',{}).get('status','offline') }}</span></p><p class="muted small" style="margin-top:14px">Use the LAN IP shown in the terminal. Never port-forward these ports to the internet.</p></section>
</div>
<footer>Designed &amp; built ♥ by <b>Dorrmant</b></footer></div>
<script>
(function(){var el=document.getElementById('livelog');if(!el)return;
function esc(t){return t.replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function line(e){var m=esc(e.message),c='';if(/error|failed|403|blocked|traceback/i.test(e.message))c='e';else if(/warn|wait|cool|retry/i.test(e.message))c='w';else if(/clicking|enter pressed|ok|started|connected/i.test(e.message))c='ok';
return '<span class="t">['+e.time+']</span> <span class="'+c+'">'+m+'</span>';}
function tick(){fetch('/logs.json',{credentials:'same-origin'}).then(function(r){return r.ok?r.json():null}).then(function(d){if(!d)return;
var stick=el.scrollTop+el.clientHeight>=el.scrollHeight-24;
el.innerHTML=d.logs.length?d.logs.map(line).join('\n'):'No activity yet.';
if(stick)el.scrollTop=el.scrollHeight;}).catch(function(){});}
el.scrollTop=el.scrollHeight;setInterval(tick,1500);tick();})();
</script></body></html>
'''
LOGIN = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#07060f"><title>Streak Control Center · Login</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet"><style>
:root{color-scheme:dark;--a:#8b5cf6;--b:#ec4899;--c:#22d3ee;--line:rgba(255,255,255,.10);--muted:#9b95b8}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:16px;background:#07060f;color:#f1eefc;font:15px/1.55 'Space Grotesk',system-ui,sans-serif;overflow:hidden}
body:before,body:after{content:"";position:fixed;z-index:-1;border-radius:50%;filter:blur(110px);pointer-events:none}
body:before{width:520px;height:520px;background:var(--a);top:-160px;left:-120px;opacity:.5}body:after{width:480px;height:480px;background:var(--b);bottom:-180px;right:-120px;opacity:.35}
.card{width:min(100%,420px);padding:34px 28px;border-radius:24px;background:rgba(255,255,255,.05);border:1px solid var(--line);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);text-align:center}
.logo{width:58px;height:58px;margin:0 auto 16px;border-radius:18px;display:grid;place-items:center;font-size:27px;background:linear-gradient(135deg,var(--a),var(--b));box-shadow:0 10px 34px rgba(139,92,246,.5)}
h1{margin:0 0 6px;font-size:26px;letter-spacing:-.02em;background:linear-gradient(90deg,#fff,#c4b5fd 60%,#f9a8d4);-webkit-background-clip:text;background-clip:text;color:transparent}
p{margin:0 0 18px;color:var(--muted);font-size:14px}
input,button{width:100%;padding:13px 15px;margin-top:12px;border-radius:13px;font:inherit}
input{background:rgba(0,0,0,.32);color:#f1eefc;border:1px solid var(--line);outline:none;text-align:center;letter-spacing:.06em}input:focus{border-color:var(--a);box-shadow:0 0 0 3px rgba(139,92,246,.22)}
button{border:0;color:#fff;font-weight:700;cursor:pointer;background:linear-gradient(135deg,var(--a),var(--b));box-shadow:0 8px 26px rgba(139,92,246,.4)}button:hover{filter:brightness(1.1)}
.err{margin-top:14px;color:#fb7185;font-size:14px}
.by{margin-top:24px;font-size:13px;color:var(--muted)}.by b{background:linear-gradient(90deg,var(--c),#a78bfa,var(--b));-webkit-background-clip:text;background-clip:text;color:transparent;font-size:15px}
</style></head><body><form class="card" method="post"><div class="logo">✦</div><h1>Streak Control Center</h1><p>Enter the password shown in the Control Center terminal.</p>
<input type="hidden" name="csrf" value="{{ csrf }}"><input type="password" name="password" required autofocus placeholder="Dashboard password"><button>Unlock →</button>{% if error %}<div class="err">{{ error }}</div>{% endif %}
<div class="by">Made by <b>Dorrmant</b></div></form></body></html>
'''

import logging
logging.getLogger('werkzeug').addFilter(lambda r: '/logs.json' not in r.getMessage())

def create_app(backend, mobile=False):
    app=Flask(__name__); app.secret_key=backend.config['auth_password']; app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',MAX_CONTENT_LENGTH=65536)
    def csrf():
        if 'csrf' not in session: session['csrf']=secrets.token_urlsafe(24)
        return session['csrf']
    @app.route('/login', methods=['GET','POST'])
    def login():
        token=csrf(); error=''
        if request.method=='POST':
            if not hmac.compare_digest(request.form.get('csrf',''),session.get('csrf','')): abort(400)
            if hmac.compare_digest(request.form.get('password',''),backend.config['auth_password']): session['authenticated']=True; return redirect('/')
            error='Invalid password.'
        return render_template_string(LOGIN,csrf=token,error=error)
    @app.before_request
    def auth():
        if request.endpoint=='login': return
        if not session.get('authenticated'): return redirect(url_for('login'))
        if request.method=='POST' and not hmac.compare_digest(request.form.get('csrf',''),session.get('csrf','')): abort(400)
    @app.get('/')
    def home():
        snap=backend.snapshot(); return render_template_string(HTML,state=snap['state'],config=snap['config'],integrated=snap['bot_integrated'],bot_source=backend.config.get('bot_source',''),logs=snap['state']['logs'],csrf=csrf(),error=request.args.get('error',''))
    @app.get('/logs.json')
    def logs_json():
        return jsonify(logs=backend.snapshot()['state']['logs'][-100:])
    @app.post('/action')
    def action():
        act=request.form.get('action')
        if act=='start': ok,msg=backend.start_bot()
        elif act=='stop': ok,msg=True,'Bot state: '+backend.stop_bot()
        elif act=='login': ok,msg=backend.open_tiktok()
        else: ok,msg=False,'Unknown action'
        backend.log(msg); return redirect('/' if ok else '/?error='+msg.replace(' ','%20'))
    @app.post('/config')
    def config():
        try:
            backend.save_config({'usernames':[x.strip() for x in request.form.get('usernames','').splitlines() if x.strip()], 'message':request.form.get('message',''), 'interval_hours':float(request.form.get('interval_hours','12')), 'wait_after_profile_load_seconds':float(request.form.get('wait_after_profile_load_seconds','3')), 'wait_after_message_click_seconds':float(request.form.get('wait_after_message_click_seconds','5')), 'profile_dir':request.form.get('profile_dir','').strip()})
            return redirect('/')
        except Exception as e: return redirect('/?error='+str(e).replace(' ','%20'))
    @app.get('/api/state')
    def api_state(): return jsonify(backend.snapshot())
    @app.get('/logout')
    def logout(): session.clear(); return redirect('/login')
    return app
