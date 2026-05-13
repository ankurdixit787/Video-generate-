"""
Video Composer - Combines voiceover, images, subtitles, and music into final MP4.
Uses FFmpeg for Ken Burns effects and smooth crossfade transitions.
"""

import shutil
import re
import subprocess
import tempfile
from pathlib import Path

import yaml
from loguru import logger

from ffmpeg_utils import find_ffmpeg


class VideoComposer:
    """Composes the final devotional video from all generated assets."""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        vc = self.config["video"]
        self.resolution: tuple[int, int] = tuple(vc["resolution"])
        self.fps: int = vc["fps"]
        self.duration: int = vc["duration_seconds"]
        self.bg_color: tuple[int, int, int] = tuple(vc["bg_color"])
        self.output_dir: Path = Path(self.config["output"]["dir"])

    def compose(self, image_path: str, audio_path: str,
                subtitle_path: str | None = None,
                output_path: str | None = None) -> str:
        """Simple compose: single image + audio (no Ken Burns)."""
        try:
            from moviepy import ImageClip, AudioFileClip, CompositeVideoClip

            if output_path is None:
                output_path = str(self.output_dir / "output.mp4")
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

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
                str(output_path_obj),
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                threads=2,
                logger=None,
            )
            audio_clip.close()
            video.close()
            return str(output_path_obj)
        except Exception as e:
            logger.error(f"Video composition failed: {e}")
            raise

    def compose_ken_burns(self, image_paths: list[str], audio_path: str,
                          output_path: str | None = None,
                          zoom_speed: float = 0.002,
                          crossfade_duration: float = 1.0) -> str:
        """Compose video with Ken Burns zoom + crossfade using FFmpeg.

        Each image gets a slow zoom-in, clips are crossfaded, audio is muxed.
        Everything runs through 2 FFmpeg steps: zoom clips → crossfade+audio.
        """
        ffmpeg = find_ffmpeg()
        if output_path is None:
            output_path = str(self.output_dir / "output.mp4")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Get audio duration
        audio_duration = self._get_audio_duration_ffmpeg(audio_path)

        num_images = len(image_paths)
        clip_duration = audio_duration / num_images
        w, h = self.resolution

        with tempfile.TemporaryDirectory(prefix="kenburns_") as tmpdir:
            tmp = Path(tmpdir)
            clip_files: list[str] = []

            for i, img_path in enumerate(image_paths):
                if not Path(img_path).exists():
                    logger.warning(f"Image not found, skipping: {img_path}")
                    continue

                clip_path = str(tmp / f"clip_{i:03d}.mp4")

                # Calculate Ken Burns end zoom level based on image index for variety
                zoom_end = 1.05 + (i % 3) * 0.03  # 1.05, 1.08, or 1.11

                # Ken Burns: slow zoom-in
                result = subprocess.run(
                    [ffmpeg, "-y", "-loop", "1", "-i", img_path,
                     "-vf", (
                         f"zoompan=z='min(1+{zoom_speed}*on,{zoom_end}):"
                         f"d={int(clip_duration * self.fps)}:"
                         f"x='iw/2-(iw/zoom/2)':"
                         f"y='ih/2-(ih/zoom/2)':"
                         f"s={w}x{h}:fps={self.fps}"
                     ),
                     "-c:v", "libx264", "-pix_fmt", "yuv420p",
                     "-preset", "ultrafast", "-crf", "28",
                     "-t", str(clip_duration), clip_path],
                    capture_output=True, timeout=60,
                )

                if result.returncode != 0:
                    logger.error(
                        f"FFmpeg ken burns failed for {img_path}: "
                        f"{result.stderr.decode()[:300]}"
                    )
                    continue

                if Path(clip_path).exists():
                    clip_files.append(clip_path)
                    logger.debug(f"Ken Burns clip {i+1}/{num_images}: {clip_path}")
                else:
                    logger.error(f"Ken Burns clip not created: {clip_path}")

            if not clip_files:
                raise RuntimeError("No valid image clips to compose")

            # --- Crossfade concatenation ---
            concat_video = str(tmp / "concat_video.mp4")
            n = len(clip_files)

            if n == 1:
                # Single clip — no crossfade needed
                shutil.copy2(clip_files[0], concat_video)
            else:
                # Build filter_complex for xfade transitions
                inputs = []
                for cp in clip_files:
                    inputs.extend(["-i", cp])

                # Calculate offsets: each transition starts at end_of_prev - xfade_dur
                filter_parts: list[str] = []
                prev_label = "0:v"
                running_duration = float(self._get_clip_duration(clip_files[0]))

                for i in range(1, n):
                    out_label = f"v{i}" if i < n - 1 else "vout"
                    offset = running_duration - crossfade_duration
                    filter_parts.append(
                        f"[{prev_label}][{i}:v]xfade=transition=fade:"
                        f"duration={crossfade_duration}:offset={max(0, offset):.3f}"
                        f"[{out_label}]"
                    )
                    prev_label = out_label
                    running_duration += float(self._get_clip_duration(clip_files[i]))

                filter_str = ";".join(filter_parts)

                result = subprocess.run(
                    [ffmpeg, "-y", *inputs,
                     "-filter_complex", filter_str,
                     "-map", f"[{prev_label}]",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p",
                     "-preset", "ultrafast", "-crf", "28",
                     concat_video],
                    capture_output=True, timeout=180,
                )

                if result.returncode != 0:
                    stderr = result.stderr.decode()[:500]
                    raise RuntimeError(
                        f"Crossfade concat FFmpeg failed (rc={result.returncode}): {stderr}"
                    )

                if not Path(concat_video).exists():
                    raise RuntimeError(
                        f"Crossfade concat failed — output not created. "
                        f"Filter: {filter_str}"
                    )

            # Add audio
            result = subprocess.run(
                [ffmpeg, "-y",
                 "-i", concat_video, "-i", audio_path,
                 "-c:v", "copy", "-c:a", "aac",
                 "-shortest",
                 "-map", "0:v:0", "-map", "1:a:0",
                 str(output_path)],
                capture_output=True, timeout=120,
            )

            if result.returncode != 0:
                stderr = result.stderr.decode()[:500]
                raise RuntimeError(f"Audio mux FFmpeg failed (rc={result.returncode}): {stderr}")

        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.success(f"Ken Burns video rendered: {output_path} ({size_mb:.1f}MB)")
            return str(output_path)
        raise RuntimeError("Video rendering failed — output file missing")

    def _get_audio_duration_ffmpeg(self, audio_path: str) -> float:
        """Get audio duration using ffprobe."""
        from ffmpeg_utils import get_audio_duration
        return get_audio_duration(audio_path)

    def _get_clip_duration(self, clip_path: str) -> float:
        """Get duration of a video clip."""
        ffprobe = shutil.which("ffprobe") or "ffprobe"
        try:
            result = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", clip_path],
                capture_output=True, text=True, timeout=10,
            )
            return float(result.stdout.strip())
        except Exception:
            return 15.0  # Default fallback
