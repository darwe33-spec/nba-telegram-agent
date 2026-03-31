import os
import requests
from datetime import datetime, timedelta

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def get_nba_full_report():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    today_md = datetime.now().strftime('%m/%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday}"
    
    try:
        data = requests.get(url, timeout=20).json()
        events = data.get('events', [])
        
        if not events:
            return "🏀 לא נמצאו משחקי NBA הלילה."

        # 1. תוצאות נבחרות (עד 4 משחקים)
        results_text = "<b>📌 תוצאות נבחרות מהלילה:</b>\n"
        for event in events[:4]:
            teams = event['competitions'][0]['competitors']
            home = next(t for t in teams if t['homeAway'] == 'home')
            away = next(t for t in teams if t['homeAway'] == 'away')
            results_text += f"• {away['team']['shortDisplayName']} {away['score']} - {home['score']} {home['team']['shortDisplayName']}\n"

        # 2. ה-MVP של הלילה
        mvp_text = "\n<b>🌟 ה-MVP של הלילה:</b>\n"
        top_performer = "נתוני שחקנים לא זמינים כרגע"
        max_score = 0
        for event in events:
            for athlete in event['competitions'][0].get('leaders', []):
                for leader in athlete.get('leaders', []):
                    if leader.get('displayValue'):
                        try:
                            val = float(leader['displayValue'].split()[0])
                            if val > max_score:
                                max_score = val
                                top_performer = f"{leader['athlete']['displayName']} ({leader['displayValue']})"
                        except: continue
        mvp_text += top_performer

        # 3. זווית ישראלית (אבדיה, שרף, וולף)
        israeli_text = "\n\n<b>🇮🇱 הזווית הישראלית:</b>\n"
        israelis = {
            "Trail Blazers": "דני אבדיה",
            "Nets": "בן שרף ודני וולף"
        }
        found_israelis = []
        for event in events:
            for team_key, name in israelis.items():
                if team_key in event['name'] and name not in found_israelis:
                    found_israelis.append(f"• <b>{name}</b> שיחקו הלילה במדי {team_key}!")
        
        israeli_text += "\n".join(found_israelis) if found_israelis else "אין נציגים ישראלים הלילה."

        # 4. פינה היסטורית (לפי תאריך)
        history_events = {
            "03/31": "ב-1991, הבולס ניצחו את ה-76ers וקבעו שיא מועדון של 62 ניצחונות.",
            "04/01": "ב-1970, הניקס ניצחו את הבולס בחצי גמר המזרח בדרך לאליפות."
        }
        history_text = f"\n\n<b>📜 היום בהיסטוריה ({today_md}):</b>\n"
        history_text += history_events.get(today_md, "יום מרגש בתולדות ה-NBA!")

        return f"{results_text}{mvp_text}{israeli_text}{history_text}"

    except Exception as e:
        return f"⚠️ שגיאה בבניית הדו\"ח: {str(e)}"

if __name__ == "__main__":
    report = get_nba_full_report()
    send_telegram(report)
