import os
import time
import asyncio
import edge_tts
from moviepy.editor import AudioFileClip, ImageClip

# Safely import or install required libraries
try:
    import requests
except ImportError:
    os.system("pip install requests")
    import requests

try:
    from PIL import Image
except ImportError:
    os.system("pip install Pillow")
    from PIL import Image

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

# Multiple reliable URLs to ensure at least one works
IMAGE_URLS = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/Shiva_Bangalore.jpg/800px-Shiva_Bangalore.jpg",
    "https://cdn.pixabay.com/photo/2020/06/19/08/04/shiva-5316139_1280.jpg"
]

# ==========================================
# TELEGRAM CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # Replace with your Bot Token
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID_HERE"      # Replace with your Chat ID

# ==========================================
# FUNCTIONS
# ==========================================

def download_image():
    for url in IMAGE_URLS:
        try:
            print(f"Trying to download image from {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(BG_IMAGE_FILE, 'wb') as f:
                    f.write(response.content)
                print("Image downloaded successfully!")
                return True
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
    return False

async def generate_audio():
    print("Generating audio using edge-tts...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("Audio generated successfully!")

def create_video():
    print("Creating video...")
    audio_clip = AudioFileClip(AUDIO_FILE)
    image_clip = ImageClip(BG_IMAGE_FILE)
    
    # Set video duration to audio duration
    video = image_clip.set_duration(audio_clip.duration)
    video = video.set_audio(audio_clip)
    
    video.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
    print("Video created successfully!")

def send_image_to_telegram(image_path):
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("Telegram Bot Token is missing. Skipping Telegram upload.")
        return

    print("Sending image to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, 'rb') as photo:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID, 
                "caption": "Har Har Mahadev! Background image successfully generated."
            }
            files = {"photo": photo}
            response = requests.post(url, data=payload, files=files)
            
            if response.status_code == 200:
                print("Image sent to Telegram successfully!")
            else:
                print(f"Failed to send image: {response.text}")
    except Exception as e:
        print(f"Error sending image to Telegram: {e}")

async def main():
    if download_image():
        await generate_audio()
        create_video()
        # Send the downloaded image to Telegram
        send_image_to_telegram(BG_IMAGE_FILE)
    else:
        print("Failed to download any image. Exiting process.")

if __name__ == "__main__":
    asyncio.run(main())
