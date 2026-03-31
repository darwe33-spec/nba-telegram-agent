import os
import requests
from datetime import datetime, timedelta

# משיכת המפתחות מה-Secrets
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload)
        print(f"Telegram response: {res.text}")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

def get_espn_nba_results():
    # תאריך אתמול בפורמט ש-ESPN אוהב (YYYYMMDD)
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday}"
    
    try:
        print(f"מושך נתונים מ-ESPN עבור תאריך: {yesterday}")
        response = requests.get(url, timeout=20)
        data = response.json()
        
        events = data.get('events', [])
        if not events:
            return f"🏀 לא נמצאו משחקים ב-ESPN עבור תאריך {yesterday}."

        report = f"🏀 <b>תוצאות NBA מהלילה (ESPN):</b>\n\n"
        
        for event in events:
            # חילוץ שמות וקבוצות
            competitions = event.get('competitions', [{}])[0]
            competitors = competitions.get('competitors', [])
            
            # ESPN מחזיר רשימה של 2 קבוצות
            team1 = competitors[0]
            team2 = competitors[1]
            
            # בדיקה מי הבית ומי החוץ
            if team1.get('homeAway') == 'home':
                home_team = team1
                away_team = team2
            else:
                home_team = team2
                away_team = team1
                
            home_name = home_team['team']['shortDisplayName']
            away_name = away_team['team']['shortDisplayName']
            home_score = home_team['score']
            away_score = away_team['score']
            
            # הוספת מצב המשחק (אם נגמר או עדיין רץ)
            status = event['status']['type']['shortDetail']
            
            report += f"• {away_name} {away_score} - {home_score} {home_name} ({status})\n"
            
        return report

    except Exception as e:
        print(f"שגיאה במשיכת נתונים מ-ESPN: {e}")
        return f"⚠️ שגיאה במשיכת נתונים מ-ESPN: {str(e)}"

if __name__ == "__main__":
    report_text = get_espn_nba_results()
    send_telegram(report_text)
