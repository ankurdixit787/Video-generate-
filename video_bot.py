import os
import asyncio
import edge_tts
import urllib.request
from moviepy.editor import AudioFileClip, ImageClip
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

VOICE = "hi-IN-SwaraNeural" 
AUDIO_FILE = "bhakti_audio.mp3"
VIDEO_FILE = "bhakti_video.mp4"
BG_IMAGE_FILE = "background_image.jpg"

# Ek achhi nature/temple type image ka direct URL
IMAGE_URL = "https://images.unsplash.com/photo-1544928147-79a2dbc1f389?q=80&w=1920&auto=format&fit=crop"

# ==========================================
# 2. GENERATE AUDIO (TEXT TO SPEECH)
# ==========================================
async def generate_audio():
    print("Audio generate ho rahi hai...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("Audio successfully save ho gayi!")

# ==========================================
# 3. DOWNLOAD BACKGROUND IMAGE
# ==========================================
def download_image():
    print("Background image download ho rahi hai...")
    try:
        # User-Agent header zaroori hai taaki image server block na kare
        req = urllib.request.Request(IMAGE_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(BG_IMAGE_FILE, 'wb') as out_file:
            out_file.write(response.read())
        print("Image download complete!")
    except Exception as e:
        print(f"Image download me error aayi: {e}")

# ==========================================
# 4. CREATE VIDEO
# ==========================================
def create_video():
    print("Video ban rahi hai...")
    try:
        # Load audio
        audio = AudioFileClip(AUDIO_FILE)
        
        # Load image (ab yeh actual image dikhayega)
        video = ImageClip(BG_IMAGE_FILE)
        
        # Video ki lambai audio ke barabar set karein
        video = video.set_duration(audio.duration)
        
        # Audio ko video ke saath merge karein
        video = video.set_audio(audio)
        
        # Video ko save karein (fps=24 dena bahut zaroori hai warna image properly render nahi hoti)
        video.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
        print(f"Video successfully ban gayi hai: {VIDEO_FILE}")
    except Exception as e:
        print(f"Video banate waqt error aayi: {e}")

# ==========================================
# MAIN FUNCTION
# ==========================================
def main():
    # Pehle audio banayenge
    asyncio.run(generate_audio())
    
    # Phir image download karenge
    download_image()
    
    # Uske baad un dono ko jod kar video banayenge
    create_video()

if __name__ == "__main__":
    main()
