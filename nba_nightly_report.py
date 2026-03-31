import os
import requests
from nba_api.stats.endpoints import scoreboardv2
from datetime import datetime, timedelta

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def get_data():
    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://www.nba.com/'
    }
    try:
        # בדיקה על תאריך קבוע כדי לוודא שיש נתונים (למשל ה-30 במרץ)
        test_date = "2026-03-30" 
        sb = scoreboardv2.ScoreboardV2(game_date=test_date, headers=headers, timeout=30)
        games = sb.get_dict()['resultSets'][0]['rowSet']
        
        if not games:
            return "לא נמצאו משחקים אתמול."
        
        res = "🏀 <b>תוצאות NBA:</b>\n\n"
        for g in games:
            res += f"• {g[5]} נגד {g[4]}\n"
        return res
    except Exception as e:
        return f"שגיאה בתקשורת עם ה-NBA: {str(e)}"

if __name__ == "__main__":
    report = get_data()
    send_telegram(report)
