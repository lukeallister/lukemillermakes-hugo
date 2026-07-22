import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "ocr-pipeline" / "ocr_backends.py"
spec = importlib.util.spec_from_file_location("ocr_backends", MODULE_PATH)
ocr_backends = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ocr_backends
spec.loader.exec_module(ocr_backends)


class FakeProvider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def recognize(self, image_path):
        self.calls.append(image_path)
        if self.error:
            raise self.error
        return self.result


class FallbackOCRTests(unittest.TestCase):
    def test_returns_first_nonempty_provider_result(self):
        first = FakeProvider("  AI transcript  ")
        fallback = FakeProvider("tesseract")
        chain = ocr_backends.FallbackOCR([first, fallback])

        result = chain.recognize(Path("page.jpg"))

        self.assertEqual(result.text, "AI transcript")
        self.assertEqual(result.provider, first)
        self.assertEqual(fallback.calls, [])

    def test_falls_back_after_provider_error(self):
        primary = FakeProvider(error=ocr_backends.OCRProviderError("offline"))
        fallback = FakeProvider("tesseract transcript")
        chain = ocr_backends.FallbackOCR([primary, fallback])

        result = chain.recognize(Path("page.jpg"))

        self.assertEqual(result.text, "tesseract transcript")
        self.assertEqual(result.provider, fallback)

    def test_falls_back_after_empty_result(self):
        primary = FakeProvider("   ")
        fallback = FakeProvider("fallback")

        result = ocr_backends.FallbackOCR([primary, fallback]).recognize(Path("page.jpg"))

        self.assertEqual(result.text, "fallback")

    def test_raises_when_every_provider_fails(self):
        chain = ocr_backends.FallbackOCR([
            FakeProvider(error=ocr_backends.OCRProviderError("down")),
            FakeProvider(""),
        ])

        with self.assertRaises(ocr_backends.OCRProviderError):
            chain.recognize(Path("page.jpg"))

    def test_recognize_pages_keeps_page_alignment_when_one_page_fails(self):
        provider = SequenceProvider(["page one", ocr_backends.OCRProviderError("bad"), "page three"])
        chain = ocr_backends.FallbackOCR([provider])

        pages, provider_names = ocr_backends.recognize_pages(
            chain,
            [Path("1.jpg"), Path("2.jpg"), Path("3.jpg")],
        )

        self.assertEqual(pages, ["page one", "", "page three"])
        self.assertEqual(provider_names, ["SequenceProvider", "failed", "SequenceProvider"])


class SequenceProvider:
    def __init__(self, results):
        self.results = iter(results)

    def recognize(self, image_path):
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


class HermesVisionOCRTests(unittest.TestCase):
    def test_sends_openai_compatible_inline_image_request(self):
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "page.jpg"
            image.write_bytes(b"jpeg-data")
            provider = ocr_backends.HermesVisionOCR(
                endpoint="http://hermes.example:8643/v1",
                api_key="secret",
                model="hermes-ocr",
            )
            response = json.dumps({
                "choices": [{"message": {"content": "Exact transcript"}}]
            }).encode()

            with patch.object(ocr_backends, "urlopen", return_value=FakeHTTPResponse(response)) as mocked:
                text = provider.recognize(image)

            request = mocked.call_args.args[0]
            body = json.loads(request.data)
            self.assertEqual(request.full_url, "http://hermes.example:8643/v1/chat/completions")
            self.assertEqual(request.headers["Authorization"], "Bearer secret")
            self.assertEqual(body["model"], "hermes-ocr")
            parts = body["messages"][0]["content"]
            self.assertEqual(parts[1]["type"], "image_url")
            self.assertTrue(parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
            self.assertEqual(text, "Exact transcript")

    def test_rejects_malformed_response(self):
        provider = ocr_backends.HermesVisionOCR("http://x/v1", "key", "model")
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "page.png"
            image.write_bytes(b"png")
            with patch.object(ocr_backends, "urlopen", return_value=FakeHTTPResponse(b"{}")):
                with self.assertRaises(ocr_backends.OCRProviderError):
                    provider.recognize(image)


class TesseractOCRTests(unittest.TestCase):
    def test_reads_stdout_from_tesseract(self):
        completed = subprocess.CompletedProcess([], 0, stdout="typed words\n", stderr="")
        with patch.object(ocr_backends.subprocess, "run", return_value=completed) as mocked:
            text = ocr_backends.TesseractOCR(language="eng").recognize(Path("page.jpg"))

        self.assertEqual(text, "typed words")
        self.assertEqual(mocked.call_args.args[0], ["tesseract", "page.jpg", "stdout", "-l", "eng"])


class OllamaDirectOCRTests(unittest.TestCase):
    def test_posts_to_ollama_api_chat_with_inline_base64_image(self):
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "page.jpg"
            image.write_bytes(b"jpeg-data")
            provider = ocr_backends.OllamaDirectOCR(
                endpoint="http://192.168.0.8:11434",
                model="glm-ocr",
            )
            response = json.dumps({"message": {"content": "Direct OCR transcript"}}).encode()

            with patch.object(ocr_backends, "urlopen", return_value=FakeHTTPResponse(response)) as mocked:
                text = provider.recognize(image)

            request = mocked.call_args.args[0]
            body = json.loads(request.data)
            self.assertEqual(request.full_url, "http://192.168.0.8:11434/api/chat")
            self.assertEqual(body["model"], "glm-ocr")
            self.assertEqual(body["messages"][0]["content"], ocr_backends.DEFAULT_PROMPT)
            self.assertEqual(body["messages"][0]["images"], ["anBlZy1kYXRh"])
            self.assertEqual(body["options"]["num_ctx"], 8192)
            self.assertEqual(text, "Direct OCR transcript")

    def test_rejects_empty_or_invalid_ollama_responses(self):
        provider = ocr_backends.OllamaDirectOCR("http://x", "glm-ocr")
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "page.png"
            image.write_bytes(b"png")
            with patch.object(ocr_backends, "urlopen", return_value=FakeHTTPResponse(b"{}")):
                with self.assertRaises(ocr_backends.OCRProviderError):
                    provider.recognize(image)

    def test_ollama_provider_accepts_text_only_responses(self):
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "page.jpg"
            image.write_bytes(b"x")
            provider = ocr_backends.OllamaDirectOCR("http://x", "glm-ocr")
            response = json.dumps({"response": "Plain text response"}).encode()
            with patch.object(ocr_backends, "urlopen", return_value=FakeHTTPResponse(response)):
                self.assertEqual(provider.recognize(image), "Plain text response")


class ConfigurationTests(unittest.TestCase):
    def test_default_chain_is_direct_ollama_then_tesseract(self):
        with patch.dict(ocr_backends.os.environ, {}, clear=True):
            chain = ocr_backends.build_ocr_chain_from_env()

        self.assertEqual([p.__class__ for p in chain.providers], [
            ocr_backends.OllamaDirectOCR,
            ocr_backends.TesseractOCR,
        ])
        self.assertEqual(chain.providers[0].endpoint, "http://192.168.0.8:11434")
        self.assertEqual(chain.providers[0].model, "glm-ocr")
        self.assertEqual(chain.providers[0].timeout, 300.0)

    def test_builds_ollama_then_hermes_then_tesseract_chain_from_environment(self):
        env = {
            "SCAN_OCR_PROVIDERS": "ollama,hermes,tesseract",
            "OLLAMA_OCR_URL": "http://192.168.0.8:11434",
            "OLLAMA_OCR_MODEL": "glm-ocr",
            "OLLAMA_OCR_CONTEXT": "4096",
            "HERMES_OCR_URL": "http://host:8643/v1",
            "HERMES_OCR_API_KEY": "key",
            "HERMES_OCR_MODEL": "hermes-ocr",
        }
        with patch.dict(ocr_backends.os.environ, env, clear=True):
            chain = ocr_backends.build_ocr_chain_from_env()

        self.assertEqual([p.__class__ for p in chain.providers], [
            ocr_backends.OllamaDirectOCR,
            ocr_backends.HermesVisionOCR,
            ocr_backends.TesseractOCR,
        ])
        self.assertEqual(chain.providers[0].model, "glm-ocr")

    def test_skipping_ollama_when_url_missing(self):
        env = {
            "SCAN_OCR_PROVIDERS": "ollama,hermes,tesseract",
            "OLLAMA_OCR_URL": "",
            "OLLAMA_OCR_MODEL": "",
            "HERMES_OCR_URL": "http://host:8643/v1",
            "HERMES_OCR_API_KEY": "key",
            "HERMES_OCR_MODEL": "hermes-ocr",
        }
        with patch.dict(ocr_backends.os.environ, env, clear=True):
            chain = ocr_backends.build_ocr_chain_from_env()

        self.assertEqual([p.__class__ for p in chain.providers], [
            ocr_backends.HermesVisionOCR,
            ocr_backends.TesseractOCR,
        ])

    def test_legacy_hermes_then_tesseract_still_works(self):
        env = {
            "SCAN_OCR_PROVIDERS": "hermes,tesseract",
            "HERMES_OCR_URL": "http://host:8643/v1",
            "HERMES_OCR_API_KEY": "key",
            "HERMES_OCR_MODEL": "hermes-ocr",
        }
        with patch.dict(ocr_backends.os.environ, env, clear=True):
            chain = ocr_backends.build_ocr_chain_from_env()

        self.assertEqual([p.__class__ for p in chain.providers], [
            ocr_backends.HermesVisionOCR,
            ocr_backends.TesseractOCR,
        ])


class FakeHTTPResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


if __name__ == "__main__":
    unittest.main()
