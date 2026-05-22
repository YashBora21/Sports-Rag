"""
src/frontend/app.py
Sports RAG — Streamlit frontend

Run:
    streamlit run src/frontend/app.py

Requires API running at http://localhost:8000
    uvicorn src.api.main:app --reload --port 8000
"""

import time
import requests
import streamlit as st

API_BASE = "http://localhost:8000"
TIMEOUT  = 120

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "Sports RAG",
    page_icon  = "⚽",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
.stApp {
    background: #0a0e17;
}

/* ── Hide default elements ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* ── Header ── */
.rag-header {
    background: linear-gradient(135deg, #0f1623 0%, #1a2540 50%, #0f1623 100%);
    border: 1px solid rgba(255,165,0,0.2);
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.rag-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #ff6b00, #ffa500, #ff6b00);
}
.rag-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    letter-spacing: 4px;
    color: #ffffff;
    margin: 0;
    line-height: 1;
}
.rag-title span { color: #ffa500; }
.rag-subtitle {
    font-size: 0.85rem;
    color: #8892a4;
    margin-top: 6px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* ── Status pills ── */
.status-row { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
.status-pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 4px 12px;
    border-radius: 20px;
    border: 1px solid;
}
.pill-ok    { background: rgba(0,200,100,0.1); border-color: rgba(0,200,100,0.4); color: #00c864; }
.pill-warn  { background: rgba(255,165,0,0.1); border-color: rgba(255,165,0,0.4); color: #ffa500; }
.pill-error { background: rgba(255,60,60,0.1); border-color: rgba(255,60,60,0.4); color: #ff3c3c; }

/* ── Answer card ── */
.answer-card {
    background: linear-gradient(135deg, #111827 0%, #1a2540 100%);
    border: 1px solid rgba(255,165,0,0.3);
    border-radius: 14px;
    padding: 24px 28px;
    margin: 16px 0;
    position: relative;
}
.answer-card::before {
    content: '';
    position: absolute;
    left: 0; top: 20%; bottom: 20%;
    width: 3px;
    background: linear-gradient(180deg, #ff6b00, #ffa500);
    border-radius: 2px;
}
.answer-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    color: #ffa500;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.answer-text {
    font-size: 1.05rem;
    color: #e8edf5;
    line-height: 1.75;
    margin: 0;
}

/* ── Timing bar ── */
.timing-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 14px;
}
.timing-chip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 6px;
    padding: 3px 10px;
    color: #8892a4;
}
.timing-chip b { color: #c8d3e0; }

/* ── Source chunk card ── */
.source-card {
    background: #111827;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
}
.source-card:hover { border-color: rgba(255,165,0,0.3); }
.source-meta {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
    flex-wrap: wrap;
}
.sport-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.tag-football   { background: rgba(0,128,255,0.15); color: #4d9fff; border: 1px solid rgba(0,128,255,0.3); }
.tag-basketball { background: rgba(255,100,0,0.15); color: #ff7433; border: 1px solid rgba(255,100,0,0.3); }
.tag-tennis     { background: rgba(50,200,100,0.15); color: #32c864; border: 1px solid rgba(50,200,100,0.3); }
.tag-cricket    { background: rgba(180,100,255,0.15); color: #c86eff; border: 1px solid rgba(180,100,255,0.3); }
.tag-unknown    { background: rgba(150,150,150,0.15); color: #aaa; border: 1px solid rgba(150,150,150,0.3); }
.score-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #8892a4;
    margin-left: auto;
}
.source-text {
    font-size: 0.88rem;
    color: #8892a4;
    line-height: 1.6;
    margin: 0;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0d1120 !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
.sidebar-section {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    color: #ffa500;
    text-transform: uppercase;
    margin: 20px 0 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255,165,0,0.2);
}

/* ── Input styling ── */
.stTextArea textarea {
    background: #111827 !important;
    border: 1px solid rgba(255,165,0,0.2) !important;
    color: #e8edf5 !important;
    font-family: 'DM Sans', sans-serif !important;
    border-radius: 10px !important;
}
.stTextArea textarea:focus {
    border-color: rgba(255,165,0,0.6) !important;
    box-shadow: 0 0 0 1px rgba(255,165,0,0.3) !important;
}
.stButton > button {
    background: linear-gradient(135deg, #ff6b00, #ffa500) !important;
    color: #000 !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.1rem !important;
    letter-spacing: 2px !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.5rem 2rem !important;
    width: 100% !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* ── Chat history ── */
.history-item {
    background: #111827;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 6px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}
.history-item:hover {
    border-color: rgba(255,165,0,0.3);
    background: #151d2e;
}
.history-q {
    font-size: 0.82rem;
    color: #c8d3e0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.history-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: #4a5568;
    margin-top: 2px;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #4a5568;
}
.empty-icon { font-size: 3rem; margin-bottom: 12px; }
.empty-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.5rem;
    letter-spacing: 3px;
    color: #2d3748;
    margin-bottom: 8px;
}
.example-queries { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 20px; }
.example-chip {
    background: rgba(255,165,0,0.08);
    border: 1px solid rgba(255,165,0,0.2);
    color: #ffa500;
    font-size: 0.8rem;
    padding: 6px 14px;
    border-radius: 20px;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "history"       not in st.session_state: st.session_state.history       = []
if "current_result" not in st.session_state: st.session_state.current_result = None
if "api_status"    not in st.session_state: st.session_state.api_status    = None


# ── API helpers ───────────────────────────────────────────────────────────────

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
        st.error("Cannot reach API. Is the server running?\n`uvicorn src.api.main:app --reload --port 8000`")
        return None
    except requests.Timeout:
        st.error("Request timed out. The LLM may be slow — try again.")
        return None


def sport_tag_html(sport: str) -> str:
    cls = f"tag-{sport.lower()}" if sport.lower() in ["football","basketball","tennis","cricket"] else "tag-unknown"
    icons = {"football": "⚽", "basketball": "🏀", "tennis": "🎾", "cricket": "🏏"}
    icon  = icons.get(sport.lower(), "🏆")
    return f'<span class="sport-tag {cls}">{icon} {sport}</span>'


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="sidebar-section">⚙ Configuration</div>', unsafe_allow_html=True)

    sport_filter = st.selectbox(
        "Sport filter",
        ["All sports", "Football", "Basketball", "Tennis", "Cricket"],
        help="Restrict retrieval to one sport",
    )
    top_k = st.slider("Source chunks", min_value=1, max_value=10, value=5,
                      help="Number of source passages shown to the LLM")

    st.markdown('<div class="sidebar-section">📡 API Status</div>', unsafe_allow_html=True)
    health = get_health()
    if health:
        overall = health.get("status", "unknown")
        pill_cls = "pill-ok" if overall == "ok" else "pill-warn" if overall == "degraded" else "pill-error"
        st.markdown(f"""
        <div class="status-row">
          <span class="status-pill {pill_cls}">● {overall.upper()}</span>
          <span class="status-pill pill-ok">{health.get('index_vectors',0):,} vectors</span>
          <span class="status-pill pill-ok">↑ {health.get('uptime_s',0):.0f}s</span>
        </div>""", unsafe_allow_html=True)
        for k, v in health.get("components", {}).items():
            icon = "✓" if v["status"] == "ok" else "✗"
            cls  = "pill-ok" if v["status"] == "ok" else "pill-error"
            st.markdown(f'<div style="margin-top:6px"><span class="status-pill {cls}">{icon} {k}</span></div>',
                        unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-pill pill-error">● API OFFLINE</span>', unsafe_allow_html=True)
        st.caption("Start: `uvicorn src.api.main:app --reload --port 8000`")

    if st.button("↺ Refresh status", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Query history
    if st.session_state.history:
        st.markdown('<div class="sidebar-section">🕑 History</div>', unsafe_allow_html=True)
        for i, item in enumerate(reversed(st.session_state.history[-10:])):
            elapsed = time.time() - item["timestamp"]
            age     = f"{int(elapsed//60)}m ago" if elapsed > 60 else f"{int(elapsed)}s ago"
            sport_label = item.get("sport_filter") or "all"
            st.markdown(f"""
            <div class="history-item">
              <div class="history-q">{item['question'][:60]}{'…' if len(item['question'])>60 else ''}</div>
              <div class="history-meta">{age} · {sport_label} · {item.get('total_ms',0)}ms</div>
            </div>""", unsafe_allow_html=True)

        if st.button("Clear history", use_container_width=True):
            st.session_state.history       = []
            st.session_state.current_result = None
            st.rerun()


# ── Main content ──────────────────────────────────────────────────────────────

# Header
st.markdown("""
<div class="rag-header">
  <div class="rag-title">SPORTS <span>RAG</span></div>
  <div class="rag-subtitle">Retrieval-Augmented Generation · Football · Basketball · Tennis · Cricket</div>
</div>
""", unsafe_allow_html=True)

# Query input
col1, col2 = st.columns([5, 1])
with col1:
    question = st.text_area(
        "Ask a sports question",
        placeholder="e.g. Who won the 2019 IPL final?  ·  Arsenal results in 2021  ·  Nadal clay court record",
        height=90,
        label_visibility="collapsed",
    )
with col2:
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    submit = st.button("ASK", use_container_width=True)

# Example queries (shown when no history)
EXAMPLES = [
    "Who won the 2019 IPL final?",
    "Arsenal vs Chelsea results 2021",
    "Djokovic vs Federer Wimbledon",
    "LeBron James stats this season",
    "Nadal clay court record",
    "Premier League top scorer 2020",
]

# Handle submit
if submit and question.strip():
    if len(question.strip()) < 3:
        st.warning("Question is too short.")
    else:
        with st.spinner("🔍 Retrieving · Reranking · Generating..."):
            result = query_api(
                question     = question.strip(),
                sport_filter = sport_filter,
                top_k        = top_k,
            )
        if result:
            st.session_state.current_result = result
            st.session_state.history.append({
                "question":    question.strip(),
                "answer":      result["answer"],
                "sport_filter": sport_filter if sport_filter != "All sports" else None,
                "total_ms":    result["latency_ms"].get("total_ms", 0),
                "timestamp":   time.time(),
            })

elif submit and not question.strip():
    st.warning("Please enter a question.")

# ── Result display ────────────────────────────────────────────────────────────

result = st.session_state.current_result

if result:
    lat = result.get("latency_ms", {})

    # Answer card
    st.markdown(f"""
    <div class="answer-card">
      <div class="answer-label">Answer</div>
      <p class="answer-text">{result['answer']}</p>
      <div class="timing-row">
        <span class="timing-chip">⚡ total <b>{lat.get('total_ms',0)}ms</b></span>
        <span class="timing-chip">🔍 retrieve <b>{lat.get('dense_ms',0)}ms</b></span>
        <span class="timing-chip">📊 rerank <b>{lat.get('rerank_ms',0)}ms</b></span>
        <span class="timing-chip">🤖 llm <b>{lat.get('llm_ms',0)}ms</b></span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Sources
    sources = result.get("sources", [])
    if sources:
        with st.expander(f"📄 View {len(sources)} source chunks used", expanded=False):
            for i, src in enumerate(sources, 1):
                sport     = src.get("sport", "unknown")
                score     = src.get("rerank_score", 0)
                text      = src.get("text", "")
                meta      = src.get("metadata", {})
                season    = meta.get("season", meta.get("date", ""))
                comp      = meta.get("competition", meta.get("tournament", ""))

                st.markdown(f"""
                <div class="source-card">
                  <div class="source-meta">
                    <span style="font-family:monospace;font-size:11px;color:#4a5568">#{i}</span>
                    {sport_tag_html(sport)}
                    {"<span style='font-size:11px;color:#4a5568'>" + comp + "</span>" if comp else ""}
                    {"<span style='font-size:11px;color:#4a5568'>" + str(season) + "</span>" if season else ""}
                    <span class="score-badge">score: {score:.3f}</span>
                  </div>
                  <p class="source-text">{text}</p>
                </div>
                """, unsafe_allow_html=True)

else:
    # Empty state with example queries
    st.markdown("""
    <div class="empty-state">
      <div class="empty-icon">🏆</div>
      <div class="empty-title">Ask anything about sports</div>
      <div style="font-size:0.85rem;color:#4a5568">121,239 matches · Football · Basketball · Tennis · Cricket</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='text-align:center;margin-top:8px;font-size:0.8rem;color:#4a5568'>Try an example:</div>",
                unsafe_allow_html=True)

    cols = st.columns(3)
    for i, ex in enumerate(EXAMPLES):
        with cols[i % 3]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                with st.spinner("🔍 Retrieving · Reranking · Generating..."):
                    result = query_api(ex, sport_filter, top_k)
                if result:
                    st.session_state.current_result = result
                    st.session_state.history.append({
                        "question":    ex,
                        "answer":      result["answer"],
                        "sport_filter": sport_filter if sport_filter != "All sports" else None,
                        "total_ms":    result["latency_ms"].get("total_ms", 0),
                        "timestamp":   time.time(),
                    })
                    st.rerun()
