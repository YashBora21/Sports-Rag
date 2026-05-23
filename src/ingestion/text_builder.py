"""
src/ingestion/text_builder.py
Converts structured CSV rows → natural language text passages.
This is the most critical file in Week 1. RAG quality depends on it.

Each sport has its own builder method.
Output: a dict with 'text', 'sport', 'metadata' keys.
"""
import pandas as pd
from typing import Optional


class SportsTextBuilder:

    # ── Football ──────────────────────────────────────────────────────────────
    def football_row_to_doc(self, row: dict) -> dict:
        pts = float(row.get("Team_Points", 0) or 0)
        result = "won" if pts == 3 else "drew" if pts == 1 else "lost"

        opp_pts = float(row.get("Opponent_Points", 0) or 0)
        ts = row.get("Team_Score", "?")
        os_ = row.get("Opponent_Score", "?")

        text = (
            f"{row['Team']} {result} against {row['Opponent']} "
            f"with a scoreline of {ts}-{os_} "
            f"in the {row['Competition'].replace('-', ' ').title()} "
            f"({row['Country'].replace('-', ' ').title()}) "
            f"during the {row['season']} season, "
            f"played {row.get('Location', 'away').lower()}."
        )
        return {
            "text": text,
            "sport": "football",
            "metadata": {
                "team": row["Team"],
                "opponent": row["Opponent"],
                "score": f"{ts}-{os_}",
                "competition": row["Competition"],
                "season": str(row["season"]),
                "country": row["Country"],
                "result": result,
                "date": str(row.get("Date", "")),
            }
        }

    # ── NBA ───────────────────────────────────────────────────────────────────
    def nba_game_to_doc(self, game: dict, top_players: list[dict]) -> dict:
        wl = "won" if str(game.get("WL", "")).strip() == "W" else "lost"
        matchup = game.get("MATCHUP", "Unknown matchup")
        date = game.get("GAME_DATE", "")

        fg_pct = float(game.get("FG_PCT", 0) or 0)
        fg3_pct = float(game.get("FG3_PCT", 0) or 0)
        pts = int(game.get("PTS", 0) or 0)
        reb = int(game.get("REB", 0) or 0)
        ast = int(game.get("AST", 0) or 0)
        blk = int(game.get("BLK", 0) or 0)
        stl = int(game.get("STL", 0) or 0)

        player_lines = []
        for p in top_players[:3]:
            name = p.get("full_name", p.get("Player_ID", "Unknown"))
            p_pts = int(p.get("PTS", 0) or 0)
            p_reb = int(p.get("REB", 0) or 0)
            p_ast = int(p.get("AST", 0) or 0)
            player_lines.append(f"{name} ({p_pts}pts/{p_reb}reb/{p_ast}ast)")

        performers = ", ".join(player_lines) if player_lines else "data unavailable"

        text = (
            f"NBA game: {matchup} on {date} — team {wl}. "
            f"Team stats: {pts} points, {reb} rebounds, {ast} assists, "
            f"{stl} steals, {blk} blocks. "
            f"Shooting: {fg_pct:.1%} FG, {fg3_pct:.1%} from three. "
            f"Top performers: {performers}."
        )
        return {
            "text": text,
            "sport": "basketball",
            "metadata": {
                "matchup": matchup,
                "date": date,
                "result": wl,
                "points": pts,
                "game_id": str(game.get("Game_ID", "")),
                "team_id": str(game.get("Team_ID", "")),
            }
        }

    # ── ATP Tennis ────────────────────────────────────────────────────────────
    def atp_row_to_doc(self, row: dict) -> dict:
        winner = str(row.get("Winner", "Unknown"))
        p1 = str(row.get("Player1", "Unknown"))
        p2 = str(row.get("Player2", "Unknown"))
        loser = p2 if winner == p1 else p1
        winner_rank = row.get("Player1_Rank" if winner == p1 else "Player2_Rank", "?")
        loser_rank = row.get("Player2_Rank" if winner == p1 else "Player1_Rank", "?")

        text = (
            f"{winner} (ranked #{winner_rank}) defeated {loser} (ranked #{loser_rank}) "
            f"in the {row.get('Round', '?').replace('_', ' ')} "
            f"of the {row.get('Tournament', '?')} tournament "
            f"({row.get('Series', '?')}, {row.get('Surface', '?')} court, "
            f"{row.get('Court', '?')})."
        )
        return {
            "text": text,
            "sport": "tennis",
            "metadata": {
                "winner": winner,
                "loser": loser,
                "tournament": str(row.get("Tournament", "")),
                "surface": str(row.get("Surface", "")),
                "round": str(row.get("Round", "")),
                "series": str(row.get("Series", "")),
                "winner_rank": str(winner_rank),
            }
        }

    # ── IPL Cricket ───────────────────────────────────────────────────────────
    def ipl_match_to_doc(self, match: dict, deliveries: pd.DataFrame) -> dict:
        winner = str(match.get("winner", "Unknown"))
        team1 = str(match.get("team1", ""))
        team2 = str(match.get("team2", ""))
        loser = team2 if winner == team1 else team1
        season = match.get("season", "")
        venue = match.get("venue", "Unknown venue")
        city = match.get("city", "")
        pom = match.get("player_of_match", "Unknown")

        win_runs = int(match.get("win_by_runs", 0) or 0)
        win_wkts = int(match.get("win_by_wickets", 0) or 0)
        margin = f"{win_runs} runs" if win_runs > 0 else f"{win_wkts} wickets"

        # aggregate deliveries for this match
        top_bat = top_bowl = ""
        if not deliveries.empty:
            bat_stats = (
                deliveries.groupby("batsman")["batsman_runs"]
                .sum().sort_values(ascending=False).head(2)
            )
            top_bat = ", ".join(f"{p} ({r})" for p, r in bat_stats.items())

            bowl_stats = (
                deliveries[deliveries["player_dismissed"].notna()]
                .groupby("bowler")["player_dismissed"]
                .count().sort_values(ascending=False).head(2)
            )
            top_bowl = ", ".join(f"{p} ({w}w)" for p, w in bowl_stats.items())

        text = (
            f"IPL {season}: {winner} beat {loser} by {margin} "
            f"at {venue}, {city}. "
            f"Toss won by {match.get('toss_winner', '?')} "
            f"who chose to {match.get('toss_decision', '?')}. "
            f"Player of the match: {pom}."
        )
        if top_bat:
            text += f" Top batsmen: {top_bat}."
        if top_bowl:
            text += f" Top bowlers: {top_bowl}."

        return {
            "text": text,
            "sport": "cricket",
            "metadata": {
                "season": str(season),
                "winner": winner,
                "loser": loser,
                "venue": venue,
                "player_of_match": pom,
                "match_id": str(match.get("id", "")),
            }
        }

    # ── ODI Cricket (One Day International) ───────────────────────────────────
    def odi_batting_to_doc(self, row: dict) -> dict:
        player = str(row.get("Player", "Unknown"))
        span = str(row.get("Span", ""))
        mat = int(row.get("Mat", 0) or 0)
        inns = int(row.get("Inns", 0) or 0)
        runs = int(row.get("Runs", 0) or 0)
        ave = float(row.get("Ave", 0) or 0)
        centuries = int(row.get("100", 0) or 0)
        fifties = int(row.get("50", 0) or 0)
        
        text = (
            f"ODI cricket: {player} played {mat} matches ({inns} innings) "
            f"from {span}, scoring {runs} runs with an average of {ave:.2f}. "
            f"International centuries: {centuries}, half-centuries: {fifties}."
        )
        return {
            "text": text,
            "sport": "cricket",
            "metadata": {
                "format": "ODI",
                "player": player,
                "matches": str(mat),
                "runs": str(runs),
                "centuries": str(centuries),
                "span": span,
            }
        }

    # ── Test Cricket ──────────────────────────────────────────────────────────
    def test_batting_to_doc(self, row: dict) -> dict:
        player = str(row.get("Player", "Unknown"))
        span = str(row.get("Span", ""))
        mat = int(row.get("Mat", 0) or 0)
        inns = int(row.get("Inns", 0) or 0)
        runs = int(row.get("Runs", 0) or 0)
        ave = float(row.get("Ave", 0) or 0)
        centuries = int(row.get("100", 0) or 0)
        fifties = int(row.get("50", 0) or 0)
        
        text = (
            f"Test cricket: {player} played {mat} test matches ({inns} innings) "
            f"from {span}, accumulating {runs} runs with an average of {ave:.2f}. "
            f"Test centuries: {centuries}, half-centuries: {fifties}."
        )
        return {
            "text": text,
            "sport": "cricket",
            "metadata": {
                "format": "Test",
                "player": player,
                "matches": str(mat),
                "runs": str(runs),
                "centuries": str(centuries),
                "span": span,
            }
        }

    # ── Cricket International Tournaments ─────────────────────────────────────
    def cricket_tournament_to_doc(self, row: dict) -> dict:
        player = str(row.get("Player", "Unknown"))
        tournament = str(row.get("Tournament", ""))
        format_type = str(row.get("Format", ""))
        year = str(row.get("Year", ""))
        result = str(row.get("Result", ""))
        
        achievement = "won" if result == "Champion" else "was runner-up in"
        
        text = (
            f"International cricket: {player} {achievement} the {tournament} "
            f"({format_type} format) in {year}."
        )
        return {
            "text": text,
            "sport": "cricket",
            "metadata": {
                "tournament": tournament,
                "player": player,
                "format": format_type,
                "year": year,
                "result": result,
            }
        }

    # ── T20 International Cricket ─────────────────────────────────────────────
    def t20_batting_to_doc(self, row: dict) -> dict:
        player = str(row.get("Player", "Unknown"))
        span = str(row.get("Span", ""))
        mat = int(row.get("Mat", 0) or 0)
        inns = int(row.get("Inns", 0) or 0)
        runs = int(row.get("Runs", 0) or 0)
        ave = float(row.get("Ave", 0) or 0)
        centuries = int(row.get("100", 0) or 0)
        fifties = int(row.get("50", 0) or 0)
        
        text = (
            f"T20 International cricket: {player} played {mat} T20 matches ({inns} innings) "
            f"from {span}, scoring {runs} runs with an average of {ave:.2f}. "
            f"T20 centuries: {centuries}, half-centuries: {fifties}."
        )
        return {
            "text": text,
            "sport": "cricket",
            "metadata": {
                "format": "T20",
                "player": player,
                "matches": str(mat),
                "runs": str(runs),
                "centuries": str(centuries),
                "span": span,
            }
        }

    # ── FIFA ─────────────────────────────────────────────────────────────────
    def fifa_summary_to_doc(self, row: dict) -> dict:
        text = (
            f"FIFA World Cup {row['YEAR']} was hosted by {row['HOST']}. "
            f"{row['CHAMPION']} won the tournament, defeating {row['RUNNER UP']} in the final. "
            f"Third place went to {row['THIRD PLACE']}. "
            f"{row['TEAMS']} teams played {row['MATCHES PLAYED']} matches, "
            f"scoring {row['GOALS SCORED']} goals "
            f"(average {row['AVG GOALS PER GAME']} per game)."
        )
        return {
            "text": text,
            "sport": "football",
            "metadata": {
                "tournament": "FIFA World Cup",
                "year": str(row["YEAR"]),
                "champion": row["CHAMPION"],
                "host": row["HOST"],
            }
        }
