import os
import requests
from datetime import datetime, timedelta

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
# הקישור שלך יהיה: https://[YOUR_USERNAME].github.io/[YOUR_REPO_NAME]/
DASHBOARD_URL = f"https://{os.getenv('GITHUB_REPOSITORY_OWNER')}.github.io/{os.getenv('GITHUB_REPOSITORY').split('/')[-1]}/"

def get_nba_data():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday}"
    response = requests.get(url).json()
    
    events = response.get('events', [])
    games_data = []
    all_players = []

    for event in events:
        comp = event['competitions'][0]
        game_info = {
            'name': event['name'],
            'status': event['status']['type']['shortDetail'],
            'teams': []
        }
        
        for team in comp['competitors']:
            t_info = {
                'name': team['team']['shortDisplayName'],
                'score': team['score'],
                'logo': team['team']['logo'],
                'leaders': []
            }
            # משיכת 2 קלעים מובילים
            for leader_cat in comp.get('leaders', []):
                if leader_cat['name'] == 'points':
                    team_leaders = [l for l in leader_cat['leaders'] if l['athlete']['team']['id'] == team['id']]
                    for l in team_leaders[:2]:
                        t_info['leaders'].append({'name': l['athlete']['shortName'], 'val': l['displayValue']})
                        all_players.append({'name': l['athlete']['displayName'], 'points': float(l['displayValue']), 'team': t_info['name']})
            game_info['teams'].append(t_info)
        games_data.append(game_info)
        
    return games_data, all_players

def create_html(games, mvp):
    if not os.path.exists('public'): os.makedirs('public')
    
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>NBA Dashboard</title>
        <style>
            body {{ font-family: sans-serif; background: #f4f4f9; text-align: center; }}
            .game-card {{ background: white; margin: 10px auto; padding: 20px; width: 80%; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .mvp {{ background: #ffd700; padding: 20px; border-radius: 10px; display: inline-block; margin: 20px; }}
        </style>
    </head>
    <body>
        <h1>NBA Daily Dashboard - {datetime.now().strftime('%d/%m/%Y')}</h1>
        <div class="mvp">⭐ <b>MVP הלילה:</b> {mvp['name']} ({mvp['team']}) - {int(mvp['points'])} נקודות</div>
        <div id="games">
    """
    for g in games:
        html_content += f"""
        <div class="game-card">
            <h3>{g['name']} ({g['status']})</h3>
            <p><b>{g['teams'][0]['name']} {g['teams'][0]['score']} - {g['teams'][1]['score']} {g['teams'][1]['name']}</b></p>
            <p><small>{g['teams'][0]['name']}: {g['teams'][0]['leaders'][0]['name']} ({g['teams'][0]['leaders'][0]['val']}), {g['teams'][0]['leaders'][1]['name']} ({g['teams'][0]['leaders'][1]['val']})</small></p>
            <p><small>{g['teams'][1]['name']}: {g['teams'][1]['leaders'][0]['name']} ({g['teams'][1]['leaders'][0]['val']}), {g['teams'][1]['leaders'][1]['name']} ({g['teams'][1]['leaders'][1]['val']})</small></p>
        </div>
        """
    html_content += "</div></body></html>"
    
    with open('public/index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

def send_telegram(games, mvp):
    msg = f"📊 <b>NBA DASHBOARD | {datetime.now().strftime('%d/%m/%Y')}</b>\n\n"
    msg += f"⭐ <b>MVP:</b> {mvp['name']} ({int(mvp['points'])} נק')\n\n"
    for g in games[:4]:
        msg += f"• {g['name']} ({g['status']})\n"
        msg += f"  🏆 {g['teams'][0]['leaders'][0]['name']} ({g['teams'][0]['leaders'][0]['val']}) | {g['teams'][1]['leaders'][0]['name']} ({g['teams'][1]['leaders'][0]['val']})\n"
    
    msg += f"\n💻 <a href='{DASHBOARD_URL}'>לדשבורד המלא המעודכן 🖥️</a>"
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

if __name__ == "__main__":
    games, players = get_nba_data()
    if players:
        mvp = max(players, key=lambda x: x['points'])
        create_html(games, mvp)
        send_telegram(games, mvp)
