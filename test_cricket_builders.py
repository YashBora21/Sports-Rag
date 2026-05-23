#!/usr/bin/env python
"""Verify that all cricket format data builders are working."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

try:
    from src.ingestion.text_builder import SportsTextBuilder
    
    builder = SportsTextBuilder()
    
    # Test ODI
    odi_data = {
        "Player": "MS Dhoni (INDIA)",
        "Span": "2004-2019",
        "Mat": 350,
        "Inns": 297,
        "Runs": 10773,
        "Ave": 50.57,
        "100": 10,
        "50": 73,
    }
    odi_doc = builder.odi_batting_to_doc(odi_data)
    print("✓ ODI batting doc:")
    print(f"  {odi_doc['text']}\n")
    
    # Test Test cricket
    test_data = {
        "Player": "SR Tendulkar (INDIA)",
        "Span": "1989-2013",
        "Mat": 200,
        "Inns": 329,
        "Runs": 15921,
        "Ave": 53.78,
        "100": 51,
        "50": 68,
    }
    test_doc = builder.test_batting_to_doc(test_data)
    print("✓ Test batting doc:")
    print(f"  {test_doc['text']}\n")
    
    # Test T20
    t20_data = {
        "Player": "MS Dhoni (INDIA)",
        "Span": "2006-2019",
        "Mat": 98,
        "Inns": 85,
        "Runs": 1617,
        "Ave": 37.6,
        "100": 0,
        "50": 2,
    }
    t20_doc = builder.t20_batting_to_doc(t20_data)
    print("✓ T20 batting doc:")
    print(f"  {t20_doc['text']}\n")
    
    # Test tournament
    tournament_data = {
        "Player": "MS Dhoni",
        "Tournament": "Cricket World Cup",
        "Format": "ODI",
        "Year": 2011,
        "Result": "Champion",
    }
    tournament_doc = builder.cricket_tournament_to_doc(tournament_data)
    print("✓ Tournament doc:")
    print(f"  {tournament_doc['text']}\n")
    
    print("\n✅ All cricket builders working correctly!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
