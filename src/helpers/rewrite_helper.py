import os
import pathlib
import requests

_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = "llama-3.3-70b-versatile"
_PROMPT_FILE = pathlib.Path(__file__).parent / "rewrite_prompt.txt"

def _load_system_prompt() -> str:
    try:
        return _PROMPT_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""

_SYSTEM_PROMPT = _load_system_prompt()


def strip_hashtags(text: str) -> str:
    """Remove #hashtag tokens from text."""
    import re
    return re.sub(r"#\S+", "", text).strip()


def rewrite_to_russian(title: str, text: str) -> str | None:
    """Rewrite article as a short Russian summary via Groq. Returns None on failure."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None
    prompt = f"{title}\n\n{text}" if title else text
    try:
        r = requests.post(
            _API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt[:4000]},
                ],
                "max_tokens": 400,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
