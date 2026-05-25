"""
scripts/test_wiki.py
Diagnoses Wikipedia connectivity — run this if source_used shows
"faiss_bio_fallback" instead of "wikipedia" in eval results.

    python scripts/test_wiki.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from rich.console import Console
from rich.panel   import Panel

console = Console()
console.print(Panel("[bold]Wikipedia Connectivity Diagnostic[/bold]", border_style="blue"))

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS       = {"User-Agent": "SportsRAG/1.0"}

# Test 1 — basic connectivity
console.print("\n[bold]Test 1 — Basic connectivity[/bold]")
try:
    r = requests.get(MEDIAWIKI_API,
                     params={"action":"query","format":"json","titles":"Cricket","prop":"info"},
                     headers=HEADERS, timeout=10)
    console.print(f"  [green]✓[/green]  Status {r.status_code} — Wikipedia reachable")
except Exception as e:
    console.print(f"  [red]✗[/red]  {type(e).__name__}: {e}")
    console.print("\n  [yellow]Your machine cannot reach Wikipedia.[/yellow]")
    console.print("  This means bio queries will fall back to FAISS.")
    console.print("  Source accuracy in eval will show 'faiss_bio_fallback' for bio queries.")
    console.print("\n  This is expected on some corporate/restricted networks.")
    sys.exit(0)

# Test 2 — fetch Steve Smith
console.print("\n[bold]Test 2 — Fetch Steve Smith[/bold]")
from src.tools.wiki_tool import search_wikipedia
result = search_wikipedia("Steve Smith", "cricket")
if result:
    console.print(f"  [green]✓[/green]  Found: '{result['title']}'")
    console.print(f"  [dim]  Preview: {result['text'][:100]}...[/dim]")
    console.print(f"  [dim]  Tried: {result.get('tried',[])}[/dim]")
else:
    console.print("  [red]✗[/red]  search_wikipedia returned None")

# Test 3 — fetch Ronaldo
console.print("\n[bold]Test 3 — Fetch Cristiano Ronaldo[/bold]")
result = search_wikipedia("Cristiano Ronaldo", "football")
if result:
    console.print(f"  [green]✓[/green]  Found: '{result['title']}'")
else:
    console.print("  [red]✗[/red]  Not found")

# Test 4 — fetch LeBron James
console.print("\n[bold]Test 4 — Fetch LeBron James[/bold]")
result = search_wikipedia("LeBron James", "basketball")
if result:
    console.print(f"  [green]✓[/green]  Found: '{result['title']}'")
else:
    console.print("  [red]✗[/red]  Not found")

console.print(Panel(
    "If all tests passed → re-run eval:\n"
    "  [bold]python scripts/run_eval.py[/bold]\n\n"
    "Source accuracy should now show 90%+ instead of 70%.",
    border_style="green"
))
