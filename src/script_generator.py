"""
Script Generator - Uses Ollama (Llama 3/Mistral) to generate devotional scripts in Hindi.
Falls back to pre-written templates if Ollama is unavailable.
"""

import json
import random
import urllib.request
import urllib.error
import yaml
from pathlib import Path
from datetime import datetime
from loguru import logger


class ScriptGenerator:
    """Generates Hindi devotional scripts using Ollama LLM."""

    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.model = self.config["script"]["model"]
        self.ollama_url = self.config["script"]["ollama_url"]
        self.temperature = self.config["script"]["temperature"]
        self.max_tokens = self.config["script"]["max_tokens"]
        self.language = self.config["script"]["language"]

        # Fallback templates per deity
        self.templates = {
            "krishna": [
                "श्री कृष्ण भगवान की महिमा अपरंपार है। वे ब्रह्मांड के पालनकर्ता हैं। "
                "उनकी मुरली की धुन सारे जगत को मोहित कर देती है। गीता का उपदेश देने वाले "
                "कृष्ण ने अर्जुन को कर्तव्य का पाठ पढ़ाया। हरे कृष्ण हरे कृष्ण, कृष्ण कृष्ण हरे हरे। "
                "हरे राम हरे राम, राम राम हरे हरे। भगवान कृष्ण की कृपा से सब संभव है।"
            ],
            "shiva": [
                "ॐ नमः शिवाय। भोलेनाथ त्रिलोक के स्वामी हैं। वे संहारक भी हैं और पालनकर्ता भी। "
                "कैलाश पर्वत पर ध्यानमग्न शिवजी की जटाओं से गंगा निकलती है। "
                "उनके तीसरे नेत्र से ब्रह्मांड का विनाश होता है। ॐ नमः शिवाय, शिवाय नमः। "
                "महादेव की भक्ति से सारे दुख दूर होते हैं।"
            ],
            "ram": [
                "जय श्री राम। मर्यादा पुरुषोत्तम भगवान राम सत्य और धर्म के प्रतीक हैं। "
                "अयोध्या के राजा राम ने रावण का वध करके संसार को बुराई से मुक्त किया। "
                "रामायण का हर पात्र हमें कुछ न कुछ सिखाता है। सीता माता की पवित्रता और "
                "हनुमान जी की भक्ति अद्वितीय है। जय श्री राम।"
            ],
        }

    def generate_script(self, deity="krishna", topic=None):
        """Generate a devotional script using Ollama, with fallback to templates."""
        try:
            prompt = self._build_prompt(deity, topic)
            response = self._call_ollama(prompt)
            if response:
                logger.info(f"Script generated via Ollama for deity={deity}")
                return response.strip()
        except Exception as e:
            logger.warning(f"Ollama unavailable, using template: {e}")

        # Fallback to template
        return self._fallback_template(deity)

    def _build_prompt(self, deity, topic=None):
        """Build a prompt for the LLM."""
        topic_text = f"विषय: {topic}" if topic else ""
        return (
            f"तुम एक भक्ति वीडियो स्क्रिप्ट राइटर हो। "
            f"बिल्कुल {deity} भगवान पर 60 सेकंड की हिंदी भक्ति वीडियो स्क्रिप्ट लिखो। "
            f"{topic_text}\n"
            f"स्क्रिप्ट इतनी होनी चाहिए कि सामान्य बोलने की गति पर 45-55 सेकंड में बोली जा सके। "
            f"केवल स्क्रिप्ट दो, कोई निर्देश नहीं। भावपूर्ण, प्रेरणादायक और आध्यात्मिक भाषा में। "
            f"अंत में एक मंत्र या भजन की पंक्ति जोड़ो।"
        )

    def _call_ollama(self, prompt):
        """Call Ollama API to generate text."""
        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }).encode()
        req = urllib.request.Request(
            self.ollama_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "")

    def _fallback_template(self, deity):
        """Return pre-written template for the deity."""
        deity = deity.lower()
        if deity not in self.templates:
            deity = "krishna"
        return random.choice(self.templates[deity])

    def estimate_duration(self, script_text):
        """Estimate spoken duration in seconds (~4 chars/sec for Hindi)."""
        return len(script_text) / 4.0
