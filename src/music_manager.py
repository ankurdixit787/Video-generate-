"""
Music Manager - Handles background music for devotional videos.
Supports AudioCraft generation and local music files.
"""

from pathlib import Path
import random
import json
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

    def get_background_music(self, output_path, duration_sec=60, deity="krishna"):
        """Get background music track for the specified duration."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try local music first
        local_path = self._get_local_music()
        if local_path:
            return self._adjust_duration(local_path, str(output_path), duration_sec)

        # Try AudioCraft
        if self.provider == "audiocraft":
            try:
                return self._generate_music(duration_sec, str(output_path), deity)
            except Exception as e:
                logger.warning(f"AudioCraft failed: {e}")

        # Fallback: generate silence
        return self._generate_silence(duration_sec, str(output_path))

    def _get_local_music(self):
        """Pick a random music file from local directory."""
        if self.local_music_dir.exists():
            music_files = list(self.local_music_dir.glob("*.mp3"))
            if music_files:
                return str(random.choice(music_files))
        return None

    def _adjust_duration(self, input_path, output_path, target_duration):
        """Loop or trim music to match target duration using pydub."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(input_path)
            if len(audio) < target_duration * 1000:
                loops = int(target_duration * 1000 / len(audio)) + 1
                audio = audio * loops
            audio = audio[:int(target_duration * 1000)]
            audio.export(output_path, format="mp3")
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
        """Generate silent audio as fallback."""
        from pydub import AudioSegment, generators
        silence = AudioSegment.silent(duration=duration_sec * 1000)
        silence.export(output_path, format="mp3")
        logger.warning(f"Silence track created as fallback: {output_path}")
        return str(output_path)

    def mix_with_voice(self, music_path, voice_path, output_path, music_volume=None):
        """Mix background music with voiceover."""
        try:
            from pydub import AudioSegment
            if music_volume is None:
                music_volume = self.volume_reduction

            music = AudioSegment.from_mp3(music_path)
            voice = AudioSegment.from_mp3(voice_path)

            # Reduce music volume and overlay
            music = music - (music_volume * 20)  # Convert ratio to dB reduction
            mixed = voice.overlay(music, loop=True)

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mixed.export(str(output_path), format="mp3")
            logger.info(f"Mixed audio saved: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Audio mixing failed: {e}")
            return voice_path
