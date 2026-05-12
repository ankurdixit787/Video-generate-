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
    print("🎵 Audio generate ho raha hai...")
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
def generate_video():
    print("🎥 Video generate ho raha hai...")
    try:
        if not os.path.exists(AUDIO_FILE):
            print("❌ Audio file nahi mili, video generate nahi ho sakta.")
            return False
            
        # Load Audio
        audio_clip = AudioFileClip(AUDIO_FILE)
        
        # Create a blank Orange Color Clip for the duration of the audio (Vertical Shorts format)
        # Orange color RGB: 255, 165, 0
        video_clip = ColorClip(size=(1080, 1920), color=(255, 165, 0))
        video_clip = video_clip.set_duration(audio_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)
        
        # Export Video
        video_clip.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
        print("✅ Video successfully generate ho gaya!")
        return True
    except Exception as e:
        print(f"❌ Video generation mein error: {e}")
        return False

# ==========================================
# 4. YOUTUBE UPLOAD (GOOGLE API)
# ==========================================
def upload_to_youtube():
    print("☁️ YouTube par upload karne ki koshish kar rahe hain...")
    client_secrets_file = "client_secret.json"
    
    if not os.path.exists(client_secrets_file):
        print("⚠️ 'client_secret.json' file nahi mili! YouTube upload skip kar rahe hain.")
        print("💡 Note: Aapki video properly ban chuki hai aur local system par save ho gayi hai.")
        return

    try:
        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
        credentials = flow.run_local_server(port=0)
        youtube = build('youtube', 'v3', credentials=credentials)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "categoryId": "22",
                    "description": "Har Har Mahadev! Bhakti Status shorts.",
                    "title": "Bholenath Status | Om Namah Shivaya | Har Har Mahadev"
                },
                "status": {
                    "privacyStatus": "private" # Default private rakha hai testing ke liye
                }
            },
            media_body=MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True)
        )
        response = request.execute()
        print(f"✅ Video successfully YouTube par upload ho gayi! Video ID: {response.get('id')}")
    except Exception as e:
        print(f"❌ YouTube upload mein error aayi: {e}")

# ==========================================
# 5. MAIN EXECUTION (NON-STOP)
# ==========================================
async def main():
    print("🚀 Script start ho rahi hai...")
    audio_success = await generate_audio()
    
    if audio_success:
        video_success = generate_video()
        if video_success:
            upload_to_youtube()
            
    print("🎉 Process complete ho gaya! Script bina crash huye chal gayi.")

if __name__ == "__main__":
    # Handle async loop gracefully
    asyncio.run(main())
