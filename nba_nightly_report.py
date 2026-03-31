import os
import requests
from datetime import datetime, timedelta

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_nba_data():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday}"
    try:
        data = requests.get(url, timeout=15).json()
    except Exception as e:
        print(f"ESPN API error: {e}")
        return [], []

    games_data = []
    all_players = []

    for event in data.get('events', []):
        try:
            comp = event['competitions'][0]
            game_info = {
                'name': event.get('name', 'Unknown'),
                'status': event.get('status', {}).get('type', {}).get('shortDetail', 'Final'),
                'teams': []
            }

            leaders_by_team = {}
            for cat in comp.get('leaders', []):
                if cat.get('name') == 'points':
                    for ldr in cat.get('leaders', []):
                        try:
                            tid = ldr['athlete']['team']['id']
                            leaders_by_team.setdefault(tid, [])
                            if len(leaders_by_team[tid]) < 2:
                                leaders_by_team[tid].append({
                                    'name': ldr['athlete'].get('shortName', '?'),
                                    'full_name': ldr['athlete'].get('displayName', '?'),
                                    'val': ldr.get('displayValue', '0'),
                                    'points': float(ldr.get('value', 0)),
                                })
                        except Exception:
                            continue

            for team in comp.get('competitors', []):
                try:
                    tid = team['team']['id']
                    tname = team['team'].get('shortDisplayName', '?')
                    leaders = leaders_by_team.get(tid, [])
                    game_info['teams'].append({
                        'name': tname,
                        'score': team.get('score', '0'),
                        'leaders': leaders,
                    })
                    for ldr in leaders:
                        all_players.append({
                            'name': ldr['full_name'],
                            'points': ldr['points'],
                            'val': ldr['val'],
                            'team': tname,
                        })
                except Exception:
                    continue

            if len(game_info['teams']) == 2:
                games_data.append(game_info)

        except Exception as e:
            print(f"Skipping game: {e}")
            continue

    return games_data, all_players


def send_telegram(games, mvp):
    if not TOKEN or not CHAT_ID:
        print("ERROR: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return False

    date_str = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')

    msg = f"<b>NBA Nightly Report</b>\n"
    msg += f"Date: {date_str}\n"
    msg += "--------------------\n\n"

    if mvp:
        msg += f"MVP of the Night\n"
        msg += f"<b>{mvp['name']}</b> - {mvp['team']}\n"
        msg += f"{int(mvp['points'])} points\n\n"
        msg += "--------------------\n\n"

    if not games:
        msg += "No games last night.\n"
    else:
        msg += f"<b>{len(games)} Games Last Night</b>\n\n"
        for g in games:
            try:
                t0 = g['teams'][0]
                t1 = g['teams'][1]
                s0 = int(t0['score'])
                s1 = int(t1['score'])
                score0 = f"<b>{s0}</b>" if s0 > s1 else str(s0)
                score1 = f"<b>{s1}</b>" if s1 > s0 else str(s1)
                msg += f"<b>{t0['name']} vs {t1['name']}</b>\n"
                msg += f"{score0} - {score1}   {g['status']}\n"
                for team in [t0, t1]:
                    if team['leaders']:
                        top = team['leaders'][0]
                        second = ""
                        if len(team['leaders']) > 1:
                            second = f", {team['leaders'][1]['name']} {team['leaders'][1]['val']}"
                        msg += f"{top['name']} {top['val']}{second}\n"
                msg += "\n"
            except Exception as e:
                print(f"Error formatting game: {e}")
                continue

    msg += "--------------------\n"
    msg += "<i>NBA Nightly Bot</i>"

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if resp.ok:
            print("Message sent successfully!")
            return True
        else:
            print(f"Telegram error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"Send failed: {e}")
        return False


if __name__ == "__main__":
    print("Fetching NBA data...")
    games, players = get_nba_data()
    print(f"Found {len(games)} games, {len(players)} players")
    mvp = max(players, key=lambda x: x['points']) if players else None
    if mvp:
        print(f"MVP: {mvp['name']} - {int(mvp['points'])} pts")
    send_telegram(games, mvp)
