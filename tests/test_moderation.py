"""Unit tests for the rule-matching logic in src/guard/moderation.py."""

import os

from src.guard.moderation import compile_rules, find_action, normalize


def _cfg(*rules):
    return {"enabled": True, "chats": [], "rules": list(rules)}


PROFANITY = {"name": "profanity", "words": ["хуй"], "action": "delete_warn", "reason": "мат"}
CAPS = {"name": "caps", "regex": ["!{3,}"], "action": "warn", "reason": "капс"}
INVITES = {"name": "invites", "regex": [r"t\.me/\+"], "action": "delete", "reason": "спам"}


class TestNormalize:
    def test_casefolds_and_unifies_yo(self):
        assert normalize("ХУЁВЫЙ") == "хуевый"

    def test_strips_zero_width_chars(self):
        assert normalize("ху​й") == "хуй"

    def test_collapses_whitespace(self):
        assert normalize("  а   б \n в ") == "а б в"


class TestWordMatching:
    def test_matches_plain_word(self):
        assert find_action("ты хуй", compile_rules(_cfg(PROFANITY))) == ("delete_warn", "мат")

    def test_matches_suffixed_form(self):
        rule = {"name": "p", "words": ["пизд"], "action": "delete_warn", "reason": "мат"}
        assert find_action("полный пиздец", compile_rules(_cfg(rule))) == ("delete_warn", "мат")

    def test_stem_alternation_needs_its_own_entry(self):
        """Russian inflection mutates the stem's last letter, so 'хуй' alone misses 'хуёвый'.

        Each alternation must be listed separately in config — the \\b anchor is what makes
        short variants like 'хую' safe to list at all.
        """
        only_j = compile_rules(_cfg(PROFANITY))
        assert find_action("хуёвый день", only_j) is None

        rule = {"name": "p", "words": ["хуй", "хуе"], "action": "delete_warn", "reason": "мат"}
        both = compile_rules(_cfg(rule))
        assert find_action("хуёвый день", both) == ("delete_warn", "мат")
        assert find_action("страхую машину", both) is None

    def test_matches_regardless_of_case(self):
        assert find_action("ХУЙ", compile_rules(_cfg(PROFANITY))) == ("delete_warn", "мат")

    def test_does_not_match_mid_word(self):
        """Scunthorpe guard: 'страхую' really does contain the stem 'хую'.

        The stem here must be 'хую', not 'хуй' — with 'хуй' the test would pass even if the
        word anchor were deleted entirely, proving nothing.
        """
        rule = {"name": "p", "words": ["хую"], "action": "delete_warn", "reason": "мат"}
        rules = compile_rules(_cfg(rule))
        assert find_action("страхую машину", rules) is None
        assert find_action("застрахую лодку", rules) is None
        assert find_action("иди на хую", rules) == ("delete_warn", "мат")

    def test_clean_message_returns_none(self):
        assert find_action("привет всем", compile_rules(_cfg(PROFANITY))) is None

    def test_empty_text_returns_none(self):
        assert find_action("", compile_rules(_cfg(PROFANITY))) is None

    def test_word_starting_with_symbol_still_matches(self):
        rule = {"name": "h", "words": ["@spambot"], "action": "delete", "reason": "спам"}
        assert find_action("пишите @spambot", compile_rules(_cfg(rule))) == ("delete", "спам")

    def test_blank_word_entry_does_not_match_everything(self):
        """A stray "" or " " in the word list would otherwise compile to a match-all pattern."""
        rule = {"name": "p", "words": ["хуй", " ", ""], "action": "delete_warn", "reason": "мат"}
        rules = compile_rules(_cfg(rule))
        assert find_action("привет, кто едет кататься?", rules) is None
        assert find_action("ты хуй", rules) == ("delete_warn", "мат")


class TestPrefixedForms:
    """Russian obscenity is prefix-productive; a bare \\b anchor would miss the whole register."""

    def test_prefixed_forms_are_caught(self):
        rule = {"name": "p", "words": ["хуй", "хуя", "хуе", "ебал"],
                "action": "delete_warn", "reason": "мат"}
        rules = compile_rules(_cfg(rule))
        for text in ["иди нахуй", "да похуй", "нихуя себе", "дохуя народу",
                     "охуеть просто", "он заебал", "наебал меня"]:
            assert find_action(text, rules) == ("delete_warn", "мат"), text

    def test_prefix_support_keeps_innocent_words_clean(self):
        rule = {"name": "p", "words": ["хую", "хуе", "муда", "ебо"],
                "action": "delete_warn", "reason": "мат"}
        rules = compile_rules(_cfg(rule))
        for text in ["я страхую машину", "похудел на два кило", "мудрый совет",
                     "себестоимость доски", "небо чистое", "прохудился гидрик"]:
            assert find_action(text, rules) is None, text


class TestRegexRules:
    def test_regex_rule_matches(self):
        assert find_action("t.me/+abc", compile_rules(_cfg(INVITES))) == ("delete", "спам")

    def test_broken_regex_is_skipped_without_crashing(self):
        bad = {"name": "bad", "regex": ["([a-z"], "action": "delete", "reason": "x"}
        rules = compile_rules(_cfg(bad, PROFANITY))
        assert find_action("ты хуй", rules) == ("delete_warn", "мат")

    def test_rule_with_only_broken_regex_is_dropped(self):
        bad = {"name": "bad", "regex": ["([a-z"], "action": "delete", "reason": "x"}
        assert compile_rules(_cfg(bad)) == []

    def test_uppercase_regex_still_fires(self):
        """The haystack is normalized, so a raw uppercase pattern would otherwise never match."""
        rule = {"name": "s", "regex": ["Купить кайт"], "action": "delete", "reason": "спам"}
        assert find_action("Купить кайт срочно", compile_rules(_cfg(rule))) == ("delete", "спам")

    def test_regex_containing_yo_still_fires(self):
        rule = {"name": "s", "regex": ["ещё"], "action": "delete", "reason": "спам"}
        assert find_action("ещё один кайт", compile_rules(_cfg(rule))) == ("delete", "спам")


class TestSeverity:
    def test_strictest_action_wins(self):
        rules = compile_rules(_cfg(CAPS, PROFANITY))
        assert find_action("что!!! и хуй", rules) == ("delete_warn", "мат")

    def test_strictest_wins_regardless_of_rule_order(self):
        rules = compile_rules(_cfg(PROFANITY, CAPS))
        assert find_action("что!!! и хуй", rules) == ("delete_warn", "мат")

    def test_lone_warn_rule_yields_warn(self):
        assert find_action("что!!!", compile_rules(_cfg(CAPS))) == ("warn", "капс")

    def test_unknown_action_is_skipped(self):
        weird = {"name": "w", "words": ["хуй"], "action": "nuke", "reason": "x"}
        assert compile_rules(_cfg(weird)) == []


class TestLiveConfig:
    """Guards the shipped rule list itself — the word list is where mistakes actually land."""

    @staticmethod
    def _live_rules():
        import json
        path = os.path.join(os.path.dirname(__file__), "..", "config.guard.json")
        with open(path, encoding="utf-8") as f:
            return compile_rules(json.load(f)["moderation"])

    INNOCENT = [
        "я страхую машину", "застрахую лодку", "художник рисует", "похудел на два кило",
        "прохудился гидрокостюм", "мудрый совет", "наихудший вариант", "обед в час",
        "победа наша", "себестоимость доски", "небо чистое", "требуется инструктор",
        "область низкого давления", "гондола подъемника", "гандбол по телику",
        "мудборд для проекта", "набережная пустая", "проехали мимо", "подъезд закрыт",
        "объявление на доске", "съезд в субботу", "привет всем кто едет на спот",
    ]

    PROFANITY = [
        "ты хуй", "иди нахуй", "да похуй", "нихуя себе волна", "дохуя народу",
        "охуеть просто", "хуёвый день", "полный пиздец", "он заебал уже",
        "заебись покатались", "ебать как дует", "наебали с прокатом", "уебан какой-то",
        "бля ветер сдох", "блядь опять штиль", "мудак на воде", "пидор редкостный",
        "отъебись уже", "съебался с гонки",
    ]

    def test_no_false_positives_on_everyday_speech(self):
        rules = self._live_rules()
        caught = [t for t in self.INNOCENT if find_action(t, rules)]
        assert caught == [], f"innocent messages flagged: {caught}"

    def test_catches_common_profanity_including_prefixed_forms(self):
        rules = self._live_rules()
        missed = [t for t in self.PROFANITY if not find_action(t, rules)]
        assert missed == [], f"profanity that slipped through: {missed}"

    def test_spam_links_are_caught(self):
        rules = self._live_rules()
        for link in ["заходи t.me/+abcdef", "t.me/joinchat/AAAA", "смотри bit.ly/xyz"]:
            assert find_action(link, rules) == ("delete", "спам-ссылка"), link


class TestCompileCache:
    def test_same_config_returns_cached_object(self):
        cfg = _cfg(PROFANITY)
        assert compile_rules(cfg) is compile_rules(cfg)

    def test_changed_config_recompiles(self):
        first = compile_rules(_cfg(PROFANITY))
        second = compile_rules(_cfg(CAPS))
        assert first is not second
        assert find_action("что!!!", second) == ("warn", "капс")
