import json
import urllib.request
from collections.abc import Iterator

from ..config import settings
from .provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini. New AI Studio keys talk to gemini-3.8-flash."""

    def __init__(self):
        self.api_key = (settings.gemini_api_key or "").strip()
        self.model = (settings.gemini_model or "gemini-3.8-flash").strip()
        if not self.api_key:
            raise RuntimeError("Set GEMINI_API_KEY in .env")

    def generate_response(self, prompt: str) -> str:
        return "".join(self.generate_stream(prompt))

    def generate_stream(self, prompt: str) -> Iterator[str]:
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800},
        }
        request = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?alt=sse",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            buffer = ""
            while True:
                piece = response.read(1024)
                if not piece:
                    break
                buffer += piece.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    yield from self._texts(line)
            if buffer.strip():
                yield from self._texts(buffer)

    def _texts(self, line: str) -> Iterator[str]:
        line = line.strip()
        if not line.startswith("data:"):
            return
        raw = line[5:].strip()
        if not raw or raw == "[DONE]":
            return
        data = json.loads(raw)
        for candidate in data.get("candidates") or []:
            for part in (candidate.get("content") or {}).get("parts") or []:
                if part.get("thought"):
                    continue
                text = part.get("text")
                if text:
                    yield text
