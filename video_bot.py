#!/usr/bin/env python3
"""
Bhakti Video Generator — Multi-Image Voice-Synced with Ken Burns
=================================================================
Generates 4 devotional images with different mantras/scenes,
creates voice-synced Ken Burns zoom clips, crossfades between them,
and delivers the final video via Telegram.

Voice-sync: each image's duration = (chars in segment / total chars) × audio_duration
This ensures images change exactly with the spoken content.
"""

import os
import sys
import asyncio
from pathlib import Path

from ffmpeg_utils import get_audio_duration

# ================================================================
# CONFIG
# ================================================================

TEXT_SCRIPT = [
    # Segment 0: Shiva intro + Kailash
    "Om Namah Shivaya. Dosto, bhagwan shiv ki kripa jis par hoti hai, uska jeevan dhanya ho jata hai. Shiv ji ko bholenath kaha jata hai kyunki wo apne bhakton ki pukar bahut jaldi sunte hain.",

    # Segment 1: Sawan / Ganga
    "Sawan ke mahine mein shiv ji ki pooja ka vishesh mahatva hota hai. Kaha jata hai ki jo bhi bhakt sachhe dil se ek lota jal shivling par arpit karta hai, mahadev uski sabhi manokamna puri karte hain.",

    # Segment 2: Kalyug / Dhyan
    "Aaj ke is kalyug mein, dhyan aur jap hi sabse bada sahara hai. Aap jab bhi pareshan ho, bas aankh band karke Har Har Mahadev ka jaap karein.",

    # Segment 3: Closing / Subscribe
    "Bholenath kabhi apne bhakton ko niraash nahi karte. Agar aapko yeh video pasand aayi ho, toh kripya is channel ko subscribe karein, aur comment mein Har Har Mahadev zaroor likhein. Dhanyawad aur Om Namah Shivaya.",
]

IMAGE_SCENES = [
    {"scene": "कैलाश पर्वत — त्रिशूल",   "mantra": "ॐ नमः शिवाय",     "sub": "Shiv Darshan"},
    {"scene": "गंगाधर — जलाभिषेक",       "mantra": "हर हर गंगे",       "sub": "Sawan Bhakti"},
    {"scene": "नटराज — तांडव",            "mantra": "ॐ त्र्यम्बकं यजामहे", "sub": "Dhyan Shakti"},
    {"scene": "पंचाक्षर — ॐकार",          "mantra": "हर हर महादेव",     "sub": "Bhole Nath"},
]

VOICE = "hi-IN-SwaraNeural"
AUDIO_FILE = "bhakti_audio.mp3"
VIDEO_FILE = "bhakti_video.mp4"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

TARGET_W, TARGET_H = 1080, 1920
FPS = 24
ZOOM_SPEED = 0.0025
XFADE_DUR = 1.0

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SHIVA_COLORS = {
    "top": (75, 0, 130),
    "bottom": (255, 140, 0),
}


# ================================================================
# IMAGE GENERATION
# ================================================================

def create_gradient_images():
    """Generate 4 themed devotional images with different scenes."""
    from PIL import Image, ImageDraw
    import numpy as np

    w, h = TARGET_W, TARGET_H
    tc, bc = SHIVA_COLORS["top"], SHIVA_COLORS["bottom"]
    paths = []

    for i, scene_data in enumerate(IMAGE_SCENES):
        path = f"devotional_img_{i:02d}.png"

        # Gradient background
        gradient = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            ratio = y / h
            gradient[y, :, 0] = int(tc[0] * (1 - ratio) + bc[0] * ratio)
            gradient[y, :, 1] = int(tc[1] * (1 - ratio) + bc[1] * ratio)
            gradient[y, :, 2] = int(tc[2] * (1 - ratio) + bc[2] * ratio)

        img = Image.fromarray(gradient)
        draw = ImageDraw.Draw(img)

        # Decorative concentric circles
        cx, cy = w // 2, h // 3
        for radius in range(240, 60, -20):
            alpha = int(80 + 175 * (1 - radius / 240))
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                outline=(alpha, alpha, alpha),
                width=2,
            )

        # Big mantra
        font_size = 70
        try:
            from PIL import ImageFont
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", font_size
            )
        except Exception:
            font = ImageFont.load_default()

        draw.text((cx, cy - 50), scene_data["mantra"], fill=(255, 255, 220),
                  anchor="mm", font=font)
        draw.text((cx, cy + 60), f"--- {scene_data['scene']} ---",
                  fill=(255, 215, 0), anchor="mm")
        draw.text((cx, h * 2 // 3), scene_data["sub"],
                  fill=(240, 240, 240), anchor="mm")
        draw.text((w - 60, h - 40), f"{i+1} / {len(IMAGE_SCENES)}",
                  fill=(200, 200, 200), anchor="mm")
        draw.text((cx, h - 60), "OM NAMAH SHIVAYA", fill=(255, 255, 200),
                  anchor="mm")

        img.save(path, quality=95)
        paths.append(path)
        print(f"      ✓ Image {i+1}/4: {scene_data['scene']} → {path}")

    return paths


# ================================================================
# AUDIO
# ================================================================

async def generate_audio():
    """Generate Hindi voiceover from concatenated script."""
    import edge_tts
    full_script = " ".join(TEXT_SCRIPT).strip()
    print(f"[Audio] Generating voiceover ({len(full_script)} chars)...")
    try:
        comm = edge_tts.Communicate(full_script, VOICE)
        await comm.save(AUDIO_FILE)
        size_kb = os.path.getsize(AUDIO_FILE) / 1024
        print(f"      ✓ Audio: {AUDIO_FILE} ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"      ✗ Audio FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# ================================================================
# TIMESTAMP CALCULATION (VOICE-SYNCED)
# ================================================================

def calc_segment_durations(segments, total_audio_duration):
    """Distribute audio duration proportionally by segment char count."""
    char_counts = [len(s) for s in segments]
    total_chars = sum(char_counts)

    durations = []
    for count in char_counts:
        dur = (count / total_chars) * total_audio_duration
        durations.append(max(dur, 1.5))

    scale = total_audio_duration / sum(durations)
    durations = [d * scale for d in durations]

    starts = [0.0]
    for d in durations[:-1]:
        starts.append(starts[-1] + d)

    return list(zip(starts, durations))


# ================================================================
# VIDEO COMPOSITION (FFmpeg Ken Burns + Crossfade + Audio Sync)
# ================================================================

def compose_multi_image_video(image_paths, segment_timings):
    """
    Create multi-image video with Ken Burns zoom + crossfade + audio.
    Uses FFmpeg directly for reliability.
    """
    from ffmpeg_utils import find_ffmpeg
    import subprocess
    import tempfile
    import re

    ffmpeg = find_ffmpeg()
    print(f"[Video] Composing {len(image_paths)} images with voice-synced timings...")

    with tempfile.TemporaryDirectory(prefix="bhakti_") as tmpdir:
        tmp = Path(tmpdir)
        clip_files = []

        # --- Phase 1: Create individual zoom clips ---
        for i, (img_path, (start, dur)) in enumerate(zip(image_paths, segment_timings)):
            clip_path = str(tmp / f"zoom_{i:02d}.mp4")
            total_frames = max(1, int(dur * FPS))

            print(f"      Clip {i+1}: {dur:.1f}s → '{IMAGE_SCENES[i]['scene']}'")

            zoom_end = 1.05 + (i % 3) * 0.03
            result = subprocess.run(
                [
                    ffmpeg, "-y", "-loop", "1", "-i", img_path,
                    "-vf",
                    f"zoompan=z='min(1+{ZOOM_SPEED}*on,{zoom_end}):"
                    f"d={total_frames}:"
                    f"x='iw/2-(iw/zoom/2)':"
                    f"y='ih/2-(ih/zoom/2)':"
                    f"s={TARGET_W}x{TARGET_H}:fps={FPS}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-t", str(dur), clip_path,
                ],
                capture_output=True, timeout=120,
            )

            if result.returncode != 0:
                print(f"      ✗ FFmpeg zoom FAILED: {result.stderr.decode()[:300]}")
                continue
            if Path(clip_path).exists():
                clip_files.append((clip_path, dur))
            else:
                print(f"      ✗ Clip not created: {clip_path}")

        if len(clip_files) < 2:
            print("[FATAL] Need >= 2 clips for crossfade. Aborting.")
            return None

        # --- Phase 2: Crossfade concatenation ---
        print(f"      Crossfading {len(clip_files)} clips...")

        inputs = []
        for cp, _ in clip_files:
            inputs.extend(["-i", cp])

        # Calculate running durations for xfade offsets
        filter_parts = []
        prev_label = "0:v"
        running = get_clip_duration(clip_files[0][0])

        for i in range(1, len(clip_files)):
            out_label = f"v{i}" if i < len(clip_files) - 1 else "vout"
            offset = running - XFADE_DUR
            filter_parts.append(
                f"[{prev_label}][{i}:v]xfade=transition=fade:"
                f"duration={XFADE_DUR}:offset={max(0, offset):.3f}[{out_label}]"
            )
            prev_label = out_label
            running += get_clip_duration(clip_files[i][0])

        filter_str = ";".join(filter_parts)
        concat_path = str(tmp / "concat.mp4")

        subprocess.run(
            [ffmpeg, "-y", *inputs, "-filter_complex", filter_str,
             "-map", f"[{prev_label}]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", concat_path],
            capture_output=True, timeout=180,
        )

        if not Path(concat_path).exists():
            print("[FATAL] Crossfade concat failed!")
            return None

        # --- Phase 3: Mux with audio ---
        print("      Muxing with audio...")
        final_path = str(OUTPUT_DIR / VIDEO_FILE)

        subprocess.run(
            [ffmpeg, "-y", "-i", concat_path, "-i", AUDIO_FILE,
             "-c:v", "copy", "-c:a", "aac", "-shortest",
             "-map", "0:v:0", "-map", "1:a:0", final_path],
            capture_output=True, timeout=60,
        )

        if Path(final_path).exists():
            size_mb = os.path.getsize(final_path) / (1024 * 1024)
            print(f"      ✓ Video: {final_path} ({size_mb:.1f} MB)")
            return final_path

        print("      ✗ Final video missing!")
        return None


def get_clip_duration(clip_path: str) -> float:
    """Get video clip duration."""
    try:
        return float(get_audio_duration(clip_path))
    except Exception:
        return 15.0


# ================================================================
# TELEGRAM
# ================================================================

def send_to_telegram(video_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] ⚠ No token/chat_id set. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID env vars.")
        return False

    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    caption = (
        "🔱 **ॐ नमः शिवाय** 🔱\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎬 Multi-Image Bhakti Video\n"
        "🖼 4 Themed Scenes — Voice Synced\n"
        "🎥 Ken Burns Zoom + Crossfade\n"
        "🗣 Voice: AI Hindi (SwaraNeural)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🙏 Har Har Mahadev 🙏"
    )
    try:
        with open(video_path, "rb") as vf:
            resp = requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
                files={"video": vf}, timeout=120,
            )
        if resp.status_code == 200:
            print("[Telegram] ✓ Sent!")
            return True
        print(f"[Telegram] ✗ {resp.status_code}: {resp.text[:300]}")
        return False
    except Exception as e:
        print(f"[Telegram] ✗ Error: {e}")
        return False


# ================================================================
# MAIN
# ================================================================

async def main():
    print("=" * 55)
    print("  🔱 BHAKTI VIDEO GENERATOR — Multi-Image Voice-Synced")
    print("  Shiv Bhakti | Ken Burns | AI Voiceover")
    print("=" * 55)

    # 1. Images
    print("\n[1/5] Generating 4 themed devotional images...")
    image_paths = create_gradient_images()
    if len(image_paths) < 2:
        print("[FATAL] Need >= 2 images.")
        sys.exit(1)

    # 2. Audio
    print("\n[2/5] Generating AI voiceover...")
    if not await generate_audio():
        sys.exit(1)

    # 3. Timestamps (voice-synced)
    print("\n[3/5] Calculating voice-synced timestamps...")
    audio_dur = get_audio_duration(AUDIO_FILE)
    print(f"      Audio duration: {audio_dur:.2f}s")
    segment_timings = calc_segment_durations(TEXT_SCRIPT, audio_dur)
    for i, (start, dur) in enumerate(segment_timings):
        print(f"      Seg {i+1}: {start:.1f}s → {start+dur:.1f}s ({dur:.1f}s) "
              f"[{IMAGE_SCENES[i]['scene']}]")

    # 4. Video
    print("\n[4/5] Composing Ken Burns video with crossfade...")
    video_path = compose_multi_image_video(image_paths, segment_timings)
    if not video_path:
        print("[FATAL] Video composition failed.")
        sys.exit(1)

    # 5. Telegram
    print("\n[5/5] Sending to Telegram...")
    send_to_telegram(video_path)

    print("=" * 55)
    print(f"  ✅ DONE! {video_path}")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())