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
        events      = resp.json().get('events', [])
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
                                    player_entry = {
                                        'name': full,
                                        'pts':  pts,
                                        'val':  val,
                                        'team': tname,
                                    }
                                    all_players.append(player_entry)
                                    if any(il in full for il in ISRAELI_PLAYERS):
                                        il_players.append({
                                            **player_entry, 'game': game_name
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


def build_message(games, all_players, il_players, history_fact):
    try:
        date_obj  = datetime.now() - timedelta(days=1)
        days_he   = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']
        months_he = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                     'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
        day_name  = days_he[date_obj.weekday()]
        date_str  = f'יום {day_name}, {date_obj.day} ב{months_he[date_obj.month - 1]} {date_obj.year}'
    except Exception:
        date_str  = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')

    lines = []

    # כותרת
    lines.append('🏀 <b>NBA NIGHTLY REPORT</b>')
    lines.append(f'📅 {date_str}')
    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')

    # ביצוע הלילה
    if all_players:
        mvp = max(all_players, key=lambda x: x['pts'])
        lines.append('')
        lines.append('🌟 <b>ביצוע הלילה</b>')
        lines.append('━━━━━━━━━━━━━━')
        lines.append(f'<b>{mvp["name"]}</b>')
        lines.append(f'{mvp["team"]}  •  {int(mvp["pts"])} PTS')

    # משחקים
    lines.append('')
    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')
    if not games:
        lines.append('😴 לא היו משחקים הלילה.')
    else:
        lines.append(f'🎯 <b>{len(games)} משחקים הלילה</b>')
        lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')

        for g in games:
            t0, t1 = g['teams'][0], g['teams'][1]
            s0, s1 = int(t0['score']), int(t1['score'])
            sc0    = f'<b>{s0}</b>' if s0 > s1 else str(s0)
            sc1    = f'<b>{s1}</b>' if s1 > s0 else str(s1)
            star   = '⭐ ' if g['is_fav'] else ''

            lines.append('')
            lines.append(f'{star}<b>{t0["name"]} vs {t1["name"]}</b>')
            lines.append(f'   🏆 {sc0} — {sc1}  •  {g["status"]}')

            for team in [t0, t1]:
                if team['leaders']:
                    top    = team['leaders'][0]
                    second = (f'  •  {team["leaders"][1]["short"]} '
                              f'{team["leaders"][1]["val"]} PTS') \
                             if len(team['leaders']) > 1 else ''
                    lines.append(f'   📊 {top["short"]} {top["val"]} PTS{second}')

            yt = search_youtube(f'NBA {t0["name"]} vs {t1["name"]} highlights')
            lines.append(f'   <a href="{yt}">▶️ Highlights</a>')
            lines.append('──────────────────────')

    # ישראלים
    lines.append('')
    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')
    lines.append('🇮🇱 <b>ישראלים הלילה</b>')
    lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')
    if il_players:
        for p in il_players:
            lines.append(f'<b>{p["name"]}</b>  •  {p["team"]}')
            lines.append(f'{int(p["pts"])} PTS')
    else:
        lines.append('לא שיחק אף ישראלי הלילה.')

    # היסטוריה
    if history_fact:
        lines.append('')
        lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')
        lines.append('📜 <b>היום לפני בהיסטוריה</b>')
        lines.append('━━━━━━━━━━━━━━━━━━━━━━━━')
        lines.append(f'{history_fact["year"]}: {history_fact["fact"]}')

    lines.append('')
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

    date_obj = datetime.now() - timedelta(days=1)
    print('שולף עובדה היסטורית מ-Wikipedia...')
    history_fact = get_nba_history(date_obj)
    if history_fact:
        print(f'נמצא: {history_fact["year"]} - {history_fact["fact"][:50]}...')
    else:
        print('לא נמצאה עובדה היסטורית להיום.')

    msg = build_message(games, players, il, history_fact)
    send_telegram(msg)
