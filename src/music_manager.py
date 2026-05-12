"""
Music Manager - Handles background music for devotional videos.
Uses FFmpeg directly for audio operations (no pydub dependency).
"""

from pathlib import Path
import random
import json
import subprocess
import urllib.request
from loguru import logger


class MusicManager:
    """Manages background music selection, generation, and mixing."""

    def __init__(self, config_path="config.yaml"):
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        mc = self.config["music"]
        self.provider = mc.get("provider", "audiocraft")
        self.audiocraft_url = mc["audiocraft_url"]
        self.local_music_dir = Path(mc["local_music_dir"])
        self.volume_reduction = mc["volume_reduction"]
        self._ffmpeg = self._find_ffmpeg()

    def _find_ffmpeg(self):
        """Find ffmpeg binary."""
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

    def get_background_music(self, output_path, duration_sec=60, deity="krishna"):
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

        # Fallback: generate silence using ffmpeg
        return self._generate_silence(duration_sec, str(output_path))

    def _get_local_music(self):
        """Pick a random music file from local directory."""
        if self.local_music_dir.exists():
            music_files = list(self.local_music_dir.glob("*.mp3"))
            if music_files:
                return str(random.choice(music_files))
        return None

    def _adjust_duration(self, input_path, output_path, target_duration):
        """Loop or trim music to match target duration using FFmpeg."""
        try:
            # Get duration of input
            result = subprocess.run(
                [self._ffmpeg, "-i", input_path, "-f", "null", "-"],
                capture_output=True, text=True, timeout=10
            )
            import re
            duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
            if not duration_match:
                return None
            h, m, s = map(float, duration_match.groups())
            input_duration = h * 3600 + m * 60 + s

            if input_duration < target_duration:
                # Loop the audio
                loops = int(target_duration / input_duration) + 1
                # Create a concat file
                concat_file = str(Path(output_path).parent / "concat_list.txt")
                with open(concat_file, "w") as f:
                    for _ in range(loops):
                        f.write(f"file '{input_path}'\n")

                subprocess.run(
                    [self._ffmpeg, "-f", "concat", "-safe", "0",
                     "-i", concat_file, "-t", str(target_duration),
                     "-c", "copy", "-y", output_path],
                    capture_output=True, timeout=30
                )
            else:
                # Trim to exact duration
                subprocess.run(
                    [self._ffmpeg, "-i", input_path, "-t", str(target_duration),
                     "-c", "copy", "-y", output_path],
                    capture_output=True, timeout=30
                )

            if Path(output_path).exists():
                logger.info(f"Music adjusted to {target_duration}s: {output_path}")
                return str(output_path)
        except Exception as e:
            logger.error(f"Audio adjustment failed: {e}")
        return None

    def _generate_music(self, duration, output_path, deity="krishna"):
        """Generate devotional music using AudioCraft/MusicGen."""
        prompt = self._build_music_prompt(deity)
        payload = json.dumps({
            "prompt": prompt,
            "duration": duration,
        }).encode()
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

    def _build_music_prompt(self, deity):
        """Build MusicGen prompt for devotional music."""
        prompts = {
            "krishna": "Indian devotional bhajan flute sitar calm spiritual music",
            "shiva": "Indian meditation mantra bhajan calm peaceful spiritual music",
            "ram": "Indian devotional bhajan ramayana spiritual uplifting music",
        }
        return prompts.get(deity.lower(), "Indian devotional spiritual calm music")

    def _generate_silence(self, duration_sec, output_path):
        """Generate silent audio using FFmpeg."""
        subprocess.run(
            [self._ffmpeg, "-f", "lavfi", "-i",
             f"anullsrc=r=44100:cl=mono", "-t",
             str(duration_sec), "-c:a", "aac", "-b:a", "128k",
             "-y", output_path],
            capture_output=True, timeout=30
        )
        logger.warning(f"Silence track created as fallback: {output_path}")
        return str(output_path)

    def mix_with_voice(self, music_path, voice_path, output_path, music_volume=None):
        """Mix background music with voiceover using FFmpeg."""
        try:
            if music_volume is None:
                music_volume = self.volume_reduction

            # Reduce music volume (0.3 = 30% of original volume)
            vol_filter = f"volume={music_volume}[music];[music][voice]amix=inputs=2:duration=first"
            subprocess.run(
                [self._ffmpeg, "-i", music_path, "-i", voice_path,
                 "-filter_complex", vol_filter,
                 "-c:a", "aac", "-b:a", "128k", "-y", output_path],
                capture_output=True, timeout=30
            )

            if Path(output_path).exists():
                logger.info(f"Mixed audio saved: {output_path}")
                return str(output_path)
        except Exception as e:
            logger.error(f"Audio mixing failed: {e}")
            return voice_path
