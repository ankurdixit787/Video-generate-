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
    print("\n🎵 Audio generate ho raha hai (Text to Speech)...")
    communicate = edge_tts.Communicate(TEXT_SCRIPT, VOICE)
    await communicate.save(AUDIO_FILE)
    print("✅ Audio successfully save ho gaya: ", AUDIO_FILE)

# ==========================================
# 3. GENERATE VIDEO (MERGING AUDIO & BACKGROUND)
# ==========================================
def generate_video():
    print("\n🎬 Video generate ho raha hai, kripya pratiksha karein...")
    try:
        # Load audio
        audio_clip = AudioFileClip(AUDIO_FILE)
        
        # Create an orange background video clip for youtube shorts (1080x1920)
        # Orange color RGB = (255, 165, 0)
        video_clip = ColorClip(size=(1080, 1920), color=(255, 165, 0), duration=audio_clip.duration)
        
        # Set audio to the video
        video_clip = video_clip.set_audio(audio_clip)
        
        # Write the result to a file
        video_clip.write_videofile(VIDEO_FILE, fps=24, codec="libx264", audio_codec="aac")
        print("\n✅ Video ban kar taiyar hai: ", VIDEO_FILE)
    except Exception as e:
        print("\n❌ Video banate samay error aaya:", e)

# ==========================================
# 4. YOUTUBE UPLOAD PROCESS
# ==========================================
def upload_to_youtube():
    print("\n🚀 YouTube par upload check kar rahe hain...")
    CLIENT_SECRETS_FILE = "client_secret.json"
    
    # Check if client_secret.json exists
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"⚠️ '{CLIENT_SECRETS_FILE}' file nahi mili.")
        print("Agar YouTube par automatically upload karna hai, toh Google Cloud Console se OAuth 2.0 Client IDs bana kar us json file ko 'client_secret.json' ke naam se save karein.")
        print("Aapki video successfully ban chuki hai aur local system mein save hai!")
        return

    try:
        SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        credentials = flow.run_local_server(port=0)
        youtube = build('youtube', 'v3', credentials=credentials)

        request_body = {
            'snippet': {
                'title': 'Om Namah Shivaya - Mahadev Bhakti Status',
                'description': 'Har Har Mahadev! Bholenath ki kripa aap sab par bani rahe.',
                'tags': ['mahadev', 'shiv', 'bhakti', 'status', 'om namah shivaya'],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'private' # Private par hai, public karne ke liye 'public' likhein
            }
        }

        media_file = MediaFileUpload(VIDEO_FILE, chunksize=-1, resumable=True)

        response_upload = youtube.videos().insert(
            part=','.join(request_body.keys()),
            body=request_body,
            media_body=media_file
        ).execute()

        print("✅ Upload successful! Video ID:", response_upload.get('id'))
    except Exception as e:
        print("❌ Upload karte samay error aaya:", e)

# ==========================================
# MAIN FUNCTION
# ==========================================
if __name__ == "__main__":
    # 1. Pehle audio create karte hain
    asyncio.run(generate_audio())
    
    # 2. Fir video generate karte hain
    if os.path.exists(AUDIO_FILE):
        generate_video()
    else:
        print("❌ Audio generate nahi ho paya, isliye video processing rok di gayi hai.")
    
    # 3. Last mein YouTube upload process start karte hain
    if os.path.exists(VIDEO_FILE):
        upload_to_youtube()
    else:
        print("❌ Video generate nahi ho payi, isliye upload skip kar diya gaya.")
