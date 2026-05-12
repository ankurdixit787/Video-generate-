"""
Image Generator - Creates devotional images with themes.
Uses ComfyUI/Stable Diffusion API, or fallback to Pillow with themed backgrounds.
"""

import json
import time
import urllib.request
import urllib.error
import base64
from pathlib import Path
from loguru import logger


class ImageGenerator:
    """Generates devotional images using ComfyUI, Stable Diffusion, or themed fallbacks."""

    THEMES = {
        "krishna": {
            "name": "कृष्ण",
            "gradient": [(70, 130, 180), (255, 215, 0)],
            "text_color": (255, 255, 200),
            "accent": (255, 200, 50),
            "mantras": ["हरे कृष्ण हरे कृष्ण", "कृष्ण कृष्ण हरे हरे", "हरे राम हरे राम"],
        },
        "shiva": {
            "name": "शिव",
            "gradient": [(148, 0, 211), (255, 165, 0)],
            "text_color": (255, 255, 255),
            "accent": (255, 215, 0),
            "mantras": ["ॐ नमः शिवाय", "शिवाय नमः", "ॐ त्र्यम्बकं यजामहे"],
        },
        "ram": {
            "name": "राम",
            "gradient": [(180, 60, 30), (255, 200, 50)],
            "text_color": (255, 255, 220),
            "accent": (255, 215, 0),
            "mantras": ["जय श्री राम", "सिया राम", "रघुपति राघव राजा राम"],
        },
    }

    SCENES = {
        "krishna": [
            "वृन्दावन में कृष्ण", "गीता का उपदेश", "मुरली की धुन",
            "रास लीला", "गोवर्धन पर्वत",
        ],
        "shiva": [
            "कैलाश पर्वत", "गंगा धारण", "त्रिपुंड धारण",
            "नटराज नृत्य", "अर्धनारीश्वर",
        ],
        "ram": [
            "अयोध्या नगरी", "वनवास", "रावण वध",
            "सीता स्वयंवर", "राम राज्य",
        ],
    }

    def __init__(self, config_path: str = "config.yaml"):
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        img_cfg = self.config["image"]
        self.provider: str = img_cfg.get("provider", "comfyui")
        self.comfyui_url: str = img_cfg.get("comfyui_url", "http://localhost:8188")
        self.sd_url: str = img_cfg.get("sd_url", "http://localhost:7860")
        self.width: int = img_cfg.get("width", 1080)
        self.height: int = img_cfg.get("height", 1920)
        self.steps: int = img_cfg.get("steps", 30)

    def generate(self, prompt: str, output_path: str) -> str:
        """Generate an image and save to output_path."""
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        if self.provider == "comfyui":
            return self._generate_comfyui(prompt, str(output_path_obj))
        else:
            return self._generate_sd(prompt, str(output_path_obj))

    def generate_themed_images(self, deity: str, script_segments: list[str],
                                output_dir: str, prefix: str = "devotional") -> list[str]:
        """Generate multiple themed devotional images based on script segments."""
        temp_img_paths: list[str] = []
        theme = self.THEMES.get(deity.lower(), self.THEMES["krishna"])
        scenes = self.SCENES.get(deity.lower(), self.SCENES["krishna"])

        num_images = max(len(script_segments), 3)
        for i in range(num_images):
            scene = scenes[i % len(scenes)]
            mantra = theme["mantras"][i % len(theme["mantras"])]
            segment_text = script_segments[i] if i < len(script_segments) else ""

            output_path = Path(output_dir) / f"{prefix}_{i:03d}.png"

            # Try API first
            api_prompt = self._build_deity_prompt(deity, scene)
            try:
                if self.provider == "comfyui":
                    result = self._generate_comfyui(api_prompt, str(output_path))
                else:
                    result = self._generate_sd(api_prompt, str(output_path))
                if result:
                    temp_img_paths.append(str(output_path))
                    logger.info(f"✓ API image {i+1}/{num_images} generated via {self.provider}")
                    continue
            except Exception as e:
                logger.warning(f"API image gen failed for segment {i}: {e}")

            # Fallback: fast themed Pillow image
            self._generate_themed_fallback(
                str(output_path), theme, scene, mantra, segment_text, i, num_images
            )
            temp_img_paths.append(str(output_path))
            logger.info(f"✓ Fallback image {i+1}/{num_images} generated")

        logger.info(f"Generated {len(temp_img_paths)} themed images for deity={deity}")
        return temp_img_paths

    def _generate_themed_fallback(self, output_path: str, theme: dict, scene: str,
                                   mantra: str, text: str, index: int, total: int) -> None:
        """Create a themed devotional image with gradient background and text."""
        import numpy as np
        from PIL import Image, ImageDraw

        w, h = self.width, self.height
        top_color, bottom_color = theme["gradient"]

        # Fast gradient using numpy
        gradient = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            ratio = y / h
            gradient[y, :, 0] = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
            gradient[y, :, 1] = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
            gradient[y, :, 2] = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)

        img = Image.fromarray(gradient)
        draw = ImageDraw.Draw(img)

        # Decorative circles
        cx, cy = w // 2, h // 3
        for radius in range(200, 50, -15):
            lightness = int(180 + 75 * (1 - radius / 200))
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                         outline=(lightness, lightness, lightness), width=2)

        # Mantra text
        draw.text((w // 2, h // 4 + 30), mantra, fill=theme["text_color"], anchor="mm")

        # Scene name
        draw.text((w // 2, h // 4 + 80), f"— {scene} —", fill=theme["accent"], anchor="mm")

        # Segment text at bottom
        if text:
            words = text.split()
            mid = len(words) // 2
            line1 = " ".join(words[:mid])[:50]
            line2 = " ".join(words[mid:])[:50] if words[mid:] else ""
            draw.text((w // 2, h * 2 // 3 - 30), line1, fill=theme["text_color"], anchor="mm")
            if line2:
                draw.text((w // 2, h * 2 // 3 + 20), line2, fill=theme["text_color"], anchor="mm")

        # Page indicator
        draw.text((w - 50, h - 30), f"{index + 1} / {total}", fill=(200, 200, 200), anchor="mm")

        img.save(output_path)
        logger.debug(f"Themed fallback image: {output_path}")

    def _build_deity_prompt(self, deity: str, scene: str) -> str:
        """Build an image prompt for the API."""
        prompts = {
            "krishna": f"Lord Krishna in Vrindavan, {scene}, divine blue skin, peacock feather,"
                       f" highly detailed devotional art, cinematic lighting, vibrant colors, 4K",
            "shiva": f"Lord Shiva on Mount Kailash, {scene}, third eye, crescent moon,"
                     f" divine peaceful scene, highly detailed, cinematic lighting, 4K",
            "ram": f"Lord Rama, {scene}, divine serene expression, bow and arrow,"
                   f" highly detailed devotional art, cinematic lighting, vibrant colors, 4K",
        }
        return prompts.get(deity.lower(), prompts["krishna"])

    def _generate_comfyui(self, prompt: str, output_path: str) -> str:
        """Generate via ComfyUI API."""
        try:
            workflow = self._build_workflow(prompt)
            req = urllib.request.Request(
                f"{self.comfyui_url}/prompt",
                data=json.dumps({"prompt": workflow}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                prompt_id = result.get("prompt_id", "")

            for _ in range(60):
                time.sleep(2)
                req = urllib.request.Request(f"{self.comfyui_url}/history/{prompt_id}")
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        history = json.loads(resp.read().decode())
                        if prompt_id in history:
                            break
                except urllib.error.HTTPError:
                    continue

            logger.info(f"Image generated via ComfyUI: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"ComfyUI failed: {e}")
            raise

    def _generate_sd(self, prompt: str, output_path: str) -> str:
        """Generate via Stable Diffusion WebUI API."""
        try:
            payload = {
                "prompt": prompt,
                "negative_prompt": "ugly, blurry, deformed, text, watermark",
                "steps": self.steps,
                "width": self.width,
                "height": self.height,
                "batch_size": 1,
            }
            req = urllib.request.Request(
                f"{self.sd_url}/sdapi/v1/txt2img",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                img_data = base64.b64decode(result["images"][0])
                with open(output_path, "wb") as f:
                    f.write(img_data)
            logger.info(f"Image generated via SD: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Stable Diffusion failed: {e}")
            raise

    def _build_workflow(self, prompt: str) -> dict:
        """Build ComfyUI workflow JSON."""
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": int(time.time()),
                    "steps": self.steps,
                    "cfg": 7,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": self.width, "height": self.height, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "ugly, blurly, deformed, text", "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "devotional", "images": ["8", 0]}},
        }

    def generate_batch(self, prompts: list[str], output_dir: str, prefix: str = "frame") -> list[str]:
        """Generate multiple images for a sequence."""
        paths: list[str] = []
        for i, prompt in enumerate(prompts):
            path = Path(output_dir) / f"{prefix}_{i:03d}.png"
            self.generate(prompt, str(path))
            paths.append(str(path))
        return paths