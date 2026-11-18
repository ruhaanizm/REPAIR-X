"""Self-contained neon UI theme. No external assets or CDN required."""
import html

CSS = r'''<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root{--rx-cyan:#00efff;--rx-violet:#a675ff;--rx-ink:#060a14;--rx-panel:#0d1628;--rx-border:#24415c}
.stApp{background:radial-gradient(ellipse at 85% -12%,#24205b 0%,transparent 39%),radial-gradient(ellipse at 0% 20%,#073347 0%,transparent 32%),#060a14;color:#e9f6ff;font-family:'Space Grotesk',sans-serif}
.block-container{max-width:1510px;padding-top:1.25rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:#080f20;border-right:1px solid #1d3854}
[data-testid="stMetric"]{background:linear-gradient(140deg,#102338,#0b1224);border:1px solid #244e6b;border-radius:16px;padding:15px;box-shadow:inset 0 1px 0 #1e5775,0 0 25px #00c8ff0a}
[data-testid="stMetricValue"]{color:#00efff;font-family:'Rajdhani',sans-serif;font-weight:700}
.stButton>button[kind="primary"]{background:linear-gradient(110deg,#00c9e9,#6c4bff);color:#051020;border:0;border-radius:11px;font-weight:800;letter-spacing:.07em;box-shadow:0 0 18px #00dfff40}
.stButton>button[kind="primary"]:hover{filter:brightness(1.15);box-shadow:0 0 30px #00eaff70}
.stTabs [data-baseweb="tab-list"]{gap:10px;flex-wrap:wrap}
.stTabs [data-baseweb="tab"]{background:#0d192c;border:1px solid #274460;border-radius:10px;color:#c3d8ee;padding:9px 17px}
.stTabs [aria-selected="true"]{border-color:#00efff!important;box-shadow:0 0 16px #00eaff30;color:#00efff!important}
.stSelectbox [data-baseweb="select"]>div,.stTextInput input{background:#0b1729;border-color:#2d4a67;color:#eafaff}
.rx-hero{position:relative;overflow:hidden;background:linear-gradient(110deg,#102e42,#10152c 62%,#23153d);border:1px solid #2a7082;border-radius:22px;padding:30px 34px;margin-bottom:20px;box-shadow:0 0 40px #00d5ff13}
.rx-hero:after{content:'';position:absolute;right:-90px;top:-130px;width:360px;height:360px;border-radius:50%;border:1px solid #00f0ff55;box-shadow:0 0 0 35px #00eaff0a,0 0 0 75px #a675ff0b;pointer-events:none}
.rx-eyebrow{color:#00eaff;letter-spacing:3px;font-size:11px;font-weight:800}
.rx-title{font-family:'Rajdhani',sans-serif;font-size:clamp(54px,7vw,92px);line-height:.95;font-weight:700;letter-spacing:-3px;color:#fff;text-shadow:0 0 24px #00eaff35}
.rx-sub{color:#c1d5ea;font-size:15px;max-width:740px;margin-top:15px;line-height:1.7}
.rx-chip{display:inline-block;border:1px solid #2e8c9b;border-radius:30px;padding:5px 11px;color:#79f5ff;font-size:11px;letter-spacing:.1em;margin-top:16px;background:#00d9ff12}
.rx-panel{background:linear-gradient(155deg,#111e34,#0a1221);border:1px solid #27435e;border-radius:15px;padding:18px;margin:10px 0;box-shadow:0 8px 30px #0003}
.rx-panel h3{font-family:'Rajdhani',sans-serif;letter-spacing:.08em;color:#00efff;margin:0 0 8px}
.rx-step{display:flex;gap:13px;align-items:flex-start;margin:9px 0;padding:13px 15px;border:1px solid #24415c;border-left:3px solid #00efff;background:#0d1a2d;border-radius:0 11px 11px 0}
.rx-index{font-family:'Rajdhani',sans-serif;color:#00efff;font-size:19px;font-weight:700;min-width:30px}
.rx-muted{color:#a9c2d8;font-size:13px;line-height:1.5}
.rx-green{color:#66ffc4}.rx-red{color:#ff7c9a}
.rx-terminal{background:#050b15;border:1px solid #24647a;border-radius:12px;padding:13px 16px;font:12px/1.7 Consolas,monospace;color:#8df3fa;max-height:310px;overflow:auto}
.rx-live-dot{display:inline-block;width:8px;height:8px;background:#32f5b7;border-radius:50%;box-shadow:0 0 10px #32f5b7;animation:rxpulse 1.7s infinite;margin-right:8px}
@keyframes rxpulse{50%{opacity:.4;box-shadow:0 0 22px #32f5b7}}
@media(max-width:760px){.rx-hero{padding:20px}.rx-title{font-size:58px}}
</style>'''


def hero():
    return '''<div class="rx-hero"><div class="rx-eyebrow"><span class="rx-live-dot"></span>AI SOFTWARE RESILIENCE · OPERATIONS CONSOLE</div><div class="rx-title">REPAIR<span style="color:#00efff">-X</span></div><div class="rx-sub">An observable, risk-aware autonomous repair prototype. Diagnose controlled Python faults, generate LLM patches, validate behavior, and recover—or abstain.</div><span class="rx-chip">◈ 3 PROVIDERS</span> <span class="rx-chip">◈ BOUNDED RECOVERY</span> <span class="rx-chip">◈ AUDITABLE TRACES</span></div>'''


def event_html(events):
    lines = []
    for kind, msg in events:
        color = '#ff8ea5' if 'error' in kind else '#74ffca' if kind in ('complete','validation_end') and ('PASS' in msg or 'ACCEPTED' in msg) else '#7eeafa'
        lines.append(f'<div><span style="color:#8ca6be">[{html.escape(kind.upper())}]</span> <span style="color:{color}">{html.escape(msg)}</span></div>')
    return '<div class="rx-terminal">'+''.join(lines or ['Awaiting a real execution event…'])+'</div>'
