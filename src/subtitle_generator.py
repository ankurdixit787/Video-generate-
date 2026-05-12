"""
Subtitle Generator - Creates Hindi subtitles with word-level timing for devotional videos.
Uses FFmpeg drawtext filter for reliable rendering (MoviePy v2 compatible).
"""

import subprocess
import tempfile
from pathlib import Path
from loguru import logger

from ffmpeg_utils import find_ffmpeg, get_audio_duration


class SubtitleGenerator:
    """Generates subtitle clips or SRT files from script text."""

    def __init__(self, config_path: str = "config.yaml"):
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        sc = self.config["subtitles"]
        self.font_size: int = sc.get("font_size", 48)
        self.font_color: str = sc.get("font_color", "white")
        self.stroke_color: str = sc.get("stroke_color", "black")
        self.stroke_width: int = sc.get("stroke_width", 2)
        self.max_chars_per_line: int = sc.get("max_chars_per_line", 40)
        self.position: str = sc.get("position", "bottom")

    def chunk_text(self, text: str, max_chars: int | None = None) -> list[str]:
        """Split text into subtitle chunks."""
        if max_chars is None:
            max_chars = self.max_chars_per_line
        words = text.split()
        lines: list[str] = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def generate_srt(self, text: str, total_duration_sec: float = 55,
                     output_path: str = "output/subtitles.srt") -> str:
        """Generate SRT subtitle file with evenly spaced timing."""
        lines = self.chunk_text(text)
        chunk_duration = total_duration_sec / len(lines) if lines else total_duration_sec
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def _fmt_time(seconds: float) -> str:
            h, rem = divmod(seconds, 3600)
            m, s = divmod(rem, 60)
            ms = int((s - int(s)) * 1000)
            return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"

        with open(output_path, "w", encoding="utf-8") as f:
            for i, line in enumerate(lines, 1):
                start = (i - 1) * chunk_duration
                end = i * chunk_duration
                f.write(f"{i}\n")
                f.write(f"{_fmt_time(start)} --> {_fmt_time(end)}\n")
                f.write(f"{line}\n\n")

        logger.info(f"SRT subtitles saved: {output_path}")
        return str(output_path)

    def burn_subtitles_to_video(self, video_path: str, text: str,
                                 total_duration: float = 55) -> str:
        """
        Burn subtitles directly onto video using FFmpeg drawtext filter.
        MoviePy v2 compatible — no TextClip needed.
        """
        ffmpeg = find_ffmpeg()
        lines = self.chunk_text(text)
        chunk_duration = total_duration / len(lines) if lines else total_duration
        output_path = str(Path(video_path).parent / "subtitled_output.mp4")

        # Build drawtext filter with multiple entries, one per subtitle line
        filters: list[str] = []
        for i, line in enumerate(lines):
            start = i * chunk_duration
            escaped = line.replace("'", "'\\''")
            filters.append(
                f"drawtext=text='{escaped}':"
                f"fontsize={self.font_size}:fontcolor={self.font_color}:"
                f"bordercolor={self.stroke_color}:borderw={self.stroke_width}:"
                f"x=(w-text_w)/2:y=h-text_h-40:"
                f"enable='between(t,{start:.2f},{start + chunk_duration:.2f})'"
            )

        filter_str = ",".join(filters)

        subprocess.run(
            [
                ffmpeg, "-y",
                "-i", video_path,
                "-vf", filter_str,
                "-c:v", "libx264", "-c:a", "copy",
                output_path,
            ],
            capture_output=True, timeout=120,
        )

        if Path(output_path).exists():
            logger.info(f"Subtitled video saved: {output_path}")
            return output_path

        logger.error("Subtitle burn failed, returning original video")
        return video_path