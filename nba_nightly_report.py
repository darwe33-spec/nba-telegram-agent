import os
import requests
from nba_api.stats.endpoints import scoreboardv2
from datetime import datetime, timedelta
import time

# הגדרות חיבור לטלגרם - נלקח מה-Secrets של GitHub
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    if not TOKEN or not CHAT_ID:
        print("Error: Telegram credentials missing.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
        print("Message sent to Telegram!")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def get_nba_data():
    # הגדרות כדי להיראות כמו דפדפן אמיתי (מונע חסימות)
    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.nba.com/',
        'Origin': 'https://www.nba.com'
    }

    try:
        # לקיחת תאריך של אתמול (NBA פועל לפי שעון ארה"ב)
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"Fetching data for: {yesterday}")

        # פנייה ל-API עם פסק זמן ארוך יותר
        sb = scoreboardv2.ScoreboardV2(game_date=yesterday, headers=headers, timeout=60)
        data = sb.get_dict()
        
        games = data['resultSets'][0]['rowSet']
        
        if not games:
            return f"🏀 לא נמצאו משחקים בתאריך {yesterday}."

        report = f"🏀 <b>סיכום משחקי ה-NBA ({yesterday}):</b>\n\n"
        
        for game in games:
            # חילוץ שמות הקבוצות והתוצאות
            away_team = game[5]
            home_team = game[4]
            # הנתונים נמצאים במיקומים קבועים במערך של ה-API
            report += f"• {away_team} נגד {home_team}\n"

        return report

    except Exception as e:
        print(f"Error fetching NBA data: {e}")
        return f"⚠️ שגיאה במשיכת הנתונים: {str(e)}"

if __name__ == "__main__":
    report_text = get_nba_data()
    send_telegram_message(report_text)
