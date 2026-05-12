"""
Subtitle Generator - Creates Hindi subtitles with word-level timing for devotional videos.
"""

from pathlib import Path
from loguru import logger


class SubtitleGenerator:
    """Generates subtitle clips or SRT files from script text."""

    def __init__(self, config_path="config.yaml"):
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        sc = self.config["subtitles"]
        self.font = sc["font"]
        self.font_size = sc["font_size"]
        self.font_color = sc["font_color"]
        self.stroke_color = sc["stroke_color"]
        self.stroke_width = sc["stroke_width"]
        self.max_chars_per_line = sc["max_chars_per_line"]

    def chunk_text(self, text, max_chars=None):
        """Split text into subtitle chunks."""
        if max_chars is None:
            max_chars = self.max_chars_per_line
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line += (" " if current_line else "") + word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def generate_srt(self, text, total_duration_sec=55, output_path="output/subtitles.srt"):
        """Generate SRT subtitle file with evenly spaced timing."""
        lines = self.chunk_text(text)
        chunk_duration = total_duration_sec / len(lines) if lines else total_duration_sec
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def _fmt_time(seconds):
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

    def generate_text_clip(self, text, duration=3, size=(1080, 250)):
        """Generate a single MoviePy TextClip for subtitles."""
        try:
            from moviepy.editor import TextClip
            return TextClip(
                text,
                font=self.font,
                fontsize=self.font_size,
                color=self.font_color,
                stroke_color=self.stroke_color,
                stroke_width=self.stroke_width,
                size=size,
                method="caption",
            ).set_duration(duration)
        except ImportError:
            logger.error("MoviePy not installed")
            return None

    def generate_subtitle_clips(self, text, total_duration=55, fps=24):
        """Generate list of TextClips from script text."""
        lines = self.chunk_text(text)
        chunk_duration = total_duration / len(lines) if lines else total_duration
        clips = []
        for i, line in enumerate(lines):
            clip = self.generate_text_clip(line, duration=chunk_duration)
            if clip:
                clip = clip.set_start(i * chunk_duration).set_position(("center", "bottom"))
                clips.append(clip)
        return clips
