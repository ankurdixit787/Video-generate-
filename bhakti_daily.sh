#!/usr/bin/env bash
# Daily Bhakti Video Generator — OPTIMIZED for speed
# Target: Complete in under 90 seconds
set -uo pipefail

source ~/.hermes/.env
export OPENROUTER_API_KEY

PY3="/usr/bin/python3"
VDUR=10

DEITY_MAP=([0]="Shiva" [1]="Hanuman" [2]="Ganesh" [3]="Durga" [4]="Krishna" [5]="Hanuman" [6]="Surya")

TITLES=(
  [0]="🔱 Har Har Mahadev | Shiv Tandava | Mahadev Bhajan 2026"
  [1]="🙏 Jai Bajrangbali | Hanuman Chalisa | Hanuman Bhajan 2026"
  [2]="🐘 Ganpati Bappa Morya | Ganesh Aarti | Siddhivinayak Bhajan"
  [3]="🛡️ Jai Maa Durga | Durga Chalisa | Navratri Bhajan 2026"
  [4]="🪄 Radhe Radhe | Krishna Bhajan | Govind Bolo Gopal Bolo"
  [5]="🙏 Jai Bajrangbali | Hanuman Chalisa | Hanuman Bhajan 2026"
  [6]="☀️ Jai Surya Dev | Surya Namaskar Mantra | Aditya Hridayam"
)

TAGS=(
  [0]="shiva,mahadev,shivratri,bhakti,bhole baba,har har mahadev,shiv tandav,mantra,hindu god,devotional,shiv bhajan,shiv shankar,mahadev status,shiva bhakti,om namah shivay,shiv parvati,tridev,kailash,shivling,neelkanth"
  [1]="hanuman,bajrangbali,hanumanchalisa,jai shri ram,sankat mochan,bhakti,devotional,hanuman bhajan,ram bhakt,hanuman status,jai bajrangbali,sundar kand,hanuman ji,shri ram,ayodhya,hanuman gayatri"
  [2]="ganesh,ganpati,ganeshchaturthi,mangalmurti,bappa,siddhivinayak,bhakti,ganesh aarti,ganpati bappa morya,ganesh status,vighnaharta,ekadanta,ganesh ji,remover of obstacles,ganesh mantra"
  [3]="durga,maadurga,navratri,jai ambe gouri,devi,chandi,sheron wali maa,bhakti,maa durga bhajan,durga status,durga chalisa,kali mata,shakti,durga puja,mahishasura mardini,jai maa"
  [4]="krishna,radhekrishna,janmashtami,radhe radhe,shri krishna,govind,vrindavan,bhakti,krishna bhajan,krishna status,govinda,gopal,banke bihari,krishna flute,makhan chor,yashoda,mathura"
  [5]="hanuman,bajrangbali,hanumanchalisa,jai shri ram,sankat mochan,bhakti,devotional,hanuman bhajan,ram bhakt,hanuman status,jai bajrangbali,sundar kand,hanuman ji,shri ram,ayodhya,hanuman gayatri"
  [6]="surya,suryadev,sun god,surya namaskar,surya bhajan,bhakti,aditya,ravi dev,surya mantra,gayatri mantra,sun worship,surya status,aditya hridayam,surya dev,chhath puja,surya devta"
)

QUERIES=(
  [0]="Shiva status shorts 1M"
  [1]="Hanuman status shorts 1M"
  [2]="Ganesh status shorts 1M"
  [3]="Durga Maa status shorts 1M"
  [4]="Krishna status shorts 1M"
  [5]="Hanuman status shorts 1M"
  [6]="Surya status shorts 1M"
)

WORKDIR="/home/ankurdixitd/bhakti-videos"
OUTDIR="$WORKDIR/lord-today"
TOKEN_FILE="$WORKDIR/token.json"
CLIENT_SECRET="$WORKDIR/client_secret.json"
LOG_FILE="$HOME/Video-generate-/daily_log.txt"

WEEKDAY=$(date +%u)
IDX=$((WEEKDAY - 1))
DEITY="${DEITY_MAP[$IDX]}"
TITLE="${TITLES[$IDX]}"
TAG="${TAGS[$IDX]}"
QUERY="${QUERIES[$IDX]}"

echo "==============================="
echo "  🙏 Daily Bhakti Video Generator"
echo "  Day: $WEEKDAY → Deity: $DEITY"
echo "  Duration: ${VDUR}s · 1 image"
echo "==============================="

mkdir -p "$OUTDIR/frames"

# ── Step 1: Generate 1 image (reuse if <48h old) ──────────────────────────
echo ""
echo "[1/4] Generating image of $DEITY..."

STYLES=(
  "photorealistic, cinematic dramatic lighting, golden hour glow, intricate details"
  "divine ethereal glow, soft ambient light, mystical atmosphere, highly detailed"
  "temple oil painting style, rich warm colors, sacred atmosphere, 8k detail"
  "cinematic portrait, rim lighting, golden halo background, devotional art"
  "traditional Indian art style, vibrant colors, divine radiance, temple setting"
  "hyperrealistic, volumetric lighting, sacred smoke effects, golden aura"
  "spiritual portrait, backlit divine glow, intricate jewelry, 8k resolution"
  "devotional art, warm golden tones, temple pillars background, dramatic angle"
)
ANGLES=(
  "front facing portrait, direct eye contact"
  "slight three-quarter view, looking upward"
  "profile view, divine side lighting"
  "low angle looking up, majestic perspective"
  "close-up portrait, intense expression"
  "wide portrait, full body with temple background"
)
BACKGROUNDS=(
  "ancient Hindu temple with golden pillars and oil lamps"
  "mountain temple at sunrise with mist and golden light"
  "sacred river bank with temple ghats and diyas"
  "cosmic background with stars and divine light rays"
  "forest temple with ancient trees and spiritual aura"
  "cave temple with stalactites and glowing crystals"
)

STYLE_IDX=$((RANDOM % ${#STYLES[@]}))
ANGLE_IDX=$((RANDOM % ${#ANGLES[@]}))
BG_IDX=$((RANDOM % ${#BACKGROUNDS[@]}))

PROMPT="Generate photorealistic 1024x1792 portrait of Lord $DEITY, divine Hindu god. ${STYLES[$STYLE_IDX]}. ${ANGLES[$ANGLE_IDX]}. Background: ${BACKGROUNDS[$BG_IDX]}. NO text NO watermark NO logo. Unique composition, varied pose and lighting each time."

OFILE="$OUTDIR/frames/frame_1.png"

# Check if image exists and is less than 48 hours old
if [ -f "$OFILE" ]; then
  FILE_AGE=$(( $(date +%s) - $(stat -c %Y "$OFILE") ))
  MAX_AGE=$((48 * 3600))
  if [ "$FILE_AGE" -lt "$MAX_AGE" ]; then
    echo "  ♻️ Reusing image ($((FILE_AGE / 3600))h old, max 48h)"
    IMG_OK=1
  else
    echo "  🗑️ Image too old ($((FILE_AGE / 3600))h), generating new one"
    rm -f "$OFILE"
  fi
fi

if [ -z "${IMG_OK:-}" ]; then
  echo "  🖼️ Generating NEW image..."
  RESP=$(curl -s --max-time 30 -X POST "https://openrouter.ai/api/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -H "HTTP-Referer: https://github.com/ankurdixit787" \
    -d "{
      \"model\": \"google/gemini-3-pro-image-preview\",
      \"messages\": [{\"role\":\"user\",\"content\":[{\"type\":\"text\",\"text\":\"$PROMPT\"}]}],
      \"max_tokens\": 4096
    }" 2>/dev/null)

  B64=$(echo "$RESP" | $PY3 -c "
import sys,json,re
d=json.load(sys.stdin)
msg=d.get('choices',[{}])[0].get('message',{})
imgs=msg.get('images',[])
if imgs:
    u=imgs[0].get('image_url',{}).get('url','')
    if u.startswith('data:image'):
        print(u.split(';base64,')[-1])
    elif u.startswith('http'):
        print('URL:'+u)
    sys.exit(0)
c=msg.get('content','')
m=re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)',c)
if m: print(m.group(1))
else: print('NO_IMAGE')
" 2>/dev/null) || B64="PARSE_ERROR"

  if [[ "$B64" == URL:http* ]]; then
    URL="${B64#URL:}"
    curl -s --max-time 15 "$URL" -o "$OFILE"
  elif [[ "$B64" != "NO_IMAGE" && "$B64" != "PARSE_ERROR" ]]; then
    echo "$B64" | base64 -d > "$OFILE" 2>/dev/null
  fi

  SIZE=$(stat -c%s "$OFILE" 2>/dev/null || echo 0)
  if [ "$SIZE" -gt 50000 ]; then
    echo "  ✅ Image saved ($((SIZE/1024))KB)"
    IMG_OK=1
  fi
fi

if [ -z "${IMG_OK:-}" ]; then
  echo "❌ No image generated, aborting"
  rm -rf "$OUTDIR"
  exit 1
fi

# ── Step 2: Create 10s video (optimized — fewer frames) ─────────────────────
echo ""
echo "[2/4] Creating ${VDUR}s video..."

CLIP_OUT="$OUTDIR/clip.mp4"
FRAMES=$((VDUR * 24))  # 24fps instead of 30 for speed

$PY3 << PYEOF
import cv2, numpy as np, subprocess, os

img = cv2.imread("$OFILE")
h, w = img.shape[:2]
cx, cy = w // 2, h // 2
frames_dir = "$OUTDIR/frames_3d"
os.makedirs(frames_dir, exist_ok=True)

FRAMES = $FRAMES
for i in range(FRAMES):
    t = i / FRAMES
    scale = 1.0 + 0.35 * np.sin(t * np.pi)
    angle = 5 * np.sin(t * 4 * np.pi)
    M = cv2.getRotationMatrix2D((cx, cy), angle, scale)
    rotated = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    resized = cv2.resize(rotated, (1080, 1920), interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(f"{frames_dir}/frame_{i:04d}.png", resized)

subprocess.run([
    "ffmpeg", "-y", "-framerate", "24",
    "-i", f"{frames_dir}/frame_%04d.png",
    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
    "-pix_fmt", "yuv420p", "-t", str($VDUR),
    "$CLIP_OUT"
], capture_output=True)
print("VIDEO_CREATED")
PYEOF

if [ -f "$CLIP_OUT" ] && [ "$(stat -c%s "$CLIP_OUT" 2>/dev/null || echo 0)" -gt 100000 ]; then
  echo "  ✅ Video done"
  cp "$CLIP_OUT" "$OUTDIR/video_nosound.mp4"
else
  echo "❌ Video creation failed"
  rm -rf "$OUTDIR"
  exit 1
fi

# ── Step 3: Find trending sound (optimized — single search) ─────────────────
echo ""
echo "[3/4] Finding trending sound for $DEITY..."

BHAJAN="$OUTDIR/bhajan.mp3"
export BHAJAN_PATH="$BHAJAN"
export DEITY QUERY

USED_FILE="$WORKDIR/used_sounds.json"
export USED_FILE

$PY3 << 'PYEOF'
import subprocess, json, sys, os

DEITY = os.environ["DEITY"]
QUERY = os.environ["QUERY"]
USED_FILE = os.environ["USED_FILE"]

used_ids = set()
if os.path.exists(USED_FILE):
    try:
        data = json.load(open(USED_FILE))
        used_ids = set(data.get("used_ids", []))
    except:
        pass

# Single search query
r = subprocess.run(
    ["yt-dlp", "--extractor-args", "youtube:player_client=android",
     "--dump-json", "--no-warnings", f"ytsearch5:{DEITY} status shorts 1M"],
    capture_output=True, text=True, timeout=15
)

seen = set()
all_v = []
for line in r.stdout.strip().split("\n"):
    if not line.strip():
        continue
    try:
        d = json.loads(line)
        if d["id"] not in seen:
            seen.add(d["id"])
            all_v.append(d)
    except:
        pass

fresh_v = [d for d in all_v if d["id"] not in used_ids]

c = [(d["duration"], d["view_count"], d["title"], d["id"])
     for d in fresh_v if 10 <= d.get("duration", 0) <= 20 and d.get("view_count", 0) >= 50000]
c.sort(key=lambda x: -x[1])

if not c:
    c = [(d["duration"], d["view_count"], d["title"], d["id"])
         for d in fresh_v if 10 <= d.get("duration", 0) <= 30]
    c.sort(key=lambda x: -x[1])

if not c:
    print("NO_SHORTS_FOUND")
    sys.exit(1)

dur, views, title, vid = c[0]
url = f"https://youtu.be/{vid}"
print(f"🎵 [{dur}s | {views:,} views] {title}")

subprocess.run([
    "yt-dlp", "--extractor-args", "youtube:player_client=android",
    "--quiet", "--no-warnings", url,
    "-x", "--audio-format", "mp3",
    "--postprocessor-args", "ffmpeg:-ss 0 -t 12",
    "-o", os.environ["BHAJAN_PATH"]
], timeout=30)

used_ids.add(vid)
json.dump({"used_ids": list(used_ids)}, open(USED_FILE, "w"))
print("AUDIO_OK")
PYEOF

FINAL="$OUTDIR/bhakti_${DEITY,,}.mp4"

if [ -f "$BHAJAN" ]; then
  echo "  ✅ Sound downloaded"
  ffmpeg -y -i "$OUTDIR/video_nosound.mp4" -i "$BHAJAN" \
    -filter_complex "[1:a]atrim=duration=${VDUR},afade=t=in:d=1,afade=t=out:st=8:d=2,volume=1.2[a]" \
    -map "0:v" -map "[a]" -c:v copy -c:a aac -b:a 192k \
    -t $VDUR \
    "$FINAL" 2>/dev/null
else
  echo "  ⚠️ No sound, silent video"
  cp "$OUTDIR/video_nosound.mp4" "$FINAL"
fi

if [ ! -f "$FINAL" ] || [ "$(stat -c%s "$FINAL")" -lt 50000 ]; then
  echo "❌ Video creation failed"
  rm -rf "$OUTDIR"
  exit 1
fi

echo ""
echo "  ✅✅ VIDEO READY: $FINAL ($(du -m "$FINAL" | cut -f1)MB)"

# ── Step 4: Upload to YouTube ──────────────────────────────────────────────
echo ""
echo "[4/4] Uploading to YouTube..."

export VIDEO_PATH="$FINAL"
export DEITY TITLE TAG

$PY3 << 'PYEOF'
import os, json
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VP = os.environ["VIDEO_PATH"]
DEITY = os.environ["DEITY"]
TITLE = os.environ["TITLE"]
TAGS = os.environ["TAG"].split(",") + ["shorts", "bhakti", "hindu", "viral", "trending", "youtubeshorts"]

tok = json.load(open("/home/ankurdixitd/bhakti-videos/token.json"))
cli = json.load(open("/home/ankurdixitd/bhakti-videos/client_secret.json"))["web"]

creds = Credentials(
    token=tok.get("access_token"),
    refresh_token=tok.get("refresh_token"),
    token_uri=cli["token_uri"],
    client_id=cli["client_id"],
    client_secret=cli["client_secret"],
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
if not creds.valid and creds.refresh_token:
    creds.refresh(Request())
    tok["access_token"] = creds.token
    json.dump(tok, open("/home/ankurdixitd/bhakti-videos/token.json", "w"))

yt = build("youtube", "v3", credentials=creds)

body = {
    "snippet": {
        "title": TITLE,
        "description": f"""{TITLE}

🙏 भगवान {DEITY} की जय हो! Har Har Mahadev! 🙏

🔔 हर रोज़ नई भक्ति वीडियो के लिए चैनल को Subscribe करें और Bell 🔔 दबाएं!

📌 इस वीडियो में:
• {DEITY} जी की दिव्य भक्ति गीत
• सुंदर भगवान की तस्वीर
• मंत्र जाप और आरती

🌐 हमारे चैनल पर देखें: https://www.youtube.com/@BhaktiShorts
📱 Instagram: https://www.instagram.com/bhakti_shorts
📘 Facebook: https://www.facebook.com/bhakti.shorts

⚠️ Disclaimer: यह वीडियो AI द्वारा generate की गई है। भक्ति का उद्देश्य मात्र पूजा और आस्था है।

#{DEITY} #bhakti #devotional #hindu #god #mantra #aarti #bhajan #hinduism #spiritual #divine #shorts #viral #trending #india #sanatandharma""",
        "tags": TAGS, "categoryId": "22"
    },
    "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
}

media = MediaFileUpload(VP, chunksize=-1, resumable=True)
resp = yt.videos().insert(part="snippet,status", body=body, media_body=media).execute()
vid = resp["id"]
url = f"https://youtu.be/{vid}"
print(f"  ✅ {url}")

with open("/home/ankurdixitd/Video-generate-/daily_log.txt", "a") as f:
    f.write(f"{datetime.now().isoformat()} | {DEITY} | {url}\n")
print(f"VIDEO_URL:{url}")
PYEOF

UP_RES=$?

# ── Cleanup ─────────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Cleaning up..."
rm -rf "$OUTDIR"
echo "  🧹 Deleted $OUTDIR"

[ $UP_RES -eq 0 ] && echo -e "\n✅✅✅ BHAKTI VIDEO COMPLETE! 🚩" && exit 0
echo "❌ Upload failed"
exit 1
