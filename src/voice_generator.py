"""
Voice Generator - Uses Edge-TTS to generate Hindi voiceover.
"""

import asyncio
import edge_tts
from pathlib import Path
from loguru import logger


class VoiceGenerator:
    """Generates Hindi female voiceover from script text using Edge-TTS."""

    def __init__(self, config_path: str = "config.yaml"):
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        vc = self.config["voice"]
        self.voice: str = vc.get("voice", "hi-IN-SwaraNeural")
        self.rate: str = vc.get("rate", "+0%")
        self.volume: str = vc.get("volume", "+0%")

    def generate(self, text: str, output_path: str) -> str:
        """Generate voiceover audio file from text."""
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(self._generate_async(text, str(output_path_obj)))
        logger.info(f"Voiceover saved: {output_path_obj}")
        return str(output_path_obj)

    async def _generate_async(self, text: str, output_path: str) -> None:
        """Async Edge-TTS generation."""
        communicate = edge_tts.Communicate(
            text,
            self.voice,
            rate=self.rate,
            volume=self.volume,
        )
        await communicate.save(output_path)