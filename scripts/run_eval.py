"""
scripts/run_eval.py
Evaluation suite with accurate source tracking.

source_used values tracked:
  wikipedia           → bio intent + Wikipedia succeeded    ✓ correct
  faiss_bio_fallback  → bio intent + Wikipedia failed       ✗ issue
  sofascore_api       → live intent + API succeeded         ✓ correct
  sofascore_unavailable→ live intent + no key              ~ acceptable
  faiss               → history intent                      ✓ correct
  faiss_wiki_boost    → history + weak FAISS + wiki boost   ✓ bonus

Run: python scripts/run_eval.py
"""
import sys
import json
import time
import requests
from pathlib import Path
from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel

BASE    = "http://localhost:8000"
TIMEOUT = 90
console = Console()

# Source correctness rules — what counts as correct for each expected source
SOURCE_CORRECT_MAP = {
    "wikipedia":     ["wikipedia", "faiss_bio_fallback"],  # tried wiki = correct intent
    "sofascore_api": ["sofascore_api", "sofascore_unavailable"],
    "faiss":         ["faiss", "faiss_wiki_boost"],
}

# Source display labels
SOURCE_LABELS = {
    "wikipedia":              "🌐 Wikipedia",
    "faiss_bio_fallback":     "⚠ Wiki→FAISS",
    "sofascore_api":          "📡 Live API",
    "sofascore_unavailable":  "⚠ No API key",
    "faiss":                  "💾 FAISS",
    "faiss_wiki_boost":       "💾+🌐 FAISS+Wiki",
}


def run():
    questions = json.loads(
        (Path(__file__).parent.parent / "data/eval/questions.json").read_text()
    )

    console.print(Panel(
        f"[bold]Sports RAG — Evaluation Suite[/bold]\n"
        f"{len(questions)} questions · intent routing · source tracking · latency",
        border_style="blue"
    ))

    # Check server
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        health = r.json()
        wiki_status = "unknown"
        console.print(
            f"  Server: [green]OK[/green] | "
            f"Vectors: {health.get('index_vectors',0):,} | "
            f"Uptime: {health.get('uptime_s',0):.0f}s"
        )
    except Exception:
        console.print("[red]Server not running. Start: uvicorn src.api.main:app --reload --port 8000[/red]")
        sys.exit(1)

    results         = []
    intent_correct  = 0
    source_correct  = 0
    wiki_succeeded  = 0
    wiki_failed     = 0
    no_data_count   = 0
    latencies       = []

    table = Table(show_lines=True, title="Evaluation Results")
    table.add_column("Q",        width=3)
    table.add_column("Question", width=35)
    table.add_column("Intent",   width=7)
    table.add_column("✓",        width=2)
    table.add_column("Source used",   width=16)
    table.add_column("✓",        width=2)
    table.add_column("ms",       width=6)
    table.add_column("Answer preview", width=38)

    for q in questions:
        try:
            t0 = time.time()
            r  = requests.post(
                f"{BASE}/query",
                json={"question": q["question"]},
                timeout=TIMEOUT,
            )
            ms = round((time.time() - t0) * 1000)

            if r.status_code != 200:
                console.print(f"  [red]Q{q['id']} HTTP {r.status_code}[/red]")
                continue

            data = r.json()
            latencies.append(ms)

            got_intent  = data.get("intent", "?")
            got_source  = data.get("source_used", "?")
            exp_intent  = q["expected_intent"]
            exp_source  = q["expected_source"]
            answer      = data.get("answer", "")
            wiki_ok     = data.get("wiki_ok", None)

            # Intent check
            intent_ok = got_intent == exp_intent
            if intent_ok:
                intent_correct += 1

            # Source check — use correctness map
            correct_sources = SOURCE_CORRECT_MAP.get(exp_source, [exp_source])
            source_ok = got_source in correct_sources
            if source_ok:
                source_correct += 1

            # Wiki tracking
            if got_source == "wikipedia":
                wiki_succeeded += 1
            elif got_source == "faiss_bio_fallback":
                wiki_failed += 1

            # No-data check
            no_data = any(phrase in answer.lower() for phrase in [
                "don't have enough data",
                "not contain",
                "no information",
                "cannot find",
                "provided context does not",
            ])
            if no_data:
                no_data_count += 1

            i_icon = "✓" if intent_ok else "✗"
            s_icon = "✓" if source_ok else "~"
            i_style = "green" if intent_ok else "red"
            s_style = "green" if source_ok else "yellow"

            source_label = SOURCE_LABELS.get(got_source, got_source)[:16]

            table.add_row(
                str(q["id"]),
                q["question"][:35],
                got_intent,
                f"[{i_style}]{i_icon}[/{i_style}]",
                source_label,
                f"[{s_style}]{s_icon}[/{s_style}]",
                str(ms),
                answer[:38] + "..." if len(answer) > 38 else answer,
            )

            results.append({
                **q,
                "got_intent":  got_intent,
                "got_source":  got_source,
                "ms":          ms,
                "intent_ok":   intent_ok,
                "source_ok":   source_ok,
                "no_data":     no_data,
                "answer":      answer,
            })

            time.sleep(1)

        except Exception as e:
            console.print(f"  [red]Q{q['id']} error: {e}[/red]")

    console.print(table)

    n = len(results)
    if n == 0:
        console.print("[red]No results — check server[/red]")
        return

    latencies.sort()

    # Wiki breakdown
    bio_total    = sum(1 for r in results if r["got_intent"] == "bio")
    wiki_rate    = f"{wiki_succeeded}/{bio_total}" if bio_total else "0/0"

    console.print(Panel(
        f"[bold]Evaluation Report ({n} questions)[/bold]\n\n"
        f"Intent routing accuracy  : "
        f"[{'green' if intent_correct/n > 0.8 else 'yellow'}]{intent_correct}/{n} ({intent_correct/n*100:.0f}%)[/]\n"
        f"Source routing accuracy  : "
        f"[{'green' if source_correct/n > 0.8 else 'yellow'}]{source_correct}/{n} ({source_correct/n*100:.0f}%)[/]\n"
        f"  Wikipedia succeeded    : [green]{wiki_succeeded}[/] bio queries\n"
        f"  Wikipedia failed→FAISS : [{'red' if wiki_failed > 2 else 'yellow'}]{wiki_failed}[/] bio queries\n"
        f"'No data' responses      : "
        f"[{'green' if no_data_count < 4 else 'red'}]{no_data_count}/{n}[/]\n\n"
        f"Latency P50  : {latencies[n//2]}ms\n"
        f"Latency P95  : {latencies[min(int(n*0.95), n-1)]}ms\n"
        f"Latency Mean : {sum(latencies)//n}ms",
        border_style="green",
        title="Evaluation Report",
    ))

    # Wiki failure analysis
    wiki_failures = [r for r in results if r["got_source"] == "faiss_bio_fallback"]
    if wiki_failures:
        console.print(f"\n[yellow]Wikipedia failed for {len(wiki_failures)} bio queries:[/yellow]")
        for r in wiki_failures:
            console.print(f"  Q{r['id']}: {r['question']}")
        console.print(
            "\n[dim]Fix: python scripts/test_wiki.py  "
            "— to diagnose Wikipedia connectivity[/dim]"
        )

    # No-data analysis
    no_data_qs = [r for r in results if r["no_data"]]
    if no_data_qs:
        console.print(f"\n[yellow]'No data' for {len(no_data_qs)} questions:[/yellow]")
        for r in no_data_qs:
            console.print(f"  Q{r['id']}: {r['question']}")

    # Save report
    report_path = Path("data/eval/report.json")
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps({
        "total":            n,
        "intent_accuracy":  round(intent_correct / n, 3),
        "source_accuracy":  round(source_correct / n, 3),
        "wiki_succeeded":   wiki_succeeded,
        "wiki_failed":      wiki_failed,
        "no_data_rate":     round(no_data_count / n, 3),
        "p50_ms":           latencies[n//2],
        "p95_ms":           latencies[min(int(n*0.95), n-1)],
        "mean_ms":          sum(latencies) // n,
        "results":          results,
    }, indent=2))
    console.print(f"\n[dim]Report saved → {report_path}[/dim]")


if __name__ == "__main__":
    run()
