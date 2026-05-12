"""
Music Manager - Handles background music for devotional videos.
Uses shared FFmpeg utilities (ffmpeg_utils.py).
"""

from pathlib import Path
import random
import json
import urllib.request
from loguru import logger

from ffmpeg_utils import find_ffmpeg, mix_audio


class MusicManager:
    """Manages background music selection, generation, and mixing."""

    def __init__(self, config_path: str = "config.yaml"):
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        mc = self.config["music"]
        self.provider: str = mc.get("provider", "audiocraft")
        self.audiocraft_url: str = mc.get("audiocraft_url", "http://localhost:8080")
        self.local_music_dir: Path = Path(mc.get("local_music_dir", "assets/music/"))
        self.volume_reduction: float = mc.get("volume_reduction", 0.3)
        self._ffmpeg = find_ffmpeg()

    def get_background_music(self, output_path: str, duration_sec: float = 60,
                             deity: str = "krishna") -> str | None:
        """Get background music track for the specified duration."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try local music first
        local_path = self._get_local_music()
        if local_path:
            result = self._adjust_duration(local_path, str(output_path), duration_sec)
            if result:
                return result

        # Try AudioCraft
        if self.provider == "audiocraft":
            try:
                return self._generate_music(duration_sec, str(output_path), deity)
            except Exception as e:
                logger.warning(f"AudioCraft failed: {e}")

        # Fallback: generate silence
        return self._generate_silence(duration_sec, str(output_path))

    def _get_local_music(self) -> str | None:
        """Pick a random music file from local directory."""
        if self.local_music_dir.exists():
            music_files = list(self.local_music_dir.glob("*.mp3"))
            if music_files:
                return str(random.choice(music_files))
        return None

    def _adjust_duration(self, input_path: str, output_path: str,
                         target_duration: float) -> str | None:
        """Loop or trim music to match target duration using FFmpeg."""
        import subprocess
        import re

        try:
            result = subprocess.run(
                [self._ffmpeg, "-i", input_path, "-f", "null", "-"],
                capture_output=True, text=True, timeout=10,
            )
            duration_match = re.search(
                r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr,
            )
            if not duration_match:
                return None
            h, m, s = duration_match.groups()
            input_duration = float(h) * 3600 + float(m) * 60 + float(s)

            if input_duration < target_duration:
                # Loop the audio
                loops = int(target_duration / input_duration) + 1
                concat_file = str(Path(output_path).parent / "concat_list.txt")
                with open(concat_file, "w") as f:
                    for _ in range(loops):
                        f.write(f"file '{input_path}'\n")

                subprocess.run(
                    [self._ffmpeg, "-f", "concat", "-safe", "0",
                     "-i", concat_file, "-t", str(target_duration),
                     "-c", "copy", "-y", output_path],
                    capture_output=True, timeout=30,
                )
            else:
                # Trim to exact duration
                subprocess.run(
                    [self._ffmpeg, "-i", input_path, "-t", str(target_duration),
                     "-c", "copy", "-y", output_path],
                    capture_output=True, timeout=30,
                )

            if Path(output_path).exists():
                logger.info(f"Music adjusted to {target_duration}s: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"Audio adjustment failed: {e}")
        return None

    def _generate_music(self, duration: float, output_path: str,
                        deity: str = "krishna") -> str:
        """Generate devotional music using AudioCraft/MusicGen."""
        prompt = self._build_music_prompt(deity)
        payload = json.dumps({"prompt": prompt, "duration": duration}).encode()
        req = urllib.request.Request(
            f"{self.audiocraft_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            music_data = result.get("audio", "")
            import base64
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(music_data))
        return str(output_path)

    def _build_music_prompt(self, deity: str) -> str:
        """Build MusicGen prompt for devotional music."""
        prompts = {
            "krishna": "Indian devotional bhajan flute sitar calm spiritual music",
            "shiva": "Indian meditation mantra bhajan calm peaceful spiritual music",
            "ram": "Indian devotional bhajan ramayana spiritual uplifting music",
        }
        return prompts.get(deity.lower(), "Indian devotional spiritual calm music")

    def _generate_silence(self, duration_sec: float, output_path: str) -> str:
        """Generate silent audio using FFmpeg."""
        import subprocess
        subprocess.run(
            [self._ffmpeg, "-f", "lavfi", "-i",
             f"anullsrc=r=44100:cl=mono", "-t",
             str(duration_sec), "-c:a", "aac", "-b:a", "128k",
             "-y", output_path],
            capture_output=True, timeout=30,
        )
        logger.warning(f"Silence track created as fallback: {output_path}")
        return str(output_path)