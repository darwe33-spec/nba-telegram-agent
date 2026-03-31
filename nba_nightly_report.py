import os
import requests
from nba_api.stats.endpoints import scoreboardv3
from datetime import datetime, timedelta

# משיכת המפתחות מה-Secrets
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    print(f"נסיונות שליחה לטלגרם לצ'אט: {CHAT_ID}")
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    res = requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    print(f"תגובת טלגרם: {res.text}")

def get_data():
    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.nba.com/'
    }
    try:
        # ננסה לקחת נתונים על אתמול
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"מושך נתונים עבור תאריך: {yesterday}")
        
        # שימוש ב-ScoreboardV3 החדש כדי להימנע מהאזהרה
        sb = scoreboardv3.ScoreboardV3(game_date=yesterday, headers=headers, timeout=30)
        data = sb.get_dict()
        
        games = data['scoreboard']['games']
        
        if not games:
            print("לא נמצאו משחקים ב-API")
            return "🏀 לא נמצאו משחקי NBA הלילה."
        
        res = f"🏀 <b>תוצאות NBA מהלילה ({yesterday}):</b>\n\n"
        for g in games:
            home = g['homeTeam']['teamName']
            away = g['awayTeam']['teamName']
            home_score = g['homeTeam']['score']
            away_score = g['awayTeam']['score']
            res += f"• {away} {away_score} - {home_score} {home}\n"
        
        return res
    except Exception as e:
        print(f"שגיאה בתהליך: {str(e)}")
        return f"שגיאה במשיכת נתונים: {str(e)}"

if __name__ == "__main__":
    print("--- תחילת ריצה ---")
    report = get_data()
    send_telegram(report)
    print("--- סיום ריצה ---")
