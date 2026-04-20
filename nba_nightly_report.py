import os
import requests
import json
import base64
from datetime import datetime, timedelta

TOKEN           = os.getenv('TELEGRAM_TOKEN')
CHAT_ID         = os.getenv('TELEGRAM_CHAT_ID')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
GITHUB_TOKEN    = os.getenv('NBA_GITHUB_TOKEN', '')
GITHUB_REPO     = 'darwe33-spec/nba-telegram-agent'

FAVORITE_TEAMS  = ['Lakers', 'LA Lakers', 'Los Angeles Lakers']
ISRAELI_PLAYERS = ['Avdija', 'Saraf', 'Wolf']

# קבוצות המזרח והמערב
EAST_TEAMS = ['BOS', 'NYK', 'MIL', 'CLE', 'ORL', 'IND', 'PHI', 'MIA', 'CHI', 'ATL', 'BKN', 'TOR', 'CHA', 'DET', 'WSH']
WEST_TEAMS = ['OKC', 'DEN', 'MIN', 'LAC', 'DAL', 'PHX', 'NOP', 'LAL', 'SAC', 'GSW', 'HOU', 'SAS', 'UTA', 'MEM', 'POR']


def search_youtube(query):
    if not YOUTUBE_API_KEY:
        q = query.replace(' ', '+')
        return f'https://www.youtube.com/results?search_query={q}'
    try:
        resp = requests.get(
            'https://www.googleapis.com/youtube/v3/search',
            params={'part': 'snippet', 'q': query, 'type': 'video',
                    'maxResults': 1, 'key': YOUTUBE_API_KEY,
                    'order': 'relevance'},
            timeout=10,
        )
        items = resp.json().get('items', [])
        if items:
            vid = items[0]['id']['videoId']
            return f'https://www.youtube.com/watch?v={vid}'
    except Exception as e:
        print(f'YouTube error: {e}')
    q = query.replace(' ', '+')
    return f'https://www.youtube.com/results?search_query={q}'


def get_top_plays_url(date_obj):
    date_str = date_obj.strftime('%B %d %Y')
    query    = f'NBA Top Plays {date_str}'
    return search_youtube(query)


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


def get_series_from_event(event):
    """שולף מידע על סדרה ישירות מתוך אירוע המשחק."""
    try:
        comp = event.get('competitions', [{}])[0]
        series = comp.get('series', {})
        if not series:
            return None
        return {
            'type':    series.get('type', ''),
            'summary': series.get('summary', ''),
            'title':   series.get('title', ''),
        }
    except Exception:
        return None


def parse_series_summary(summary, t1_abbr, t2_abbr):
    """מנתח summary כמו 'BOS leads series 1-0' ומחזיר wins1, wins2."""
    if not summary:
        return 0, 0, None
    try:
        parts = summary.split()
        # הנחה: 'BOS leads series 1-0' או 'Series tied 1-1'
        if 'tied' in summary.lower():
            for p in parts:
                if '-' in p:
                    w1, w2 = p.split('-')
                    return int(w1), int(w2), None
        else:
            leader = parts[0] if parts else None
            for p in parts:
                if '-' in p:
                    w1, w2 = p.split('-')
                    w1, w2 = int(w1), int(w2)
                    if leader == t1_abbr:
                        return w1, w2, leader
                    elif leader == t2_abbr:
                        return w2, w1, leader
                    else:
                        return w1, w2, leader
    except Exception:
        pass
    return 0, 0, None


def get_playoff_bracket_from_week():
    """בונה טבלת פלייאוף מכל משחקי השבוע האחרון."""
    series_map = {}  # key: frozenset(team1, team2), value: series info

    try:
        # שליפת 10 הימים האחרונים
        for days_ago in range(10):
            date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y%m%d')
            url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}'
            resp = requests.get(url, timeout=15)
            if not resp.ok:
                continue
            data = resp.json()

            for event in data.get('events', []):
                try:
                    comp = event.get('competitions', [{}])[0]
                    series = comp.get('series', {})
                    if not series or series.get('type') != 'playoff':
                        continue

                    competitors = comp.get('competitors', [])
                    if len(competitors) != 2:
                        continue

                    t1 = competitors[0].get('team', {}).get('abbreviation', '?')
                    t2 = competitors[1].get('team', {}).get('abbreviation', '?')
                    summary = series.get('summary', '')

                    w1, w2, leader = parse_series_summary(summary, t1, t2)

                    key = frozenset([t1, t2])
                    # שומרים את הסדרה הכי עדכנית
                    if key not in series_map or (w1 + w2) > (series_map[key]['wins1'] + series_map[key]['wins2']):
                        series_map[key] = {
                            'team1':  t1,
                            'team2':  t2,
                            'wins1':  w1,
                            'wins2':  w2,
                            'leader': leader,
                        }
                except Exception:
                    continue

        # חלוקה למזרח ומערב
        east = []
        west = []
        for s in series_map.values():
            if s['team1'] in EAST_TEAMS:
                east.append(s)
            elif s['team1'] in WEST_TEAMS:
                west.append(s)

        return east, west
    except Exception as e:
        print(f'Bracket build error: {e}')
        return [], []


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

            # שליפת מידע על הסדרה ישירות מהאירוע
            series_info = get_series_from_event(event)

            teams = []
            for competitor in comp.get('competitors', []):
                try:
                    tname   = competitor['team'].get('shortDisplayName', '?')
                    tfull   = competitor['team'].get('displayName', tname)
                    tabbr   = competitor['team'].get('abbreviation', tname)
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
                                        'team': tabbr,
                                    })
                                except Exception:
                                    continue

                    teams.append({
                        'name':    tname,
                        'abbr':    tabbr,
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
                yt_direct = search_youtube(f'NBA {teams[0]["name"]} vs {teams[1]["name"]} highlights')
                score_diff = abs(int(teams[0]['score']) - int(teams[1]['score']))

                games_data.append({
                    'game_id':    game_id,
                    'name':       game_name,
                    'status':     status,
                    'teams':      teams,
                    'is_fav':     is_fav,
                    'yt_url':     yt_direct,
                    'series':     series_info,
                    'score_diff': score_diff,
                })
        except Exception as e:
            print(f'Skipping game: {e}')
            continue

    games_data.sort(key=lambda g: (0 if g['is_fav'] else 1, g['score_diff']))
    return games_data, all_players, il_players


def save_to_github(data):
    if not GITHUB_TOKEN:
        print('אין GitHub Token — לא שומר JSON')
        return False
    try:
        api_url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/data.json'
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json',
        }
        content = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
        get_resp = requests.get(api_url, headers=headers, timeout=10)
        sha = get_resp.json().get('sha') if get_resp.ok else None
        payload = {
            'message': 'Update NBA data',
            'content': content,
        }
        if sha:
            payload['sha'] = sha
        put_resp = requests.put(api_url, headers=headers, json=payload, timeout=15)
        if put_resp.ok:
            print('data.json נשמר בגיטהאב בהצלחה!')
            return True
        else:
            print(f'שגיאה בשמירה: {put_resp.status_code}')
            return False
    except Exception as e:
        print(f'GitHub save error: {e}')
        return False


def build_bracket_section(east, west):
    """בונה את סעיף טבלת הפלייאוף."""
    if not east and not west:
        return []

    lines = []
    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')
    lines.append('🏆 <b>מצב הסדרות</b>')
    lines.append('')

    if west:
        lines.append('🌅 <b>מערב — סיבוב ראשון</b>')
        for s in west:
            mark = '⚡ ' if s['leader'] else '   '
            lines.append(f'{mark}{s["team1"]} {s["wins1"]}-{s["wins2"]} {s["team2"]}')
        lines.append('')

    if east:
        lines.append('🏙 <b>מזרח — סיבוב ראשון</b>')
        for s in east:
            mark = '⚡ ' if s['leader'] else '   '
            lines.append(f'{mark}{s["team1"]} {s["wins1"]}-{s["wins2"]} {s["team2"]}')

    return lines


def build_message(games, all_players, il_players, history_fact, top_plays_url, east, west):
    try:
        date_obj  = datetime.now() - timedelta(days=1)
        days_he   = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']
        day_name  = days_he[date_obj.weekday()]
        date_str  = f'{day_name} {date_obj.day}.{date_obj.month}.{str(date_obj.year)[2:]}'
    except Exception:
        date_str  = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%y')

    lines = []
    lines.append(f'<a href="{top_plays_url}">🎬 Top Plays of the Night</a>')
    lines.append('')
    lines.append(f'🏀 <b>NBA PLAYOFFS | {date_str}</b>')

    if all_players:
        mvp = max(all_players, key=lambda x: x['pts'])
        lines.append(f'🌟 {mvp["name"]} — {int(mvp["pts"])} PTS | {mvp["team"]}')

    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')

    if not games:
        lines.append('😴 לא היו משחקים הלילה.')
    else:
        for g in games:
            t0, t1 = g['teams'][0], g['teams'][1]
            s0, s1 = int(t0['score']), int(t1['score'])
            star   = '⭐ ' if g['is_fav'] else ''
            yt     = g.get('yt_url', '')
            series = g.get('series')

            if s0 > s1:
                score_line = f'<b>{t0["abbr"]} {s0}</b>-{s1} {t1["abbr"]}'
            else:
                score_line = f'{t0["abbr"]} {s0}-<b>{s1} {t1["abbr"]}</b>'

            series_line = ''
            if series and series.get('summary'):
                series_line = f'   🏆 {series["summary"]}'

            scorers = []
            for team in [t0, t1]:
                if team['leaders']:
                    top = team['leaders'][0]
                    scorers.append(f'{top["short"]} {top["val"]}')
            scorers_line = ' • '.join(scorers)

            lines.append(f'{star}{score_line} | <a href="{yt}">▶️</a>')
            if series_line:
                lines.append(series_line)
            lines.append(f'   {scorers_line}')

    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')

    if il_players:
        for p in il_players:
            lines.append(f'🇮🇱 {p["name"]} {int(p["pts"])}P {int(p["reb"])}R {int(p["ast"])}A | {p["team"]}')
    else:
        lines.append('🇮🇱 לא שיחק ישראלי הלילה')

    bracket_lines = build_bracket_section(east, west)
    lines.extend(bracket_lines)

    if history_fact:
        lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')
        lines.append(f'📜 {history_fact["year"]}: {history_fact["fact"]}')

    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')
    lines.append('🤖 <i>NBA Nightly Bot</i>')
    return '\n'.join(lines)


def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print('ERROR: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID')
        return False
    try:
        resp = requests.post(
            f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            json={
                'chat_id':                  CHAT_ID,
                'text':                     text,
                'parse_mode':               'HTML',
                'disable_web_page_preview': False,
            },
            timeout=15,
        )
        if resp.ok:
            print('ההודעה נשלחה בהצלחה!')
            return True
        else:
            print(f'Telegram error {resp.status_code}: {resp.text}')
            return False
    except Exception as e:
        print(f'Send failed: {e}')
        return False


if __name__ == '__main__':
    print('שולף נתוני NBA...')
    games, players, il = get_nba_data()
    print(f'משחקים: {len(games)}  |  שחקנים: {len(players)}  |  ישראלים: {len(il)}')

    today     = datetime.now()
    yesterday = today - timedelta(days=1)

    print('מחפש Top Plays...')
    top_plays_url = get_top_plays_url(yesterday)

    print('שולף עובדה היסטורית...')
    history_fact = get_nba_history(today)

    print('בונה טבלת פלייאוף מ-10 ימים אחרונים...')
    east, west = get_playoff_bracket_from_week()
    print(f'נטענו {len(east)} סדרות במזרח ו-{len(west)} במערב')

    data = {
        'date':         yesterday.strftime('%d/%m/%Y'),
        'date_he':      f'{["שני","שלישי","רביעי","חמישי","שישי","שבת","ראשון"][yesterday.weekday()]} {yesterday.day}.{yesterday.month}.{str(yesterday.year)[2:]}',
        'games':        games,
        'mvp':          max(players, key=lambda x: x["pts"]) if players else None,
        'il_players':   il,
        'history':      history_fact,
        'top_plays':    top_plays_url,
        'playoffs':     True,
        'bracket_east': east,
        'bracket_west': west,
    }
    save_to_github(data)

    msg = build_message(games, players, il, history_fact, top_plays_url, east, west)
    send_telegram(msg)
