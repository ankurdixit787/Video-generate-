"""
Video Composer - Combines voiceover, images, subtitles, and music into final MP4.
Uses FFmpeg for Ken Burns effects and MoviePy for composition.
"""

from pathlib import Path
import subprocess
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

    def _ffmpeg(self):
        """Get ffmpeg binary path."""
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

    def compose(self, image_path, audio_path, subtitle_path=None, output_path=None):
        """Simple compose: single image + audio (no Ken Burns)."""
        try:
            from moviepy import ImageClip, AudioFileClip, CompositeVideoClip

            if output_path is None:
                output_path = str(self.output_dir / "output.mp4")
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            audio_clip = AudioFileClip(audio_path)
            audio_duration = int(audio_clip.duration)

            image_clip = (
                ImageClip(image_path)
                .with_duration(audio_duration)
                .resized(new_size=self.resolution)
            )

            video = CompositeVideoClip([image_clip], size=self.resolution)
            video = video.with_audio(audio_clip)

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
            audio_clip.close()
            video.close()
            return str(output_path)
        except Exception as e:
            logger.error(f"Video composition failed: {e}")
            raise

    def compose_ken_burns(self, image_paths, audio_path, output_path=None,
                          zoom_speed=0.002, crossfade_duration=1.0):
        """Compose video with Ken Burns zoom effect on images using FFmpeg.

        Each image gets a slow zoom-in effect, then clips are concatenated with crossfade.
        """
        import tempfile
        import os

        ffmpeg = self._ffmpeg()
        if output_path is None:
            output_path = str(self.output_dir / "output.mp4")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get audio duration
        probe = subprocess.run(
            [ffmpeg, "-i", audio_path, "-f", "null", "-"],
            capture_output=True, text=True, timeout=15
        )
        import re
        dur_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
        if dur_match:
            h, m, s = map(float, dur_match.groups())
            audio_duration = h * 3600 + m * 60 + s
        else:
            audio_duration = 60

        num_images = len(image_paths)
        clip_duration = audio_duration / num_images
        w, h = self.resolution

        with tempfile.TemporaryDirectory(prefix="kenburns_") as tmpdir:
            tmp = Path(tmpdir)
            clip_files = []

            for i, img_path in enumerate(image_paths):
                if not Path(img_path).exists():
                    logger.warning(f"Image not found, skipping: {img_path}")
                    continue

                clip_path = str(tmp / f"clip_{i:03d}.mp4")
                # Ken Burns: slow zoom from 1.0 to 1.15
                result = subprocess.run(
                    [ffmpeg, "-y", "-loop", "1", "-i", img_path,
                     "-vf", (
                         f"zoompan=z='min(1+{zoom_speed}*on,1.15)':"
                         f"d={int(clip_duration * self.fps)}:"
                         f"x='iw/2-(iw/zoom/2)':"
                         f"y='ih/2-(ih/zoom/2)':"
                         f"s={w}x{h}:fps={self.fps}"
                     ),
                     "-c:v", "libx264", "-pix_fmt", "yuv420p",
                     "-t", str(clip_duration), clip_path],
                    capture_output=True, timeout=60
                )
                if result.returncode != 0:
                    logger.error(f"FFmpeg ken burns failed for {img_path}: {result.stderr.decode()[:300]}")
                    continue
                if Path(clip_path).exists():
                    clip_files.append(clip_path)
                    logger.debug(f"Ken Burns clip {i+1}/{num_images}: {clip_path}")
                else:
                    logger.error(f"Ken Burns clip not created: {clip_path}")

            if not clip_files:
                raise RuntimeError("No valid image clips to compose")

            # Create concat file for simple concatenation
            concat_file = str(tmp / "concat.txt")
            with open(concat_file, "w") as f:
                for cf in clip_files:
                    f.write(f"file '{cf}'\n")

            # Concat video clips
            concat_video = str(tmp / "concat_video.mp4")
            subprocess.run(
                [ffmpeg, "-y", "-f", "concat", "-safe", "0",
                 "-i", concat_file, "-c", "copy", concat_video],
                capture_output=True, timeout=60
            )

            # Add audio
            subprocess.run(
                [ffmpeg, "-y", "-i", concat_video, "-i", audio_path,
                 "-c:v", "copy", "-c:a", "aac", "-shortest",
                 "-map", "0:v:0", "-map", "1:a:0",
                 str(output_path)],
                capture_output=True, timeout=120
            )

        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.success(f"Ken Burns video rendered: {output_path} ({size_mb:.1f}MB)")
            return str(output_path)
        raise RuntimeError("Video rendering failed")
