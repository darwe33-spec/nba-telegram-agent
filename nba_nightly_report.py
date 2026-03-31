import os
import requests
from nba_api.stats.endpoints import scoreboardv3
from datetime import datetime, timedelta
import time

# משיכת המפתחות
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def get_data_with_retry(max_retries=3):
    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.nba.com/',
        'Connection': 'keep-alive',
    }
    
    # תאריך של אתמול
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    for i in range(max_retries):
        try:
            print(f"נסיון מספר {i+1} למשוך נתונים עבור {target_date}...")
            # הגדלנו את ה-timeout ל-60 שניות
            sb = scoreboardv3.ScoreboardV3(game_date=target_date, headers=headers, timeout=60)
            data = sb.get_dict()
            
            games = data['scoreboard']['games']
            if not games:
                return f"🏀 לא נמצאו משחקי NBA בתאריך {target_date}."
            
            res = f"🏀 <b>תוצאות NBA מהלילה ({target_date}):</b>\n\n"
            for g in games:
                home = g['homeTeam']['teamName']
                away = g['awayTeam']['teamName']
                home_score = g['homeTeam']['score']
                away_score = g['awayTeam']['score']
                res += f"• {away} {away_score} - {home_score} {home}\n"
            return res

        except Exception as e:
            print(f"נסיון {i+1} נכשל: {e}")
            if i < max_retries - 1:
                time.sleep(10) # מחכה 10 שניות לפני נסיון נוסף
            else:
                return f"⚠️ שגיאה במשיכת נתונים לאחר {max_retries} נסיונות: השרת של ה-NBA איטי מדי כרגע."

if __name__ == "__main__":
    report = get_data_with_retry()
    send_telegram(report)
