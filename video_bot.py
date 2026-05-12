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

# Telegram Credentials (Replace with your own before running)
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# Multiple reliable URLs to ensure at least one works
IMAGE_URLS = [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Shiva_Bangalore.jpg/800px-Shiva_Bangalore.jpg",
    "https://cdn.pixabay.com/photo/2023/02/13/06/13/lord-shiva-7786524_960_720.jpg"
]

def download_image():
    for url in IMAGE_URLS:
        try:
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(BG_IMAGE_FILE, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"Image successfully downloaded from {url}")
                
                # Optional: Verify if it's a valid image using PIL
                try:
                    img = Image.open(BG_IMAGE_FILE)
                    img.verify() 
                    print("Image verification passed.")
                    return True
                except Exception as verify_err:
                    print(f"Image verification failed for {url}: {verify_err}")
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
    return False

def send_image_to_telegram(image_path):
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("Telegram Bot Token not configured. Skipping Telegram debug send.")
        return

    print("Sending image to Telegram for debugging...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, 'rb') as img:
            payload = {'chat_id': TELEGRAM_CHAT_ID}
            files = {'photo': img}
            response = requests.post(url, data=payload, files=files)
            if response.status_code == 200:
                print("Image successfully sent to Telegram!")
            else:
                print(f"Failed to send image to Telegram: {response.text}")
    except Exception as e:
        print(f"Error while sending to Telegram: {e}")

async def generate_audio():
    print("Generating audio via Edge TTS...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("Audio generated successfully.")

def create_video():
    print("Creating video...")
    try:
        audio_clip = AudioFileClip(AUDIO_FILE)
        image_clip = ImageClip(BG_IMAGE_FILE)
        
        # Set the duration of the image clip to match the audio
        video_clip = image_clip.set_duration(audio_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)
        
        video_clip.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
        print("Video created successfully: ", VIDEO_FILE)
    except Exception as e:
        print(f"Error creating video: {e}")

async def main():
    if download_image():
        # Debug: Send downloaded image to Telegram
        send_image_to_telegram(BG_IMAGE_FILE)
        
        await generate_audio()
        create_video()
    else:
        print("Failed to download background image. Aborting.")

if __name__ == "__main__":
    asyncio.run(main())
