# AI Devotional Video Generator 🎬

Automatically generate 1-minute Hindi devotional/bhakti videos with AI. 

**Tech Stack:** Ollama + Edge-TTS + ComfyUI/Stable Diffusion + MoviePy + FFmpeg

## Features

- 🤖 **AI Script Generation** — Uses Ollama (Llama 3/Mistral) to write Hindi devotional scripts
- 🗣️ **Hindi Female Voiceover** — Edge-TTS with `hi-IN-SwaraNeural` natural voice
- 🎨 **AI Image Generation** — ComfyUI or Stable Diffusion for divine imagery
- 📝 **Auto Subtitles** — Hindi SRT subtitles with proper timing
- 🎵 **Background Music** — AudioCraft devotional music + voice mixing
- 📱 **Vertical Video** — 1080×1920 (9:16) for YouTube Shorts, Instagram Reels
- 🌐 **REST API** — FastAPI server mode for remote generation
- 🐳 **Docker Support** — Ready for Railway deployment

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate a video
python main.py --deity krishna --topic "Hare Krishna Mahamantra"

# Or run as a server
python main.py --server --port 8000
```

## Supported Deities

| Deity | Command |
|-------|---------|
| Krishna | `--deity krishna` |
| Shiva | `--deity shiva` |
| Ram | `--deity ram` |

## API Endpoints

- `GET /health` — Health check
- `POST /generate?deity=krishna&topic=...` — Generate video on demand

## Project Structure

```
├── config.yaml              # Main configuration
├── requirements.txt         # Python dependencies
├── main.py                  # CLI & server entry point
├── Dockerfile               # Docker build
├── railway.json             # Railway deployment config
├── src/
│   ├── script_generator.py  # Ollama script generation
│   ├── voice_generator.py   # Edge-TTS voiceover
│   ├── image_generator.py   # ComfyUI/SD image gen
│   ├── subtitle_generator.py # SRT subtitle creation
│   ├── music_manager.py     # Background music mixing
│   ├── video_composer.py    # MoviePy video assembly
│   └── pipeline.py          # End-to-end orchestrator
└── tests/
    └── test_pipeline.py     # Unit tests
```

## Deployment (Railway)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/...)

1. Push to GitHub
2. Connect Railway to your repo
3. Railway auto-detects the Dockerfile

## License

MIT