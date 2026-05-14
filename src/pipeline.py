"""
Pipeline - Orchestrates the entire devotional video generation workflow.
Coordinates: Script → Voice → Images (themed, moving) → Subtitles → Video Composition
"""

import tempfile
from pathlib import Path
from datetime import datetime
from loguru import logger

from src.script_generator import ScriptGenerator
from src.voice_generator import VoiceGenerator
from src.image_generator import ImageGenerator
from src.subtitle_generator import SubtitleGenerator
from src.video_composer import VideoComposer


class DevotionalPipeline:
    """End-to-end pipeline for devotional video generation."""

    def __init__(self, config_path: str = "config.yaml"):
        logger.info("Initializing Devotional Pipeline")
        self.config_path = config_path
        self.script_gen = ScriptGenerator(config_path)
        self.voice_gen = VoiceGenerator(config_path)
        self.image_gen = ImageGenerator(config_path)
        self.subtitle_gen = SubtitleGenerator(config_path)
        self.composer = VideoComposer(config_path)

    def generate(self, deity: str = "krishna", topic: str | None = None,
                 output_path: str | None = None) -> str:
        """Run the full pipeline with moving themed images."""
        logger.info(f"Starting pipeline: deity={deity}, topic={topic}")

        with tempfile.TemporaryDirectory(prefix="devotional_") as tmpdir:
            tmp = Path(tmpdir)

            try:
                # 1. Generate Script
                logger.info("Step 1/6: Generating script...")
                script = self.script_gen.generate_script(deity, topic)
                script_path = tmp / "script.txt"
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script)
                logger.info(f"Script generated ({len(script)} chars)")

                # Split script into segments for multi-image display
                import re
                segments = self._split_script_by_sentences(script)
                logger.info(f"Script split into {len(segments)} segments")

                # 2. Generate Voiceover
                logger.info("Step 2/6: Generating voiceover...")
                voice_path = self.voice_gen.generate(str(script_path), str(tmp / "voice.mp3"))

                # 3. Generate Themed Images
                logger.info("Step 3/6: Generating themed images...")
                image_paths = self.image_gen.generate_themed_images(
                    deity=deity,
                    script_segments=segments,
                    output_dir=str(tmp),
                    prefix="devotional",
                )
                logger.info(f"Generated {len(image_paths)} images")

                if not image_paths:
                    raise RuntimeError("No images generated!")

                # 4. Generate Subtitles (SRT file)
                logger.info("Step 4/6: Generating subtitles...")
                audio_dur = self._get_audio_duration(str(voice_path))
                subtitle_path = self.subtitle_gen.generate_srt(
                    script,
                    total_duration_sec=audio_dur,
                    output_path=str(tmp / "subtitles.srt"),
                )

                # 5. Audio ready
                logger.info("Step 5/6: Audio ready")

                # 6. Compose Video with Ken Burns effect
                logger.info("Step 6/6: Composing video with Ken Burns effect...")
                if output_path is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = f"output/{deity}_{timestamp}.mp4"

                final_video = self.composer.compose_ken_burns(
                    image_paths=image_paths,
                    audio_path=str(voice_path),
                    output_path=output_path,
                    zoom_speed=0.002,
                    crossfade_duration=1.0,
                )

                logger.success(f"Video generated: {final_video}")
                return final_video

            except Exception as e:
                logger.error(f"Pipeline failed: {e}")
                raise

    def _split_script_by_sentences(self, script: str) -> list[str]:
        """Split script on Hindi sentence boundaries (।, ?, !)."""
        import re
        # Split on sentence-ending punctuation followed by space
        raw = re.split(r'(?<=[।?!])\s+', script.strip())
        segments = [s.strip() for s in raw if s.strip()]

        # If too few segments, fall back to word-based split
        if len(segments) < 3:
            return self._split_script(script)

        return segments

    def _split_script(self, script: str, num_parts: int = 4) -> list[str]:
        """Split script into segments by word count."""
        words = script.split()
        if len(words) < num_parts:
            return [script]

        part_size = len(words) // num_parts
        segments: list[str] = []
        for i in range(num_parts):
            start = i * part_size
            end = (i + 1) * part_size if i < num_parts - 1 else len(words)
            segment = " ".join(words[start:end])
            segments.append(segment)
        return segments

    def _build_image_prompt(self, deity: str) -> str:
        """Legacy single image prompt."""
        prompts = {
            "krishna": "Lord Krishna playing flute in Vrindavan, divine blue skin,"
                       " peacock feather crown, beautiful peaceful scene, devotional art,"
                       " highly detailed, cinematic lighting, vibrant colors, 4K",
            "shiva": "Lord Shiva meditating on Mount Kailash, third eye,"
                     " Ganga flowing from matted hair, crescent moon, divine peaceful scene,"
                     " highly detailed, cinematic lighting, 4K quality",
            "ram": "Lord Rama standing with bow and arrow, divine peaceful expression,"
                   " Ayodhya background, Sita and Lakshmana nearby,"
                   " highly detailed, cinematic lighting, vibrant colors, 4K",
        }
        return prompts.get(deity.lower(), prompts["krishna"])

    @staticmethod
    def _get_audio_duration(audio_path: str) -> float:
        """Get audio duration in seconds."""
        from src.ffmpeg_utils import get_audio_duration
        return get_audio_duration(audio_path)