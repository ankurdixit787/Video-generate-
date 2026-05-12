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
import time

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
# 2. GENERATE AUDIO (TEXT TO SPEECH)
# ==========================================
async def generate_audio():
    print("Generating audio from text...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("Audio generated successfully.")

# ==========================================
# 3. CREATE VIDEO WITH BACKGROUND VISUALS
# ==========================================
def create_video():
    print("Creating video...")
    
    # Download a background image if it doesn't exist
    if not os.path.exists(BG_IMAGE_FILE):
        print("Downloading a sample background image...")
        # Unsplash free spirituality/nature image url
        image_url = "https://images.unsplash.com/photo-1590680425881-2856db32145b?q=80&w=1080"
        urllib.request.urlretrieve(image_url, BG_IMAGE_FILE)

    audio_clip = AudioFileClip(AUDIO_FILE)
    
    # Use ImageClip instead of ColorClip so we can see visuals
    image_clip = ImageClip(BG_IMAGE_FILE)
    
    # Set duration of the image to match the audio length
    video_clip = image_clip.set_duration(audio_clip.duration)
    
    # Attach the generated audio to the video
    video_clip = video_clip.set_audio(audio_clip)
    
    # Export the final video
    video_clip.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
    print(f"Video created successfully: {VIDEO_FILE}")

# ==========================================
# 4. YOUTUBE UPLOAD LOGIC (PLACEHOLDER)
# ==========================================
def upload_to_youtube():
    # Yahan aap apna YouTube upload ka logic daal sakte hain
    print("Ready for YouTube Upload.")
    pass

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    # Generate TTS Audio
    asyncio.run(generate_audio())
    
    # Create Video with visuals and audio
    create_video()
    
    # Uncomment below to enable upload
    # upload_to_youtube()

if __name__ == "__main__":
    main()
