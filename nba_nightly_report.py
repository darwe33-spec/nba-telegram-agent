import os
import requests
from datetime import datetime, timedelta

# הגדרת משתנים מה-Secrets של GitHub
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# יצירת הקישור האוטומטי לדשבורד שלך
repo_name = os.getenv('GITHUB_REPOSITORY', '').split('/')[-1]
user_name = os.getenv('GITHUB_REPOSITORY_OWNER', '')
DASHBOARD_URL = f"https://{user_name}.github.io/{repo_name}/"

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
            # שליפת 2 קלעים מובילים לכל קבוצה
            for leader_cat in comp.get('leaders', []):
                if leader_cat['name'] == 'points':
                    team_leaders = [l for l in leader_cat['leaders'] if l['athlete']['team']['id'] == team['id']]
                    for l in team_leaders[:2]:
                        t_info['leaders'].append({'name': l['athlete']['shortName'], 'val': l['displayValue']})
                        all_players.append({
                            'name': l['athlete']['displayName'], 
                            'points': float(l['displayValue']), 
                            'team': t_info['name']
                        })
            game_info['teams'].append(t_info)
        games_data.append(game_info)
        
    return games_data, all_players

def create_html(games, mvp):
    # יצירת קובץ ה-HTML בתיקייה הראשית
    html_content = f"""
    <html dir="rtl">
    <head>
        <meta charset="utf-8">
        <title>NBA Dashboard</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; background: #f4f4f9; text-align: center; padding: 20px; }}
            .game-card {{ background: white; margin: 15px auto; padding: 20px; width: 90%; max-width: 600px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            .mvp-box {{ background: linear-gradient(135deg, #ffd700, #ffae00); color: white; padding: 25px; border-radius: 15px; display: inline-block; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3); }}
            h2 {{ color: #333; }}
            .score {{ font-size: 24px; font-weight: bold; color: #1a1a1a; }}
        </style>
    </head>
    <body>
        <h1>NBA Daily Summary - {datetime.now().strftime('%d/%m/%Y')}</h1>
        <div class="mvp-box">
            <h2 style="margin:0">⭐ MVP הלילה ⭐</h2>
            <p style="font-size: 20px;"><b>{mvp['name']}</b> ({mvp['team']})</p>
            <p style="font-size: 24px; font-weight: bold;">{int(mvp['points'])} נקודות</p>
        </div>
    """
    for g in games:
        html_content += f"""
        <div class="game-card">
            <h3>{g['name']}</h3>
            <p class="score">{g['teams'][0]['score']} - {g['teams'][1]['score']}</p>
            <p style="color: #666;">{g['status']}</p>
            <hr>
            <p><b>{g['teams'][0]['name']}:</b> {g['teams'][0]['leaders'][0]['name']} ({g['teams'][0]['leaders'][0]['val']}), {g['teams'][0]['leaders'][1]['name']} ({g['teams'][0]['leaders'][1]['val']})</p>
            <p><b>{g['teams'][1]['name']}:</b> {g['teams'][1]['leaders'][0]['name']} ({g['teams'][1]['leaders'][0]['val']}), {g['teams'][1]['leaders'][1]['name']} ({g['teams'][1]['leaders'][1]['val']})</p>
        </div>
        """
    html_content += "</body></html>"
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

def send_telegram(games, mvp):
    if not TOKEN or not CHAT_ID:
        print("Error: Telegram credentials missing.")
        return

    msg = f"📊 <b>NBA NIGHTLY REPORT | {datetime.now().strftime('%d/%m/%Y')}</b>\n\n"
    msg += f"⭐ <b>MVP הלילה:</b> {mvp['name']} ({mvp['team']})\n🔥 {int(mvp['points'])} נקודות!\n\n"
    
    for g in games[:5]:
        msg += f"🏀 <b>{g['name']}</b>\n"
        msg += f"🏆 {g['teams'][0]['leaders'][0]['name']} ({g['teams'][0]['leaders'][0]['val']}) | {g['teams'][1]['leaders'][0]['name']} ({g['teams'][1]['leaders'][0]['val']})\n\n"
    
    msg += f"🖥️ <a href='{DASHBOARD_URL}'>לדשבורד המלא והמעוצב לחץ כאן</a>"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

if __name__ == "__main__":
    games, players = get_nba_data()
    if players:
        mvp_player = max(players, key=lambda x: x['points'])
        create_html(games, mvp_player)
        send_telegram(games, mvp_player)
