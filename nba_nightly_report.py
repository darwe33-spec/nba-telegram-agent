import os
import requests
from datetime import datetime, timedelta

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DASHBOARD_URL = "כאן_הקישור_לדשבורד_שלך" # עדכן את הלינק שלך כאן

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def get_nba_dashboard():
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={yesterday}"
    
    try:
        data = requests.get(url, timeout=20).json()
        events = data.get('events', [])
        if not events: return "🏀 אין משחקים לדיווח מהלילה."

        report = f"📊 <b><u>NBA DAILY DASHBOARD | {datetime.now().strftime('%d/%m/%Y')}</u></b>\n\n"
        
        all_players_stats = []

        # 1. תוצאות וקלעים (2 מכל קבוצה)
        report += "<b>📌 תוצאות וקלעים מובילים:</b>\n"
        for event in events:
            comp = event['competitions'][0]
            teams = comp['competitors']
            
            # זיהוי בית וחוץ
            home = next(t for t in teams if t['homeAway'] == 'home')
            away = next(t for t in teams if t['homeAway'] == 'away')
            
            report += f"• {away['team']['shortDisplayName']} <b>{away['score']}</b> - <b>{home['score']}</b> {home['team']['shortDisplayName']}\n"
            
            # שליפת 2 קלעים מכל קבוצה
            for team in [away, home]:
                team_name = team['team']['shortDisplayName']
                # שליפת לידרים לפי קטגוריית נקודות
                points_leaders = [l for l in comp.get('leaders', []) if l['name'] == 'points']
                if points_leaders:
                    # לוקחים את 2 הראשונים של אותה קבוצה
                    leaders = [athlete for athlete in points_leaders[0]['leaders'] if athlete['athlete']['team']['id'] == team['id']]
                    leaders_text = ", ".join([f"{l['athlete']['shortName']} ({l['displayValue']})" for l in leaders[:2]])
                    report += f"   ▫️ {team_name}: {leaders_text}\n"

            # איסוף נתונים לחישוב MVP (לפי מדד EFF)
            for leader_cat in comp.get('leaders', []):
                for athlete_data in leader_cat.get('leaders', []):
                    player = athlete_data['athlete']
                    # כאן אנחנו שומרים את הנתונים לחישוב ה-MVP הכללי
                    all_players_stats.append({
                        'name': player['displayName'],
                        'points': float(athlete_data['displayValue']),
                        'team': player['team']['shortDisplayName']
                    })

        # 2. ה-MVP של הלילה (השחקן עם הניקוד הגבוה ביותר מכל המשחקים)
        if all_players_stats:
            top_mvp = max(all_players_stats, key=lambda x: x['points'])
            report += f"\n<b>🌟 MVP הלילה:</b>\n{top_mvp['name']} ({top_mvp['team']}) עם {int(top_mvp['points'])} נקודות!\n"

        # 3. הופעה מפתיעה
        # לוגיקה: השחקן שקלע הכי הרבה נקודות והוא לא ה-MVP
        surprises = [p for p in all_players_stats if p['name'] != top_mvp['name']]
        if surprises:
            surprise_player = max(surprises, key=lambda x: x['points'])
            report += f"\n<b>⚡ ההופעה המפתיעה:</b>\n{surprise_player['name']} התעלה מעל הציפיות עם {int(surprise_player['points'])} נק'!\n"

        # 4. זווית ישראלית (אבדיה, שרף, וולף)
        report += "\n<b>🇮🇱 הנציגים שלנו:</b>\n"
        israelis = {"Trail Blazers": "דני אבדיה", "Nets": "בן שרף / דני וולף"}
        found_israeli = False
        for event in events:
            for team_key, name in israelis.items():
                if team_key in event['name']:
                    report += f"✅ {name} שיחק הלילה במדי {team_key}\n"
                    found_israeli = True
        if not found_israeli: report += "לא היו ישראלים על הפרקט הלילה.\n"

        # 5. קישורים
        report += f"\n📺 <a href='https://www.youtube.com/results?search_query=NBA+highlights+{yesterday}'>תקצירי הלילה ביוטיוב 🎬</a>"
        report += f"\n💻 <a href='{DASHBOARD_URL}'>לדשבורד המלא 🖥️</a>"

        return report

    except Exception as e:
        return f"⚠️ שגיאה בבניית הדשבורד: {str(e)}"

if __name__ == "__main__":
    send_telegram(get_nba_dashboard())
