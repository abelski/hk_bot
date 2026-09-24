"""Rule matching for chat moderation. Pure text logic — no Telegram dependencies."""

import json
import logging
import re

logger = logging.getLogger(__name__)

# Severity ladder: when several rules match one message, the highest rank wins.
ACTIONS = {"warn": 1, "delete": 2, "delete_warn": 3, "delete_ban": 4}
_MAX_RANK = max(ACTIONS.values())

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)

_cache_key = None
_cache_rules = None


def normalize(text: str) -> str:
    return " ".join(text.translate(_ZERO_WIDTH).casefold().replace("ё", "е").split())


# Russian obscenity is prefix-productive (нахуй, похуй, заебал, охуеть, распиздяй) and a
# prefix belongs to the same orthographic word, so a bare \b would only ever match the bare
# stem. Allowing one optional known prefix after the boundary keeps "страхую" clean — "стра"
# is not a prefix — while catching the register that actually dominates a Russian chat.
_PREFIXES = (
    "недо|подо|разо|пере|обо|ото|подъ|разъ|отъ|объ|съ|въ|рас|раз|под|при|про|пред|над|"
    "на|по|до|ни|за|от|об|из|во|со|вы|не|о|у|с|в"
)


def _word_pattern(word: str):
    escaped = re.escape(normalize(word))
    if not escaped:
        return None  # a blank entry would compile to an empty pattern matching every message
    if escaped[0].isalnum() or escaped[0] == "_":
        return re.compile(rf"\b(?:{_PREFIXES})?{escaped}")
    # \b before a non-word char never matches, so leave such entries unanchored.
    return re.compile(escaped)


def compile_rules(moderation_cfg: dict) -> list:
    """Compile config rules to [(rank, action, reason, patterns)], cached by config content."""
    global _cache_key, _cache_rules
    key = json.dumps(moderation_cfg, sort_keys=True, ensure_ascii=False)
    if key == _cache_key:
        return _cache_rules

    compiled = []
    for rule in moderation_cfg.get("rules", []):
        name = rule.get("name", "<unnamed>")
        rank = ACTIONS.get(rule.get("action"))
        if rank is None:
            logger.warning("Rule %r: unknown action %r, skipped", name, rule.get("action"))
            continue
        patterns = [p for p in (_word_pattern(w) for w in rule.get("words", [])) if p]
        for raw in rule.get("regex", []):
            try:
                # The haystack is normalized, so a pattern containing ё or uppercase would
                # never fire. Fold ё (not a metachar) and match case-insensitively instead of
                # normalizing the pattern itself, which would corrupt escapes like \S -> \s.
                patterns.append(re.compile(raw.replace("ё", "е").replace("Ё", "е"), re.IGNORECASE))
            except re.error as exc:
                logger.warning("Rule %r: bad regex %r (%s), skipped", name, raw, exc)
        if patterns:
            compiled.append((rank, rule["action"], rule.get("reason", ""), patterns))

    _cache_key, _cache_rules = key, compiled
    return compiled


def find_action(text: str, rules: list):
    """Return (action, reason) for the strictest matching rule, or None if nothing matches."""
    if not text:
        return None
    normalized = normalize(text)
    best = None
    for rank, action, reason, patterns in rules:
        if best is not None and rank <= best[0]:
            continue
        if any(p.search(normalized) for p in patterns):
            best = (rank, action, reason)
            if rank == _MAX_RANK:
                break
    return (best[1], best[2]) if best else None
