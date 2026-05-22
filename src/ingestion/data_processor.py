"""
src/ingestion/data_processor.py
Reads all Kaggle CSVs → runs TextBuilder → saves processed JSONL files.

Run this script once to process all raw data:
    python -m src.ingestion.data_processor

Output: data/processed/{sport}.jsonl  (one JSON object per line)
"""
import json
import glob
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from loguru import logger

from src.config import DATA_RAW, DATA_PROCESSED
from src.ingestion.text_builder import SportsTextBuilder


builder = SportsTextBuilder()


def save_jsonl(docs: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    logger.info(f"Saved {len(docs):,} docs → {path}")


# ── Football ──────────────────────────────────────────────────────────────────
def process_football(csv_path: Path) -> list[dict]:
    logger.info("Processing football data...")
    df = pd.read_csv(csv_path)
    # drop rows with missing scores
    df = df.dropna(subset=["Team", "Opponent", "Team_Score", "Opponent_Score"])
    docs = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Football"):
        try:
            docs.append(builder.football_row_to_doc(row.to_dict()))
        except Exception as e:
            logger.warning(f"Skipped row: {e}")
    return docs


def process_fifa(data_dir: Path) -> list[dict]:
    logger.info("Processing FIFA World Cup data...")
    docs = []
    # summary file
    summary_path = data_dir / "FIFA - World Cup Summary.csv"
    if summary_path.exists():
        df = pd.read_csv(summary_path)
        for _, row in df.iterrows():
            docs.append(builder.fifa_summary_to_doc(row.to_dict()))
    logger.info(f"FIFA: {len(docs)} docs")
    return docs


# ── NBA ───────────────────────────────────────────────────────────────────────
def process_nba(data_dir: Path) -> list[dict]:
    logger.info("Processing NBA data...")
    games_df = pd.read_csv(data_dir / "NBA_GAMES.csv")
    players_df = pd.read_csv(data_dir / "NBA_PLAYERS.csv")
    player_games_df = pd.read_csv(data_dir / "NBA_PLAYER_GAMES.csv")

    # merge player names into player_games
    player_games_df = player_games_df.merge(
        players_df[["id", "full_name"]],
        left_on="Player_ID", right_on="id", how="left"
    )

    docs = []
    # group by game
    for game_id, grp in tqdm(player_games_df.groupby("Game_ID"), desc="NBA games"):
        game_row = games_df[games_df["Game_ID"] == game_id]
        if game_row.empty:
            continue
        top_players = (
            grp.sort_values("PTS", ascending=False)
            .head(3)
            .to_dict("records")
        )
        try:
            docs.append(builder.nba_game_to_doc(game_row.iloc[0].to_dict(), top_players))
        except Exception as e:
            logger.warning(f"NBA game {game_id} skipped: {e}")
    return docs


# ── ATP Tennis ────────────────────────────────────────────────────────────────
def process_tennis(csv_path: Path) -> list[dict]:
    logger.info("Processing ATP tennis data...")
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["Winner", "Tournament", "Surface"])
    docs = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Tennis"):
        try:
            docs.append(builder.atp_row_to_doc(row.to_dict()))
        except Exception as e:
            logger.warning(f"ATP row skipped: {e}")
    return docs


# ── Cricket ───────────────────────────────────────────────────────────────────
def process_cricket(data_dir: Path) -> list[dict]:
    logger.info("Processing cricket (IPL) data...")
    matches_df = pd.read_csv(data_dir / "matches.csv")
    deliveries_df = pd.read_csv(data_dir / "deliveries.csv")

    docs = []
    for _, match in tqdm(matches_df.iterrows(), total=len(matches_df), desc="IPL matches"):
        match_deliveries = deliveries_df[deliveries_df["match_id"] == match["id"]]
        try:
            docs.append(builder.ipl_match_to_doc(match.to_dict(), match_deliveries))
        except Exception as e:
            logger.warning(f"IPL match {match.get('id')} skipped: {e}")
    return docs


# ── Main orchestrator ─────────────────────────────────────────────────────────
def run_all(data_dir: Path = None):
    if data_dir is None:
        data_dir = DATA_RAW

    all_stats = {}

    # Football
    fb_csv = data_dir / "Full_Dataset.csv"
    if fb_csv.exists():
        docs = process_football(fb_csv)
        docs += process_fifa(data_dir)
        save_jsonl(docs, DATA_PROCESSED / "football.jsonl")
        all_stats["football"] = len(docs)

    # NBA
    if (data_dir / "NBA_GAMES.csv").exists():
        docs = process_nba(data_dir)
        save_jsonl(docs, DATA_PROCESSED / "basketball.jsonl")
        all_stats["basketball"] = len(docs)

    # Tennis
    atp_csv = list(data_dir.glob("ATP*.csv"))
    if atp_csv:
        docs = process_tennis(atp_csv[0])
        save_jsonl(docs, DATA_PROCESSED / "tennis.jsonl")
        all_stats["tennis"] = len(docs)

    # Cricket
    if (data_dir / "matches.csv").exists():
        docs = process_cricket(data_dir)
        save_jsonl(docs, DATA_PROCESSED / "cricket.jsonl")
        all_stats["cricket"] = len(docs)

    logger.success("=== Processing complete ===")
    for sport, count in all_stats.items():
        logger.info(f"  {sport:15s}: {count:,} documents")
    total = sum(all_stats.values())
    logger.info(f"  {'TOTAL':15s}: {total:,} documents")
    return all_stats


if __name__ == "__main__":
    import sys
    # usage: python -m src.ingestion.data_processor [path/to/data/dir]
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_RAW
    run_all(data_dir)
