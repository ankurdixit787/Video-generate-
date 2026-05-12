"""Shared FFmpeg utilities — use this instead of duplicated code."""

import shutil
import subprocess
import re
from pathlib import Path


def find_ffmpeg() -> str:
    """Return path to ffmpeg binary."""
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def get_audio_duration(audio_path: str) -> float:
    """Get exact audio duration in seconds using ffprobe."""
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=10,
        )
        val = result.stdout.strip()
        return float(val) if val else 60.0
    except Exception:
        pass

    # Fallback: parse from ffmpeg stderr
    ffmpeg = find_ffmpeg()
    try:
        result = subprocess.run(
            [ffmpeg, "-i", audio_path, "-f", "null", "-"],
            capture_output=True, text=True, timeout=10,
        )
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
        if m:
            h, mi, s = m.groups()
            return float(h) * 3600 + float(mi) * 60 + float(s)
    except Exception:
        pass

    return 60.0


def get_clip_duration(media_path: str) -> float:
    """Get duration of any video/audio clip using ffprobe."""
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", media_path],
            capture_output=True, text=True, timeout=10,
        )
        val = result.stdout.strip()
        return float(val) if val else 15.0
    except Exception:
        return 15.0


def mix_audio(music_path: str, voice_path: str, output_path: str,
              music_volume: float = 0.3) -> str:
    """Mix background music with voice using FFmpeg."""
    ffmpeg = find_ffmpeg()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            ffmpeg, "-y",
            "-i", music_path,
            "-i", voice_path,
            "-filter_complex",
            f"[0:a]volume={music_volume}[music];"
            f"[music][1:a]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]",
            "-c:a", "aac", "-b:a", "128k",
            str(output_path),
        ],
        capture_output=True, timeout=30,
    )
    return str(output_path)