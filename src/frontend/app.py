"""
src/frontend/app.py  —  Sports RAG  (v7 — final clean build)

Fixes vs v6:
  - Sources HTML was rendered as escaped text inside st.expander.
    Now uses st.markdown(unsafe_allow_html=True) directly — no expander.
  - Sidebar sport filter works: clicking a pill writes to st.query_params
    which is read on every rerun (no cross-frame JS hacks needed).
  - Configuration panel (sport + top_k) accessible from sidebar filter icon.
  - Sidebar API status shown on hover of the database icon.
  - Full centered layout with sidebar overlay.
"""

import os
import time
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
TIMEOUT  = 120

st.set_page_config(
    page_title="Sports RAG",
    page_icon="🏆",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
#  READ QUERY PARAMS  (set by sidebar JS)
# ─────────────────────────────────────────────────────────────────────────────
params       = st.query_params
sport_param  = params.get("sport", "All sports")
topk_param   = int(params.get("top_k", "5"))

# ─────────────────────────────────────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Space+Grotesk:wght@600;700&display=swap');

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body, [class*="css"], .stApp {{
    font-family: 'Inter', sans-serif;
    background: #0d0d0f !important;
    color: #e2e2e6;
}}

#MainMenu, footer, header {{ visibility: hidden; }}
button[data-testid="collapsedControl"],
section[data-testid="stSidebar"] {{ display: none !important; }}

.block-container {{
    max-width: 720px !important;
    padding: 0 24px 60px !important;
    margin: 0 auto !important;
    transform: translateX(32px);
}}

/* ══ FIXED SIDEBAR ══ */
#rag-sb {{
    position: fixed;
    left: 0; top: 0; bottom: 0; width: 64px;
    background: #0f0f12;
    border-right: 1px solid rgba(255,255,255,0.05);
    display: flex; flex-direction: column; align-items: center;
    padding: 18px 0 20px; z-index: 99999; gap: 0;
}}
.sb-logo {{
    width: 36px; height: 36px; background: #ff3e7e;
    border-radius: 10px; display: flex; align-items: center;
    justify-content: center; margin-bottom: 22px; flex-shrink: 0;
    box-shadow: 0 4px 16px rgba(255,62,126,.30);
}}
.sb-logo svg {{ width: 18px; height: 18px; fill: #fff; }}
.sb-nav {{ display:flex; flex-direction:column; align-items:center; gap:2px; width:100%; }}
.sb-btn {{
    width: 40px; height: 40px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; color: #383848; position: relative;
    transition: background .15s, color .15s; user-select: none;
}}
.sb-btn:hover  {{ background: rgba(255,255,255,.05); color: #7070a0; }}
.sb-btn.active {{ background: rgba(255,62,126,.13); color: #ff3e7e; }}
.sb-btn svg {{ width:17px; height:17px; stroke:currentColor; fill:none;
               stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round; }}

/* tooltip */
.sb-btn::after {{
    content: attr(data-tip);
    position: absolute; left: 52px; top: 50%; transform: translateY(-50%) translateX(-4px);
    background: #1e1e26; color: #c0c0d0; font-size:.7rem; white-space:nowrap;
    padding: 4px 10px; border-radius:6px; border:1px solid rgba(255,255,255,.08);
    pointer-events:none; opacity:0; transition: opacity .15s, transform .15s; z-index:9999;
}}
.sb-btn:hover::after {{ opacity:1; transform:translateY(-50%) translateX(0); }}

.sb-spacer {{ flex:1; }}
.sb-avatar {{
    width:32px; height:32px;
    background: linear-gradient(135deg,#ff3e7e,#c0195a);
    border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-size:11px; font-weight:700; color:#fff;
}}

/* ══ FLYOUT PANEL ══ */
.sb-flyout {{
    position: fixed; left: 68px; top: 70px;
    background: #17171d; border: 1px solid rgba(255,255,255,.09);
    border-radius: 14px; padding: 8px; z-index: 99998;
    min-width: 200px; box-shadow: 0 12px 40px rgba(0,0,0,.6);
    display: none; flex-direction: column; gap: 2px;
}}
.sb-flyout.open {{ display: flex; }}
.flyout-title {{
    font-size:.65rem; color:#383848; letter-spacing:.08em;
    text-transform:uppercase; padding:6px 10px 8px; border-bottom:1px solid rgba(255,255,255,.05);
    margin-bottom:4px;
}}
.sf-row {{
    display:flex; align-items:center; gap:10px;
    padding:8px 10px; border-radius:8px; cursor:pointer;
    font-size:.83rem; color:#606075;
    transition: background .12s, color .12s;
}}
.sf-row:hover {{ background:rgba(255,255,255,.05); color:#c0c0d0; }}
.sf-row.sel   {{ background:rgba(255,62,126,.12); color:#ff3e7e; }}
.sf-dot {{ width:7px; height:7px; border-radius:50%; background:currentColor; flex-shrink:0; }}
.sf-divider {{ border:none; border-top:1px solid rgba(255,255,255,.05); margin:6px 0; }}
.sf-label {{ font-size:.7rem; color:#383848; padding:2px 10px 6px; }}
.sf-topk-row {{
    display:flex; align-items:center; gap:8px;
    padding:6px 10px; font-size:.8rem; color:#606075;
}}
.sf-topk-row input[type=range] {{
    flex:1; accent-color:#ff3e7e; height:3px;
}}
.sf-topk-val {{ min-width:14px; text-align:right; color:#9090b0; font-weight:500; }}

/* badge on filter icon */
#sb-sport-badge {{
    font-size:.5rem; font-weight:700; color:#ff3e7e;
    letter-spacing:.04em; margin-top:1px; text-align:center;
    line-height:1; display:none;
}}

/* ══ HERO ══ */
.hero {{ text-align:center; padding:50px 0 26px; user-select:none; }}
.hero h1 {{
    font-family:'Space Grotesk',sans-serif;
    font-size:2.15rem; font-weight:700; color:#f0f0f4;
    letter-spacing:-.5px; line-height:1.18; margin:0;
}}
.hero h1 em {{ font-style:normal; color:#ff3e7e; }}
.hero p {{ font-size:.86rem; color:#46464e; margin-top:9px; }}

/* sport badge above search */
.active-filter-bar {{
    text-align:center; margin-bottom:6px;
    font-size:.72rem; color:#ff3e7e;
    display: {'block' if sport_param != 'All sports' else 'none'};
}}
.active-filter-bar span {{
    background:rgba(255,62,126,.1); border:1px solid rgba(255,62,126,.2);
    border-radius:20px; padding:3px 10px;
}}

/* ══ SEARCH BAR ══ */
.stTextInput > div > div > input {{
    background: #14141a !important;
    border: 1.5px solid rgba(255,62,126,.24) !important;
    border-radius: 13px !important;
    color: #e0e0e8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: .96rem !important;
    padding: 0 20px !important;
    height: 52px !important;
    caret-color: #ff3e7e !important;
    transition: border-color .2s, box-shadow .2s !important;
}}
.stTextInput > div > div > input:focus {{
    border-color: rgba(255,62,126,.58) !important;
    box-shadow: 0 0 0 3px rgba(255,62,126,.09) !important;
    outline: none !important;
}}
.stTextInput > div > div > input::placeholder {{ color:#34343e !important; }}

/* submit button scoped */
.submit-wrap > div > div > button {{
    background: #ff3e7e !important; color:#fff !important;
    border:none !important; border-radius:12px !important;
    height:48px !important; width:48px !important; min-width:48px !important;
    padding:0 !important; font-size:1.15rem !important;
    display:flex !important; align-items:center !important; justify-content:center !important;
    margin-top:2px !important; cursor:pointer !important;
    transition:background .15s, transform .1s !important;
    box-shadow: 0 4px 14px rgba(255,62,126,.26) !important;
}}
.submit-wrap > div > div > button:hover  {{ background:#e8306a !important; transform:scale(1.04) !important; }}
.submit-wrap > div > div > button:active {{ transform:scale(0.96) !important; }}

/* chip / action buttons */
.stButton > button {{
    background: #14141a !important;
    border: 1px solid rgba(255,255,255,.08) !important;
    border-radius:22px !important; color:#58586e !important;
    font-family:'Inter',sans-serif !important; font-size:.79rem !important;
    padding:6px 15px !important;
    height:auto !important; width:auto !important; min-width:unset !important;
    white-space:nowrap !important; cursor:pointer !important;
    transition:border-color .18s, color .18s, background .18s !important;
}}
.stButton > button:hover {{
    border-color:rgba(255,62,126,.38) !important;
    color:#ff3e7e !important; background:rgba(255,62,126,.07) !important;
}}

/* chips label */
.chips-lbl {{
    font-size:.73rem; color:#34343e;
    text-align:center; margin:16px 0 9px; letter-spacing:.03em;
}}
/* center chip rows */
[data-testid="stHorizontalBlock"] {{
    justify-content:center !important; gap:8px !important; flex-wrap:wrap !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stColumn"] {{
    flex:0 0 auto !important; width:auto !important;
    min-width:0 !important; padding:0 !important;
}}

/* ══ QUERY BAR ══ */
.query-bar {{
    display:flex; align-items:center; gap:10px;
    background:#14141a; border:1px solid rgba(255,62,126,.13);
    border-radius:12px; padding:11px 16px; margin-bottom:10px;
    font-size:.9rem; color:#58586e;
}}
.q-tag {{
    font-size:.63rem; font-weight:600; color:#ff3e7e;
    background:rgba(255,62,126,.11); border-radius:4px;
    padding:2px 6px; letter-spacing:.05em; flex-shrink:0;
}}

/* ══ ANSWER CARD ══ */
.answer-card {{
    background:#131318; border:1px solid rgba(255,255,255,.06);
    border-radius:16px; padding:24px 26px; margin-bottom:10px;
}}
.answer-hdr {{ display:flex; align-items:center; gap:8px; margin-bottom:14px; }}
.answer-hdr .spark {{ color:#ff3e7e; font-size:.95rem; }}
.answer-hdr .lbl {{
    font-family:'Space Grotesk',sans-serif;
    font-size:.9rem; font-weight:600; color:#ff3e7e;
}}
.answer-body {{ font-size:.94rem; color:#b8b8c8; line-height:1.78; margin-bottom:16px; }}
.lat-strip {{
    display:flex; gap:18px; flex-wrap:wrap;
    border-top:1px solid rgba(255,255,255,.05); padding-top:12px;
}}
.lat {{ display:flex; align-items:center; gap:5px; font-size:.72rem; color:#34343e; }}
.lat .k {{ color:#ff3e7e; opacity:.6; }}
.lat .v {{ color:#68689a; font-weight:500; }}

/* ══ SOURCES CARD ══ */
.sources-card {{
    background:#131318; border:1px solid rgba(255,255,255,.06);
    border-radius:16px; overflow:hidden; margin-bottom:10px;
}}
.sources-hdr {{
    display:flex; justify-content:space-between; align-items:center;
    padding:13px 20px; border-bottom:1px solid rgba(255,255,255,.04);
}}
.stitle {{ font-size:.83rem; font-weight:500; color:#9090b0;
           display:flex; align-items:center; gap:7px; }}
.scount {{ font-size:.72rem; color:#34343e; }}
.src-row {{
    display:flex; align-items:flex-start; gap:12px;
    padding:13px 20px; border-bottom:1px solid rgba(255,255,255,.03);
    transition:background .13s;
}}
.src-row:last-child {{ border-bottom:none; }}
.src-row:hover {{ background:rgba(255,255,255,.013); }}
.src-num {{ font-size:.72rem; color:#28283a; font-weight:600;
            min-width:20px; padding-top:2px; flex-shrink:0; }}
.sport-pill {{
    font-size:.62rem; font-weight:700; letter-spacing:.6px;
    padding:3px 7px; border-radius:5px; text-transform:uppercase;
    white-space:nowrap; flex-shrink:0; margin-top:1px;
}}
.p-football   {{background:rgba(255,62,126,.11);color:#ff3e7e;border:1px solid rgba(255,62,126,.2);}}
.p-basketball {{background:rgba(255,140,0,.11); color:#ff8c00;border:1px solid rgba(255,140,0,.2);}}
.p-tennis     {{background:rgba(50,220,120,.11);color:#32dc78;border:1px solid rgba(50,220,120,.2);}}
.p-cricket    {{background:rgba(255,62,126,.11);color:#ff3e7e;border:1px solid rgba(255,62,126,.2);}}
.p-wikipedia  {{background:rgba(100,160,255,.11);color:#64a0ff;border:1px solid rgba(100,160,255,.2);}}
.p-unknown    {{background:rgba(100,100,110,.11);color:#58586e;border:1px solid rgba(100,100,110,.2);}}
.src-text {{
    font-size:.82rem; color:#48486a; line-height:1.58; flex:1;
    display:-webkit-box; -webkit-line-clamp:2;
    -webkit-box-orient:vertical; overflow:hidden;
}}

/* ══ HISTORY ══ */
.hist-label {{
    font-size:.65rem; color:#28283a; text-transform:uppercase;
    letter-spacing:.08em; margin:20px 0 8px;
}}
.hist-item {{ padding:9px 12px; border-radius:8px; transition:background .13s; }}
.hist-item:hover {{ background:rgba(255,255,255,.03); }}
.hist-q {{ font-size:.8rem; color:#9090b0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.hist-m {{ font-size:.65rem; color:#28283a; margin-top:2px; }}
.divider {{ border:none; border-top:1px solid rgba(255,255,255,.04); margin:16px 0; }}

/* ══ API STATUS flyout ══ */
#api-flyout {{
    position:fixed; left:68px; top:130px;
    background:#17171d; border:1px solid rgba(255,255,255,.09);
    border-radius:14px; padding:14px 16px; z-index:99998;
    min-width:220px; box-shadow:0 12px 40px rgba(0,0,0,.6);
    display:none; flex-direction:column; gap:8px;
}}
#api-flyout.open {{ display:flex; }}
.api-row {{ display:flex; align-items:center; gap:8px; font-size:.78rem; color:#7070a0; }}
.api-dot {{ width:7px; height:7px; border-radius:50%; flex-shrink:0; }}
.dot-ok    {{ background:#22cc66; }}
.dot-warn  {{ background:#ffa500; }}
.dot-error {{ background:#ff4444; }}
.api-val   {{ color:#b0b0c8; font-weight:500; margin-left:auto; font-size:.75rem; }}
.api-title {{ font-size:.65rem; color:#383848; letter-spacing:.08em; text-transform:uppercase;
              border-bottom:1px solid rgba(255,255,255,.05); padding-bottom:8px; margin-bottom:2px; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "history"        not in st.session_state: st.session_state.history        = []
if "current_result" not in st.session_state: st.session_state.current_result = None
if "show_sources"   not in st.session_state: st.session_state.show_sources   = True

sport_filter = sport_param
top_k        = topk_param

# ─────────────────────────────────────────────────────────────────────────────
#  API HELPERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def query_api(question: str, sport_filter: str, top_k: int) -> dict | None:
    try:
        payload = {"question": question, "top_k": top_k}
        if sport_filter and sport_filter != "All sports":
            payload["sport_filter"] = sport_filter.lower()
        r = requests.post(f"{API_BASE}/query", json=payload, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
        st.error(f"API error {r.status_code}: {r.json().get('detail', r.text)}")
        return None
    except requests.ConnectionError:
        st.error(f"Cannot reach API at {API_BASE}.\nRun: `uvicorn src.api.main:app --reload --port 8000`")
        return None
    except requests.Timeout:
        st.error("Request timed out. Try again.")
        return None

def sport_pill_html(sport: str, source_type: str = "") -> str:
    if source_type == "wikipedia":
        return '<span class="sport-pill p-wikipedia">🌐 Wiki</span>'
    s     = sport.lower()
    icons = {"football":"⚽","basketball":"🏀","tennis":"🎾","cricket":"🏏"}
    cls   = f"p-{s}" if s in icons else "p-unknown"
    return f'<span class="sport-pill {cls}">{icons.get(s,"")} {s.capitalize()}</span>'

def run_query(question: str):
    with st.spinner("Retrieving · Reranking · Generating…"):
        r = query_api(question.strip(), sport_filter, top_k)
    if r:
        r["question"] = question.strip()
        st.session_state.current_result = r
        st.session_state.history.append({
            "question":     question.strip(),
            "answer":       r.get("answer", ""),
            "sport_filter": None if sport_filter == "All sports" else sport_filter,
            "total_ms":     r.get("latency_ms", {}).get("total_ms", 0),
            "timestamp":    time.time(),
        })
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  BUILD API STATUS HTML for flyout
# ─────────────────────────────────────────────────────────────────────────────
health = get_health()
if health:
    overall  = health.get("status", "unknown")
    dot_cls  = "dot-ok" if overall == "ok" else "dot-warn" if overall == "degraded" else "dot-error"
    api_rows = f"""
    <div class="api-title">API Status</div>
    <div class="api-row"><div class="api-dot {dot_cls}"></div> {overall.upper()}
        <span class="api-val">{health.get('index_vectors',0):,} vectors</span>
    </div>
    <div class="api-row"><div class="api-dot dot-ok"></div> Uptime
        <span class="api-val">{health.get('uptime_s',0):.0f}s</span>
    </div>"""
    for k, v in health.get("components", {}).items():
        dc = "dot-ok" if v.get("status") == "ok" else "dot-error"
        api_rows += f'<div class="api-row"><div class="api-dot {dc}"></div> {k}</div>'
else:
    api_rows = '<div class="api-title">API Status</div><div class="api-row"><div class="api-dot dot-error"></div> Offline</div>'

# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR + FLYOUTS HTML
# ─────────────────────────────────────────────────────────────────────────────
sports_list = [
    ("All sports", "🏆"), ("Football","⚽"), ("Basketball","🏀"),
    ("Tennis","🎾"), ("Cricket","🏏"),
]
sport_rows_html = ""
for s_name, s_icon in sports_list:
    sel = "sel" if sport_filter == s_name else ""
    sport_rows_html += f'<div class="sf-row {sel}" onclick="selectSport(\'{s_name}\')">' \
                       f'<span>{s_icon}</span> {s_name}</div>'

badge_text    = sport_filter[:4].upper() if sport_filter != "All sports" else ""
badge_display = "block" if sport_filter != "All sports" else "none"

st.markdown(f"""
<!-- ════ FIXED SIDEBAR ════ -->
<div id="rag-sb">
  <div class="sb-logo">
    <svg viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
  </div>
  <nav class="sb-nav">
    <!-- Search -->
    <div class="sb-btn active" data-tip="Search">
      <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    </div>
    <!-- API Status -->
    <div class="sb-btn" data-tip="API status" id="sb-api-btn" onclick="toggleApi()">
      <svg viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
    </div>
    <!-- Sport Filter -->
    <div class="sb-btn" data-tip="Sport filter" id="sb-filter-btn" onclick="toggleFilter()">
      <svg viewBox="0 0 24 24"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
    </div>
    <div id="sb-sport-badge" style="font-size:.5rem;font-weight:700;color:#ff3e7e;text-align:center;display:{badge_display};margin-top:1px;">{badge_text}</div>
    <!-- Activity -->
    <div class="sb-btn" data-tip="Activity">
      <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
    </div>
    <!-- History -->
    <div class="sb-btn" data-tip="History">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    </div>
  </nav>
  <div class="sb-spacer"></div>
  <div class="sb-avatar">AS</div>
</div>

<!-- ════ API STATUS FLYOUT ════ -->
<div class="sb-flyout" id="api-flyout">
  {api_rows}
</div>

<!-- ════ SPORT FILTER FLYOUT ════ -->
<div class="sb-flyout" id="filter-flyout" style="top:120px;">
  <div class="flyout-title">Sport Filter</div>
  {sport_rows_html}
  <hr class="sf-divider">
  <div class="sf-label">Source chunks: <span id="topk-display">{top_k}</span></div>
  <div class="sf-topk-row">
    <span style="font-size:.7rem;color:#383848;">1</span>
    <input type="range" min="1" max="10" value="{top_k}" id="topk-range"
           oninput="updateTopK(this.value)">
    <span style="font-size:.7rem;color:#383848;">10</span>
  </div>
</div>

<script>
let filterOpen = false;
let apiOpen    = false;

function closeAll() {{
    if (filterOpen) {{ document.getElementById('filter-flyout').classList.remove('open'); filterOpen=false; }}
    if (apiOpen)    {{ document.getElementById('api-flyout').classList.remove('open');    apiOpen=false; }}
}}

function toggleFilter() {{
    apiOpen && toggleApi();
    filterOpen = !filterOpen;
    document.getElementById('filter-flyout').classList.toggle('open', filterOpen);
    document.getElementById('sb-filter-btn').classList.toggle('active', filterOpen);
}}

function toggleApi() {{
    filterOpen && toggleFilter();
    apiOpen = !apiOpen;
    document.getElementById('api-flyout').classList.toggle('open', apiOpen);
    document.getElementById('sb-api-btn').classList.toggle('active', apiOpen);
}}

function selectSport(sport) {{
    // Update URL query params → triggers Streamlit rerun with new sport value
    const url = new URL(window.location.href);
    url.searchParams.set('sport', sport);
    url.searchParams.set('top_k', document.getElementById('topk-range').value);
    window.location.href = url.toString();
}}

function updateTopK(val) {{
    document.getElementById('topk-display').textContent = val;
}}

// Submit top_k on range mouseup (navigate)
document.addEventListener('DOMContentLoaded', function() {{
    const r = document.getElementById('topk-range');
    if (r) {{
        r.addEventListener('change', function() {{
            const url = new URL(window.location.href);
            url.searchParams.set('top_k', this.value);
            url.searchParams.set('sport', '{sport_filter}');
            window.location.href = url.toString();
        }});
    }}
}});

// Close flyouts on outside click
document.addEventListener('click', function(e) {{
    if (!e.target.closest('#sb-filter-btn') && !e.target.closest('#filter-flyout') &&
        !e.target.closest('#sb-api-btn')    && !e.target.closest('#api-flyout')) {{
        closeAll();
    }}
}});
</script>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  HERO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>Sports Intelligence, Powered by <em>RAG</em></h1>
  <p>Retrieval-Augmented Generation &nbsp;·&nbsp; Football &nbsp;·&nbsp; Basketball &nbsp;·&nbsp; Tennis &nbsp;·&nbsp; Cricket</p>
</div>
""", unsafe_allow_html=True)

# show active filter pill
if sport_filter != "All sports":
    st.markdown(f'<div class="active-filter-bar"><span>Filtering: {sport_filter}</span></div>',
                unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  SEARCH BAR
# ─────────────────────────────────────────────────────────────────────────────
c_in, c_btn = st.columns([14, 1])
with c_in:
    question = st.text_input(
        "q", label_visibility="collapsed",
        placeholder="Ask anything about sports…",
        key="main_input",
    )
with c_btn:
    st.markdown('<div class="submit-wrap">', unsafe_allow_html=True)
    submit = st.button("→", key="submit_btn")
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  CHIPS  (only on empty state)
# ─────────────────────────────────────────────────────────────────────────────
EXAMPLES = [
    "Who is the best cricket player of all time?",
    "Top 5 football clubs with most trophies",
    "Compare Messi and Ronaldo stats",
    "Latest F1 race winner",
    "Djokovic Wimbledon titles",
    "IPL 2019 final result",
]

result = st.session_state.current_result

if not result:
    st.markdown('<p class="chips-lbl">Try asking</p>', unsafe_allow_html=True)
    for row_start in range(0, len(EXAMPLES), 3):
        row  = EXAMPLES[row_start : row_start + 3]
        cols = st.columns(len(row))
        for col, ex in zip(cols, row):
            with col:
                label = ex if len(ex) <= 34 else ex[:32] + "…"
                if st.button(label, key=f"chip_{EXAMPLES.index(ex)}"):
                    run_query(ex)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  SUBMIT
# ─────────────────────────────────────────────────────────────────────────────
if submit and question.strip():
    if len(question.strip()) < 3:
        st.warning("Question too short.")
    else:
        run_query(question.strip())

# ─────────────────────────────────────────────────────────────────────────────
#  RESULT PANEL
# ─────────────────────────────────────────────────────────────────────────────
if result:
    lat     = result.get("latency_ms", {})
    answer  = result.get("answer", "")
    sources = result.get("sources", [])

    # Query bar
    st.markdown(f"""
    <div class="query-bar">
      <span class="q-tag">Q</span>
      {result.get('question','')}
    </div>""", unsafe_allow_html=True)

    # Answer card
    total_ms  = lat.get("total_ms", 0)
    ret_ms    = lat.get("dense_ms", lat.get("wiki_ms", 0))
    rerank_ms = lat.get("rerank_ms", 0)
    llm_ms    = lat.get("llm_ms", 0)

    st.markdown(f"""
    <div class="answer-card">
      <div class="answer-hdr">
        <span class="spark">✦</span>
        <span class="lbl">Answer</span>
      </div>
      <div class="answer-body">{answer}</div>
      <div class="lat-strip">
        <div class="lat"><span class="k">◷</span> Total&nbsp;<span class="v">{total_ms}ms</span></div>
        <div class="lat"><span class="k">◎</span> Retrieve&nbsp;<span class="v">{ret_ms}ms</span></div>
        <div class="lat"><span class="k">⇌</span> Rerank&nbsp;<span class="v">{rerank_ms}ms</span></div>
        <div class="lat"><span class="k">⊕</span> LLM&nbsp;<span class="v">{llm_ms}ms</span></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── SOURCES — rendered via st.markdown, NOT st.expander ──
    if sources:
        rows_html = ""
        for i, src in enumerate(sources, 1):
            sp        = src.get("sport", "unknown")
            src_type  = src.get("source", "")
            text      = src.get("text", "")[:220].replace("<","&lt;").replace(">","&gt;")
            pill      = sport_pill_html(sp, src_type)
            rows_html += f"""
            <div class="src-row">
              <div class="src-num">#{i}</div>
              {pill}
              <div class="src-text">{text}…</div>
            </div>"""

        show    = st.session_state.show_sources
        chevron = "∧" if show else "∨"

        # Header always shown; rows only if show=True
        st.markdown(f"""
        <div class="sources-card">
          <div class="sources-hdr">
            <span class="stitle">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              Sources
            </span>
            <span class="scount">{len(sources)} chunks &nbsp;{chevron}</span>
          </div>
          {rows_html if show else ""}
        </div>""", unsafe_allow_html=True)

        if st.button("▲ Hide sources" if show else "▼ Show sources", key="toggle_src"):
            st.session_state.show_sources = not st.session_state.show_sources
            st.rerun()

    # New question
    if st.button("← New question", key="new_q"):
        st.session_state.current_result = None
        st.rerun()

    # History
    if st.session_state.history:
        st.markdown('<hr class="divider"><div class="hist-label">Recent</div>',
                    unsafe_allow_html=True)
        for item in reversed(st.session_state.history[-6:]):
            elapsed = time.time() - item["timestamp"]
            age = f"{int(elapsed//60)}m ago" if elapsed > 60 else f"{int(elapsed)}s ago"
            st.markdown(f"""
            <div class="hist-item">
              <div class="hist-q">{item['question'][:72]}</div>
              <div class="hist-m">{age} · {item.get('total_ms',0)}ms</div>
            </div>""", unsafe_allow_html=True)