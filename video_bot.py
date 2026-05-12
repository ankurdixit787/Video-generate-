import os
import time
import asyncio
import edge_tts
import traceback
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
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

# ==========================================
# 3. FUNCTIONS
# ==========================================

def download_and_prepare_image():
    print("[DEBUG] Starting image download...")
    # Using a reliable image URL (Unsplash nature/sunset as placeholder)
    url = "https://images.unsplash.com/photo-1604500858850-9830538f95fb?q=80&w=1080&auto=format&fit=crop"
    
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(BG_IMAGE_FILE, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print("[DEBUG] Image downloaded. Now fixing resolution and format...")
            
            # FIX: Open with PIL, convert to RGB (removes alpha channel which causes issues),
            # and resize to exactly 1080x1920 (ensures width/height are even numbers for x264 codec)
            img = Image.open(BG_IMAGE_FILE)
            img = img.convert("RGB")
            img = img.resize((1080, 1920), Image.LANCZOS)
            img.save(BG_IMAGE_FILE)
            print("[DEBUG] Image prepared successfully (1080x1920, RGB).")
            return True
        else:
            print(f"[ERROR] Failed to download image. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception during image download/preparation: {e}")
        return False

def send_image_to_telegram():
    print("[DEBUG] Sending image to Telegram...")
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("[DEBUG] Telegram Token not set. Skipping Telegram upload.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(BG_IMAGE_FILE, 'rb') as photo:
            payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": "Background Image Check"}
            files = {"photo": photo}
            response = requests.post(url, data=payload, files=files)
            if response.status_code == 200:
                print("[DEBUG] Image successfully sent to Telegram.")
            else:
                print(f"[ERROR] Telegram send failed: {response.text}")
    except Exception as e:
        print(f"[ERROR] Failed to send image to Telegram: {e}")

async def generate_audio():
    print("[DEBUG] Generating AI Voiceover...")
    try:
        communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
        await communicate.save(AUDIO_FILE)
        print("[DEBUG] Audio generation successful.")
        return True
    except Exception as e:
        print(f"[ERROR] Audio generation failed: {e}")
        return False

def create_video():
    print("[DEBUG] Starting video creation process...")
    try:
        if not os.path.exists(AUDIO_FILE):
            print("[ERROR] Audio file not found. Cannot create video.")
            return
        if not os.path.exists(BG_IMAGE_FILE):
            print("[ERROR] Background image not found. Cannot create video.")
            return
            
        print("[DEBUG] Loading AudioFileClip...")
        audio_clip = AudioFileClip(AUDIO_FILE)
        audio_duration = audio_clip.duration
        print(f"[DEBUG] Audio duration: {audio_duration} seconds.")
        
        print("[DEBUG] Loading ImageClip...")
        # FIX: Ensure we explicitly set FPS on the image clip and use a proper duration
        video_clip = ImageClip(BG_IMAGE_FILE)
        video_clip = video_clip.set_duration(audio_duration)
        video_clip = video_clip.set_audio(audio_clip)
        video_clip = video_clip.set_fps(24) # CRITICAL FIX for black screen/missing image
        
        print("[DEBUG] Writing final video file...")
        video_clip.write_videofile(
            VIDEO_FILE,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset="ultrafast",
            logger=None # Disable logger to keep console clean, or remove this to see moviepy progress bar
        )
        print(f"\n[SUCCESS] Video created successfully! Saved as {VIDEO_FILE}")
        
        # Cleanup memory
        audio_clip.close()
        video_clip.close()
        
    except Exception as e:
        print("[CRITICAL ERROR] Failed to create video. Traceback below:")
        traceback.print_exc()

# ==========================================
# 4. MAIN EXECUTION
# ==========================================
async def main():
    print("--- Starting Video Bot ---")
    
    # Step 1: Download & Prepare Image
    if not download_and_prepare_image():
        print("[ERROR] Stopping process because image failed.")
        return
        
    # Step 2: Send Image to Telegram for debugging
    send_image_to_telegram()
    
    # Step 3: Generate Audio
    if not await generate_audio():
        print("[ERROR] Stopping process because audio failed.")
        return
        
    # Step 4: Combine into Video
    create_video()
    
    print("--- Process Complete ---")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
