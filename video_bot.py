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
# Yahan apna token aur chat ID dalein
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"

def send_image_to_telegram(image_path):
    print(f"Sending {image_path} to Telegram...")
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("Please update TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to send images.")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, 'rb') as photo:
            payload = {'chat_id': TELEGRAM_CHAT_ID}
            files = {'photo': photo}
            response = requests.post(url, data=payload, files=files)
            if response.status_code == 200:
                print("Image sent to Telegram successfully! Check your chat.")
            else:
                print(f"Failed to send image. Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error sending image to Telegram: {e}")

async def generate_audio():
    print("Generating audio with edge-tts...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print(f"Audio saved to {AUDIO_FILE}")

def download_background_image():
    print("Downloading background image...")
    # Devotional/Shiv image URL for sample
    image_url = "https://images.unsplash.com/photo-1604052382103-2415170d1887?q=80&w=1920&auto=format&fit=crop"
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(BG_IMAGE_FILE, "wb") as f:
                f.write(response.content)
            print("Background image downloaded successfully.")
            
            # Send the image to Telegram to verify it downloaded correctly
            send_image_to_telegram(BG_IMAGE_FILE)
            
            return True
        else:
            print("Failed to download background image.")
            return False
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False

def create_video():
    print("Creating video...")
    try:
        audio_clip = AudioFileClip(AUDIO_FILE)
        # Load image and set duration to match audio
        image_clip = ImageClip(BG_IMAGE_FILE).set_duration(audio_clip.duration)
        
        # Set audio to image
        video = image_clip.set_audio(audio_clip)
        
        # Write to file (fps=24 is standard)
        video.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
        print(f"Video successfully created and saved as {VIDEO_FILE}")
    except Exception as e:
        print(f"Error creating video: {e}")

def main():
    # 1. Download Background Image and send to Telegram
    if not download_background_image():
        print("Skipping video creation because image download failed.")
        return
    
    # 2. Generate Audio
    asyncio.run(generate_audio())
    
    # 3. Create Video
    create_video()

if __name__ == "__main__":
    main()
