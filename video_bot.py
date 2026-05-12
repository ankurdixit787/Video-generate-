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
    "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Shiva_Bangalore.jpg/800px-Shiva_Bangalore.jpg",
    "https://images.unsplash.com/photo-1604502840003-88849b293150?q=80&w=1000&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1590080642957-36e2f473855b?q=80&w=1000&auto=format&fit=crop",
    "https://images.pexels.com/photos/7249635/pexels-photo-7249635.jpeg"
]

def download_and_verify_image():
    print("\n[*] Image download process shuru ho raha hai...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    }
    
    attempt = 1
    # Infinite loop as requested by user. Will not break until an image is 100% downloaded and verified.
    while True:
        print(f"\n--- Attempt {attempt} ---")
        for url in IMAGE_URLS:
            print(f"Checking URL: {url[:60]}...")
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    with open(BG_IMAGE_FILE, 'wb') as f:
                        f.write(response.content)
                    
                    # Verify image integrity strictly with PIL
                    try:
                        img = Image.open(BG_IMAGE_FILE)
                        img.verify()  # Throws error if not a valid image
                        print("[+] Success! Image perfectly download aur verify ho gayi hai.")
                        return True # Exit the infinite loop
                    except Exception as e:
                        print(f"[-] File download hui par corrupt thi (Image nahi hai): {e}")
                else:
                    print(f"[-] Server ne block kiya ya error diya: HTTP {response.status_code}")
            except Exception as e:
                print(f"[-] Download fail hua (Connection Error): {e}")
        
        print("[!] Saare URLs is attempt mein fail ho gaye. 5 seconds baad dobara retry kar raha hoon...")
        print("[!] Jab tak valid image nahi aayegi, yeh retry karta rahega!")
        time.sleep(5)
        attempt += 1

async def generate_audio():
    print("\n[*] Audio generate ho rahi hai...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("[+] Audio successfully save ho gayi!")

def create_video():
    print("\n[*] Video banana shuru kar rahe hain...")
    try:
        # Load audio
        audio_clip = AudioFileClip(AUDIO_FILE)
        
        # Load the guaranteed verified image
        image_clip = ImageClip(BG_IMAGE_FILE)
        
        # Process Video
        video_clip = image_clip.set_duration(audio_clip.duration)
        video_clip = video_clip.set_audio(audio_clip)
        
        # Write the result to a file
        video_clip.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
        print(f"\n[+++] YAY! Video '{VIDEO_FILE}' successfully ban gayi hai! Check karein.")
        
    except Exception as e:
        print(f"[-] Video banate waqt MoviePy error aaya: {e}")

async def main():
    # Step 1: 100% guarantee an image is downloaded first
    download_and_verify_image()
    
    # Step 2: Generate Audio
    await generate_audio()
    
    # Step 3: Mix and generate Video
    create_video()

if __name__ == "__main__":
    # Ensure required packages exist (belt and suspenders)
    os.system("pip install moviepy edge-tts")
    asyncio.run(main())
