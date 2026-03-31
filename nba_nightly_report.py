import os
import requests
from datetime import datetime, timedelta

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": msg, 
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    requests.post(url, json=payload)

def get_nba_dashboard():
    yesterday_obj = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday_obj.strftime('%Y%m%d')
    today_display = datetime.now().strftime('%d/%m/%Y')
    
    # יצירת קישור ליוטיוב עבור התקצירים של אתמול
    youtube_query = f"NBA+highlights+{yesterday_obj.strftime('%Y-%m-%d')}".replace("-", "+")
    youtube_link = f"https://www.youtube.com/results?search_query={youtube_query}"
    
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday_str}"
    
    try:
        data = requests.get(url, timeout=20).json()
        events = data.get('events', [])
        
        if not events:
            return f"<b>🏀 NBA Dashboard - {today_display}</b>\n\nלא נמצאו משחקים בלילה האחרון."

        report = f"📊 <b><u>NBA DAILY DASHBOARD | {today_display}</u></b>\n\n"

        # 1. תוצאות בולטות
        report += "<b>📌 תוצאות בולטות:</b>\n"
        for event in events[:4]:
            teams = event['competitions'][0]['competitors']
            home = next(t for t in teams if t['homeAway'] == 'home')
            away = next(t for t in teams if t['homeAway'] == 'away')
            status = event['status']['type']['shortDetail']
            report += f"• {away['team']['shortDisplayName']} <b>{away['score']}</b> - <b>{home['score']}</b> {home['team']['shortDisplayName']} ({status})\n"

        # 2. ה-MVP של הלילה
        report += "\n<b>🌟 המצטיין (MVP):</b>\n"
        mvp = "נתוני שחקנים בטעינה..."
        max_score = 0
        for event in events:
            for leader_cat in event['competitions'][0].get('leaders', []):
                if leader_cat['name'] == 'points':
                    leader = leader_cat['leaders'][0]
                    score = float(leader['displayValue'])
                    if score > max_score:
                        max_score = score
                        mvp = f"<b>{leader['athlete']['displayName']}</b> עם {leader['displayValue']} נקודות"
        report += mvp + "\n"

        # 3. זווית ישראלית
        report += "\n<b>🇮🇱 הנציגים שלנו:</b>\n"
        israelis = {"Trail Blazers": "דני אבדיה", "Nets": "בן שרף / דני וולף"}
        found = False
        for event in events:
            for team_key, name in israelis.items():
                if team_key in event['name']:
                    report += f"✅ {name} (במדי {team_key})\n"
                    found = True
        if not found: report += "לא שיחקו ישראלים הלילה.\n"

        # 4. רגע היסטורי (לפי 31 במרץ)
        history_text = "ב-1991, מייקל ג'ורדן קלע 27 נקודות והוביל את הבולס לניצחון ה-60 שלהם בעונה."
        report += f"\n<b>📜 רגע היסטורי (31/03):</b>\n{history_text}\n"

        # 5. יציאה ליוטיוב - הקישור שביקשת
        report += f"\n<b>📺 צפה בתקצירי הלילה:</b>\n<a href='{youtube_link}'>לחץ כאן לצפייה ביוטיוב 🎬</a>"

        return report

    except Exception as e:
        return f"⚠️ שגיאה בעיבוד הדשבורד: {str(e)}"

if __name__ == "__main__":
    dashboard = get_nba_dashboard()
    send_telegram(dashboard)
