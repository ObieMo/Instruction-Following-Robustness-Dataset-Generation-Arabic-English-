import re

_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
_LATIN_RE  = re.compile(r"[A-Za-z]")

def _ratio(text: str, pattern: re.Pattern) -> float:
    if not text:
        return 0.0
    hits = len(pattern.findall(text))
    return hits / max(len(text), 1)

def arabic_ratio(text: str) -> float:
    return _ratio(text, _ARABIC_RE)

def english_ratio(text: str) -> float:
    return _ratio(text, _LATIN_RE)

def basic_clean(s: str) -> str:
    return (s or "").strip()

def is_valid_chosen(text: str, *, min_chars: int, arabic_ratio_min: float) -> bool:
    t = basic_clean(text)
    if len(t) < min_chars:
        return False
    return arabic_ratio(t) >= arabic_ratio_min and english_ratio(t) <= 0.15

def is_valid_rejected(text: str, *, min_chars: int, english_ratio_min: float) -> bool:
    t = basic_clean(text)
    if len(t) < min_chars:
        return False
    # rejected should look English-heavy
    return english_ratio(t) >= english_ratio_min
