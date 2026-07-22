#!/usr/bin/env python3
"""Modular OCR providers for the scan-to-blog pipeline.

Providers expose ``recognize(image_path) -> str``. ``FallbackOCR`` tries them
in order and returns the first non-empty transcript. Provider failures are
logged and do not prevent later providers from running.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOG = logging.getLogger("scan_to_post.ocr")

DEFAULT_PROMPT = (
    "Transcribe every visible word in this scanned page exactly as written. "
    "Preserve paragraph breaks, capitalization, punctuation, and reading order. "
    "Do not summarize, correct, explain, wrap the result in Markdown fences, or "
    "add commentary. Return only the transcription."
)


class OCRProviderError(RuntimeError):
    """An OCR provider could not produce a usable transcript."""


@dataclass(frozen=True)
class OCRResult:
    text: str
    provider: object


class FallbackOCR:
    def __init__(self, providers: list[object]):
        if not providers:
            raise ValueError("at least one OCR provider is required")
        self.providers = providers

    def recognize(self, image_path: Path) -> OCRResult:
        failures = []
        for provider in self.providers:
            name = provider.__class__.__name__
            try:
                text = provider.recognize(image_path).strip()
            except OCRProviderError as exc:
                LOG.warning("%s failed for %s: %s", name, image_path.name, exc)
                failures.append(f"{name}: {exc}")
                continue
            if text:
                LOG.info("%s read %s", name, image_path.name)
                return OCRResult(text=text, provider=provider)
            LOG.warning("%s returned no text for %s", name, image_path.name)
            failures.append(f"{name}: empty result")
        raise OCRProviderError("all OCR providers failed: " + "; ".join(failures))


def recognize_pages(chain: FallbackOCR, image_paths: list[Path]) -> tuple[list[str], list[str]]:
    """Read pages independently while preserving page-to-text alignment."""
    pages = []
    provider_names = []
    for image_path in image_paths:
        try:
            result = chain.recognize(image_path)
        except OCRProviderError as exc:
            LOG.error("OCR failed for %s: %s", image_path.name, exc)
            pages.append("")
            provider_names.append("failed")
        else:
            pages.append(result.text)
            provider_names.append(result.provider.__class__.__name__)
    return pages, provider_names


class HermesVisionOCR:
    """Call a Hermes Agent OpenAI-compatible API with an inline image."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        *,
        prompt: str = DEFAULT_PROMPT,
        timeout: float = 120.0,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.timeout = timeout

    def recognize(self, image_path: Path) -> str:
        mime = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{encoded}",
                            "detail": "high",
                        },
                    },
                ],
            }],
        }
        request = Request(
            f"{self.endpoint}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read())
            text = data["choices"][0]["message"]["content"]
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError,
                KeyError, IndexError, TypeError) as exc:
            raise OCRProviderError(f"Hermes API request failed: {exc}") from exc
        if not isinstance(text, str):
            raise OCRProviderError("Hermes API returned non-text content")
        return text.strip()


class OllamaDirectOCR:
    """Call a local Ollama server directly, bypassing any wrapper API.

    This is the level-1 fallback: it survives even when the Hermes API
    server itself is crashed or unreachable. We POST to ``/api/chat`` with
    the OpenAI-compatible ``image_url`` data URL form, which Ollama accepts
    natively for multimodal models like ``glm-ocr``.
    """

    def __init__(
        self,
        endpoint: str,
        model: str,
        *,
        prompt: str = DEFAULT_PROMPT,
        timeout: float = 120.0,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.prompt = prompt
        self.timeout = timeout

    def recognize(self, image_path: Path) -> str:
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        # Ollama's native /api/chat multimodal format. Unlike the
        # OpenAI-compatible `/v1/chat/completions` endpoint, Ollama accepts
        # `content` as a plain string and the image as a base64 entry in
        # a separate `images` array on the user message.
        payload = {
            "model": self.model,
            "stream": False,
            # GLM-OCR's native 128K default reserves about 6.5 GB on this
            # 8 GB GPU and crashes the Ollama runner. OCR pages need far less.
            "options": {"num_ctx": 8192},
            "messages": [{
                "role": "user",
                "content": self.prompt,
                "images": [encoded],
            }],
        }
        request = Request(
            f"{self.endpoint}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise OCRProviderError(f"Ollama /api/chat request failed: {exc}") from exc
        text = (
            data.get("message", {}).get("content")
            if isinstance(data.get("message"), dict)
            else None
        )
        if text is None:
            text = data.get("response")
        if not isinstance(text, str):
            raise OCRProviderError(
                "Ollama returned non-text content (likely a vision model error)"
            )
        return text.strip()


class TesseractOCR:
    def __init__(self, language: str = "eng", timeout: float = 60.0):
        self.language = language
        self.timeout = timeout

    def recognize(self, image_path: Path) -> str:
        try:
            completed = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", self.language],
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError) as exc:
            raise OCRProviderError(f"Tesseract failed: {exc}") from exc
        return completed.stdout.strip()


def build_ocr_chain_from_env() -> FallbackOCR:
    """Create the configured provider chain.

    Default two-tier fallback:
      1. ollama    — direct local Ollama (no gateway or OCR profile involved)
      2. tesseract — local deterministic fallback

    ``hermes`` remains available as an optional provider for explicit
    ``SCAN_OCR_PROVIDERS`` overrides, but it is not part of the default path.

    Environment:
      SCAN_OCR_PROVIDERS      comma-separated names (default ollama,tesseract)
      OLLAMA_OCR_URL          local Ollama base URL (default http://192.168.0.8:11434)
      OLLAMA_OCR_MODEL        vision/OCR model to call directly (default glm-ocr)
      OLLAMA_OCR_TIMEOUT      request timeout seconds
      OLLAMA_OCR_CONTEXT      Ollama context tokens (default 8192; constrains VRAM)
      OLLAMA_OCR_PROMPT       optional transcription prompt
      HERMES_OCR_URL          OpenAI-compatible base URL ending in /v1
      HERMES_OCR_API_KEY      bearer token
      HERMES_OCR_MODEL        advertised Hermes API model name
      HERMES_OCR_TIMEOUT      request timeout seconds
      HERMES_OCR_PROMPT       optional transcription prompt
      TESSERACT_LANGUAGE      language pack (default eng)
    """
    names = [
        name.strip().lower()
        for name in os.getenv("SCAN_OCR_PROVIDERS", "ollama,tesseract").split(",")
        if name.strip()
    ]
    providers = []
    for name in names:
        if name == "ollama":
            endpoint = os.getenv("OLLAMA_OCR_URL", "http://192.168.0.8:11434").strip()
            model = os.getenv("OLLAMA_OCR_MODEL", "glm-ocr").strip()
            if not endpoint or not model:
                LOG.warning("Ollama OCR is configured but URL/model is missing; skipping")
                continue
            providers.append(OllamaDirectOCR(
                endpoint=endpoint,
                model=model,
                prompt=os.getenv("OLLAMA_OCR_PROMPT", DEFAULT_PROMPT),
                timeout=float(os.getenv("OLLAMA_OCR_TIMEOUT", "300")),
            ))
        elif name == "hermes":
            endpoint = os.getenv("HERMES_OCR_URL", "").strip()
            api_key = os.getenv("HERMES_OCR_API_KEY", "").strip()
            model = os.getenv("HERMES_OCR_MODEL", "hermes-ocr").strip()
            if not endpoint or not api_key:
                LOG.warning("Hermes OCR is configured but URL/key is missing; skipping")
                continue
            providers.append(HermesVisionOCR(
                endpoint=endpoint,
                api_key=api_key,
                model=model,
                prompt=os.getenv("HERMES_OCR_PROMPT", DEFAULT_PROMPT),
                timeout=float(os.getenv("HERMES_OCR_TIMEOUT", "120")),
            ))
        elif name == "tesseract":
            providers.append(TesseractOCR(
                language=os.getenv("TESSERACT_LANGUAGE", "eng"),
            ))
        else:
            raise ValueError(f"unknown OCR provider: {name}")
    if not providers:
        raise ValueError("no usable OCR providers configured")
    return FallbackOCR(providers)
