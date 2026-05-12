"""
Tests for the Devotional Video Generation Pipeline.
"""

import tempfile
from pathlib import Path
import yaml


SAMPLE_CONFIG = {
    "video": {"resolution": [1080, 1920], "fps": 24, "duration_seconds": 60, "bg_color": [255, 200, 100]},
    "script": {"model": "llama3:8b", "ollama_url": "http://localhost:11434/api/generate", "temperature": 0.7, "max_tokens": 500, "language": "hindi", "default_deity": "krishna"},
    "voice": {"provider": "edge-tts", "voice": "hi-IN-SwaraNeural", "rate": "+0%", "volume": "+0%"},
    "image": {"provider": "comfyui", "comfyui_url": "http://localhost:8188", "sd_url": "http://localhost:7860", "width": 1080, "height": 1920, "steps": 30, "cfg_scale": 7.0, "batch_size": 1},
    "subtitles": {"font": "assets/fonts/NotoSansHindi-Bold.ttf", "font_size": 48, "font_color": "white", "stroke_color": "black", "stroke_width": 2, "position": "bottom", "max_chars_per_line": 40},
    "music": {"provider": "audiocraft", "audiocraft_url": "http://localhost:8080", "local_music_dir": "assets/music/", "volume_reduction": 0.3},
    "output": {"dir": "output/", "filename_template": "{deity}_{timestamp}.mp4", "temp_dir": "temp/"},
    "logging": {"level": "INFO", "file": "logs/pipeline.log"},
}


def test_config_loading():
    """Test that config loads correctly."""
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        config_path = f.name

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        assert config["video"]["resolution"] == [1080, 1920]
        assert config["voice"]["voice"] == "hi-IN-SwaraNeural"
        assert config["script"]["default_deity"] == "krishna"
    finally:
        os.unlink(config_path)


def test_subtitle_chunking():
    """Test subtitle text chunking logic."""
    from src.subtitle_generator import SubtitleGenerator

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        config_path = f.name

    try:
        gen = SubtitleGenerator(config_path)
        text = "हरे कृष्ण हरे कृष्ण कृष्ण कृष्ण हरे हरे हरे राम हरे राम राम राम हरे हरे"
        chunks = gen.chunk_text(text, max_chars=20)
        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk) <= 20
    finally:
        import os
        os.unlink(config_path)


def test_script_fallback():
    """Test script generator fallback template."""
    from src.script_generator import ScriptGenerator

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        config_path = f.name

    try:
        gen = ScriptGenerator(config_path)
        script = gen._fallback_template("krishna")
        assert script is not None
        assert len(script) > 10
        assert "कृष्ण" in script
    finally:
        import os
        os.unlink(config_path)


def test_srt_generation():
    """Test SRT subtitle file generation."""
    from src.subtitle_generator import SubtitleGenerator

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        config_path = f.name

    try:
        gen = SubtitleGenerator(config_path)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False) as out_f:
            output_path = out_f.name

        result = gen.generate_srt("हरे कृष्ण हरे राम", total_duration_sec=10, output_path=output_path)
        assert result is not None

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "1" in content
        assert "-->" in content
    finally:
        import os
        os.unlink(config_path)
        if "output_path" in dir():
            os.unlink(output_path)


def test_image_fallback_generation():
    """Test fallback image generation."""
    from src.image_generator import ImageGenerator

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        config_path = f.name

    try:
        gen = ImageGenerator(config_path)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as out_f:
            out_path = out_f.name

        gen._generate_fallback_image(out_path, "Test prompt")
        from PIL import Image
        img = Image.open(out_path)
        assert img.size == (1080, 1920)
    finally:
        import os
        os.unlink(config_path)
        if "out_path" in dir():
            os.unlink(out_path)


def test_pipeline_init():
    """Test pipeline initialization."""
    from src.pipeline import DevotionalPipeline

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        config_path = f.name

    try:
        pipeline = DevotionalPipeline(config_path)
        assert pipeline.config_path == config_path
        assert pipeline.script_gen is not None
        assert pipeline.voice_gen is not None
        assert pipeline.image_gen is not None
        assert pipeline.subtitle_gen is not None
        assert pipeline.music_mgr is not None
        assert pipeline.composer is not None
    finally:
        import os
        os.unlink(config_path)