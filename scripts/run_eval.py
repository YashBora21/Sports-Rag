"""
scripts/run_eval.py
Runs 30 evaluation questions, measures intent routing accuracy,
latency, and answer quality.

    # Server must be running:
    uvicorn src.api.main:app --reload --port 8000

    python scripts/run_eval.py
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

def run():
    questions = json.loads(
        (Path(__file__).parent.parent / "data/eval/questions.json").read_text()
    )

    console.print(Panel(
        f"[bold]Sports RAG — Evaluation Suite[/bold]\n"
        f"{len(questions)} questions · intent routing · latency · source accuracy",
        border_style="blue"
    ))

    results = []
    intent_correct  = 0
    source_correct  = 0
    no_data_count   = 0
    latencies       = []

    table = Table(show_lines=True, title="Evaluation Results")
    table.add_column("Q",         width=3)
    table.add_column("Question",  width=38)
    table.add_column("Intent",    width=8)
    table.add_column("✓?",        width=3)
    table.add_column("Source",    width=18)
    table.add_column("✓?",        width=3)
    table.add_column("ms",        width=6)
    table.add_column("Answer",    width=40)

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
                console.print(f"  [red]Q{q['id']} failed: {r.status_code}[/red]")
                continue

            data = r.json()
            latencies.append(ms)

            got_intent  = data.get("intent", "?")
            got_source  = data.get("source_used", "?")
            exp_intent  = q["expected_intent"]
            exp_source  = q["expected_source"]
            answer      = data.get("answer", "")

            intent_ok   = got_intent == exp_intent
            source_ok   = exp_source in got_source  # partial match ok
            no_data     = "don't have enough data" in answer.lower() or \
                          "insufficient" in answer.lower()

            if intent_ok:  intent_correct += 1
            if source_ok:  source_correct += 1
            if no_data:    no_data_count  += 1

            i_icon = "[green]✓[/green]" if intent_ok else "[red]✗[/red]"
            s_icon = "[green]✓[/green]" if source_ok else "[yellow]~[/yellow]"
            row_style = "" if intent_ok else "dim"

            table.add_row(
                str(q["id"]),
                q["question"][:38],
                f"{got_intent}",
                i_icon,
                got_source[:18],
                s_icon,
                str(ms),
                answer[:40] + "..." if len(answer) > 40 else answer,
                style=row_style,
            )

            results.append({**q, "got_intent": got_intent,
                             "got_source": got_source, "ms": ms,
                             "intent_ok": intent_ok, "source_ok": source_ok,
                             "no_data": no_data})

            time.sleep(1)   # polite delay between queries

        except Exception as e:
            console.print(f"  [red]Q{q['id']} error: {e}[/red]")

    console.print(table)

    n = len(results)
    latencies.sort()

    console.print(Panel(
        f"[bold]Summary ({n} questions)[/bold]\n\n"
        f"Intent routing accuracy : [{'green' if intent_correct/n > 0.8 else 'yellow'}]"
        f"{intent_correct}/{n} ({intent_correct/n*100:.0f}%)[/]\n"
        f"Source routing accuracy : {source_correct}/{n} ({source_correct/n*100:.0f}%)\n"
        f"'No data' responses     : [{'green' if no_data_count < 5 else 'red'}]{no_data_count}/{n}[/]\n\n"
        f"Latency P50 : {latencies[n//2]}ms\n"
        f"Latency P95 : {latencies[int(n*0.95)]}ms\n"
        f"Latency Mean: {sum(latencies)//n}ms",
        border_style="green",
        title="Evaluation Report",
    ))

    # Save report
    report_path = Path("data/eval/report.json")
    report_path.write_text(json.dumps({
        "total":           n,
        "intent_accuracy": intent_correct / n,
        "source_accuracy": source_correct / n,
        "no_data_rate":    no_data_count / n,
        "p50_ms":          latencies[n//2],
        "p95_ms":          latencies[int(n*0.95)],
        "mean_ms":         sum(latencies) // n,
        "results":         results,
    }, indent=2))
    console.print(f"Report saved → {report_path}")


if __name__ == "__main__":
    run()
