"""
scripts/test_retriever.py
──────────────────────────────────────────────────────────────────────────────
Validates the retriever across all 4 sports and query types.
Run BEFORE testing the full RAG chain — isolates retrieval issues from LLM issues.

Usage:
    python scripts/test_retriever.py
    python scripts/test_retriever.py --explain  (shows stage-by-stage scores)
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel

console = Console()


TEST_QUERIES = [
    # (query, expected_sport, description)
    ("Who won the 2019 IPL final?",                       "cricket",    "Exact match — known winner"),
    ("Top scorer in Premier League 2020 season",          "football",   "Stat lookup — football"),
    ("Djokovic Wimbledon 2015",                           "tennis",     "Player + tournament + year"),
    ("NBA game with most points scored",                  "basketball", "Superlative query"),
    ("Arsenal vs Chelsea result",                         "football",   "Head-to-head match"),
    ("Which team won the most IPL seasons?",              "cricket",    "Aggregate / multi-hop"),
    ("Rafael Nadal clay court matches",                   "tennis",     "Player + surface"),
    ("LeBron James stats",                                "basketball", "Player profile"),
]


def run_tests(explain: bool = False):
    console.print(Panel(
        "[bold]Sports RAG — Retriever Test Suite[/bold]\n"
        "Testing FAISS + BM25 hybrid retrieval across 4 sports",
        border_style="blue"
    ))

    from src.retrieval.retriever import SportsRetriever
    retriever = SportsRetriever()

    results_table = Table(
        title="Retrieval Results",
        show_lines=True,
        title_style="bold"
    )
    results_table.add_column("Query",          width=40)
    results_table.add_column("Expected",       width=12)
    results_table.add_column("Got sport",      width=12)
    results_table.add_column("Top chunk",      width=50)
    results_table.add_column("Rerank",         width=8)
    results_table.add_column("Time ms",        width=8)

    passed = 0
    for query, expected_sport, desc in TEST_QUERIES:
        result = retriever.retrieve(query)

        if not result.chunks:
            results_table.add_row(
                query[:40], expected_sport, "NO RESULTS", "—", "—", "—",
                style="red"
            )
            continue

        top    = result.chunks[0]
        got    = top.sport
        match  = "✓" if got == expected_sport else "?"
        style  = "green" if got == expected_sport else "yellow"

        if got == expected_sport:
            passed += 1

        results_table.add_row(
            query[:40],
            expected_sport,
            f"{match} {got}",
            top.text[:50] + "...",
            f"{top.rerank_score:.3f}",
            str(result.latency.get("total_ms", 0)),
            style=style,
        )

        if explain:
            retriever.explain(query)

    console.print(results_table)
    console.print(
        f"\n[bold]Result: {passed}/{len(TEST_QUERIES)} sport matches correct[/bold]"
    )

    # Latency summary
    console.print("\n[bold]Running latency benchmark (5 queries × 3 runs)...[/bold]")
    import time
    latencies = []
    bench_queries = TEST_QUERIES[:5]

    for _ in range(3):
        for q, _, _ in bench_queries:
            t0 = time.time()
            retriever.retrieve(q)
            latencies.append(round((time.time() - t0) * 1000))

    latencies.sort()
    n = len(latencies)
    console.print(f"  P50  : {latencies[n//2]}ms")
    console.print(f"  P95  : {latencies[int(n*0.95)]}ms")
    console.print(f"  P99  : {latencies[int(n*0.99)]}ms")
    console.print(f"  Mean : {sum(latencies)//len(latencies)}ms")

    console.print("\n[bold green]Retriever test complete.[/bold green]")
    console.print("Next step: python scripts/test_rag_chain.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--explain", action="store_true",
                        help="Show stage-by-stage scores for each query")
    args = parser.parse_args()
    run_tests(explain=args.explain)
