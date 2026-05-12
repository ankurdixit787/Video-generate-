#!/usr/bin/env python3
"""
AI Bhakti Video Generator Bot
- Generates devotional video with voiceover + image slideshow
- Sends to Telegram automatically
- Falls back to gradient image if download fails
"""

import os
import sys
import time
import asyncio
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
# NOTE: Run pip install edge-tts moviepy requests Pillow numpy first

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

# Telegram — set via env vars: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# Audio settings
VOICE = "hi-IN-SwaraNeural"
AUDIO_FILE = "bhakti_audio.mp3"

# Video output
VIDEO_FILE = "bhakti_video.mp4"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Image settings
TARGET_W = 1080
TARGET_H = 1920
BG_IMAGE_FILE = "background_image.jpg"
UNSPLASH_URL = "https://images.unsplash.com/photo-1604500858850-9830538f95fb?q=80&w=1080&auto=format&fit=crop"

# ---------------------------------------------------------------------------
# IMAGE: Download or generate fallback
# ---------------------------------------------------------------------------
def get_or_create_image():
    """Download image from Unsplash, or create a gradient devotional image."""
    import requests
    from PIL import Image, ImageDraw
    import numpy as np

    # --- Attempt 1: Download ---
    print("[1/4] Downloading background image...")
    try:
        resp = requests.get(UNSPLASH_URL, stream=True, timeout=15)
        if resp.status_code == 200:
            with open(BG_IMAGE_FILE, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            print("      ✓ Downloaded from Unsplash")
        else:
            raise Exception(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"      ⚠ Download failed ({e}), using gradient fallback...")
        _create_gradient_image(BG_IMAGE_FILE)

    # --- Step 2: Normalize (RGB, 1080×1920) ---
    print("[2/4] Normalizing image (1080×1920 RGB)...")
    try:
        img = Image.open(BG_IMAGE_FILE)
        img = img.convert("RGB")
        img = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)
        img.save(BG_IMAGE_FILE, quality=95)
        print(f"      ✓ Image ready: {img.size}, mode={img.mode}")
        return True
    except Exception as e:
        print(f"      ✗ Image normalization failed: {e}")
        return False


def _create_gradient_image(path):
    """Create a beautiful devotional gradient image as fallback."""
    from PIL import Image, ImageDraw
    import numpy as np

    w, h = TARGET_W, TARGET_H

    # Shiv-themed gradient: orange/purple
    top_color = (75, 0, 130)     # Deep purple
    bottom_color = (255, 140, 0)  # Orange

    gradient = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        ratio = y / h
        gradient[y, :, 0] = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        gradient[y, :, 1] = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        gradient[y, :, 2] = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)

    img = Image.fromarray(gradient)
    draw = ImageDraw.Draw(img)

    # Om symbol / mantra
    cx, cy = w // 2, h // 3
    for radius in range(220, 60, -20):
        alpha = int(100 + 155 * (1 - radius / 220))
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=(alpha, alpha, alpha),
            width=2,
        )

    # Text - try to use devanagari font if available, else default
    try:
        from PIL import ImageFont
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/NotoNaskhArabic/NotoNaskhArabic-Regular.ttf", 80)
    except Exception:
        font_large = None

    # Mantra
    draw.text((cx, cy - 40), "ॐ नमः शिवाय", fill=(255, 255, 220), anchor="mm", font=font_large)
    draw.text((cx, cy + 40), "-- कैलाश पर्वत --", fill=(255, 215, 0), anchor="mm", font=font_large)
    draw.text((cx, h * 2 // 3), "हर हर महादेव", fill=(255, 255, 255), anchor="mm", font=font_large)
    draw.text((w - 60, h - 30), "🙏", fill=(255, 255, 255), anchor="mm")

    img.save(path, quality=95)
    print("      ✓ Gradient devotional image created")


# ---------------------------------------------------------------------------
# AUDIO: Edge-TTS voiceover
# ---------------------------------------------------------------------------
async def generate_audio():
    """Generate Hindi voiceover with Edge-TTS."""
    print("[3/4] Generating AI voiceover...")
    try:
        import edge_tts
        communicate = edge_tts.Communicate(TEXT_SCRIPT.strip(), VOICE)
        await communicate.save(AUDIO_FILE)
        size = os.path.getsize(AUDIO_FILE) / 1024
        print(f"      ✓ Audio saved: {AUDIO_FILE} ({size:.0f} KB)")
        return True
    except Exception as e:
        print(f"      ✗ Audio failed: {e}")
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# VIDEO: Compose image + audio
# ---------------------------------------------------------------------------
def create_video():
    """Compose video from background image + audio using MoviePy v2."""
    print("[4/4] Composing video...")

    if not os.path.exists(AUDIO_FILE):
        print("      ✗ Audio file missing!")
        return None
    if not os.path.exists(BG_IMAGE_FILE):
        print("      ✗ Background image missing!")
        return None

    try:
        from moviepy import (
            ImageClip,
            AudioFileClip,
        )

        # Load audio
        audio_clip = AudioFileClip(AUDIO_FILE)
        audio_duration = audio_clip.duration
        print(f"      Audio duration: {audio_duration:.1f}s")

        # --- MoviePy v2 API: with_duration / resized ---
        video_clip = (
            ImageClip(BG_IMAGE_FILE)
            .with_duration(audio_duration)
            .resized(new_size=(TARGET_W, TARGET_H))
            .with_audio(audio_clip)
        )

        output_path = str(OUTPUT_DIR / VIDEO_FILE)
        print(f"      Rendering to: {output_path}")

        video_clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None,
        )

        # Cleanup
        audio_clip.close()
        video_clip.close()

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"      ✓ Video created: {output_path} ({size_mb:.1f} MB)")
            return output_path
        else:
            print("      ✗ Video file wasn't created!")
            return None

    except Exception as e:
        print(f"      ✗ Video creation CRASHED:")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# TELEGRAM: Send video
# ---------------------------------------------------------------------------
def send_video_to_telegram(video_path):
    """Send generated video to Telegram bot."""
    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID

    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("[Telegram] ⚠ Bot token not set. Set TELEGRAM_BOT_TOKEN env var.")
        return False
    if not chat_id or chat_id == "YOUR_CHAT_ID_HERE":
        print("[Telegram] ⚠ Chat ID not set. Set TELEGRAM_CHAT_ID env var.")
        return False

    import requests
    print(f"[Telegram] Sending video to chat {chat_id}...")
    url = f"https://api.telegram.org/bot{token}/sendVideo"
    try:
        with open(video_path, "rb") as video:
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "caption": "🔱 ॐ नमः शिवाय 🔱\nShiv Bhakti Video — Generated by AI"},
                files={"video": video},
                timeout=60,
            )
        if resp.status_code == 200:
            print(f"[Telegram] ✓ Video sent successfully!")
            return True
        else:
            print(f"[Telegram] ✗ Failed: {resp.text}")
            return False
    except Exception as e:
        print(f"[Telegram] ✗ Error: {e}")
        return False


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
async def main():
    print("=" * 50)
    print("  AI BHAKTI VIDEO GENERATOR BOT")
    print("  Shiv | Krishna | Ram — 1-Minute Videos")
    print("=" * 50)

    # Step 1: Image
    if not get_or_create_image():
        print("[FATAL] Cannot create/procure image. Exiting.")
        sys.exit(1)

    # Step 2: Audio
    if not await generate_audio():
        print("[FATAL] Audio generation failed. Exiting.")
        sys.exit(1)

    # Step 3: Video
    video_path = create_video()
    if not video_path:
        print("[FATAL] Video composition failed. Exiting.")
        sys.exit(1)

    # Step 4: Telegram
    send_video_to_telegram(video_path)

    print("=" * 50)
    print(f"  ✅ DONE! Video: {video_path}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
