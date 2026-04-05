import time
import requests
from helpers.abstract_helper import AbstractHelper

_API_URL = "https://api.mymemory.translated.net/get"
_MAX_CHARS = 500


class TranslationHelper(AbstractHelper):
    def process_text(self, text: str) -> str:
        return translate_to_russian(text)


def translate_to_russian(text: str) -> str:
    """Translate text to Russian via MyMemory. Returns original text on any failure."""
    if not text or not text.strip():
        return text
    chunks = _split(text)
    translated = []
    for chunk in chunks:
        result = _translate_chunk(chunk)
        if result is None:
            return text  # fallback: return original
        translated.append(result)
    return "\n\n".join(translated)


def _split(text: str) -> list:
    """Split text into ≤500-char chunks on paragraph then sentence boundaries."""
    paragraphs = text.split("\n\n")
    chunks = []
    for para in paragraphs:
        if len(para) <= _MAX_CHARS:
            chunks.append(para)
        else:
            sentences = para.split(". ")
            current = ""
            for s in sentences:
                piece = (current + ". " + s).strip() if current else s
                if len(piece) <= _MAX_CHARS:
                    current = piece
                else:
                    if current:
                        chunks.append(current)
                    current = s
            if current:
                chunks.append(current)
    return chunks


def _translate_chunk(text: str, retries: int = 1) -> str | None:
    for attempt in range(retries + 1):
        try:
            r = requests.get(
                _API_URL,
                params={"q": text, "langpair": "en|ru"},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("responseStatus") == 200:
                return data["responseData"]["translatedText"]
            return None
        except Exception:
            if attempt == retries:
                return None
            time.sleep(1)
