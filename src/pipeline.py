"""
Pipeline - Orchestrates the entire devotional video generation workflow.
Coordinates: Script → Voice → Images → Subtitles → Music → Video Composition
"""

from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from loguru import logger

from src.script_generator import ScriptGenerator
from src.voice_generator import VoiceGenerator
from src.image_generator import ImageGenerator
from src.subtitle_generator import SubtitleGenerator
from src.music_manager import MusicManager
from src.video_composer import VideoComposer


class DevotionalPipeline:
    """End-to-end pipeline for devotional video generation."""

    def __init__(self, config_path="config.yaml"):
        logger.info("Initializing Devotional Pipeline")
        self.config_path = config_path
        self.script_gen = ScriptGenerator(config_path)
        self.voice_gen = VoiceGenerator(config_path)
        self.image_gen = ImageGenerator(config_path)
        self.subtitle_gen = SubtitleGenerator(config_path)
        self.music_mgr = MusicManager(config_path)
        self.composer = VideoComposer(config_path)

    def generate(self, deity="krishna", topic=None, output_path=None):
        """Run the full pipeline: generate a complete devotional video."""
        logger.info(f"Starting pipeline: deity={deity}, topic={topic}")

        with tempfile.TemporaryDirectory(prefix="devotional_") as tmpdir:
            tmp = Path(tmpdir)

            # 1. Generate Script
            logger.info("Step 1/6: Generating script...")
            script = self.script_gen.generate_script(deity, topic)
            script_path = str(tmp / "script.txt")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script)
            logger.info(f"Script generated ({len(script)} chars)")

            # 2. Generate Voiceover
            logger.info("Step 2/6: Generating voiceover...")
            voice_path = self.voice_gen.generate(script, str(tmp / "voice.mp3"))

            # 3. Generate Images
            logger.info("Step 3/6: Generating images...")
            image_prompt = self._build_image_prompt(deity)
            image_path = self.image_gen.generate(image_prompt, str(tmp / "main_image.png"))

            # 4. Generate Subtitles
            logger.info("Step 4/6: Generating subtitles...")
            subtitle_path = self.subtitle_gen.generate_srt(
                script, total_duration_sec=55, output_path=str(tmp / "subtitles.srt")
            )

            # 5. Generate/Mix Music
            logger.info("Step 5/6: Processing background music...")
            bg_music_path = self.music_mgr.get_background_music(
                str(tmp / "background.mp3"), duration_sec=60, deity=deity
            )
            mixed_audio = self.music_mgr.mix_with_voice(
                bg_music_path, voice_path, str(tmp / "mixed_audio.mp3")
            )

            # 6. Compose Video
            logger.info("Step 6/6: Composing video...")
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"output/{deity}_{timestamp}.mp4"

            final_video = self.composer.compose(
                image_path=image_path,
                audio_path=mixed_audio,
                subtitle_path=subtitle_path,
                output_path=output_path,
            )

            logger.success(f"Video generated: {final_video}")
            return final_video

    def generate_multi_image(self, deity="krishna", topic=None, num_images=3, output_path=None):
        """Generate video with multiple transitioning images."""
        logger.info(f"Starting multi-image pipeline: deity={deity}, topic={topic}")

        with tempfile.TemporaryDirectory(prefix="devotional_") as tmpdir:
            tmp = Path(tmpdir)

            # 1. Script
            script = self.script_gen.generate_script(deity, topic)
            with open(str(tmp / "script.txt"), "w", encoding="utf-8") as f:
                f.write(script)

            # 2. Voice
            voice_path = self.voice_gen.generate(script, str(tmp / "voice.mp3"))

            # 3. Multiple images
            image_prompt = self._build_image_prompt(deity)
            image_variations = [
                f"{image_prompt}, wide angle view",
                f"{image_prompt}, close up detailed",
                f"{image_prompt}, artistic painting style",
            ]
            image_paths = self.image_gen.generate_batch(
                image_variations[:num_images], str(tmp), "frame"
            )

            # 4. Subtitles
            subtitle_path = self.subtitle_gen.generate_srt(
                script, total_duration_sec=55, output_path=str(tmp / "subtitles.srt")
            )

            # 5. Music
            bg_music = self.music_mgr.get_background_music(
                str(tmp / "background.mp3"), duration_sec=60, deity=deity
            )
            mixed_audio = self.music_mgr.mix_with_voice(
                bg_music, voice_path, str(tmp / "mixed_audio.mp3")
            )

            # 6. Compose with transitions
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"output/{deity}_multi_{timestamp}.mp4"

            final_video = self.composer.compose_with_transitions(
                image_paths=image_paths,
                audio_path=mixed_audio,
                subtitle_text=script,
                output_path=output_path,
            )

            logger.success(f"Multi-image video generated: {final_video}")
            return final_video

    def _build_image_prompt(self, deity):
        """Build image generation prompt for the deity."""
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
