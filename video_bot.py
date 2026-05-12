import os
import asyncio
import edge_tts
from moviepy.editor import AudioFileClip, ColorClip
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

# ==========================================
# 1. CONFIGURATION & SCRIPT
# ==========================================
# 1 minute se bada video banane ke liye script thodi lambi honi chahiye (approx 150 words)
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

# Free Hindi Female Voice (Edge TTS)
VOICE = "hi-IN-SwaraNeural" 
AUDIO_FILE = "bhakti_audio.mp3"
VIDEO_FILE = "bhakti_video.mp4"

# ==========================================
# 2. GENERATE AUDIO (TEXT TO SPEECH)
# ==========================================
async def generate_audio():
    print("1. Audio generate ho rahi hai (Free Edge TTS)...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("-> Audio successfully ban gayi!")

# ==========================================
# 3. CREATE VIDEO (MOVIEPY)
# ==========================================
def create_video():
    print("\n2. Video ban rahi hai...")
    audio = AudioFileClip(AUDIO_FILE)
    duration = audio.duration

    # Bhagwa (Orange) background color video (1920x1080) taaki error na aaye bina images ke
    bg_clip = ColorClip(size=(1920, 1080), color=(255, 153, 51), duration=duration)
    
    video = bg_clip.set_audio(audio)
    
    # Video save karein
    video.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac", logger=None)
    print(f"-> Video ready hai! ({VIDEO_FILE})")

# ==========================================
# 4. UPLOAD TO YOUTUBE
# ==========================================
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def upload_to_youtube():
    print("\n3. YouTube par upload ho raha hai...")
    if not os.path.exists("client_secrets.json"):
        print("ERROR: 'client_secrets.json' file nahi mili!")
        print("Kripya Google Cloud Console se YouTube Data API v3 enable karein aur OAuth credentials download karke is folder mein rakhein.")
        return

    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    credentials = flow.run_local_server(port=0)
    youtube = build("youtube", "v3", credentials=credentials)

    request_body = {
        "snippet": {
            "categoryId": "22",
            "title": "Bhagwan Shiv Ki Mahima 🙏 | Har Har Mahadev | Hindi Bhakti Status",
            "description": "Om Namah Shivaya! Yeh ek bhakti video hai. Agar pasand aaye toh Like aur Subscribe zaroor karein.",
            "tags": ["bhakti", "shiv", "har har mahadev", "hindi", "devotional"]
        },
        "status": {
            "privacyStatus": "public" # Ya 'private' rakh sakte hain starting mein
        }
    }

    media_file = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )
    response = request.execute()
    print(f"-> Success! Video Uploaded. Video ID: {response['id']}")

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    # 1. Audio banayein
    asyncio.run(generate_audio())
    
    # 2. Video banayein
    create_video()
    
    # 3. YouTube Upload (Jab client_secrets.json ready ho tab isko uncomment karein)
    # upload_to_youtube()
