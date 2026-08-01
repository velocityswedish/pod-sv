"""
Set the Velocity Swedish Podcast YouTube channel description (About section).
"""
import os, json
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

CHANNEL_DESCRIPTION = "🎙️ Velocity Swedish Podcast - Lär dig svenska på ett naturligt sätt\n\nVälkommen till den tvåspråkiga podden för att lära dig svenska. Varje avsnitt är en enkel och avslappnad konversation mellan Astrid och Erik, på A2-nivå - perfekt för nybörjare.\n\nWelcome to the bilingual Swedish podcast for learning Swedish naturally. Every episode is a simple, relaxed conversation between Astrid and Erik at A2 level - perfect for beginners.\n\n📚 WHAT YOU'LL GET:\n• Daily bilingual conversations (Swedish + English)\n• Natural pronunciation from native speakers\n• Practical vocabulary for everyday life\n• Short, easy-to-follow episodes\n\n🇸🇪 How to use this podcast:\n1. Listen to the Swedish, try to understand\n2. Check the English translation\n3. Repeat the phrases out loud\n4. Listen again the next day - it gets easier!\n\n🔔 Subscribe and turn on notifications so you never miss a lesson.\n\n📅 New episodes every day!\n\n#LearnSwedish #SwedishPodcast #Bilingual #LanguageLearning"


def _get_creds():
    cid = os.getenv("YT_CLIENT_ID")
    csecret = os.getenv("YT_CLIENT_SECRET")
    refresh = os.getenv("YT_REFRESH_TOKEN")
    if cid and csecret and refresh:
        return Credentials(None, refresh_token=refresh,
                           token_uri="https://oauth2.googleapis.com/token",
                           client_id=cid, client_secret=csecret)
    tok_file = Path(__file__).parent / "token.json"
    candidates = [
        tok_file,
        Path(r'C:\Users\kreg9\Downloads\kreggscode\open code\bots\youtube refresh tokens bot\token_Vheelocity Swedish podcast.json'),
    ]
    for c in candidates:
        if c.exists():
            tok = json.load(open(c, encoding='utf-8'))
            return Credentials(None, refresh_token=tok['refresh_token'],
                               token_uri="https://oauth2.googleapis.com/token",
                               client_id=tok['client_id'], client_secret=tok['client_secret'])
    raise ValueError("No YouTube credentials found")


def main():
    creds = _get_creds()
    creds.refresh(Request())
    service = build("youtube", "v3", credentials=creds)
    channels = service.channels().list(part="brandingSettings", mine=True).execute()
    channel_id = channels["items"][0]["id"]
    branding = dict(channels["items"][0]["brandingSettings"])
    branding.setdefault("channel", {})
    branding["channel"]["description"] = CHANNEL_DESCRIPTION
    body = {"id": channel_id, "brandingSettings": branding}
    resp = service.channels().update(part="brandingSettings", body=body).execute()
    new_desc = resp["brandingSettings"]["channel"].get("description", "")
    print("Channel:", channel_id)
    print("Description set to", len(new_desc), "chars")


if __name__ == "__main__":
    main()
