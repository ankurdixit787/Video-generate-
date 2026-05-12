import os
import asyncio
import edge_tts
from moviepy.editor import AudioFileClip, ColorClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# ==========================================
# 1. CONFIGURATION & SCRIPT
# ==========================================
# 1 minute se bada video banane ke liye script thodi lambi honi chahiye (approx 150 words)
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
    print("Generating Audio...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print(f"Audio saved successfully as {AUDIO_FILE}")

# ==========================================
# 3. CREATE VIDEO
# ==========================================
def generate_video():
    print("Generating Video...")
    audio_clip = AudioFileClip(AUDIO_FILE)
    
    # Vertical Shorts Resolution (1080x1920) with a simple orange color background
    video_clip = ColorClip(size=(1080, 1920), color=(255, 153, 51), duration=audio_clip.duration)
    video_clip = video_clip.set_audio(audio_clip)
    
    video_clip.write_videofile(
        VIDEO_FILE,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )
    print(f"Video saved successfully as {VIDEO_FILE}")

# ==========================================
# 4. UPLOAD TO YOUTUBE
# ==========================================
def upload_to_youtube():
    CLIENT_SECRETS_FILE = "client_secret.json"
    
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"Error: '{CLIENT_SECRETS_FILE}' file not found. Skipping YouTube upload.")
        return

    print("Uploading to YouTube...")
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server(port=0)
    youtube = build('youtube', 'v3', credentials=credentials)

    request_body = {
        'snippet': {
            'title': 'Har Har Mahadev | Bhakti Video',
            'description': 'Om Namah Shivaya! Bholenath bhakti video. #shorts #mahadev #bhakti #bholenath',
            'tags': ['mahadev', 'bhakti', 'shiv', 'shorts', 'bholenath'],
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'private' # Set 'public' when you are ready to publish
        }
    }

    media_file = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )
    response = request.execute()
    print("Video uploaded successfully! Video ID:", response.get('id'))

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
def main():
    # Run Audio Generation (Async)
    asyncio.run(generate_audio())
    
    # Run Video Generation
    generate_video()
    
    # Upload to YouTube
    upload_to_youtube()

if __name__ == "__main__":
    main()
