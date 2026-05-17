#!/usr/bin/env bash
# Daily Bhakti Video Generator — no_agent cron script
# Detects day → deity, generates video via existing scripts, uploads to YouTube
# No set -e: we handle errors explicitly with fallbacks
set -uo pipefail

source ~/.hermes/.env
export OPENROUTER_API_KEY

# Use hardcoded python3 path for cron compatibility
PY3="/usr/bin/python3"

DEITY_MAP=(
  [0]="Shiva"
  [1]="Hanuman"
  [2]="Ganesh"
  [3]="Durga"
  [4]="Krishna"
  [5]="Vishnu"
  [6]="Surya"
)

TITLES=(
  [0]="🔱 Har Har Mahadev - Shiv Shankar Bhajan | Shiva Tandava | Viral Bhakti Shorts"
  [1]="🙏 Jai Shri Ram - Hanuman Chalisa | Bajrangbali Ki Jai | Viral Hanuman Bhajan"
  [2]="🐘 Ganpati Bappa Morya ✨ | Ganesh Aarti | Mangalmurti Viral Shorts"
  [3]="🛡️ Maa Durga - Jai Ambe Gauri 🙏 | Navratri Special | Viral Devi Bhajan"
  [4]="🪄 Radhe Radhe - Shri Krishna 🙌 | Vrindavan Ki Leela | Viral Bhakti Shorts"
  [5]="🔱 ॐ नमो भगवते वासुदेवाय - Vishnu Bhajan | Hari Narayan | Viral Bhakti Shorts"
  [6]="☀️ Jai Surya Dev - Surya Bhagwan 🙏 | Surya Namaskar | Viral Bhakti Shorts"
)

TAGS=(
  [0]="shiva,mahadev,shivratri,bhakti,bhole baba,har har mahadev,shiv tandav,mantra,hindu god,devotional,viral shorts,shiv bhajan"
  [1]="hanuman,bajrangbali,hanumanchalisa,jai shri ram,sankat mochan,bhakti,devotional,viral shorts,hanuman bhajan,ram bhakt"
  [2]="ganesh,ganpati,ganeshchaturthi,mangalmurti,bappa,siddhivinayak,bhakti,viral shorts,ganesh aarti"
  [3]="durga,maadurga,navratri,jai ambe gouri,devi,chandi,sheron wali maa,bhakti,viral shorts,maa durga bhajan"
  [4]="krishna,radhekrishna,janmashtami,radhe radhe,shri krishna,govind,vrindavan,bhakti,viral shorts,krishna bhajan"
  [5]="vishnu,narayan,hari,bhagwan vishnu,vishnu bhajan,om namo bhagwate vasudevaya,vaishnav,sanatan dharma,bhakti,viral shorts"
  [6]="surya,suryadev,sun,surya namaskar,surya bhajan,bhakti,devotional,viral shorts,aditya,ravi dev"
)

QUERIES=(
  [0]="Shiva bhajan viral shorts 30 seconds"
  [1]="Hanuman bhajan viral shorts 30 seconds"
  [2]="Ganesh bhajan viral shorts 30 seconds"
  [3]="Durga Maa bhajan viral shorts 30 seconds"
  [4]="Krishna bhajan viral shorts 30 seconds"
  [5]="Vishnu bhajan viral shorts 30 seconds"
  [6]="Surya bhajan viral shorts 30 seconds"
)

WORKDIR="/home/ankurdixitd/bhakti-videos"
OUTDIR="$WORKDIR/lord-today"
LOG="$HOME/Video-generate-/daily_log.txt"
TOKEN="$WORKDIR/token.json"
CLIENT_SECRET="$WORKDIR/client_secret.json"

# Detect deity
WEEKDAY=$(date +%u)  # 1=Mon ... 7=Sun → 0=Mon for array
IDX=$((WEEKDAY - 1))
DEITY="${DEITY_MAP[$IDX]}"
TITLE="${TITLES[$IDX]}"
TAG="${TAGS[$IDX]}"
QUERY="${QUERIES[$IDX]}"

echo "==============================="
echo "  🙏 Daily Bhakti Video Generator"
echo "  Day: $WEEKDAY → Deity: $DEITY"
echo "==============================="

mkdir -p "$OUTDIR/frames"

# ── Step 1: Generate 2 images via Gemini 3 Pro ──────────────────────────
echo ""
echo "[1/4] Generating 2 images of $DEITY..."

PROMPTS=(
  "Photorealistic portrait of Lord $DEITY, divine Hindu god, sacred temple background, golden divine glow, spiritual atmosphere, highly detailed, 8k, devotional Indian art style, NO text NO watermark"
  "Cinematic artistic depiction of Lord $DEITY, majestic divine form, celestial clouds, warm golden lighting, sacred atmosphere, Hindu devotional painting, photorealistic, 8k, NO text NO watermark"
)

IMG_COUNT=0
PID1=""
PID2=""

# Run both image generations in parallel
for i in 0 1; do
  PROMPT="${PROMPTS[$i]}"
  OUTFILE="$OUTDIR/frames/frame_$((i+1)).png"

  if [ -f "$OUTFILE" ]; then
    echo "  ♻️  Reusing existing image $((i+1))"
    IMG_COUNT=$((IMG_COUNT + 1))
    continue
  fi

  echo "  🖼️ Generating image $((i+1))/2..."
  
  (
    RESPONSE=$(curl -s --max-time 45 -X POST "https://openrouter.ai/api/v1/chat/completions" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $OPENROUTER_API_KEY" \
      -H "HTTP-Referer: https://github.com/ankurdixit787" \
      -d "{
        \"model\": \"google/gemini-3-pro-image-preview\",
        \"messages\": [{\"role\":\"user\",\"content\":[{\"type\":\"text\",\"text\":\"Generate photorealistic 1024x1792 portrait: $PROMPT\"}]}],
        \"max_tokens\": 4096
      }" 2>/dev/null)

    B64=$(echo "$RESPONSE" | $PY3 -c "
import sys,json,re
data=json.load(sys.stdin)
msg=data.get('choices',[{}])[0].get('message',{})
images=msg.get('images',[])
if images:
    url=images[0].get('image_url',{}).get('url','')
    if url.startswith('data:image'):
        print(url.split(';base64,')[-1])
    elif url.startswith('http'):
        print('URL:'+url)
    sys.exit(0)
content=msg.get('content','')
m=re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=]+)',content)
if m: print(m.group(1))
else: print('NO_IMAGE')
" 2>/dev/null) || B64="PARSE_ERROR"

    if [[ "$B64" == URL:http* ]]; then
      URL="${B64#URL:}"
      curl -s "$URL" -o "$OUTFILE"
    elif [[ "$B64" != "NO_IMAGE" && "$B64" != "PARSE_ERROR" ]]; then
      echo "$B64" | base64 -d > "$OUTFILE" 2>/dev/null
    fi

    SIZE=$(stat -c%s "$OUTFILE" 2>/dev/null || echo 0)
    if [ "$SIZE" -gt 50000 ]; then
      echo "  ✅ Image $((i+1)) saved ($((SIZE/1024))KB)" >&2
      exit 0
    else
      rm -f "$OUTFILE"
      exit 1
    fi
  ) &
  
  if [ $i -eq 0 ]; then
    PID1=$!
  else
    PID2=$!
  fi
done

# Wait for parallel jobs
for pid in $PID1 $PID2; do
  [ -n "$pid" ] && wait "$pid" && IMG_COUNT=$((IMG_COUNT + 1))
done

if [ "$IMG_COUNT" -lt 1 ]; then
  echo "❌ No images generated, aborting"
  rm -rf "$OUTDIR"
  # Fallback: send Telegram notification
  $PY3 -c "
import requests
requests.post('https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage', json={
  'chat_id': '5909464423',
  'text': '⚠️ Bhakti video failed: No images generated for $DEITY today'
})"
  exit 1
fi

# ── Step 2: Create 30s video with crossfade ──────────────────────────────
echo ""
echo "[2/4] Creating 30s video..."

# Scale images to 1080x1920 (9:16) and create clips
CLIP_DIR="$OUTDIR/clips"
mkdir -p "$CLIP_DIR"

CLIP_NUM=0
for fp in "$OUTDIR"/frames/frame_*.png; do
  [ -f "$fp" ] || continue
  NUM=$((CLIP_NUM + 1))
  CLIP_OUT="$CLIP_DIR/clip_${NUM}.mp4"

  # Create 15s clip with subtle zoompan
  ffmpeg -y -loop 1 -i "$fp" \
    -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p,zoompan=z='1.02':d=450:s=1080x1920:fps=30" \
    -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p -t 15 \
    "$CLIP_OUT" 2>/dev/null; RC=$?

  if [ $RC -eq 0 ] && [ -f "$CLIP_OUT" ] && [ "$(stat -c%s "$CLIP_OUT" 2>/dev/null || echo 0)" -gt 100000 ]; then
    echo "  ✅ Clip $NUM (15s)"
    CLIP_NUM=$NUM
  else
    echo "  ⚠️ Clip $NUM failed (exit=$RC)"
    rm -f "$CLIP_OUT"
  fi
done

if [ "$CLIP_NUM" -lt 1 ]; then
  echo "❌ No clips created"
  rm -rf "$OUTDIR"
  exit 1
fi

# Crossfade clips if we have 2
VIDEO_NO_SOUND="$OUTDIR/video_nosound.mp4"
if [ "$CLIP_NUM" -ge 2 ]; then
  $PY3 -c "
import subprocess, os
clips = sorted(['$CLIP_DIR/clip_1.mp4', '$CLIP_DIR/clip_2.mp4'])
inputs = []
for c in clips:
    inputs.extend(['-i', c])
filter_str = '[0:v][1:v]xfade=transition=fade:duration=0.5:offset=14.5[vout]'
subprocess.run([
    'ffmpeg', '-y', *inputs,
    '-filter_complex', filter_str,
    '-map', '[vout]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
    '-preset', 'medium', '-crf', '20',
    '$VIDEO_NO_SOUND'
], capture_output=True, timeout=120)
"
  # Fallback: just concat
  if [ ! -f "$VIDEO_NO_SOUND" ] || [ "$(stat -c%s "$VIDEO_NO_SOUND")" -lt 100000 ]; then
    echo "  ⚠️ Crossfade failed, using concat fallback"
    LIST="$CLIP_DIR/list.txt"
    > "$LIST"
    for i in $(seq 1 $CLIP_NUM); do
      echo "file '$CLIP_DIR/clip_${i}.mp4'" >> "$LIST"
    done
    ffmpeg -y -f concat -safe 0 -i "$LIST" -c copy "$VIDEO_NO_SOUND" 2>/dev/null
  fi
else
  # Single clip — just use it
  cp "$CLIP_DIR/clip_1.mp4" "$VIDEO_NO_SOUND"
fi

# Trim to exactly 30s
VIDEO_TRIM="$OUTDIR/video_trim.mp4"
ffmpeg -y -i "$VIDEO_NO_SOUND" -t 30 -c copy "$VIDEO_TRIM" 2>/dev/null

# ── Step 3: Download best viral Shorts bhajan ────────────────────────────
echo ""
echo "[3/4] Finding best viral Shorts for $DEITY..."

BHAJAN="$OUTDIR/bhajan.mp3"
export BHAJAN_PATH="$BHAJAN"
export DEITY
export QUERY

# Search top 5 viral Shorts, pick the best (short + high views)
$PY3 << 'PYEOF'
import subprocess, json, sys, os

DEITY = os.environ.get("DEITY", "Vishnu")
QUERY = os.environ.get("QUERY", f"{DEITY} bhajan viral shorts")

# Search for top results
result = subprocess.run(
    ["yt-dlp", "--dump-json", "--no-warnings",
     f"ytsearch5:{QUERY}"],
    capture_output=True, text=True, timeout=30
)

lines = result.stdout.strip().split("\n")
candidates = []
for line in lines:
    if not line.strip():
        continue
    try:
        data = json.loads(line)
        dur = data.get("duration", 999)
        views = data.get("view_count", 0)
        title = data.get("title", "?")
        vid = data["id"]
        # Prefer videos under 60s (Shorts), but accept up to 90s
        if dur <= 90:
            candidates.append((dur, -views, title, vid))
    except:
        pass

if not candidates:
    print("NO_SHORTS_FOUND")
    sys.exit(1)

# Sort by views (highest first), pick best
candidates.sort()
dur, nviews, title, vid = candidates[0]
views = -nviews
url = f"https://youtu.be/{vid}"
print(f"🎵 [{dur}s | {views:,} views] {title}")
print(f"   {url}")

# Download audio (30-35s)
subprocess.run([
    "yt-dlp", "--quiet", "--no-warnings",
    url,
    "-x", "--audio-format", "mp3",
    "--postprocessor-args", "-ss 0 -t 35",
    "-o", os.environ["BHAJAN_PATH"]
], timeout=60)
print("AUDIO_OK")
PYEOF

VIDEO_FINAL="$OUTDIR/bhakti_${DEITY,,}.mp4"

if [ -f "$BHAJAN" ]; then
  echo "  ✅ Bhajan downloaded"
  # Add audio with fade-in/out
  ffmpeg -y -i "$VIDEO_TRIM" -i "$BHAJAN" \
    -filter_complex "[1:a]atrim=duration=30,afade=t=in:d=2,afade=t=out:st=28:d=2,volume=0.7[a]" \
    -map "0:v" -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest \
    "$VIDEO_FINAL" 2>/dev/null; RC=$?
  if [ $RC -ne 0 ] || [ ! -f "$VIDEO_FINAL" ] || [ "$(stat -c%s "$VIDEO_FINAL" 2>/dev/null || echo 0)" -lt 50000 ]; then
    echo "  ⚠️ Audio add failed (exit=$RC), trying concat..."
    # Fallback: just concat video + audio without filters
    ffmpeg -y -i "$VIDEO_TRIM" -i "$BHAJAN" -c:v copy -c:a aac -shortest \
      "$VIDEO_FINAL" 2>/dev/null; RC2=$?
    if [ $RC2 -ne 0 ] || [ ! -f "$VIDEO_FINAL" ] || [ "$(stat -c%s "$VIDEO_FINAL" 2>/dev/null || echo 0)" -lt 50000 ]; then
      echo "  ❌ Audio add fallback also failed"
      cp "$VIDEO_TRIM" "$VIDEO_FINAL"
    fi
  fi
else
  echo "  ⚠️ No bhajan found, video without audio"
  cp "$VIDEO_TRIM" "$VIDEO_FINAL"
fi

if [ ! -f "$VIDEO_FINAL" ] || [ "$(stat -c%s "$VIDEO_FINAL")" -lt 50000 ]; then
  echo "❌ Video creation failed"
  rm -rf "$OUTDIR"
  exit 1
fi

SIZE_MB=$(du -m "$VIDEO_FINAL" | cut -f1)
echo ""
echo "  ✅✅ VIDEO READY: $VIDEO_FINAL (${SIZE_MB}MB)"

# ── Step 4: Upload to YouTube ─────────────────────────────────────────────
echo ""
echo "[4/4] Uploading to YouTube..."

# Export env vars for the Python upload script
export VIDEO_PATH="$VIDEO_FINAL"
export DEITY
export TITLE
export TAG

$PY3 << 'PYEOF'
import os, json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO_PATH = os.environ["VIDEO_PATH"]
DEITY = os.environ["DEITY"]
TITLE = os.environ["TITLE"]
TAG_STR = os.environ["TAG"]
TAGS = TAG_STR.split(",") + ["shorts", "bhakti", "hindu", "devotional", "viral", "sanatan", "dharma", "youtubeshorts", "trending"]

tok = json.load(open("/home/ankurdixitd/bhakti-videos/token.json"))
client = json.load(open("/home/ankurdixitd/bhakti-videos/client_secret.json"))["web"]

creds = Credentials(
    token=tok.get("access_token"),
    refresh_token=tok.get("refresh_token"),
    token_uri=client["token_uri"],
    client_id=client["client_id"],
    client_secret=client["client_secret"],
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
if not creds.valid and creds.expired and creds.refresh_token:
    creds.refresh(Request())
    tok["access_token"] = creds.token
    json.dump(tok, open("/home/ankurdixitd/bhakti-videos/token.json", "w"))

youtube = build("youtube", "v3", credentials=creds)

body = {
    "snippet": {
        "title": TITLE,
        "description": f"""{TITLE}

भगवान {DEITY} की जय हो! 🙏✨

🙏 Like 👍 | Share 🔄 | Subscribe 🔔 | Bell 🛎️

#shorts #bhakti #{DEITY} #hindugod #devotional #viral #sanatan #dharma #mantra #aarti #hindutv #viralvideo #trending""",
        "tags": TAGS,
        "categoryId": "22"
    },
    "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
}

media = MediaFileUpload(VIDEO_PATH, chunksize=-1, resumable=True)
print(f"  Uploading {os.path.basename(VIDEO_PATH)}...")
response = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
vid = response["id"]
url = f"https://youtu.be/{vid}"
print(f"  ✅ {url}")

with open("/home/ankurdixitd/Video-generate-/daily_log.txt", "a") as f:
    from datetime import datetime
    f.write(f"{datetime.now().isoformat()} | {DEITY} | {url}\n")

print(f"VIDEO_URL:{url}")
PYEOF

UPLOAD_RESULT=$?

# ── Step 5: Cleanup ──────────────────────────────────────────────────────
echo ""
echo "[5/5] Cleaning up..."
rm -rf "$OUTDIR"
echo "  🧹 Deleted $OUTDIR"

if [ $UPLOAD_RESULT -eq 0 ]; then
  echo ""
  echo "==============================="
  echo "  ✅✅✅ BHAKTI VIDEO COMPLETE! 🚩"
  echo "==============================="
  exit 0
else
  echo "❌ Upload failed"
  exit 1
fi