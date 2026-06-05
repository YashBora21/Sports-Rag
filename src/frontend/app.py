"""
src/frontend/app.py
Sports RAG — Streamlit frontend (v5 — clean minimal rewrite)
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
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
#  CSS + FIXED SIDEBAR HTML
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Space+Grotesk:wght@600;700&display=swap');

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif;
    background: #0d0d0f !important;
    color: #e2e2e6;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
button[data-testid="collapsedControl"],
section[data-testid="stSidebar"] { display: none !important; }

/* ── Main container ── */
.block-container {
    max-width: 780px !important;
    padding: 0 24px 60px !important;
    margin: 0 auto 0 96px !important;
}

/* ═══════════════════════════════════
   FIXED SIDEBAR
═══════════════════════════════════ */
#rag-sidebar {
    position: fixed;
    left: 0; top: 0; bottom: 0;
    width: 64px;
    background: #111114;
    border-right: 1px solid rgba(255,255,255,0.05);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 20px 0;
    z-index: 9999;
    gap: 0;
}
.sb-logo {
    width: 38px; height: 38px;
    background: #ff3e7e;
    border-radius: 11px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 28px;
    flex-shrink: 0;
    box-shadow: 0 4px 14px rgba(255,62,126,0.35);
}
.sb-logo svg { width: 20px; height: 20px; fill: #fff; }

.sb-nav { display: flex; flex-direction: column; align-items: center; gap: 4px; width: 100%; }
.sb-btn {
    width: 40px; height: 40px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    color: #40404e;
    text-decoration: none;
}
.sb-btn:hover  { background: rgba(255,255,255,0.05); color: #80809a; }
.sb-btn.active { background: rgba(255,62,126,0.12); color: #ff3e7e; }
.sb-btn svg { width: 18px; height: 18px; stroke: currentColor; fill: none; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }

.sb-spacer { flex: 1; }
.sb-avatar {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #ff3e7e, #c0195a);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; color: #fff;
    flex-shrink: 0;
}

/* ═══════════════════════════════════
   HERO
═══════════════════════════════════ */
.hero {
    text-align: center;
    padding: 48px 0 28px;
}
.hero h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.25rem;
    font-weight: 700;
    color: #f0f0f4;
    letter-spacing: -0.5px;
    line-height: 1.18;
    margin: 0;
}
.hero h1 em { font-style: normal; color: #ff3e7e; }
.hero p {
    font-size: 0.875rem;
    color: #55555f;
    margin-top: 10px;
    line-height: 1.5;
}

/* ═══════════════════════════════════
   SEARCH ROW
═══════════════════════════════════ */
/* input */
.stTextInput > div > div > input {
    background: #16161a !important;
    border: 1.5px solid rgba(255,62,126,0.28) !important;
    border-radius: 14px !important;
    color: #e0e0e8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.97rem !important;
    padding: 0 20px !important;
    height: 52px !important;
    caret-color: #ff3e7e !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(255,62,126,0.65) !important;
    box-shadow: 0 0 0 3px rgba(255,62,126,0.10) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: #3d3d4a !important; }

/* ── submit button: scoped via .submit-wrap ── */
.submit-wrap > div > div > button {
    background: #ff3e7e !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    height: 48px !important;
    width: 48px !important;
    min-width: 48px !important;
    padding: 0 !important;
    font-size: 1.15rem !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    margin-top: 2px !important;
    transition: background 0.15s, transform 0.1s !important;
    box-shadow: 0 4px 14px rgba(255,62,126,0.3) !important;
}
.submit-wrap > div > div > button:hover {
    background: #e8306a !important;
    transform: scale(1.04) !important;
}
.submit-wrap > div > div > button:active { transform: scale(0.96) !important; }

/* ── all OTHER buttons (chips, toggles) ── */
.stButton > button {
    background: #16161a !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 22px !important;
    color: #7070a0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
    font-weight: 400 !important;
    padding: 6px 15px !important;
    height: auto !important;
    width: auto !important;
    min-width: unset !important;
    white-space: nowrap !important;
    cursor: pointer !important;
    transition: border-color 0.18s, color 0.18s, background 0.18s !important;
}
.stButton > button:hover {
    border-color: rgba(255,62,126,0.4) !important;
    color: #ff3e7e !important;
    background: rgba(255,62,126,0.07) !important;
}
.stButton > button:active { transform: scale(0.97) !important; }

/* ── chips row: center-justify the st.columns ── */
.chips-outer {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 16px 0 8px;
}
.chips-label {
    font-size: 0.75rem;
    color: #3d3d4a;
    margin-bottom: 10px;
    letter-spacing: 0.03em;
}
/* make each chip column shrink to content */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    min-width: 0 !important;
    flex: 0 0 auto !important;
    width: auto !important;
}

/* ═══════════════════════════════════
   QUERY BAR
═══════════════════════════════════ */
.query-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #16161a;
    border: 1px solid rgba(255,62,126,0.16);
    border-radius: 12px;
    padding: 11px 16px;
    margin-bottom: 10px;
    font-size: 0.9rem;
    color: #70709a;
}
.query-bar .q-tag {
    font-size: 0.65rem;
    font-weight: 600;
    color: #ff3e7e;
    background: rgba(255,62,126,0.12);
    border-radius: 4px;
    padding: 2px 6px;
    letter-spacing: 0.05em;
    flex-shrink: 0;
}

/* ═══════════════════════════════════
   ANSWER CARD
═══════════════════════════════════ */
.answer-card {
    background: #141418;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 24px 26px;
    margin-bottom: 10px;
}
.answer-hdr {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
}
.answer-hdr .spark { color: #ff3e7e; font-size: 1rem; }
.answer-hdr .label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.92rem;
    font-weight: 600;
    color: #ff3e7e;
    letter-spacing: 0.02em;
}
.answer-body {
    font-size: 0.95rem;
    color: #c8c8d8;
    line-height: 1.78;
    margin-bottom: 18px;
}
.latency-strip {
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
    border-top: 1px solid rgba(255,255,255,0.05);
    padding-top: 12px;
}
.lat { display: flex; align-items: center; gap: 5px; font-size: 0.74rem; color: #3d3d4a; }
.lat .k { color: #ff3e7e; opacity: 0.6; font-size: 0.78rem; }
.lat .v { color: #80809a; font-weight: 500; }

/* ═══════════════════════════════════
   SOURCES CARD
═══════════════════════════════════ */
.sources-card {
    background: #141418;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 10px;
}
.sources-hdr {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 13px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.sources-hdr .stitle {
    font-size: 0.84rem;
    font-weight: 500;
    color: #b0b0c4;
    display: flex;
    align-items: center;
    gap: 7px;
}
.sources-hdr .scount { font-size: 0.74rem; color: #3d3d4a; }
.src-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 13px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    transition: background 0.14s;
}
.src-row:last-child { border-bottom: none; }
.src-row:hover { background: rgba(255,255,255,0.015); }
.src-num { font-size: 0.74rem; color: #2e2e3a; font-weight: 600; min-width: 20px; padding-top: 2px; }
.sport-pill {
    font-size: 0.63rem; font-weight: 700; letter-spacing: 0.6px;
    padding: 3px 7px; border-radius: 5px; text-transform: uppercase;
    white-space: nowrap; flex-shrink: 0; margin-top: 1px;
}
.p-football   { background:rgba(255,62,126,0.12); color:#ff3e7e; border:1px solid rgba(255,62,126,0.22); }
.p-basketball { background:rgba(255,140,0,0.12);  color:#ff8c00; border:1px solid rgba(255,140,0,0.22); }
.p-tennis     { background:rgba(50,220,120,0.12); color:#32dc78; border:1px solid rgba(50,220,120,0.22); }
.p-cricket    { background:rgba(255,62,126,0.12); color:#ff3e7e; border:1px solid rgba(255,62,126,0.22); }
.p-wikipedia  { background:rgba(100,160,255,0.12);color:#64a0ff; border:1px solid rgba(100,160,255,0.22); }
.p-unknown    { background:rgba(100,100,110,0.12);color:#707090; border:1px solid rgba(100,100,110,0.22); }
.src-text {
    font-size: 0.82rem; color: #606080; line-height: 1.58; flex: 1;
    display: -webkit-box; -webkit-line-clamp: 2;
    -webkit-box-orient: vertical; overflow: hidden;
}

/* ═══════════════════════════════════
   HISTORY
═══════════════════════════════════ */
.hist-label {
    font-size: 0.67rem; color: #2e2e3a;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin: 22px 0 8px;
}
.hist-item {
    padding: 9px 12px; border-radius: 8px;
    transition: background 0.14s; cursor: default;
}
.hist-item:hover { background: rgba(255,255,255,0.03); }
.hist-q { font-size: 0.8rem; color: #b0b0c4; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.hist-m { font-size: 0.67rem; color: #2e2e3a; margin-top: 2px; }

.divider { border:none; border-top:1px solid rgba(255,255,255,0.04); margin:16px 0; }
</style>

<!-- ═══ FIXED SIDEBAR ═══ -->
<div id="rag-sidebar">
  <!-- Logo -->
  <div class="sb-logo">
    <svg viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
  </div>

  <nav class="sb-nav">
    <!-- Search -->
    <div class="sb-btn active" title="Search">
      <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    </div>
    <!-- Database -->
    <div class="sb-btn" title="Index">
      <svg viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
    </div>
    <!-- Activity -->
    <div class="sb-btn" title="Activity">
      <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
    </div>
    <!-- Clock -->
    <div class="sb-btn" title="History">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    </div>
  </nav>

  <div class="sb-spacer"></div>
  <div class="sb-avatar">AS</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "history"        not in st.session_state: st.session_state.history        = []
if "current_result" not in st.session_state: st.session_state.current_result = None
if "show_sources"   not in st.session_state: st.session_state.show_sources   = True

# Hidden sidebar keeps filter values alive across reruns
with st.sidebar:
    sport_filter = st.selectbox("Sport", ["All sports","Football","Basketball","Tennis","Cricket"])
    top_k        = st.slider("Chunks", 1, 10, 5)

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

def query_api(question: str, sport_filter: str | None, top_k: int) -> dict | None:
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
        st.error(f"Cannot reach API at {API_BASE}. Is the server running?\n`uvicorn src.api.main:app --reload --port 8000`")
        return None
    except requests.Timeout:
        st.error("Request timed out. Try again.")
        return None

def sport_pill(sport: str) -> str:
    s = sport.lower()
    if s == "wikipedia":
        return '<span class="sport-pill p-wikipedia">🌐 Wiki</span>'
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
            "answer":       r.get("answer",""),
            "sport_filter": None if sport_filter == "All sports" else sport_filter,
            "total_ms":     r.get("latency_ms",{}).get("total_ms", 0),
            "timestamp":    time.time(),
        })
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  HERO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>Sports Intelligence, Powered by <em>RAG</em></h1>
  <p>Retrieval-Augmented Generation for Football, Basketball, Tennis, Cricket and more.</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  SEARCH BAR  —  input + pink submit button side by side
# ─────────────────────────────────────────────────────────────────────────────
c_input, c_btn = st.columns([15, 1])
with c_input:
    question = st.text_input(
        "q", label_visibility="collapsed",
        placeholder="Ask anything about sports…",
        key="main_input",
    )
with c_btn:
    # .submit-wrap scopes the pink style to ONLY this button
    st.markdown('<div class="submit-wrap">', unsafe_allow_html=True)
    submit = st.button("→", key="submit_btn")
    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  CHIPS  —  shown only on empty state, centered, 3 per row
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
    st.markdown('<div class="chips-outer"><div class="chips-label">Try asking</div></div>',
                unsafe_allow_html=True)

    for row_start in range(0, len(EXAMPLES), 3):
        row = EXAMPLES[row_start : row_start + 3]
        # equal-width columns; 3 is wide enough for chip text
        cols = st.columns([1, 1, 1])
        for col, ex in zip(cols, row):
            with col:
                label = ex if len(ex) <= 34 else ex[:32] + "…"
                if st.button(label, key=f"chip_{EXAMPLES.index(ex)}", use_container_width=False):
                    run_query(ex)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  SUBMIT HANDLER
# ─────────────────────────────────────────────────────────────────────────────
if submit and question.strip():
    if len(question.strip()) < 3:
        st.warning("Question too short.")
    else:
        run_query(question.strip())

# ─────────────────────────────────────────────────────────────────────────────
#  RESULT
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

    # Answer
    total_ms  = lat.get("total_ms", 0)
    ret_ms    = lat.get("dense_ms", lat.get("wiki_ms", 0))
    rerank_ms = lat.get("rerank_ms", 0)
    llm_ms    = lat.get("llm_ms", 0)

    st.markdown(f"""
    <div class="answer-card">
      <div class="answer-hdr">
        <span class="spark">✦</span>
        <span class="label">Answer</span>
      </div>
      <div class="answer-body">{answer}</div>
      <div class="latency-strip">
        <div class="lat"><span class="k">◷</span> Total&nbsp;<span class="v">{total_ms}ms</span></div>
        <div class="lat"><span class="k">◎</span> Retrieve&nbsp;<span class="v">{ret_ms}ms</span></div>
        <div class="lat"><span class="k">⇌</span> Rerank&nbsp;<span class="v">{rerank_ms}ms</span></div>
        <div class="lat"><span class="k">⊕</span> LLM&nbsp;<span class="v">{llm_ms}ms</span></div>
      </div>
    </div>""", unsafe_allow_html=True)

    # Sources
    if sources:
        rows_html = ""
        for i, src in enumerate(sources, 1):
            sp   = src.get("sport", "unknown")
            text = src.get("text", "")[:200]
            pill = ('<span class="sport-pill p-wikipedia">🌐 Wiki</span>'
                    if src.get("source","") == "wikipedia" else sport_pill(sp))
            rows_html += f"""
            <div class="src-row">
              <div class="src-num">#{i}</div>
              {pill}
              <div class="src-text">{text}…</div>
            </div>"""

        show    = st.session_state.show_sources
        chevron = "∧" if show else "∨"

        st.markdown(f"""
        <div class="sources-card">
          <div class="sources-hdr">
            <span class="stitle">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              Sources
            </span>
            <span class="scount">{len(sources)} chunks &nbsp;{chevron}</span>
          </div>
          {"" if not show else rows_html}
        </div>""", unsafe_allow_html=True)

        if st.button("▲ Hide" if show else "▼ Show sources", key="toggle_src"):
            st.session_state.show_sources = not st.session_state.show_sources
            st.rerun()

    # New question button
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