import os
import asyncio
import edge_tts
import urllib.request
from urllib.request import Request, urlopen
from moviepy.editor import AudioFileClip, ImageClip, ColorClip
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

IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d2/Shiva_Statue_in_Rishikesh.jpg/800px-Shiva_Statue_in_Rishikesh.jpg"

async def generate_audio():
    print("Generating audio with Edge TTS...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("Audio generated successfully.")

def download_image():
    print(f"Downloading background image from: {IMAGE_URL}")
    req = Request(
        IMAGE_URL, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
    )
    try:
        with urlopen(req) as response, open(BG_IMAGE_FILE, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        
        # Check if file actually downloaded properly and is not an empty/corrupted file
        if os.path.exists(BG_IMAGE_FILE) and os.path.getsize(BG_IMAGE_FILE) > 5000:
            print("Image successfully downloaded and verified!")
            return True
        else:
            print("Downloaded image is corrupted or too small.")
            return False
    except Exception as e:
        print(f"Failed to download image. Error: {e}")
        return False

def create_video():
    print("Starting video creation...")
    audio_clip = AudioFileClip(AUDIO_FILE)
    
    # Verify if image exists and is valid before passing to MoviePy
    if os.path.exists(BG_IMAGE_FILE) and os.path.getsize(BG_IMAGE_FILE) > 5000:
        try:
            image_clip = ImageClip(BG_IMAGE_FILE)
            video_clip = image_clip.set_duration(audio_clip.duration)
        except Exception as e:
            print(f"MoviePy couldn't process the image. Error: {e}")
            print("Using a black background fallback.")
            video_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_duration(audio_clip.duration)
    else:
        print("Valid image not found. Using a black background fallback.")
        video_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_duration(audio_clip.duration)

    video_clip = video_clip.set_audio(audio_clip)
    
    print("Writing video file...")
    video_clip.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
    print("Video created successfully as", VIDEO_FILE)

def main():
    asyncio.run(generate_audio())
    download_image()
    create_video()

if __name__ == "__main__":
    main()
