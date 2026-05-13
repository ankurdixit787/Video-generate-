#!/usr/bin/env python3
"""
Final Bhakti Video Generator - FLUX + Smooth Ken Burns + No Text + Bhajan
"""

import os
import json
import subprocess
from huggingface_hub import InferenceClient
from PIL import Image
import cv2
import numpy as np
import time

# Setup
HF_TOKEN = "HF_TOKEN_PLACEHOLDER"
OUTPUT_DIR = "/tmp/bhakti_video_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Bhakti scenes with FLUX prompts
SCENES = [
    {
        "prompt": "Lord Shiva meditating on Mount Kailash, cosmic background, divine glow, photorealistic, 4K, devotional art",
        "duration": 12.0,
        "zoom_start": 1.0,
        "zoom_end": 1.12,
    },
    {
        "prompt": "Lord Rama in Ayodhya palace, golden light, bow and arrow, divine atmosphere, highly detailed, 4K",
        "duration": 12.0,
        "zoom_start": 1.12,
        "zoom_end": 1.0,
    },
    {
        "prompt": "Lord Krishna playing flute under kadamba tree, Vrindavan forest, divine blue glow, photorealistic, 8K",
        "duration": 12.0,
        "zoom_start": 1.0,
        "zoom_end": 1.15,
    },
    {
        "prompt": "Ganesh ji with modak and flowers, warm divine light, intricate details, devotional art style, 4K",
        "duration": 12.0,
        "zoom_start": 1.15,
        "zoom_end": 1.0,
    },
    {
        "prompt": "Hanuman ji flying with Sanjeevani mountain, dramatic sky, divine power, hyperrealistic, 8K",
        "duration": 12.0,
        "zoom_start": 1.0,
        "zoom_end": 1.12,
    },
]

def generate_flux_image(prompt, output_path, scene_num):
    """Generate image using FLUX.1-schnell"""
    print(f"\n[Scene {scene_num}] Generating: {prompt[:50]}...")
    try:
        client = InferenceClient(token=HF_TOKEN)
        image = client.text_to_image(
            prompt,
            model='black-forest-labs/FLUX.1-schnell'
        )
        # Resize to 1024x1792 for 9:16 aspect
        image = image.resize((1024, 1792), Image.LANCZOS)
        image.save(output_path, quality=95)
        print(f"✓ Saved: {output_path}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def gentle_process_image(input_path, output_path):
    """Gentle processing - no CLAHE, mild sharpening"""
    img = cv2.imread(input_path)
    if img is None:
        return False
    
    # Mild sharpening (1.2/-0.2)
    blurred = cv2.GaussianBlur(img, (0, 0), 1.0)
    sharpened = cv2.addWeighted(img, 1.2, blurred, -0.2, 0)
    
    # Subtle contrast
    bright = cv2.convertScaleAbs(sharpened, alpha=1.03, beta=3)
    
    # Upscale to 1080x1920
    final = cv2.resize(bright, (1080, 1920), interpolation=cv2.INTER_LANCZOS4)
    cv2.imwrite(output_path, final, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return True

def create_ken_burns_clip(image_path, output_path, duration, zoom_start, zoom_end, fps=30):
    """Create smooth Ken Burns zoom clip (animated z, no slide)"""
    total_frames = int(duration * fps)
    z_diff = zoom_end - zoom_start
    
    # Animated zoom expression
    if z_diff > 0:  # zoom in
        z_expr = f"{zoom_start}+{z_diff}*on/{total_frames-1}"
    else:  # zoom out
        abs_diff = abs(z_diff)
        z_expr = f"{zoom_start}-{abs_diff}*on/{total_frames-1}"
    
    # Centered, no x/y slide
    x_expr = f"iw/2-(iw/{z_expr}/2)"
    y_expr = f"ih/2-(ih/{z_expr}/2)"
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-vf", f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s=1080x1920:fps={fps}",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "17",
        "-b:v", "8000k",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        output_path
    ]
    
    print(f"Creating clip: {output_path}")
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path

def main():
    print("=" * 60)
    print("🌺 BHAKTI VIDEO GENERATOR - FINAL VERSION")
    print("=" * 60)
    
    # Step 1: Generate images with FLUX
    print("\n📸 Step 1: Generating FLUX images...")
    image_paths = []
    for i, scene in enumerate(SCENES, 1):
        img_path = f"{OUTPUT_DIR}/scene_{i:02d}_raw.png"
        if generate_flux_image(scene['prompt'], img_path, i):
            image_paths.append((img_path, i))
        time.sleep(2)  # Rate limiting
    
    if not image_paths:
        print("✗ No images generated!")
        return
    
    # Step 2: Gentle processing
    print("\n🎨 Step 2: Gentle processing (no CLAHE)...")
    processed_paths = []
    for img_path, idx in image_paths:
        out_path = f"{OUTPUT_DIR}/scene_{idx:02d}_processed.jpg"
        if gentle_process_image(img_path, out_path):
            processed_paths.append((out_path, idx))
    
    # Step 3: Create Ken Burns clips
    print("\n🎬 Step 3: Creating smooth Ken Burns clips...")
    clip_paths = []
    for proc_path, idx in processed_paths:
        scene = SCENES[idx - 1]
        clip_path = f"{OUTPUT_DIR}/clip_{idx:02d}.mp4"
        try:
            create_ken_burns_clip(
                proc_path, clip_path,
                scene['duration'],
                scene['zoom_start'],
                scene['zoom_end']
            )
            clip_paths.append((clip_path, scene['duration']))
        except Exception as e:
            print(f"✗ Clip creation failed: {e}")
    
    # Step 4: Concatenate with xfade
    print("\n🔗 Step 4: Concatenating with crossfade...")
    concat_file = f"{OUTPUT_DIR}/concat_list.txt"
    with open(concat_file, 'w') as f:
        for clip_path, _ in clip_paths:
            f.write(f"file '{clip_path}'\n")
    
    # Create video without audio first
    silent_video = f"{OUTPUT_DIR}/final_silent.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c", "copy",
        silent_video
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    
    # Step 5: Add bhajan music (generate tone if no audio)
    print("\n🎵 Step 5: Adding background bhajan...")
    bg_music = f"{OUTPUT_DIR}/bg_music.mp3"
    
    # Generate a simple drone tone as placeholder bhajan
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "lavfi:sine=frequency=128:duration=60",
        "-ac", "2",
        "-ar", "44100",
        bg_music
    ], capture_output=True)
    
    # Mux video + audio with fade
    final_video = f"{OUTPUT_DIR}/bhakti_video_final.mp4"
    total_dur = sum(d for _, d in clip_paths)
    
    cmd = [
        "ffmpeg", "-y",
        "-i", silent_video,
        "-i", bg_music,
        "-filter_complex", (
            f"[1:a]aloop=loop=-1:size=44100*{int(total_dur)},"
            f"atrim=duration={total_dur},"
            f"afade=t=in:d=2.0,"
            f"afade=t=out:st={total_dur-2.0}:d=2.0,"
            f"volume=0.6[a]"
        ),
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_video
    ]
    
    print(f"\n🎉 Creating final video: {final_video}")
    subprocess.run(cmd, capture_output=True, check=True)
    
    print("\n" + "=" * 60)
    print("✅ VIDEO COMPLETE!")
    print(f"📹 Output: {final_video}")
    print(f"⏱️  Duration: ~{total_dur}s")
    print(f"📐 Resolution: 1080×1920 (9:16)")
    print(f"🎨 Style: FLUX AI + Smooth Ken Burns + No Text")
    print("=" * 60)

if __name__ == "__main__":
    main()
