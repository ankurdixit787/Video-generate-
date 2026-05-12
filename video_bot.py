import os
import time
import asyncio
import edge_tts
import urllib.request
from urllib.request import Request, urlopen
from moviepy.editor import AudioFileClip, ImageClip

# Importing PIL (Pillow) to strictly verify the downloaded image
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

# Reliable image URL for Lord Shiva
IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Shiva_Bangalore.jpg/800px-Shiva_Bangalore.jpg"

# ==========================================
# 2. STRICT IMAGE DOWNLOADER & VERIFIER
# ==========================================
def download_and_verify_image():
    print("Image download shuru kar rahe hain...")
    attempt = 1
    
    # Jab tak image theek se nahi aa jati, loop chalta rahega
    while True:
        try:
            print(f"Attempt {attempt}: Downloading image...")
            
            # Added strict browser headers so Wikimedia doesn't block us
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
            }
            req = Request(IMAGE_URL, headers=headers)
            
            with urlopen(req) as response, open(BG_IMAGE_FILE, 'wb') as out_file:
                data = response.read()
                out_file.write(data)
            
            # Strict Check: Verifying if the file is a REAL image
            try:
                img = Image.open(BG_IMAGE_FILE)
                img.verify() # Verifies if it's broken/corrupt without loading the whole thing
                img.close()  # Close the file correctly
                print(f"Success! Image proper aa gayi aur verify ho gayi attempt {attempt} mein.")
                break # Image verified, breaking the infinite loop
            except Exception as img_err:
                print(f"Attempt {attempt} failed: File download hui par corrupt hai (Real image nahi hai). Retrying...")
                
        except Exception as e:
            print(f"Attempt {attempt} failed (Network/Server error): {e}. Retrying in 2 seconds...")
        
        attempt += 1
        time.sleep(2) # Wait 2 seconds before requesting again so we don't get IP banned

# ==========================================
# 3. TEXT-TO-SPEECH GENERATION
# ==========================================
async def generate_audio():
    print("Audio generate ho raha hai...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("Audio successfully generate ho gaya!")

# ==========================================
# 4. VIDEO GENERATION
# ==========================================
def create_video():
    print("Video creation shuru kar rahe hain...")
    try:
        audio_clip = AudioFileClip(AUDIO_FILE)
        audio_duration = audio_clip.duration
        
        # Yahan tak aane ka matlab hai image pakka theek hai!
        image_clip = ImageClip(BG_IMAGE_FILE)
        
        # Resizing properly so it doesn't crash
        w, h = image_clip.size
        target_ratio = 1080 / 1920
        current_ratio = w / h
        
        if current_ratio > target_ratio:
            new_w = int(h * target_ratio)
            x_center = w / 2
            image_clip = image_clip.crop(x1=x_center-new_w/2, y1=0, x2=x_center+new_w/2, y2=h)
        
        image_clip = image_clip.resize(height=1920, width=1080)
        
        video = image_clip.set_duration(audio_duration)
        video = video.set_audio(audio_clip)
        
        video.write_videofile(
            VIDEO_FILE, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            threads=4
        )
        print("Video successfully ban gayi hai image ke sath! Check: bhakti_video.mp4")
        
        audio_clip.close()
        image_clip.close()
        video.close()
        
    except Exception as e:
        print(f"Video banate waqt error aayi: {e}")

# ==========================================
# 5. MAIN PIPELINE
# ==========================================
def main():
    # 1. Jab tak image nahi aayegi, ye function aage nahi badhne dega
    download_and_verify_image()
    
    # 2. Audio banega
    asyncio.run(generate_audio())
    
    # 3. Video banega 100% guarantee image ke sath
    create_video()
    
    print("Poora process complete ho gaya. Video image ke sath ready hai!")

if __name__ == "__main__":
    main()
