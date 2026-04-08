import os
import requests

_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = "llama-3.3-70b-versatile"
_SYSTEM_PROMPT = (
    "Ты русскоязычный журналист в области кайтсёрфинга. "
    "Перепиши данную статью на русском языке — коротко и ёмко, сохрани ключевые факты. "
    "Текст должен умещаться в одно сообщение Telegram — не более 3500 символов. "
    "Не упоминай источник статьи, название сайта или издания. "
    "Не включай внешние ссылки, призывы перейти на другой сайт и фразы вроде «читайте далее». "
    "Выводи только текст статьи, без пояснений и пометок. "
    "Используй правильную терминологию: бар (bar), трапеция (harness), райдер (rider)."
)


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
