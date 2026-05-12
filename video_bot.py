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

# 100% Reliable direct image URL (Lord Shiva Statue on Wikimedia Commons)
IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Shiva_statue_at_Murudeshwara.jpg/800px-Shiva_statue_at_Murudeshwara.jpg"

# ==========================================
# 2. AUDIO GENERATION
# ==========================================
async def generate_audio():
    print("🎵 Audio generate ho rahi hai...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("✅ Audio successfully save ho gayi!")

# ==========================================
# 3. VIDEO GENERATION
# ==========================================
def download_image():
    print("🖼️ Background image download ho rahi hai...")
    # User-Agent header add kiya hai taaki download block na ho
    req = urllib.request.Request(IMAGE_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(BG_IMAGE_FILE, 'wb') as out_file:
        out_file.write(response.read())
    print("✅ Image download ho gayi!")

def create_video():
    print("🎬 Video ban rahi hai...")
    audio_clip = AudioFileClip(AUDIO_FILE)
    
    # ImageClip ko load karke audio ki length ke barabar set karte hain
    image_clip = ImageClip(BG_IMAGE_FILE)
    
    # Audio ko image ke sath jodhna
    video = image_clip.set_audio(audio_clip)
    video = video.set_duration(audio_clip.duration)
    
    # Codec set karna BOHOT zaroori hai taaki video blank na dikhe
    print("⏳ Rendering video with image and audio...")
    video.write_videofile(
        VIDEO_FILE, 
        fps=24, 
        codec="libx264",  # H.264 video codec
        audio_codec="aac" # AAC audio codec
    )
    print("✅ Video successfully ban gayi! Aap ab 'bhakti_video.mp4' file play karke dekh sakte hain.")

# ==========================================
# 4. YOUTUBE UPLOAD LOGIC
# ==========================================
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def authenticate_youtube():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secret.json'):
                print("⚠️ client_secret.json file nahi mili! YouTube upload skip kar rahe hain.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def upload_to_youtube(youtube):
    if youtube is None:
        return
        
    print("🚀 YouTube par upload ho raha hai...")
    request_body = {
        'snippet': {
            'title': 'Bhagwan Shiv Ki Mahima | Har Har Mahadev 🙏',
            'description': 'Om Namah Shivaya! Bhagwan shiv ki kripa jis par hoti hai, uska jeevan dhanya ho jata hai.\n\n#LordShiva #Mahadev #Bholenath #Bhakti #Sawan',
            'tags': ['Shiva', 'Mahadev', 'Bhakti', 'Bholenath', 'Hinduism'],
            'categoryId': '22' # People & Blogs
        },
        'status': {
            'privacyStatus': 'private' # Testing ke liye private rakhein
        }
    }
    
    media_file = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media_file
    )
    response = request.execute()
    print(f"✅ Video Uploaded Successfully! Video ID: {response.get('id')}")

# ==========================================
# 5. MAIN EXECUTION
# ==========================================
async def main():
    # Step 1: Audio banayein
    await generate_audio()
    
    # Step 2: Image download karein (Proper headers ke sath)
    download_image()
    
    # Step 3: Video banayein (proper h264 codec ke sath)
    create_video()
    
    # Step 4: YouTube par upload karein (Optional)
    # youtube_service = authenticate_youtube()
    # upload_to_youtube(youtube_service)
    print("🎉 Sabhi steps pure ho gaye!")

if __name__ == "__main__":
    asyncio.run(main())
