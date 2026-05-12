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

# ==========================================
# 2. TELEGRAM CREDENTIALS
# ==========================================
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# ==========================================
# 3. FUNCTIONS WITH DEBUGGING
# ==========================================

async def generate_audio():
    print("[Debug] Starting Audio Generation...")
    try:
        communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
        await communicate.save(AUDIO_FILE)
        print(f"[Debug] Audio saved successfully as {AUDIO_FILE}")
        return True
    except Exception as e:
        print(f"[Error] Failed to generate audio: {e}")
        return False

def download_image():
    print("[Debug] Starting Image Download...")
    # Reliable high quality religious/nature placeholder from Unsplash
    image_url = "https://images.unsplash.com/photo-1590086782792-42dd2350140d?ixlib=rb-4.0.3&auto=format&fit=crop&w=1080&q=80"
    try:
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(BG_IMAGE_FILE, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"[Debug] Image downloaded successfully to {BG_IMAGE_FILE}")
            
            # Verify if it's a valid image using PIL
            try:
                img = Image.open(BG_IMAGE_FILE)
                img.verify()
                print(f"[Debug] Image verification successful. Format: {img.format}, Size: {img.size}")
                return True
            except Exception as img_err:
                print(f"[Error] Downloaded file is not a valid image: {img_err}")
                return False
        else:
            print(f"[Error] Failed to download image. HTTP Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"[Error] Exception during image download: {e}")
        return False

def send_image_to_telegram():
    print(f"[Debug] Sending {BG_IMAGE_FILE} to Telegram...")
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("[Warning] Telegram Bot Token not set! Skipping sending to Telegram.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(BG_IMAGE_FILE, 'rb') as img:
            payload = {'chat_id': TELEGRAM_CHAT_ID}
            files = {'photo': img}
            response = requests.post(url, data=payload, files=files)
            if response.status_code == 200:
                print("[Debug] Image successfully sent to Telegram.")
            else:
                print(f"[Error] Failed to send to Telegram. Response: {response.text}")
    except Exception as e:
        print(f"[Error] Exception sending to Telegram: {e}")

def create_video():
    print("[Debug] Starting Video Generation...")
    try:
        if not os.path.exists(AUDIO_FILE):
            print(f"[Error] Audio file {AUDIO_FILE} not found!")
            return
        if not os.path.exists(BG_IMAGE_FILE):
            print(f"[Error] Image file {BG_IMAGE_FILE} not found!")
            return

        print("[Debug] Loading AudioClip...")
        audio_clip = AudioFileClip(AUDIO_FILE)
        duration = audio_clip.duration
        print(f"[Debug] Audio duration is: {duration} seconds")

        print("[Debug] Loading ImageClip...")
        video_clip = ImageClip(BG_IMAGE_FILE)
        
        print("[Debug] Configuring ImageClip duration and FPS...")
        # IMPORTANT: If duration and FPS are not set, ImageClip renders as empty/black frames.
        video_clip = video_clip.set_duration(duration)
        
        print("[Debug] Setting Audio to Video...")
        video_clip = video_clip.set_audio(audio_clip)

        print("[Debug] Writing video file (this may take some time)...")
        # Specifying fps is very important for an ImageClip to render correctly
        video_clip.write_videofile(
            VIDEO_FILE, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            logger="bar"
        )
        print("[Debug] Video generated successfully!")
        
    except Exception as e:
        print(f"[Error] An unexpected error occurred during video creation: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print("\n=== Script Started ===")
    
    audio_success = await generate_audio()
    if not audio_success:
        print("[Error] Stopping script due to Audio Generation failure.")
        return

    image_success = download_image()
    if not image_success:
        print("[Error] Stopping script due to Image Download failure.")
        return
        
    send_image_to_telegram()
    
    create_video()
    
    print("=== Script Finished ===\n")

if __name__ == "__main__":
    asyncio.run(main())
