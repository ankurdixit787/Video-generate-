"""
Video Composer - Combines voiceover, images, subtitles, and music into final MP4.
Uses MoviePy for video composition and FFmpeg for rendering.
"""

from pathlib import Path
import yaml
from loguru import logger


class VideoComposer:
    """Composes the final devotional video from all generated assets."""

    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        vc = self.config["video"]
        self.resolution = tuple(vc["resolution"])
        self.fps = vc["fps"]
        self.duration = vc["duration_seconds"]
        self.bg_color = tuple(vc["bg_color"])
        self.output_dir = Path(self.config["output"]["dir"])

    def compose(self, image_path, audio_path, subtitle_path=None, output_path=None):
        """Compose the final video with image, audio, and subtitles."""
        try:
            from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips

            if output_path is None:
                output_path = str(self.output_dir / "output.mp4")
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Load audio to get duration
            audio_clip = AudioFileClip(audio_path)
            audio_duration = int(audio_clip.duration)

            # Create image clip matching audio duration
            image_clip = (
                ImageClip(image_path)
                .set_duration(audio_duration)
                .resize(newsize=self.resolution)
            )

            # Assemble video
            video = CompositeVideoClip([image_clip], size=self.resolution)

            # Add subtitles if provided
            if subtitle_path and Path(subtitle_path).exists():
                subtitle_clips = self._load_subtitles(subtitle_path, audio_duration)
                if subtitle_clips:
                    video = CompositeVideoClip([video] + subtitle_clips, size=self.resolution)

            # Set audio
            video = video.set_audio(audio_clip)

            # Render
            logger.info(f"Rendering video: {output_path}")
            video.write_videofile(
                str(output_path),
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                threads=2,
                logger=None,
            )

            # Cleanup
            audio_clip.close()
            video.close()

            return str(output_path)
        except Exception as e:
            logger.error(f"Video composition failed: {e}")
            raise

    def compose_with_transitions(self, image_paths, audio_path, subtitle_text, output_path=None):
        """Compose video with multiple images and crossfade transitions."""
        try:
            from moviepy.editor import (
                ImageClip, AudioFileClip, CompositeVideoClip,
                concatenate_videoclips, TextClip,
            )

            if output_path is None:
                output_path = str(self.output_dir / "output.mp4")
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            audio_clip = AudioFileClip(audio_path)
            audio_duration = int(audio_clip.duration)

            num_images = len(image_paths)
            clip_duration = audio_duration / num_images if num_images else audio_duration
            crossfade = 0.5

            clips = []
            for img_path in image_paths:
                if Path(img_path).exists():
                    clip = (
                        ImageClip(img_path)
                        .set_duration(clip_duration + crossfade)
                        .resize(newsize=self.resolution)
                        .crossfadein(crossfade)
                        .crossfadeout(crossfade)
                    )
                    clips.append(clip)

            if not clips:
                from PIL import Image
                img = Image.new("RGB", self.resolution, self.bg_color)
                fallback_path = str(Path(output_path).parent / "fallback.png")
                img.save(fallback_path)
                clips = [ImageClip(fallback_path).set_duration(audio_duration)]

            video = concatenate_videoclips(clips, method="compose")
            video = video.set_audio(audio_clip)

            # Add subtitles
            if subtitle_text:
                subtitle_clips = self._generate_text_clips(subtitle_text, audio_duration)
                video = CompositeVideoClip([video] + subtitle_clips, size=self.resolution)

            video.write_videofile(
                str(output_path),
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                threads=2,
                logger=None,
            )

            audio_clip.close()
            video.close()
            return str(output_path)
        except Exception as e:
            logger.error(f"Video composition with transitions failed: {e}")
            raise

    def _load_subtitles(self, srt_path, duration):
        """Load SRT file and return list of TextClips."""
        try:
            from moviepy.editor import TextClip
            clips = []
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Simple SRT parser
            blocks = content.strip().split("\n\n")
            for block in blocks:
                lines = block.strip().split("\n")
                if len(lines) >= 3:
                    time_line = lines[1]
                    text = " ".join(lines[2:])
                    start_str, end_str = time_line.split(" --> ")
                    start = self._srt_time_to_sec(start_str)
                    end = self._srt_time_to_sec(end_str)
                    clip = TextClip(
                        text,
                        font=self.config["subtitles"]["font"],
                        fontsize=self.config["subtitles"]["font_size"],
                        color=self.config["subtitles"]["font_color"],
                        method="caption",
                        size=(self.resolution[0] - 100, 200),
                    ).set_start(start).set_duration(end - start).set_position(("center", self.resolution[1] - 250))
                    clips.append(clip)
            return clips
        except Exception as e:
            logger.warning(f"Subtitle loading failed: {e}")
            return []

    def _generate_text_clips(self, text, duration):
        """Generate subtitle clips directly from text."""
        from moviepy.editor import TextClip
        # Simple chunking
        words = text.split()
        lines = []
        current = ""
        for w in words:
            if len(current) + len(w) < 40:
                current += " " + w
            else:
                lines.append(current.strip())
                current = w
        if current:
            lines.append(current.strip())

        clips = []
        chunk_dur = duration / len(lines) if lines else duration
        for i, line in enumerate(lines):
            clip = TextClip(
                line,
                font=self.config["subtitles"]["font"],
                fontsize=self.config["subtitles"]["font_size"],
                color=self.config["subtitles"]["font_color"],
                method="caption",
                size=(self.resolution[0] - 100, 200),
            ).set_start(i * chunk_dur).set_duration(chunk_dur).set_position(("center", self.resolution[1] - 250))
            clips.append(clip)
        return clips

    @staticmethod
    def _srt_time_to_sec(time_str):
        """Convert SRT time format to seconds."""
        parts = time_str.replace(",", ".").split(":")
        h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return h * 3600 + m * 60 + s
