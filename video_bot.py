import os
import asyncio
import edge_tts
import urllib.request
from moviepy.editor import AudioFileClip, ImageClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleRequest
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

VOICE = "hi-IN-SwaraNeural" 
AUDIO_FILE = "bhakti_audio.mp3"
VIDEO_FILE = "bhakti_video.mp4"
BG_IMAGE_FILE = "background_image.jpg"

# Reliable direct image URL (Lord Shiva Statue on Wikimedia Commons)
IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Shiva_Bangalore.jpg/800px-Shiva_Bangalore.jpg"

# ==========================================
# 2. AUDIO GENERATION (TTS)
# ==========================================
async def generate_audio():
    print("Audio generate ho raha hai...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("Audio successfully save ho gaya:", AUDIO_FILE)

# ==========================================
# 3. IMAGE DOWNLOAD (WITH USER-AGENT FIX)
# ==========================================
def download_image():
    print("Image download ho rahi hai...")
    try:
        # Wikipedia/Wikimedia blocks default python user agents. We must pass a standard web browser User-Agent.
        req = urllib.request.Request(
            IMAGE_URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        with urllib.request.urlopen(req) as response, open(BG_IMAGE_FILE, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print("Image successfully download ho gayi:", BG_IMAGE_FILE)
    except Exception as e:
        print(f"Error downloading image: {e}")
        raise

# ==========================================
# 4. VIDEO CREATION
# ==========================================
def create_video():
    print("Video create ho rahi hai...")
    try:
        audio_clip = AudioFileClip(AUDIO_FILE)
        image_clip = ImageClip(BG_IMAGE_FILE)
        
        video_clip = image_clip.set_duration(audio_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)
        
        video_clip.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
        print("Video successfully ban gayi:", VIDEO_FILE)
    except Exception as e:
        print(f"Video banane mein error aayi: {e}")

# ==========================================
# 5. MAIN FUNCTION
# ==========================================
def main():
    # 1. Download image first with proper headers
    download_image()
    
    # 2. Generate Audio
    asyncio.run(generate_audio())
    
    # 3. Combine to Video
    create_video()
    print("Process complete! Check", VIDEO_FILE)

if __name__ == "__main__":
    main()
