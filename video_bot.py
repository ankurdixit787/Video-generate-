import os
import asyncio
import edge_tts
from moviepy.editor import AudioFileClip, ColorClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import time

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
    print("🔊 Audio generate ho raha hai...")
    try:
        communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
        await communicate.save(AUDIO_FILE)
        print("✅ Audio successfully save ho gaya: ", AUDIO_FILE)
        return True
    except Exception as e:
        print(f"❌ Audio generation mein error: {e}")
        return False

# ==========================================
# 3. GENERATE VIDEO
# ==========================================
def generate_video():
    print("🎬 Video generate ho rahi hai...")
    try:
        # Load Audio
        audio_clip = AudioFileClip(AUDIO_FILE)
        duration = audio_clip.duration
        
        # Create Orange Background (1080x1920 for Shorts)
        video_clip = ColorClip(size=(1080, 1920), color=(255, 165, 0), duration=duration)
        
        # Set Audio to Video
        video_clip = video_clip.set_audio(audio_clip)
        
        # Export Video (using libx264 for better compatibility)
        video_clip.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
        print("✅ Video successfully ban gayi: ", VIDEO_FILE)
        return True
    except Exception as e:
        print(f"❌ Video generation mein error: {e}")
        return False

# ==========================================
# 4. YOUTUBE UPLOAD (Optional)
# ==========================================
def upload_to_youtube():
    print("☁️ YouTube upload attempt kar rahe hain...")
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    creds = None
    try:
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('client_secret.json'):
                    print("⚠️ 'client_secret.json' nahi mili. YouTube upload skip kar rahe hain.")
                    return
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        youtube = build('youtube', 'v3', credentials=creds)
        
        request_body = {
            'snippet': {
                'title': 'Har Har Mahadev - Shiv Bhakti #shorts',
                'description': 'Om Namah Shivaya. Bholenath ki kripa sab par bani rahe.',
                'tags': ['shiv', 'mahadev', 'bhakti', 'shorts', 'hindu'],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'public' # change to private if testing
            }
        }
        
        media_file = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media_file
        )
        response = request.execute()
        print(f"✅ Video successfully uploaded to YouTube! Video ID: {response.get('id')}")
        
    except Exception as e:
        print(f"⚠️ YouTube upload failed: {e}\n(Lekin video locally aapke PC me {VIDEO_FILE} ke naam se save ho chuki hai!)")

# ==========================================
# 5. MAIN EXECUTION LOOP
# ==========================================
async def main():
    video_success = False
    
    # Jab tak video successfully ban nahi jati, script rukegi nahi
    while not video_success:
        print("\n--- Process Start ---")
        
        # Step 1: Generate Audio
        if not os.path.exists(AUDIO_FILE):
            audio_success = await generate_audio()
            if not audio_success:
                print("Audio fail hua, 3 second baad retry kar rahe hain...")
                await asyncio.sleep(3)
                continue
        else:
            print("✅ Audio file pehle se maujud hai.")
            
        # Step 2: Generate Video
        if not os.path.exists(VIDEO_FILE):
            video_success = generate_video()
            if not video_success:
                print("Video creation fail hua, 3 second baad retry kar rahe hain...")
                time.sleep(3)
                continue
        else:
            print("✅ Video file pehle se maujud hai.")
            video_success = True
            
    print("\n🎉 Video successfully create ho chuki hai! Ab video banane ka process ruk raha hai.")
    
    # Step 3: Upload to YouTube (Agar error aaya to skip ho jayega par script fail nahi hogi)
    upload_to_youtube()

if __name__ == "__main__":
    asyncio.run(main())
