"""
Image Generator - Uses ComfyUI or Stable Diffusion API to generate devotional images.
"""

import json
import time
import urllib.request
import urllib.error
import base64
from pathlib import Path
from loguru import logger


class ImageGenerator:
    """Generates devotional images using ComfyUI or Stable Diffusion."""

    def __init__(self, config_path="config.yaml"):
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        img_cfg = self.config["image"]
        self.provider = img_cfg.get("provider", "comfyui")
        self.comfyui_url = img_cfg["comfyui_url"]
        self.sd_url = img_cfg["sd_url"]
        self.width = img_cfg["width"]
        self.height = img_cfg["height"]
        self.steps = img_cfg["steps"]

    def generate(self, prompt, output_path):
        """Generate an image and save to output_path."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.provider == "comfyui":
            return self._generate_comfyui(prompt, str(output_path))
        else:
            return self._generate_sd(prompt, str(output_path))

    def _generate_comfyui(self, prompt, output_path):
        """Generate via ComfyUI API."""
        try:
            workflow = self._build_workflow(prompt)
            # Queue prompt
            req = urllib.request.Request(
                f"{self.comfyui_url}/prompt",
                data=json.dumps({"prompt": workflow}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                prompt_id = result.get("prompt_id", "")

            # Wait for completion
            for _ in range(60):
                time.sleep(2)
                req = urllib.request.Request(
                    f"{self.comfyui_url}/history/{prompt_id}"
                )
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
            return self._generate_fallback_image(output_path, prompt)

    def _generate_sd(self, prompt, output_path):
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
            return self._generate_fallback_image(output_path, prompt)

    def _build_workflow(self, prompt):
        """Build ComfyUI workflow JSON for devotional image generation."""
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
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "ugly, blurry, deformed, text", "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "devotional", "images": ["8", 0]}},
        }

    def _generate_fallback_image(self, output_path, prompt_text):
        """Create a placeholder devotional image using Pillow."""
        from PIL import Image, ImageDraw, ImageFont
        w, h = self.width, self.height
        img = Image.new("RGB", (w, h), (255, 200, 100))
        draw = ImageDraw.Draw(img)
        draw.text((w // 2 - 100, h // 2 - 50), "जय श्री कृष्ण", fill=(139, 69, 19))
        img.save(output_path)
        logger.warning(f"Fallback image created: {output_path}")
        return output_path

    def generate_batch(self, prompts, output_dir, prefix="frame"):
        """Generate multiple images for a sequence."""
        paths = []
        for i, prompt in enumerate(prompts):
            path = Path(output_dir) / f"{prefix}_{i:03d}.png"
            self.generate(prompt, str(path))
            paths.append(str(path))
        return paths
