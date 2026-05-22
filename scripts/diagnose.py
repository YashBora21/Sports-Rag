"""
scripts/diagnose.py
Run this whenever the API fails to start. It checks every file
the system needs and tells you exactly what's missing or broken.

Usage:
    python scripts/diagnose.py
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table   import Table

console = Console()


def check(label, ok, detail=""):
    icon  = "[green]✓[/green]" if ok else "[red]✗[/red]"
    color = "green" if ok else "red"
    console.print(f"  {icon}  [{color}]{label}[/{color}]  {detail}")
    return ok


def run():
    console.print("\n[bold]Sports RAG — Startup Diagnostics[/bold]\n")
    all_ok = True

    # ── Paths ──────────────────────────────────────────────────────────────
    from src.config import (
        DATA_RAW, DATA_PROCESSED, DATA_CHUNKS,
        DATA_EMBEDDINGS, FAISS_INDEX_PATH,
        GEMINI_API_KEY, EMBEDDING_MODEL,
    )

    console.print("[bold]1. Required files[/bold]")

    index_path = Path(str(FAISS_INDEX_PATH) + ".index")
    all_ok &= check("FAISS index",    index_path.exists(),
                    f"{index_path}")

    meta_path  = DATA_EMBEDDINGS / "metadata.jsonl"
    all_ok &= check("metadata.jsonl", meta_path.exists(),
                    f"{meta_path}")

    # ── metadata.jsonl content check ───────────────────────────────────────
    if meta_path.exists():
        console.print("\n[bold]2. metadata.jsonl integrity[/bold]")
        total = 0
        empty_lines = 0
        bad_json    = 0
        has_text    = 0
        no_text     = 0
        sample      = []

        with open(meta_path, encoding="utf-8") as f:
            for i, raw in enumerate(f):
                raw = raw.strip()
                if not raw:
                    empty_lines += 1
                    continue
                try:
                    obj = json.loads(raw)
                    total += 1
                    if obj.get("text"):
                        has_text += 1
                        if len(sample) < 2:
                            sample.append(obj)
                    else:
                        no_text += 1
                except json.JSONDecodeError:
                    bad_json += 1

        check("Total entries",      total > 0,     f"{total:,}")
        check("Empty lines",        empty_lines == 0,
              f"{empty_lines} found (OK if small)")
        check("Bad JSON lines",     bad_json == 0, f"{bad_json} found")
        check("Entries WITH text",  has_text > 0,  f"{has_text:,}")
        check("Entries WITHOUT text", no_text == 0,
              f"{no_text:,} — run: python scripts/patch_metadata.py")

        if sample:
            console.print("\n  [dim]Sample entry 1:[/dim]")
            obj = sample[0]
            console.print(f"    faiss_id : {obj.get('faiss_id')}")
            console.print(f"    sport    : {obj.get('sport')}")
            console.print(f"    text     : {obj.get('text','')[:80]}...")
            console.print(f"    chunk_id : {obj.get('chunk_id','')[:40]}")

    # ── Chunk files ────────────────────────────────────────────────────────
    console.print("\n[bold]3. Chunk files[/bold]")
    chunk_files = list(DATA_CHUNKS.glob("*_chunks.jsonl"))
    check("Chunk files exist", len(chunk_files) > 0,
          f"{len(chunk_files)} files found")
    for cf in sorted(chunk_files):
        n = sum(1 for _ in open(cf, encoding="utf-8") if _.strip())
        check(f"  {cf.name}", n > 0, f"{n:,} chunks")

    # ── Environment ────────────────────────────────────────────────────────
    console.print("\n[bold]4. Environment[/bold]")
    check("GEMINI_API_KEY set",
          bool(GEMINI_API_KEY) and GEMINI_API_KEY != "AIza-your-gemini-key-here",
          f"{'set (' + GEMINI_API_KEY[:8] + '...)' if GEMINI_API_KEY else 'MISSING'}")

    # ── Python packages ────────────────────────────────────────────────────
    console.print("\n[bold]5. Key packages[/bold]")
    packages = [
        ("faiss",               "faiss"),
        ("sentence_transformers","sentence_transformers"),
        ("rank_bm25",           "rank_bm25"),
        ("google.generativeai", "google.generativeai"),
        ("fastapi",             "fastapi"),
        ("langchain",           "langchain"),
    ]
    for label, mod in packages:
        try:
            __import__(mod)
            check(label, True)
        except ImportError as e:
            check(label, False, str(e))
            all_ok = False

    # ── Final verdict ──────────────────────────────────────────────────────
    console.print()
    if all_ok:
        console.print("[bold green]All checks passed — server should start cleanly.[/bold green]")
    else:
        console.print("[bold red]Issues found — fix them before starting the server.[/bold red]")

    # ── Fix suggestions ────────────────────────────────────────────────────
    console.print("\n[bold]Fix commands (run in order if anything failed):[/bold]")
    console.print("  1. python scripts/patch_metadata.py        # fix missing text fields")
    console.print("  2. python scripts/run_pipeline.py --data-dir data/raw --skip-api --skip-embed")
    console.print("  3. uvicorn src.api.main:app --reload --port 8000")


if __name__ == "__main__":
    run()
