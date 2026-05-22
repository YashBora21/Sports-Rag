"""
scripts/test_api.py
Tests all API endpoints.

    # Terminal 1
    uvicorn src.api.main:app --reload --port 8000

    # Terminal 2
    python scripts/test_api.py
"""
import sys
import time
import requests
from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel

BASE    = "http://localhost:8000"
TIMEOUT = 60        # seconds — LLM + retrieval can take up to 15s cold
console = Console()


def check_server():
    try:
        requests.get(f"{BASE}/health", timeout=5)
    except requests.ConnectionError:
        console.print(
            "[red]Server not running.[/red]\n"
            "Start it:\n  [bold]uvicorn src.api.main:app --reload --port 8000[/bold]"
        )
        sys.exit(1)


def test_health():
    console.print("\n[bold]── GET /health ──[/bold]")
    r    = requests.get(f"{BASE}/health", timeout=10)
    data = r.json()
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    from rich.table import Table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("key",   style="dim",  width=22)
    table.add_column("value", style="bold")
    table.add_row("status",        data["status"])
    table.add_row("version",       data["version"])
    table.add_row("index vectors", f"{data['index_vectors']:,}")
    table.add_row("uptime",        f"{data['uptime_s']}s")
    for k, v in data["components"].items():
        icon   = "✓" if v["status"] == "ok" else "✗"
        detail = f" — {v['detail']}" if v.get("detail") else ""
        table.add_row(f"  {k}", f"[green]{icon}[/green] {v['status']}{detail}")
    console.print(table)

    assert data["status"] == "ok", f"Health not ok: {data}"
    console.print("[green]✓ /health passed[/green]")


def test_query_basic():
    console.print("\n[bold]── POST /query — basic ──[/bold]")
    r = requests.post(
        f"{BASE}/query",
        json={"question": "Who won the 2019 IPL final?"},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, f"{r.status_code}: {r.text}"
    data = r.json()

    console.print(Panel(data["answer"], title="Answer", border_style="green"))
    console.print(f"[dim]Latency : {data['latency_ms']}[/dim]")
    console.print(f"[dim]Sources : {len(data['sources'])} chunks[/dim]")
    if data["sources"]:
        console.print(f"[dim]Sports  : {list({s['sport'] for s in data['sources']})}[/dim]")
        console.print(f"[dim]Top src : {data['sources'][0]['text'][:100]}...[/dim]")

    assert data["answer"], "Empty answer"
    assert len(data["sources"]) > 0, "No sources returned"
    if "don't have enough data" in data["answer"].lower():
        console.print("[yellow]⚠  Gemini said no data despite sources — check gemini_client.py safety settings[/yellow]")
    console.print("[green]✓ /query basic passed[/green]")


def test_query_sport_filter():
    console.print("\n[bold]── POST /query — sport filter ──[/bold]")
    r = requests.post(
        f"{BASE}/query",
        json={"question": "Arsenal vs Chelsea match results", "sport_filter": "football", "top_k": 3},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, f"{r.status_code}: {r.text}"
    data = r.json()

    sports = {s["sport"] for s in data["sources"]}
    console.print(f"Sports in sources: {sports}")
    console.print(Panel(data["answer"][:400], title="Answer (football filter)"))

    if sports:
        assert sports == {"football"}, f"Expected only football, got {sports}"
    console.print("[green]✓ /query sport_filter passed[/green]")


def test_query_validation():
    console.print("\n[bold]── POST /query — input validation ──[/bold]")

    r = requests.post(f"{BASE}/query", json={"question": "hi"}, timeout=10)
    assert r.status_code == 422, f"Expected 422 for short query, got {r.status_code}"
    console.print("  ✓ Short query rejected (422)")

    r = requests.post(f"{BASE}/query", json={}, timeout=10)
    assert r.status_code == 422, f"Expected 422 for missing question, got {r.status_code}"
    console.print("  ✓ Missing question rejected (422)")

    r = requests.post(f"{BASE}/query", json={"question": "valid question here", "top_k": 99}, timeout=10)
    assert r.status_code == 422, f"Expected 422 for top_k=99, got {r.status_code}"
    console.print("  ✓ top_k=99 rejected (422)")

    console.print("[green]✓ /query validation passed[/green]")


def test_multiple_sports():
    console.print("\n[bold]── POST /query — all 4 sports ──[/bold]")
    queries = [
        ("Who won the 2019 IPL final?",             "cricket"),
        ("Arsenal Premier League results 2021",     "football"),
        ("Djokovic vs Federer Wimbledon match",     "tennis"),
        ("LeBron James points rebounds assists",    "basketball"),
    ]
    table = Table(title="Multi-sport queries", show_lines=True)
    table.add_column("Question",       width=40)
    table.add_column("Filter",         width=12)
    table.add_column("Answer preview", width=48)
    table.add_column("ms",             width=6)

    for question, sport in queries:
        t0  = time.time()
        r   = requests.post(
            f"{BASE}/query",
            json={"question": question, "sport_filter": sport},
            timeout=TIMEOUT,
        )
        ms  = round((time.time() - t0) * 1000)
        assert r.status_code == 200, f"{r.status_code}: {r.text}"
        data = r.json()
        table.add_row(question[:40], sport, data["answer"][:48] + "...", str(ms))

    console.print(table)
    console.print("[green]✓ Multi-sport queries passed[/green]")


def test_latency_benchmark():
    console.print("\n[bold]── Latency benchmark (10 queries) ──[/bold]")
    questions = [
        "Who won the 2018 IPL final?",
        "Arsenal away matches 2020",
        "Nadal French Open wins",
        "NBA player with most assists",
        "Premier League top scorer 2019",
    ]
    latencies = []
    for q in questions * 2:
        t0 = time.time()
        r  = requests.post(
            f"{BASE}/query",
            json={"question": q},
            timeout=TIMEOUT,          # ← FIX: was missing, caused AssertionError on slow queries
        )
        ms = round((time.time() - t0) * 1000)
        if r.status_code != 200:
            console.print(f"  [yellow]Skip {r.status_code}: {q[:40]}[/yellow]")
            continue
        latencies.append(ms)

    if not latencies:
        console.print("[red]No successful queries in benchmark[/red]")
        return

    latencies.sort()
    n = len(latencies)
    console.print(f"  P50 : {latencies[n//2]}ms")
    console.print(f"  P95 : {latencies[min(int(n*0.95), n-1)]}ms")
    console.print(f"  Mean: {sum(latencies)//n}ms")
    console.print("[green]✓ Latency benchmark complete[/green]")


def run_all():
    console.print(Panel(
        "[bold]Sports RAG API — Test Suite[/bold]\n"
        f"Testing against {BASE}",
        border_style="blue",
    ))
    check_server()
    test_health()
    test_query_basic()
    test_query_sport_filter()
    test_query_validation()
    test_multiple_sports()
    test_latency_benchmark()
    console.print(Panel(
        "[bold green]All tests passed![/bold green]\n"
        "Next: streamlit run src/frontend/app.py",
        border_style="green",
    ))


if __name__ == "__main__":
    run_all()
