import os
import asyncio
import edge_tts
from moviepy.editor import AudioFileClip, ColorClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ==========================================
# 1. CONFIGURATION & SCRIPT
# ==========================================
TEXT_SCRIPT = """
Om Namah Shivaya. Dosto, bhagwan shiv ki kripa jis par hoti hai, uska jeevan dhanya ho jata hai.
Shiv ji ko bholenath kaha jata hai kyunki wo apne bhakton ki pukar bahut jaldi sunte hain.
Sawan ke mahine mein shiv ji ki pooja ka vishesh mahatva hota hai. 
Kaha jata hai ki jo bhi bhakt sachhe dil se ek lota jal shivling par arpit karta hai, mahadev uski sabhi manokamna puri karte hain.
Aaj ke is kalyug mein, dhyan aur jap hi sabse bada sahara hai.
Aap jab bhi pareshan ho, bas aankh band karke 'Har Har Mahadev' ka jaap karein.
Bholenath kabhi apne bhakton ko niraash nahi karte. 
Agar aapko yeh video pasand aayi ho, toh kripya is channel ko subscribe karein, aur comment mein 'Har Har Mahadev' zaroor likhein. 
Dhanyawad aur Om Namah Shivaya.
"""

# Free Hindi Female Voice (Edge TTS)
VOICE = "hi-IN-SwaraNeural" 
AUDIO_FILE = "bhakti_audio.mp3"
VIDEO_FILE = "bhakti_video.mp4"

# ==========================================
# 2. GENERATE AUDIO (TEXT TO SPEECH)
# ==========================================
async def generate_audio():
    print("\n🎵 Audio generate ho raha hai...")
    try:
        communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
        await communicate.save(AUDIO_FILE)
        print("✅ Audio successfully generate ho gaya!")
        return True
    except Exception as e:
        print(f"❌ Audio generation mein error: {e}")
        return False

# ==========================================
# 3. GENERATE VIDEO (MOVIEPY)
# ==========================================
def create_video():
    print("\n🎬 Video ban rahi hai...")
    try:
        if not os.path.exists(AUDIO_FILE):
            print("❌ Audio file nahi mili. Video nahi ban sakti.")
            return False

        audio_clip = AudioFileClip(AUDIO_FILE)
        duration = audio_clip.duration
        
        # Orange background (R, G, B) = (255, 165, 0)
        video_clip = ColorClip(size=(1080, 1920), color=(255, 165, 0), duration=duration)
        video_clip = video_clip.set_audio(audio_clip)
        
        video_clip.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
        print("✅ Video successfully ban gayi!")
        return True
    except Exception as e:
        print(f"❌ Video generation mein error: {e}")
        return False

# ==========================================
# 4. YOUTUBE UPLOAD (Optional)
# ==========================================
def upload_to_youtube():
    print("\n🚀 YouTube par upload karne ki koshish kar rahe hain...")
    try:
        if not os.path.exists(VIDEO_FILE):
            print("❌ Video file nahi mili. Upload skip ho raha hai.")
            return

        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        creds = None
        
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('client_secret.json'):
                    print("⚠️ 'client_secret.json' nahi mila! YouTube upload skip kar rahe hain. Video aapki local disk par mil jayegi.")
                    return
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        youtube = build('youtube', 'v3', credentials=creds)

        request_body = {
            'snippet': {
                'title': 'Om Namah Shivaya - Bholenath Status',
                'description': 'Har Har Mahadev. Shiv bhakti status.',
                'tags': ['shiv', 'mahadev', 'bhakti', 'status', 'shorts'],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'private',
                'selfDeclaredMadeForKids': False
            }
        }

        media_file = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part=','.join(request_body.keys()),
            body=request_body,
            media_body=media_file
        )
        response = request.execute()
        print(f"✅ Video successfully uploaded! Video ID: {response['id']}")

    except Exception as e:
        print(f"⚠️ YouTube upload mein error aayi (lekin video ban chuki hai, koi tension nahi): {e}")

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
async def main():
    print("🚀 Script start ho rahi hai...")
    audio_success = await generate_audio()
    
    if audio_success:
        video_success = create_video()
        if video_success:
            upload_to_youtube()
    
    print("\n🎉 Process complete ho gaya!")

if __name__ == "__main__":
    asyncio.run(main())
