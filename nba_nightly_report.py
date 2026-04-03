import os
import requests
from datetime import datetime, timedelta

TOKEN           = os.getenv('TELEGRAM_TOKEN')
CHAT_ID         = os.getenv('TELEGRAM_CHAT_ID')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')

FAVORITE_TEAMS  = ['Lakers', 'LA Lakers', 'Los Angeles Lakers']
ISRAELI_PLAYERS = ['Avdija', 'Saraf', 'Wolf']


def search_youtube(query):
    if not YOUTUBE_API_KEY:
        q = query.replace(' ', '+')
        return f'https://www.youtube.com/results?search_query={q}'
    try:
        resp  = requests.get(
            'https://www.googleapis.com/youtube/v3/search',
            params={'part': 'snippet', 'q': query, 'type': 'video',
                    'maxResults': 1, 'key': YOUTUBE_API_KEY, 'order': 'relevance'},
            timeout=10,
        )
        items = resp.json().get('items', [])
        if items:
            return f'https://www.youtube.com/watch?v={items[0]["id"]["videoId"]}'
    except Exception as e:
        print(f'YouTube error: {e}')
    q = query.replace(' ', '+')
    return f'https://www.youtube.com/results?search_query={q}'


def get_nba_history(date_obj):
    try:
        day  = date_obj.day
        url  = f'https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{date_obj.month}/{day}'
        resp = requests.get(url, timeout=10)
        if not resp.ok:
            return None
        events       = resp.json().get('events', [])
        nba_keywords = ['NBA', 'basketball', 'Lakers', 'Celtics', 'Bulls',
                        'Warriors', 'Heat', 'Knicks', 'points', 'championship',
                        'Finals', 'All-Star', 'draft', 'scored', 'record']
        for event in events:
            text = event.get('text', '')
            if any(kw.lower() in text.lower() for kw in nba_keywords):
                year = event.get('year', '')
                if len(text) > 120:
                    text = text[:117] + '...'
                return {'year': year, 'fact': text}
        return None
    except Exception as e:
        print(f'Wikipedia error: {e}')
        return None


def get_standings():
    """שולף טבלת ליגה מ-ESPN."""
    try:
        url  = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'
        resp = requests.get(url, timeout=15)
        if not resp.ok:
            return None, None

        data = resp.json()
        east = {'playoff': [], 'playin': []}
        west = {'playoff': [], 'playin': []}

        for conf in data.get('children', []):
            conf_name = conf.get('name', '')
            is_east   = 'East' in conf_name
            target    = east if is_east else west

            entries = conf.get('standings', {}).get('entries', [])
            # מיון לפי אחוז ניצחונות
            def sort_key(e):
                for s in e.get('stats', []):
                    if s['name'] == 'winPercent':
                        return -float(s.get('value', 0))
                return 0

            entries_sorted = sorted(entries, key=sort_key)

            for rank, entry in enumerate(entries_sorted, 1):
                team  = entry.get('team', {}).get('shortDisplayName', '?')
                stats = {s['name']: s.get('displayValue', '?')
                         for s in entry.get('stats', [])}
                wins   = stats.get('wins',   '?')
                losses = stats.get('losses', '?')
                row    = f'{rank}. {team}  {wins}-{losses}'

                if rank <= 6:
                    target['playoff'].append(row)
                elif rank <= 10:
                    target['playin'].append(row)

        return east, west
    except Exception as e:
        print(f'Standings error: {e}')
        return None, None


def get_player_stats(game_id):
    try:
        url  = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}'
        resp = requests.get(url, timeout=15)
        if not resp.ok:
            return []
        data    = resp.json()
        players = []

        for box in data.get('boxscore', {}).get('players', []):
            team_abbr = box.get('team', {}).get('abbreviation', '?')
            for stat_group in box.get('statistics', []):
                labels = stat_group.get('labels', [])
                try:
                    pts_idx = labels.index('PTS')
                    reb_idx = labels.index('REB')
                    ast_idx = labels.index('AST')
                    min_idx = labels.index('MIN') if 'MIN' in labels else 0
                except ValueError:
                    continue

                for athlete in stat_group.get('athletes', []):
                    try:
                        name  = athlete.get('athlete', {}).get('displayName', '?')
                        stats = athlete.get('stats', [])
                        if len(stats) <= max(pts_idx, reb_idx, ast_idx):
                            continue
                        pts = float(stats[pts_idx]) if stats[pts_idx] not in ('--', '') else 0
                        reb = float(stats[reb_idx]) if stats[reb_idx] not in ('--', '') else 0
                        ast = float(stats[ast_idx]) if stats[ast_idx] not in ('--', '') else 0
                        mn  = stats[min_idx] if stats[min_idx] not in ('--', '') else '0'
                        players.append({
                            'name': name,
                            'team': team_abbr,
                            'pts':  pts,
                            'reb':  reb,
                            'ast':  ast,
                            'min':  mn,
                        })
                    except Exception:
                        continue
        return players
    except Exception as e:
        print(f'Stats error: {e}')
        return []


def get_nba_data():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    url = (f'https://site.api.espn.com/apis/site/v2/sports/'
           f'basketball/nba/scoreboard?dates={yesterday}')
    try:
        data = requests.get(url, timeout=15).json()
    except Exception as e:
        print(f'ESPN error: {e}')
        return [], [], []

    games_data  = []
    all_players = []
    il_players  = []

    for event in data.get('events', []):
        try:
            comp      = event['competitions'][0]
            game_id   = event.get('id', '')
            game_name = event.get('name', 'Unknown')
            status    = (event.get('status', {})
                             .get('type', {})
                             .get('shortDetail', 'Final'))

            teams = []
            for competitor in comp.get('competitors', []):
                try:
                    tname   = competitor['team'].get('shortDisplayName', '?')
                    tfull   = competitor['team'].get('displayName', tname)
                    score   = competitor.get('score', '0')
                    leaders = []

                    for stat_cat in competitor.get('leaders', []):
                        if stat_cat.get('name') == 'points':
                            for ldr in stat_cat.get('leaders', [])[:2]:
                                try:
                                    athlete = ldr.get('athlete', {})
                                    full    = athlete.get('displayName', '?')
                                    short   = athlete.get('shortName', '?')
                                    pts     = float(ldr.get('value', 0))
                                    val     = ldr.get('displayValue', '0')
                                    leaders.append({
                                        'full':  full,
                                        'short': short,
                                        'val':   val,
                                        'pts':   pts,
                                    })
                                    all_players.append({
                                        'name': full,
                                        'pts':  pts,
                                        'val':  val,
                                        'team': tname,
                                    })
                                except Exception:
                                    continue

                    teams.append({
                        'name':    tname,
                        'full':    tfull,
                        'score':   score,
                        'leaders': leaders,
                    })
                except Exception:
                    continue

            if game_id:
                full_stats = get_player_stats(game_id)
                for p in full_stats:
                    if any(il in p['name'] for il in ISRAELI_PLAYERS):
                        il_players.append({**p, 'game': game_name})
                        print(f'נמצא ישראלי: {p["name"]} - {int(p["pts"])} PTS')

            if len(teams) == 2:
                is_fav = any(
                    any(fav.lower() in t['full'].lower() for fav in FAVORITE_TEAMS)
                    for t in teams
                )
                games_data.append({
