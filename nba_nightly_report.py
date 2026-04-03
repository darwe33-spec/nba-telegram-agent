import os
import requests
from datetime import datetime, timedelta

TOKEN           = os.getenv('TELEGRAM_TOKEN')
CHAT_ID         = os.getenv('TELEGRAM_CHAT_ID')

FAVORITE_TEAMS  = ['Lakers', 'LA Lakers', 'Los Angeles Lakers']
ISRAELI_PLAYERS = ['Avdija', 'Saraf', 'Wolf']


def get_youtube_link(team1, team2):
    query = f'{team1}+{team2}+highlights'
    return f'https://www.youtube.com/@NBA/search?query={query}'


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

            def sort_key(e):
                for s in e.get('stats', []):
                    if s['name'] == 'winPercent':
                        return -float(s.get('value', 0))
                return 0

            entries_sorted = sorted(entries, key=sort_key)

            for rank, entry in enumerate(entries_sorted, 1):
                team   = entry.get('team', {}).get('abbreviation', '?')
                stats  = {s['name']: s.get('displayValue', '?') for s in entry.get('stats', [])}
                wins   = stats.get('wins', '?')
                row    = f'{team} {wins}'
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
                games_data.append({
                    'game_id': game_id,
                    'name':    game_name,
                    'status':  status,
                    'teams':   teams,
                    'is_fav':  is_fav,
                })
        except Exception as e:
            print(f'Skipping game: {e}')
            continue

    games_data.sort(key=lambda g: (0 if g['is_fav'] else 1))
    return games_data, all_players, il_players


def build_message(games, all_players, il_players, history_fact, east, west):
    try:
        date_obj  = datetime.now() - timedelta(days=1)
        days_he   = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']
        months_he = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                     'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
        day_name  = days_he[date_obj.weekday()]
        date_str  = f'{day_name} {date_obj.day}.{date_obj.month}.{str(date_obj.year)[2:]}'
    except Exception:
        date_str  = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%y')

    lines = []

    # כותרת קצרה
    lines.append(f'🏀 <b>NBA | {date_str}</b>')

    # MVP
    if all_players:
        mvp = max(all_players, key=lambda x: x['pts'])
        lines.append(f'🌟 {mvp["name"]} — {int(mvp["pts"])} PTS | {mvp["team"]}')

    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')

    # משחקים — דחוס
    if not games:
        lines.append('😴 לא היו משחקים הלילה.')
    else:
        for g in games:
            t0, t1 = g['teams'][0], g['teams'][1]
            s0, s1 = int(t0['score']), int(t1['score'])
            star   = '⭐ ' if g['is_fav'] else ''
            yt     = get_youtube_link(t0['abbr'], t1['abbr'])

            # שורת תוצאה
            if s0 > s1:
                score_line = f'<b>{t0["abbr"]} {s0}</b>-{s1} {t1["abbr"]}'
            else:
                score_line = f'{t0["abbr"]} {s0}-<b>{s1} {t1["abbr"]}</b>'

            # קלעים
            scorers = []
            for team in [t0, t1]:
                if team['leaders']:
                    top = team['leaders'][0]
                    scorers.append(f'{top["short"]} {top["val"]}')

            scorers_line = ' • '.join(scorers)
            lines.append(f'{star}{score_line} | <a href="{yt}">▶️</a>')
            lines.append(f'   {scorers_line}')

    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')

    # ישראלים
    if il_players:
        for p in il_players:
            lines.append(f'🇮🇱 {p["name"]} {int(p["pts"])}P {int(p["reb"])}R {int(p["ast"])}A | {p["team"]}')
    else:
        lines.append('🇮🇱 לא שיחק ישראלי הלילה')

    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')

    # טבלה דחוסה
    if east and west:
        e_playoff = ' '.join(east['playoff'])
        e_playin  = ' '.join(east['playin'])
        w_playoff = ' '.join(west['playoff'])
        w_playin  = ' '.join(west['playin'])
        lines.append(f'🏙 🏆 {e_playoff}')
        lines.append(f'   ⚡ {e_playin}')
        lines.append(f'🌅 🏆 {w_playoff}')
        lines.append(f'   ⚡ {w_playin}')
        lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')

    # היסטוריה
    if history_fact:
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
                'disable_web_page_preview': True,
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

    print('שולף טבלה...')
    east, west = get_standings()
    if east:
        print('טבלה נטענה בהצלחה')
    else:
        print('שגיאה בטעינת הטבלה')

    today = datetime.now()
    print('שולף עובדה היסטורית...')
    history_fact = get_nba_history(today)
    if history_fact:
        print(f'נמצא: {history_fact["year"]}')
    else:
        print('לא נמצאה עובדה היסטורית.')

    msg = build_message(games, players, il, history_fact, east, west)
    send_telegram(msg)
