"""
scripts/pre_enrich_check.py
Run this BEFORE enrich_data.py to make sure everything is ready.

    python scripts/pre_enrich_check.py
"""
import sys
import json
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.panel   import Panel

console = Console()
console.print(Panel("[bold]Pre-enrichment check[/bold]", border_style="blue"))

ok = True

# ── 1. Chunk files exist ──────────────────────────────────────────────────────
console.print("\n[bold]1. Chunk files[/bold]")
from src.config import DATA_CHUNKS, DATA_PROCESSED, DATA_EMBEDDINGS, RAPIDAPI_KEY

for name in ["football_chunks.jsonl", "basketball_chunks.jsonl",
             "tennis_chunks.jsonl",   "cricket_chunks.jsonl"]:
    path = DATA_CHUNKS / name
    if path.exists():
        n = sum(1 for _ in open(path, encoding="utf-8") if _.strip())
        console.print(f"  [green]✓[/green]  {name}  ({n:,} chunks)")
    else:
        console.print(f"  [red]✗[/red]  {name} MISSING")
        ok = False

# ── 2. Wikipedia scraper importable ──────────────────────────────────────────
console.print("\n[bold]2. Wikipedia scraper[/bold]")
try:
    from src.ingestion.wikipedia_scraper import PLAYERS, fetch_summary
    total_pages = sum(len(v) for v in PLAYERS.values())
    console.print(f"  [green]✓[/green]  wikipedia_scraper.py loaded ({total_pages} pages to scrape)")
except Exception as e:
    console.print(f"  [red]✗[/red]  {e}")
    ok = False

# ── 3. Wikipedia connectivity ─────────────────────────────────────────────────
console.print("\n[bold]3. Wikipedia API connectivity[/bold]")
try:
    r = requests.get(
        "https://en.wikipedia.org/api/rest_v1/page/summary/Cristiano_Ronaldo",
        headers={"User-Agent": "SportsRAG/1.0"},
        timeout=8,
    )
    if r.status_code == 200:
        data = r.json()
        preview = data.get("extract", "")[:80]
        console.print(f"  [green]✓[/green]  Wikipedia reachable")
        console.print(f"  [dim]  Preview: {preview}...[/dim]")
    else:
        console.print(f"  [yellow]⚠[/yellow]  Wikipedia returned {r.status_code}")
except Exception as e:
    console.print(f"  [red]✗[/red]  Cannot reach Wikipedia: {e}")
    ok = False

# ── 4. SofaScore API key ──────────────────────────────────────────────────────
console.print("\n[bold]4. SofaScore API (optional)[/bold]")
if RAPIDAPI_KEY and RAPIDAPI_KEY != "your-rapidapi-key-here":
    console.print(f"  [green]✓[/green]  RAPIDAPI_KEY set ({RAPIDAPI_KEY[:8]}...)")
    console.print(f"  [dim]  Live data will be collected[/dim]")
else:
    console.print(f"  [yellow]⚠[/yellow]  RAPIDAPI_KEY not set — will skip live data")
    console.print(f"  [dim]  Add to .env: RAPIDAPI_KEY=your-key[/dim]")

# ── 5. Disk space estimate ────────────────────────────────────────────────────
console.print("\n[bold]5. Estimated additions[/bold]")
console.print("  Wikipedia pages   : ~90 pages × ~800 chars = ~90 docs")
console.print("  SofaScore live    : ~500-800 match events")
console.print("  New chunks total  : ~1,000-1,500")
console.print("  Re-embedding time : ~25 min (same as first run)")

# ── Final verdict ─────────────────────────────────────────────────────────────
console.print()
if ok:
    console.print(Panel(
        "[bold green]All checks passed![/bold green]\n\n"
        "Run enrichment now:\n\n"
        "  [bold]# Step 1 — Collect data only (5 min, no re-embed yet)[/bold]\n"
        "  python scripts/enrich_data.py --skip-api --skip-embed\n\n"
        "  [bold]# Step 2 — Check what was collected[/bold]\n"
        "  python scripts/pre_enrich_check.py\n\n"
        "  [bold]# Step 3 — Rebuild the full index (25 min)[/bold]\n"
        "  python scripts/run_pipeline.py --data-dir data/raw --skip-api",
        border_style="green",
    ))
else:
    console.print(Panel(
        "[bold red]Fix the issues above before running enrich_data.py[/bold red]",
        border_style="red",
    ))
