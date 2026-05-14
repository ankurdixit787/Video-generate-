#!/usr/bin/env python3
"""
Bhakti Video Generator v2.0 — Multi-Image Voice-Synced with Ken Burns
=====================================================================
Generates 4 devotional images with different mantras/scenes,
creates voice-synced Ken Burns zoom clips, crossfades between them,
and delivers the final video via Telegram.

Supports skip flags for each pipeline step.
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add src/ to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ffmpeg_utils import get_audio_duration

# ================================================================
# CONFIG
# ================================================================

TEXT_SCRIPT = [
    "Om Namah Shivaya. Dosto, bhagwan shiv ki kripa jis par hoti hai, uska jeevan dhanya ho jata hai. Shiv ji ko bholenath kaha jata hai kyunki wo apne bhakton ki pukar bahut jaldi sunte hain.",
    "Sawan ke mahine mein shiv ji ki pooja ka vishesh mahatva hota hai. Kaha jata hai ki jo bhi bhakt sachhe dil se ek lota jal shivling par arpit karta hai, mahadev uski sabhi manokamna puri karte hain.",
    "Aaj ke is kalyug mein, dhyan aur jap hi sabse bada sahara hai. Aap jab bhi pareshan ho, bas aankh band karke Har Har Mahadev ka jaap karein.",
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


# ================================================================
# IMAGE GENERATION
# ================================================================

def generate_ai_images():
    """Generate HD religious images using Pollinations.ai (free, no API key)."""
    import requests
    from PIL import Image
    from io import BytesIO
    import cv2
    import numpy as np

    w, h = TARGET_W, TARGET_H
    paths = []

    # More detailed prompts for better quality
    AI_PROMPTS = [
        "Lord Shiva sitting on Mount Kailash in deep meditation, trident beside him, "
        "divine blue glow around him, Himalayan snow peaks background, celestial clouds, "
        "stars in sky, hindu devotional art, cinematic dramatic lighting, 8k, highly detailed, "
        "photorealistic, sacred atmosphere",

        "Lord Shiva as Gangadhar, river Ganga flowing from his matted jata hair, "
        "beautiful blue skin, crescent moon on head, sacred water pouring on shiva lingam, "
        "devotees doing abhishekam ceremony, golden divine light, hindu art masterpiece, "
        "8k, highly detailed, photorealistic",

        "Lord Shiva as Nataraja performing cosmic Tandava dance, ring of blue fire around him, "
        "four arms in dynamic pose holding damaru and agni, cosmic universe background, "
        "golden divine aura, hindu mythology art, 8k, highly detailed, dramatic lighting",

        "Sacred Om symbol with panchakshara mantra glowing golden light, "
        "lotus flowers surrounding, spiritual meditation scene, cosmic energy radiating, "
        "hindu devotional art, peaceful divine atmosphere, 8k, highly detailed, photorealistic",
    ]

    for i, (scene_data, prompt) in enumerate(zip(IMAGE_SCENES, AI_PROMPTS)):
        path = f"devotional_img_{i:02d}.png"

        print(f"      🎨 Generating image {i+1}/4: {scene_data['scene']}")
        print(f"         Prompt: {prompt[:60]}...")

        try:
            # Pollinations.ai — free, no API key required
            url = (
                f"https://image.pollinations.ai/prompt/"
                f"{requests.utils.quote(prompt)}"
                f"?width={w}&height={h}&nologo=true&seed={i + 42}"
            )
            r = requests.get(url, timeout=120)

            if r.status_code != 200 or 'image' not in r.headers.get('content-type', ''):
                print(f"      ✗ Pollinations returned {r.status_code}, trying fallback...")
                raise RuntimeError(f"Pollinations failed: {r.status_code}")

            img = Image.open(BytesIO(r.content))

            # High quality resize using LANCZOS
            img = img.resize((w, h), Image.LANCZOS)

            # Advanced enhancement: sharpen + contrast + upscale quality
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

            # Unsharp mask for sharpness
            blurred = cv2.GaussianBlur(img_cv, (0, 0), 2.0)
            sharpened = cv2.addWeighted(img_cv, 1.5, blurred, -0.5, 0)

            # CLAHE for contrast enhancement
            lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
            l_ch, a_ch, b_ch = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l_ch = clahe.apply(l_ch)
            enhanced = cv2.merge([l_ch, a_ch, b_ch])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

            # Convert back to PIL
            img = Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))

            # Save at highest quality
            img.save(path, quality=95, optimize=False)
            paths.append(path)
            print(f"      ✓ Image {i+1}/4: {img.size} → {path}")

        except Exception as e:
            print(f"      ✗ AI generation failed for image {i+1}: {e}")
            # Fallback: create a simple colored image so pipeline doesn't break
            from PIL import Image as FallbackImage, ImageDraw, ImageFont
            fallback = FallbackImage.new("RGB", (w, h), (25, 25, 50))
            draw = ImageDraw.Draw(fallback)
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", 60
                )
            except Exception:
                font = ImageFont.load_default()
            draw.text((w//2, h//2), f"{scene_data['mantra']}\n{scene_data['scene']}",
                      fill=(200, 200, 200), anchor="mm", font=font, align="center")
            fallback.save(path, quality=85)
            paths.append(path)
            print(f"      ⚠ Fallback image used for {scene_data['scene']}")

    return paths


# ================================================================
# AUDIO
# ================================================================

async def generate_audio():
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
        import traceback; traceback.print_exc()
        return False


# ================================================================
# TIMESTAMP CALCULATION
# ================================================================

def calc_segment_durations(segments, total_audio_duration):
    char_counts = [len(s) for s in segments]
    total_chars = sum(char_counts)
    durations = [max((c / total_chars) * total_audio_duration, 1.5) for c in char_counts]
    scale = total_audio_duration / sum(durations)
    durations = [d * scale for d in durations]
    starts = [0.0]
    for d in durations[:-1]:
        starts.append(starts[-1] + d)
    return list(zip(starts, durations))


# ================================================================
# VIDEO COMPOSITION
# ================================================================

def compose_multi_image_video(image_paths, segment_timings):
    from ffmpeg_utils import find_ffmpeg, get_clip_duration as _gcd
    import subprocess, tempfile

    ffmpeg = find_ffmpeg()
    print(f"[Video] Composing {len(image_paths)} images with voice-synced timings...")

    with tempfile.TemporaryDirectory(prefix="bhakti_") as tmpdir:
        tmp = Path(tmpdir)
        clip_files = []

        for i, (img_path, (start, dur)) in enumerate(zip(image_paths, segment_timings)):
            clip_path = str(tmp / f"zoom_{i:02d}.mp4")
            total_frames = max(1, int(dur * FPS))
            print(f"      Clip {i+1}: {dur:.1f}s → '{IMAGE_SCENES[i]['scene']}'")

            zoom_end = 1.05 + (i % 3) * 0.03
            result = subprocess.run(
                [ffmpeg, "-y", "-loop", "1", "-i", img_path,
                 "-vf", f"zoompan=z='min(1+{ZOOM_SPEED}*on,{zoom_end}):"
                        f"d={total_frames}:x='iw/2-(iw/zoom/2)':"
                        f"y='ih/2-(ih/zoom/2)':s={TARGET_W}x{TARGET_H}:fps={FPS}",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p",
                 "-preset", "medium", "-crf", "23", "-b:v", "5000k",
                 "-t", str(dur), clip_path],
                capture_output=True, timeout=120,
            )

            if result.returncode != 0:
                err = result.stderr.decode()
                # Skip ffmpeg version header, show actual error
                tail_lines = err.split('\n')[-10:]
                print(f"      ✗ FAILED: {' '.join([l for l in tail_lines if 'Error' in l or 'error' in l or 'Invalid' in l or 'Expected' in l])}")
                print(f"      Last line: {tail_lines[-1][:200]}")
                continue
            if Path(clip_path).exists():
                clip_files.append((clip_path, dur))

        if len(clip_files) < 2:
            print("[FATAL] Need >= 2 clips. Aborting.")
            return None

        # Crossfade
        print(f"      Crossfading {len(clip_files)} clips...")
        inputs = []
        for cp, _ in clip_files:
            inputs.extend(["-i", cp])

        filter_parts = []
        prev_label = "0:v"
        running = _gcd(clip_files[0][0])

        for i in range(1, len(clip_files)):
            out_label = f"v{i}" if i < len(clip_files) - 1 else "vout"
            offset = running - XFADE_DUR
            filter_parts.append(
                f"[{prev_label}][{i}:v]xfade=transition=fade:"
                f"duration={XFADE_DUR}:offset={max(0, offset):.3f}[{out_label}]"
            )
            prev_label = out_label
            running += _gcd(clip_files[i][0])

        filter_str = ";".join(filter_parts)
        concat_path = str(tmp / "concat.mp4")

        result = subprocess.run(
            [ffmpeg, "-y", *inputs, "-filter_complex", filter_str,
             "-map", f"[{prev_label}]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-preset", "medium", "-crf", "23", "-b:v", "5000k",
             concat_path],
            capture_output=True, timeout=180,
        )
        if result.returncode != 0:
            print(f"      ✗ Crossfade FAILED: {result.stderr.decode()[:400]}")
            return None

        if not Path(concat_path).exists():
            print("[FATAL] Crossfade failed — output missing!")
            return None

        # Mux audio
        print("      Muxing with audio...")
        final_path = str(OUTPUT_DIR / VIDEO_FILE)
        result = subprocess.run(
            [ffmpeg, "-y", "-i", concat_path, "-i", AUDIO_FILE,
             "-c:v", "copy", "-c:a", "aac", "-shortest",
             "-map", "0:v:0", "-map", "1:a:0", final_path],
            capture_output=True, timeout=60,
        )
        if result.returncode != 0:
            print(f"      ✗ Audio mux FAILED: {result.stderr.decode()[:300]}")
            return None

        if Path(final_path).exists():
            size_mb = os.path.getsize(final_path) / (1024 * 1024)
            print(f"      ✓ Video: {final_path} ({size_mb:.1f} MB)")
            return final_path

        print("      ✗ Final video missing!")
        return None


def compose_silent_video(image_paths):
    """Create video from images only (no audio)."""
    from ffmpeg_utils import find_ffmpeg
    import subprocess, tempfile

    ffmpeg = find_ffmpeg()
    print("[Video] Composing silent video from images...")

    with tempfile.TemporaryDirectory(prefix="silent_") as tmpdir:
        tmp = Path(tmpdir)
        clip_files = []

        for i, img_path in enumerate(image_paths):
            clip_path = str(tmp / f"clip_{i:02d}.mp4")
            dur = 15.0  # 15s per image
            total_frames = int(dur * FPS)

            result = subprocess.run(
                [ffmpeg, "-y", "-loop", "1", "-i", img_path,
                 "-vf", f"zoompan=z='min(1+0.002*on,1.1)':d={total_frames}:"
                        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"s={TARGET_W}x{TARGET_H}:fps={FPS}",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p",
                 "-t", str(dur), clip_path],
                capture_output=True, timeout=120,
            )
            if result.returncode == 0 and Path(clip_path).exists():
                clip_files.append(clip_path)

        if not clip_files:
            return None

        concat_path = str(tmp / "concat.mp4")
        inputs = []
        for cp in clip_files:
            inputs.extend(["-i", cp])

        filter_parts = []
        prev_label = "0:v"
        for i in range(1, len(clip_files)):
            out_label = f"v{i}" if i < len(clip_files) - 1 else "vout"
            filter_parts.append(
                f"[{prev_label}][{i}:v]xfade=transition=fade:"
                f"duration=1:offset={max(0, i * 15 - 1)}[{out_label}]"
            )
            prev_label = out_label

        subprocess.run(
            [ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filter_parts),
             "-map", f"[{prev_label}]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             concat_path],
            capture_output=True, timeout=180,
        )

        final_path = str(OUTPUT_DIR / "silent_video.mp4")
        subprocess.run(
            [ffmpeg, "-y", "-i", concat_path,
             "-c:v", "copy", str(OUTPUT_DIR / "silent_video.mp4")],
            capture_output=True, timeout=60,
        )

        if Path(final_path).exists():
            print(f"      ✓ Silent video: {final_path}")
            return final_path
        return None


# ================================================================
# TELEGRAM
# ================================================================

def send_to_telegram(video_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] ⚠ No token/chat_id. Set env vars TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID.")
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
                files={"video": vf}, timeout=180,
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
    parser = argparse.ArgumentParser(description="🔱 Bhakti Video Generator v2.0")
    parser.add_argument("--deity", choices=["krishna", "shiva", "ram"], default="shiva")
    parser.add_argument("--skip-images", action="store_true", help="Skip image generation")
    parser.add_argument("--skip-voice", action="store_true", help="Skip voiceover generation")
    parser.add_argument("--skip-subtitles", action="store_true", help="Skip subtitle overlay")
    parser.add_argument("--skip-telegram", action="store_true", help="Skip Telegram delivery")
    parser.add_argument("--skip-video", action="store_true", help="Skip video composition (audio only)")
    parser.add_argument("--output", type=str, default=None, help="Custom output filename")
    args = parser.parse_args()

    print("=" * 55)
    print(f"  🔱 BHAKTI VIDEO GENERATOR v2.0")
    print(f"  Deity: {args.deity} | Skips: "
          f"{'images' if args.skip_images else ''} "
          f"{'voice' if args.skip_voice else ''} "
          f"{'subtitles' if args.skip_subtitles else ''} "
          f"{'telegram' if args.skip_telegram else ''} "
          f"{'video' if args.skip_video else ''}")
    print("=" * 55)

    image_paths = []
    video_path = None

    # Step 1: Images (optional)
    if not args.skip_images:
        print("\n[1/5] Generating 4 themed images...")
        image_paths = generate_ai_images()
        if len(image_paths) < 2 and not args.skip_video:
            print("[FATAL] Need >= 2 images for video.")
            sys.exit(1)
    else:
        print("\n[1/5] ⏭ Images skipped")

    # Step 2: Audio (optional)
    if not args.skip_voice:
        print("\n[2/5] Generating AI voiceover...")
        if not await generate_audio():
            print("[FATAL] Audio generation failed.")
            sys.exit(1)
    else:
        print("\n[2/5] ⏭ Voice skipped")

    # Step 3: Video composition
    if args.skip_video:
        print("\n[3/5] ⏭ Video composition skipped (audio-only mode)")
        if not args.skip_voice:
            print(f"\n✅ Done! Audio file: {AUDIO_FILE}")
        else:
            print("\n⚠ Nothing to generate!")
        return

    # Step 4: Compose video
    if image_paths:
        print("\n[3/5] Calculating voice-synced timestamps...")
        audio_dur = get_audio_duration(AUDIO_FILE) if not args.skip_voice else len(" ".join(TEXT_SCRIPT)) / 4.0
        print(f"      Duration: {audio_dur:.2f}s")
        segment_timings = calc_segment_durations(TEXT_SCRIPT, audio_dur)

        print("\n[4/5] Composing Ken Burns video...")
        video_path = compose_multi_image_video(image_paths, segment_timings)
    else:
        # No images but still need video — compose silent
        print("\n[3/5] No images — checking for silent video mode...")
        if args.skip_images:
            print("      ⚠ Cannot compose video without images. Try without --skip-images")
            sys.exit(1)
        video_path = compose_silent_video([])

    if not video_path:
        print("[FATAL] Video composition failed.")
        sys.exit(1)

    # Step 5: Telegram (optional)
    if not args.skip_telegram:
        print("\n[5/5] Sending to Telegram...")
        send_to_telegram(video_path)
    else:
        print("\n[5/5] ⏭ Telegram skipped")

    print("=" * 55)
    print(f"  ✅ DONE! {video_path}")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())