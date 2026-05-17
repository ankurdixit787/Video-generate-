#!/usr/bin/env bash
# Daily Bhakti Video Generator — no_agent cron script
# 1 image, 10s video, viral trending Shorts sound (10-15s)
set -uo pipefail

source ~/.hermes/.env
export OPENROUTER_API_KEY

PY3="/usr/bin/python3"
VDUR=10  # 10 seconds

DEITY_MAP=([0]="Shiva" [1]="Hanuman" [2]="Ganesh" [3]="Durga" [4]="Krishna" [5]="Vishnu" [6]="Surya")

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
  [0]="Shiva status shorts 1M"
  [1]="Hanuman status shorts 1M"
  [2]="Ganesh status shorts 1M"
  [3]="Durga Maa status shorts 1M"
  [4]="Krishna status shorts 1M"
  [5]="Vishnu status shorts 1M"
  [6]="Surya status shorts 1M"
)

WORKDIR="/home/ankurdixitd/bhakti-videos"
OUTDIR="$WORKDIR/lord-today"
TOKEN_FILE="$WORKDIR/token.json"
CLIENT_SECRET="$WORKDIR/client_secret.json"
LOG_FILE="$HOME/Video-generate-/daily_log.txt"

# Detect deity
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

# ── Step 1: Generate 1 image ──────────────────────────────────────────────
echo ""
echo "[1/4] Generating image of $DEITY..."

PROMPT="Photorealistic portrait of Lord $DEITY, divine Hindu god, sacred temple background, golden divine glow, spiritual atmosphere, highly detailed, 8k, devotional Indian art style, NO text NO watermark"
OFILE="$OUTDIR/frames/frame_1.png"

if [ -f "$OFILE" ]; then
  echo "  ♻️  Reusing existing image"
  IMG_OK=1
else
  echo "  🖼️ Generating image..."
  RESP=$(curl -s --max-time 45 -X POST "https://openrouter.ai/api/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -H "HTTP-Referer: https://github.com/ankurdixit787" \
    -d "{
      \"model\": \"google/gemini-3-pro-image-preview\",
      \"messages\": [{\"role\":\"user\",\"content\":[{\"type\":\"text\",\"text\":\"Generate photorealistic 1024x1792 portrait: $PROMPT\"}]}],
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
    curl -s "$URL" -o "$OFILE"
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

# ── Step 2: Create 10s video clip (10s) ────────────────────────────────────
echo ""
echo "[2/4] Creating ${VDUR}s video..."

CLIP_OUT="$OUTDIR/clip.mp4"
FRAMES=$((VDUR * 30))

ffmpeg -y -loop 1 -i "$OFILE" \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p,zoompan=z='1.02':d=${FRAMES}:s=1080x1920:fps=30" \
  -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p -t $VDUR \
  "$CLIP_OUT" 2>/dev/null

if [ -f "$CLIP_OUT" ] && [ "$(stat -c%s "$CLIP_OUT" 2>/dev/null || echo 0)" -gt 100000 ]; then
  echo "  ✅ Video done"
  cp "$CLIP_OUT" "$OUTDIR/video_nosound.mp4"
else
  echo "❌ Video creation failed"
  rm -rf "$OUTDIR"
  exit 1
fi

# ── Step 3: Find trending 10-12s sound ────────────────────────────────────
echo ""
echo "[3/4] Finding trending sound for $DEITY..."

BHAJAN="$OUTDIR/bhajan.mp3"
export BHAJAN_PATH="$BHAJAN"
export DEITY QUERY

$PY3 << 'PYEOF'
import subprocess, json, sys, os

DEITY = os.environ["DEITY"]
QUERY = os.environ["QUERY"]

queries = [
    QUERY,
    f"{DEITY} whatsapp status trending",
    f"viral {DEITY} bhajan shorts",
    f"{DEITY} trending shorts",
]

seen=set()
all_v=[]
for q in queries:
    r=subprocess.run(["yt-dlp","--dump-json","--no-warnings",f"ytsearch10:{q}"],
        capture_output=True,text=True,timeout=20)
    for line in r.stdout.strip().split("\n"):
        if not line.strip(): continue
        try:
            d=json.loads(line)
            if d["id"] not in seen:
                seen.add(d["id"])
                all_v.append(d)
        except: pass

# Tier 1: 10-15s, 50k+ views
c=[(d["duration"],d["view_count"],d["title"],d["id"])
   for d in all_v if d.get("duration",999)<=15 and d.get("view_count",0)>=50000]
c.sort(key=lambda x:-x[1])

# Tier 2: 5-20s, 10k+ views
if not c:
    c=[(d["duration"],d["view_count"],d["title"],d["id"])
       for d in all_v if d.get("duration",999)<=20 and d.get("view_count",0)>=10000]
    c.sort(key=lambda x:-x[1])

# Tier 3: any 5-20s
if not c:
    c=[(d["duration"],d["view_count"],d["title"],d["id"])
       for d in all_v if d.get("duration",999)<=20]
    c.sort(key=lambda x:-x[1])

if not c:
    print("NO_SHORTS_FOUND")
    sys.exit(1)

dur,views,title,vid=c[0]
url=f"https://youtu.be/{vid}"
print(f"🎵 [{dur}s | {views:,} views] {title}")
print(f"   {url}")

subprocess.run(["yt-dlp","--quiet","--no-warnings",url,
    "-x","--audio-format","mp3",
    "--postprocessor-args","-ss 0 -t 10",
    "-o",os.environ["BHAJAN_PATH"]],timeout=60)
print("AUDIO_OK")
PYEOF

FINAL="$OUTDIR/bhakti_${DEITY,,}.mp4"

if [ -f "$BHAJAN" ]; then
  echo "  ✅ Sound downloaded"
  ffmpeg -y -i "$OUTDIR/video_nosound.mp4" -i "$BHAJAN" \
    -filter_complex "[1:a]atrim=duration=${VDUR},afade=t=in:d=1,afade=t=out:st=8:d=2,volume=0.75[a]" \
    -map "0:v" -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest \
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

VP=os.environ["VIDEO_PATH"]
DEITY=os.environ["DEITY"]
TITLE=os.environ["TITLE"]
TAGS=os.environ["TAG"].split(",")+["shorts","bhakti","hindu","viral","trending","youtubeshorts"]

tok=json.load(open("/home/ankurdixitd/bhakti-videos/token.json"))
cli=json.load(open("/home/ankurdixitd/bhakti-videos/client_secret.json"))["web"]

creds=Credentials(
    token=tok.get("access_token"),
    refresh_token=tok.get("refresh_token"),
    token_uri=cli["token_uri"],
    client_id=cli["client_id"],
    client_secret=cli["client_secret"],
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
if not creds.valid and creds.refresh_tok:
    creds.refresh(Request())
    tok["access_token"]=creds.token
    json.dump(tok,open("/home/ankurdixitd/bhakti-videos/token.json","w"))

yt=build("youtube","v3",credentials=creds)

body={
    "snippet":{"title":TITLE,"description":f"""{TITLE}\nभगवान {DEITY} की जय हो! 🙏✨\n\n#shorts #{DEITY} #bhakti #bhakti #viral #trending""",
    "tags":TAGS,"categoryId":"22"},
    "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False}
}

media=MediaFileUpload(VP,chunksize=-1,resumable=True)
resp=yt.videos().insert(part="snippet,status",body=body,media_body=media).execute()
vid=resp["id"]
url=f"https://youtu.be/{vid}"
print(f"  ✅ {url}")

with open("/home/ankurdixitd/Video-generate-/daily_log.txt","a") as f:
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
