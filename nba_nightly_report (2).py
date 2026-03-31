"""
NBA Nightly Report — Telegram Bot
===================================
Fetches last night's NBA results and sends a formatted
Telegram message with MVP, top scorers, Israeli players,
YouTube links, and historical facts.

Setup:
    pip install nba_api requests

Environment variables (set in GitHub Actions Secrets or locally):
    TELEGRAM_TOKEN      — your bot token from @BotFather
    TELEGRAM_CHAT_ID    — your personal or group chat ID
    YOUTUBE_API_KEY     — Google YouTube Data API v3 key

Run locally:
    export TELEGRAM_TOKEN="..."
    export TELEGRAM_CHAT_ID="..."
    export YOUTUBE_API_KEY="..."
    python nba_nightly_report.py
"""

import os, json, time, urllib.parse
from datetime import datetime, timedelta
import requests
from nba_api.stats.endpoints import scoreboardv2, boxscoretraditionalv2
from nba_api.stats.static import teams as nba_teams_static

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG  —  all secrets come from environment variables, never hardcoded
# ─────────────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]       # raises if missing — intentional
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
YOUTUBE_API_KEY  = os.environ.get("YOUTUBE_API_KEY", "")

# Teams you care most about — their games bubble to the top of the message.
# Use exact NBA full names as returned by nba_api.
FAVORITE_TEAMS = [
    "Golden State Warriors",
    "Boston Celtics",
    # Add or change any team here
]

# ─────────────────────────────────────────────────────────────────────────────
#  Israeli players
# ─────────────────────────────────────────────────────────────────────────────
ISRAELI_PLAYERS = {
    "Deni Avdija": "Portland Trail Blazers",
    "Yam Madar":   "Brooklyn Nets",
    "Omri Casspi": "Retired",
    "Gal Mekel":   "Retired",
}
ISRAELI_NAMES = set(ISRAELI_PLAYERS.keys())

# ─────────────────────────────────────────────────────────────────────────────
#  Historical "On This Day" facts
# ─────────────────────────────────────────────────────────────────────────────
NBA_HISTORY: dict[str, list[dict]] = {
    "01/01": [{"year": 1946, "fact": "The BAA (predecessor to the NBA) played its very first New Year's Day games."}],
    "01/07": [{"year": 2003, "fact": "Tracy McGrady scored 62 points against Washington — a career high."}],
    "01/13": [{"year": 1990, "fact": "Michael Jordan scored 69 points against Cleveland, an NBA record at the time."}],
    "01/22": [{"year": 2006, "fact": "Kobe Bryant dropped 81 points on the Toronto Raptors — 2nd highest single-game total ever."}],
    "02/02": [{"year": 1962, "fact": "Wilt Chamberlain set the single-game rebounding record with 55 boards vs. the Celtics."}],
    "03/02": [{"year": 1962, "fact": "Wilt Chamberlain scored 100 points against the Knicks — the greatest individual game in NBA history."}],
    "03/28": [{"year": 1990, "fact": "Michael Jordan scored 69 points in overtime against the Cleveland Cavaliers."}],
    "03/31": [{"year": 2016, "fact": "Stephen Curry hit his 400th three-pointer of the season, setting an NBA record."}],
    "04/01": [
        {"year": 1984, "fact": "Kareem Abdul-Jabbar became the NBA's all-time leading scorer, surpassing Wilt Chamberlain."},
        {"year": 1997, "fact": "Michael Jordan scored 55 points against the Knicks at Madison Square Garden."},
    ],
    "04/06": [{"year": 2017, "fact": "Russell Westbrook recorded his 42nd triple-double, breaking Oscar Robertson's single-season record."}],
    "04/09": [{"year": 2003, "fact": "Michael Jordan played his final NBA game, scoring 15 points for the Washington Wizards."}],
    "04/14": [{"year": 2019, "fact": "Kobe Bryant's #8 and #24 jerseys were retired by the Los Angeles Lakers."}],
    "05/07": [{"year": 1989, "fact": "Magic Johnson hit 'Junior Skyhook' to beat Detroit in Game 4 of the Eastern Conference Finals."}],
    "06/11": [{"year": 1997, "fact": "Michael Jordan hit the 'Flu Game' winner against Utah in Game 5 of the NBA Finals."}],
    "06/13": [{"year": 2013, "fact": "LeBron James hit a corner three to force overtime in Game 6 of the Finals vs. San Antonio."}],
    "10/29": [{"year": 1946, "fact": "The BAA tipped off its very first game — New York Knicks vs. Toronto Huskies."}],
    "11/01": [{"year": 1946, "fact": "The NBA (then BAA) opened its inaugural season, launching professional basketball in America."}],
    "12/13": [{"year": 1983, "fact": "Detroit Pistons defeated Denver Nuggets 186–184 in the highest-scoring game in NBA history."}],
}

def get_historical_facts(date_str: str) -> list[dict]:
    return NBA_HISTORY.get(date_str[:5], [])

# ─────────────────────────────────────────────────────────────────────────────
#  YouTube
# ─────────────────────────────────────────────────────────────────────────────
def search_youtube(query: str) -> dict:
    if not YOUTUBE_API_KEY:
        return _yt_fallback(query)
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video",
                    "maxResults": 1, "key": YOUTUBE_API_KEY,
                    "order": "relevance", "relevanceLanguage": "en"},
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return _yt_fallback(query)
        vid_id = items[0]["id"]["videoId"]
        title  = items[0]["snippet"]["title"]
        return {"url": f"https://www.youtube.com/watch?v={vid_id}", "title": title, "direct": True}
    except Exception as e:
        print(f"  ⚠️  YouTube error: {e}")
        return _yt_fallback(query)

def _yt_fallback(query: str) -> dict:
    return {
        "url":   f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}",
        "title": query,
        "direct": False,
    }

# ─────────────────────────────────────────────────────────────────────────────
#  NBA data helpers
# ─────────────────────────────────────────────────────────────────────────────
def get_yesterday() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")

def team_name(team_id: int) -> str:
    for t in nba_teams_static.get_teams():
        if t["id"] == team_id:
            return t["full_name"]
    return f"Team {team_id}"

def fetch_games(date_str: str) -> list[dict]:
    sb    = scoreboardv2.ScoreboardV2(game_date=date_str)
    games = sb.game_header.get_data_frame()
    lines = sb.line_score.get_data_frame()
    pts   = {r["TEAM_ID"]: int(r.get("PTS") or 0) for _, r in lines.iterrows()}
    return [{
        "game_id":    str(r["GAME_ID"]),
        "home_id":    r["HOME_TEAM_ID"],
        "away_id":    r["VISITOR_TEAM_ID"],
        "home_score": pts.get(r["HOME_TEAM_ID"], 0),
        "away_score": pts.get(r["VISITOR_TEAM_ID"], 0),
        "status":     r.get("GAME_STATUS_TEXT", "Final"),
    } for _, r in games.iterrows()]

def fetch_players(game_id: str) -> list[dict]:
    time.sleep(0.65)
    df = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id).player_stats.get_data_frame()
    out = []
    for _, r in df.iterrows():
        pts, reb, ast = int(r.get("PTS") or 0), int(r.get("REB") or 0), int(r.get("AST") or 0)
        blk, stl      = int(r.get("BLK") or 0), int(r.get("STL") or 0)
        name = r["PLAYER_NAME"]
        out.append({
            "name":       name,
            "team_abbr":  r["TEAM_ABBREVIATION"],
            "pts": pts, "reb": reb, "ast": ast, "blk": blk, "stl": stl,
            "min": str(r.get("MIN") or "0:00"),
            "is_israeli": name in ISRAELI_NAMES,
            "mvp_score":  pts + 0.8*reb + 1.5*ast + 1.5*stl + 1.5*blk,
        })
    return out

def top2_per_team(players: list[dict]) -> dict[str, list[dict]]:
    from collections import defaultdict
    by_team = defaultdict(list)
    for p in players:
        by_team[p["team_abbr"]].append(p)
    return {abbr: sorted(lst, key=lambda x: x["pts"], reverse=True)[:2]
            for abbr, lst in by_team.items()}

def is_favorite(home: str, away: str) -> bool:
    return home in FAVORITE_TEAMS or away in FAVORITE_TEAMS

# ─────────────────────────────────────────────────────────────────────────────
#  Telegram message formatter
# ─────────────────────────────────────────────────────────────────────────────
def fmt_game_block(game: dict) -> str:
    """Formats one game into a clean Telegram message block."""
    home   = game["home_team_name"]
    away   = game["away_team_name"]
    hs     = game["home_score"]
    as_    = game["away_score"]
    status = game["game_status"]

    # Winner indicator
    if hs > as_:
        home_score = f"*{hs}*"
        away_score = str(as_)
    elif as_ > hs:
        away_score = f"*{as_}*"
        home_score = str(hs)
    else:
        home_score = str(hs)
        away_score = str(as_)

    # Favorite team star
    fav_marker = " ⭐" if is_favorite(home, away) else ""

    lines = [
        f"🏀 *{away} vs {home}*{fav_marker}",
        f"    {away_score} – {home_score}  |  _{status}_",
        "",
    ]

    # Top scorers per team
    for abbr, scorers in game.get("top_scorers", {}).items():
        for i, p in enumerate(scorers):
            medal   = "🥇" if i == 0 else "🥈"
            il_flag = " 🇮🇱" if p.get("is_israeli") else ""
            lines.append(
                f"  {medal} {p['name']}{il_flag}  "
                f"*{p['pts']} pts*  {p['reb']} reb  {p['ast']} ast"
            )

    # YouTube link
    yt = game.get("youtube", {})
    if yt.get("url"):
        icon = "▶️" if yt.get("direct") else "🔍"
        lines.append(f"\n  {icon} [Highlights]({yt['url']})")

    return "\n".join(lines)


def build_message(date_str: str, games: list[dict], mvp: dict | None,
                  israelis: list[dict], facts: list[dict]) -> str:
    """Assembles the full Telegram message."""

    # Human-readable date
    try:
        m, d, y = date_str.split("/")
        readable = datetime(int(y), int(m), int(d)).strftime("%A, %B %-d %Y")
    except Exception:
        readable = date_str

    parts: list[str] = []

    # ── Header ──────────────────────────────────────────────────
    parts.append(f"🏆 *NBA Nightly Report*")
    parts.append(f"📅 {readable}")
    parts.append(f"━━━━━━━━━━━━━━━━━━━━━━")

    # ── No games ─────────────────────────────────────────────────
    if not games:
        parts.append("\n_No games last night._")
        return "\n".join(parts)

    # ── Daily MVP ────────────────────────────────────────────────
    if mvp:
        il = " 🇮🇱" if mvp.get("is_israeli") else ""
        parts.append(
            f"\n🌟 *Daily MVP — {mvp['name']}*{il}  \\({mvp['team_abbr']}\\)\n"
            f"   *{mvp['pts']} pts*  {mvp['reb']} reb  "
            f"{mvp['ast']} ast  {mvp['stl']} stl  {mvp['blk']} blk\n"
            f"   _Composite: {mvp['mvp_score']:.1f}_"
        )
        parts.append("━━━━━━━━━━━━━━━━━━━━━━")

    # ── Games — favorites first ───────────────────────────────────
    parts.append(f"\n🎯 *{len(games)} Games Tonight*\n")

    fav_games   = [g for g in games if is_favorite(g["home_team_name"], g["away_team_name"])]
    other_games = [g for g in games if not is_favorite(g["home_team_name"], g["away_team_name"])]
    ordered     = fav_games + other_games

    for i, game in enumerate(ordered):
        parts.append(fmt_game_block(game))
        if i < len(ordered) - 1:
            parts.append("─────────────────────")

    # ── Israeli players ───────────────────────────────────────────
    if israelis:
        parts.append("\n━━━━━━━━━━━━━━━━━━━━━━")
        parts.append("🇮🇱 *Israeli Players Tonight*\n")
        for p in israelis:
            parts.append(
                f"  🔵 *{p['name']}*  \\({p.get('game', p['team_abbr'])}\\)\n"
                f"      *{p['pts']} pts*  {p['reb']} reb  "
                f"{p['ast']} ast  {p['min']} min"
            )

    # ── On This Day ───────────────────────────────────────────────
    if facts:
        parts.append("\n━━━━━━━━━━━━━━━━━━━━━━")
        parts.append("📜 *On This Day in NBA History*\n")
        for f in facts:
            parts.append(f"  🏅 *{f['year']}* — {f['fact']}")

    # ── Footer ───────────────────────────────────────────────────
    parts.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    parts.append("_NBA Nightly Bot · Powered by nba\\_api_")

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
#  Telegram sender
# ─────────────────────────────────────────────────────────────────────────────
TELEGRAM_MAX = 4096   # Telegram hard limit per message

def send_telegram(text: str) -> None:
    """Splits long messages and sends them via Telegram Bot API."""
    url    = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chunks = _split_message(text, TELEGRAM_MAX)

    for i, chunk in enumerate(chunks):
        payload = {
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       chunk,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": False,
        }
        resp = requests.post(url, json=payload, timeout=15)
        if not resp.ok:
            # Retry once with plain text if MarkdownV2 fails
            print(f"  ⚠️  Telegram error ({resp.status_code}): {resp.text[:200]}")
            print("  🔁  Retrying as plain text...")
            payload["parse_mode"] = "HTML"
            plain = _strip_markdown(chunk)
            payload["text"] = plain
            resp2 = requests.post(url, json={**payload, "text": plain}, timeout=15)
            if not resp2.ok:
                raise RuntimeError(f"Telegram send failed: {resp2.text}")
        print(f"  ✅  Sent chunk {i+1}/{len(chunks)}")
        if len(chunks) > 1:
            time.sleep(0.5)   # avoid hitting rate limits


def _split_message(text: str, limit: int) -> list[str]:
    """Splits on double-newlines to avoid cutting mid-block."""
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for para in text.split("\n\n"):
        block = para + "\n\n"
        if len(current) + len(block) > limit:
            if current:
                chunks.append(current.rstrip())
            current = block
        else:
            current += block
    if current.strip():
        chunks.append(current.rstrip())
    return chunks or [text[:limit]]


def _strip_markdown(text: str) -> str:
    """Very basic MarkdownV2 → plain text fallback."""
    import re
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_',  r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\\(.)', r'\1', text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────
def run(date_str: str | None = None) -> None:
    date_str = date_str or get_yesterday()
    print(f"\n🏀 NBA Nightly — {date_str}")
    print("─" * 48)

    raw_games = fetch_games(date_str)
    if not raw_games:
        print("No games found — sending empty report.")
        send_telegram(
            f"🏀 *NBA Nightly Report*\n📅 {date_str}\n\n_No games last night\\._"
        )
        return

    print(f"Found {len(raw_games)} games")

    all_players, israelis, games_out = [], [], []

    for g in raw_games:
        home = team_name(g["home_id"])
        away = team_name(g["away_id"])
        fav  = "⭐ " if is_favorite(home, away) else "  "
        print(f" {fav}{away} @ {home}")

        try:
            players = fetch_players(g["game_id"])
        except Exception as e:
            print(f"     ⚠️  Box score error: {e}"); players = []

        all_players.extend(players)
        for p in players:
            if p["is_israeli"]:
                israelis.append({**p, "game": f"{away} @ {home}"})

        yt    = search_youtube(f"NBA {away} vs {home} full game highlights")
        label = "✅ direct" if yt.get("direct") else "🔍 search"
        print(f"     YouTube [{label}]: {yt['title'][:55]}")

        games_out.append({
            "game_id":        g["game_id"],
            "home_team_name": home,
            "away_team_name": away,
            "home_score":     g["home_score"],
            "away_score":     g["away_score"],
            "game_status":    g["status"],
            "top_scorers":    top2_per_team(players),
            "youtube":        yt,
        })

    mvp   = max(all_players, key=lambda p: p["mvp_score"]) if all_players else None
    facts = get_historical_facts(date_str)

    if mvp:
        print(f"\n🏆 MVP: {mvp['name']} — {mvp['mvp_score']:.1f}")

    message = build_message(date_str, games_out, mvp, israelis, facts)

    print("\n📤 Sending to Telegram...")
    send_telegram(message)
    print("✅ Done!\n")


if __name__ == "__main__":
    run()
    # run("03/30/2025")   # ← uncomment for a specific date
