import os
import requests
from datetime import datetime, timedelta

TOKEN            = os.getenv('TELEGRAM_TOKEN')
CHAT_ID          = os.getenv('TELEGRAM_CHAT_ID')
YOUTUBE_API_KEY  = os.getenv('YOUTUBE_API_KEY', '')

# -- Your favorite team (appears first with a star) --
FAVORITE_TEAMS = ['Lakers', 'LA Lakers', 'Los Angeles Lakers']

# -- Israeli players to track --
ISRAELI_PLAYERS = ['Deni Avdija', 'Ben Sheppard', 'Dani Wolf']

# -- Historical facts (MM-DD format) --
HISTORY = {
    '01-07': [{'year': 2003, 'fact': 'Tracy McGrady scored 62 points against Washington.'}],
    '01-13': [{'year': 1990, 'fact': 'Michael Jordan scored 69 points against Cleveland.'}],
    '01-22': [{'year': 2006, 'fact': 'Kobe Bryant scored 81 points against Toronto Raptors.'}],
    '03-02': [{'year': 1962, 'fact': 'Wilt Chamberlain scored 100 points against the Knicks.'}],
    '03-31': [{'year': 2016, 'fact': 'Stephen Curry hit his 400th three-pointer of the season.'}],
    '04-01': [{'year': 1984, 'fact': 'Kareem Abdul-Jabbar became the all-time NBA scoring leader.'}],
    '04-06': [{'year': 2017, 'fact': 'Russell Westbrook broke the single-season triple-double record.'}],
    '06-11': [{'year': 1997, 'fact': 'Michael Jordan hit the game-winner in the famous Flu Game.'}],
    '12-13': [{'year': 1983, 'fact': 'Detroit beat Denver 186-184 in the highest-scoring game ever.'}],
}


def search_youtube(query):
    if not YOUTUBE_API_KEY:
        q = query.replace(' ', '+')
        return f'https://www.youtube.com/results?search_query={q}'
    try:
        resp = requests.get(
            'https://www.googleapis.com/youtube/v3/search',
            params={
                'part': 'snippet', 'q': query, 'type': 'video',
                'maxResults': 1, 'key': YOUTUBE_API_KEY,
                'order': 'relevance',
            },
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


def get_standings():
    url = 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings'
    try:
        data = requests.get(url, timeout=15).json()
        east = {'playoff': [], 'playin': [], 'rest': []}
        west = {'playoff': [], 'playin': [], 'rest': []}

        for conf in data.get('children', []):
            conf_name = conf.get('name', '')
            is_east   = 'East' in conf_name

            entries = conf.get('standings', {}).get('entries', [])
            for i, entry in enumerate(entries):
                rank   = i + 1
                team   = entry.get('team', {}).get('shortDisplayName', '?')
                stats  = {s['name']: s.get('displayValue', '?') for s in entry.get('stats', [])}
                wins   = stats.get('wins',   '?')
                losses = stats.get('losses', '?')
                gb     = stats.get('gamesBehind', '-')
                gb_str = f'GB: {gb}' if gb != '-' else 'Leader'
                row    = f'{rank}. {team}  {wins}-{losses}  {gb_str}'

                if rank <= 6:
                    cat = 'playoff'
                elif rank <= 10:
                    cat = 'playin'
                else:
                    cat = 'rest'

                if is_east:
                    east[cat].append(row)
                else:
                    west[cat].append(row)

        return east, west
    except Exception as e:
        print(f'Standings error: {e}')
        return None, None


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
            game_name = event.get('name', 'Unknown')
            status    = (event.get('status', {})
                             .get('type', {})
                             .get('shortDetail', 'Final'))

            leaders_by_team = {}
            for cat in comp.get('leaders', []):
                if cat.get('name') == 'points':
                    for ldr in cat.get('leaders', []):
                        try:
                            tid = ldr['athlete']['team']['id']
                            leaders_by_team.setdefault(tid, [])
                            if len(leaders_by_team[tid]) < 2:
                                full  = ldr['athlete'].get('displayName', '?')
                                short = ldr['athlete'].get('shortName', '?')
                                pts   = float(ldr.get('value', 0))
                                leaders_by_team[tid].append({
                                    'full':  full,
                                    'short': short,
                                    'val':   ldr.get('displayValue', '0'),
                                    'pts':   pts,
                                })
                        except Exception:
                            continue

            teams = []
            for team in comp.get('competitors', []):
                try:
                    tid     = team['team']['id']
                    tname   = team['team'].get('shortDisplayName', '?')
                    tfull   = team['team'].get('displayName', tname)
                    score   = team.get('score', '0')
                    leaders = leaders_by_team.get(tid, [])

                    teams.append({
                        'name':    tname,
                        'full':    tfull,
                        'score':   score,
                        'leaders': leaders,
                    })

                    for ldr in leaders:
                        player_entry = {
                            'name': ldr['full'],
                            'pts':  ldr['pts'],
                            'val':  ldr['val'],
                            'team': tname,
                        }
                        all_players.append(player_entry)
                        if any(il in ldr['full'] for il in ISRAELI_PLAYERS):
                            il_players.append({**player_entry, 'game': game_name})
                except Exception:
                    continue

            if len(teams) == 2:
                is_fav = any(
                    any(fav.lower() in t['full'].lower() for fav in FAVORITE_TEAMS)
                    for t in teams
                )
                games_data.append({
                    'name':   game_name,
                    'status': status,
                    'teams':  teams,
                    'is_fav': is_fav,
                })
        except Exception as e:
            print(f'Skipping game: {e}')
            continue

    games_data.sort(key=lambda g: (0 if g['is_fav'] else 1))
    return games_data, all_players, il_players


def build_message(games, all_players, il_players, east, west):
    date_str  = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
    today_key = datetime.now().strftime('%m-%d')
    lines     = []

    lines.append('<b>NBA Nightly Report</b>')
    lines.append(f'Date: {date_str}')
    lines.append('=' * 22)

    if all_players:
        mvp = max(all_players, key=lambda x: x['pts'])
        lines.append('')
        lines.append('<b>Performance of the Night</b>')
        lines.append(f'<b>{mvp["name"]}</b>  ({mvp["team"]})')
        lines.append(f'{int(mvp["pts"])} points')
        lines.append('=' * 22)

    if not games:
        lines.append('')
        lines.append('No games last night.')
    else:
        lines.append('')
        lines.append(f'<b>{len(games)} Games Last Night</b>')
        for g in games:
            t0, t1 = g['teams'][0], g['teams'][1]
            s0, s1 = int(t0['score']), int(t1['score'])
            sc0    = f'<b>{s0}</b>' if s0 > s1 else str(s0)
            sc1    = f'<b>{s1}</b>' if s1 > s0 else str(s1)
            star   = ' STAR' if g['is_fav'] else ''

            lines.append('')
            lines.append(f'<b>{t0["name"]} vs {t1["name"]}</b>{star}')
            lines.append(f'{sc0} - {sc1}   {g["status"]}')

            for team in [t0, t1]:
                if team['leaders']:
                    top    = team['leaders'][0]
                    second = (f',  {team["leaders"][1]["short"]} {team["leaders"][1]["val"]}')  \
                             if len(team['leaders']) > 1 else ''
                    lines.append(f'  {top["short"]} {top["val"]}{second}')

            yt_url = search_youtube(f'NBA {t0["name"]} vs {t1["name"]} highlights')
            lines.append(f'  Highlights: {yt_url}')

        lines.append('')
        lines.append('=' * 22)

    lines.append('')
    lines.append('<b>Israeli Players Tonight</b>')
    if il_players:
        for p in il_players:
            lines.append(f'  {p["name"]}  ({p["team"]})  {int(p["pts"])} pts')
    else:
        lines.append('  No Israeli players tonight.')
    lines.append('=' * 22)

    if east and west:
        for conf_name, conf in [('EAST', east), ('WEST', west)]:
            lines.append('')
            lines.append(f'<b>{conf_name} Standings</b>')

            if conf['playoff']:
                lines.append('<b>Playoff (1-6)</b>')
                for row in conf['playoff']:
                    lines.append(f'  {row}')

            if conf['playin']:
                lines.append('<b>Play-In (7-10)</b>')
                for row in conf['playin']:
                    lines.append(f'  {row}')

            if conf['rest']:
                lines.append('<b>Out (11-15)</b>')
                for row in conf['rest'][:3]:
                    lines.append(f'  {row}')
                if len(conf['rest']) > 3:
                    lines.append(f'  ... and {len(conf["rest"]) - 3} more')

        lines.append('')
        lines.append('=' * 22)

    facts = HISTORY.get(today_key, [])
    if facts:
        lines.append('')
        lines.append('<b>On This Day in NBA History</b>')
        for f in facts:
            lines.append(f'  {f["year"]}: {f["fact"]}')
        lines.append('=' * 22)

    lines.append('')
    lines.append('<i>NBA Nightly Bot</i>')
    return '\n'.join(lines)


def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print('ERROR: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID')
        return False
    try:
        resp = requests.post(
            f'https://api.telegram.org/bot{TOKEN}/sendMessage',
            json={
                'chat_id':    CHAT_ID,
                'text':       text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            },
            timeout=15,
        )
        if resp.ok:
            print('Message sent successfully!')
            return True
        else:
            print(f'Telegram error {resp.status_code}: {resp.text}')
            return False
    except Exception as e:
        print(f'Send failed: {e}')
        return False


if __name__ == '__main__':
    print('Fetching NBA data...')
    games, players, il = get_nba_data()
    print(f'Games: {len(games)}  |  Players: {len(players)}  |  Israelis: {len(il)}')

    print('Fetching standings...')
    east, west = get_standings()

    msg = build_message(games, players, il, east, west)
    send_telegram(msg)
