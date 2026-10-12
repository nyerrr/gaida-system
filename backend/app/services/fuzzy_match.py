"""
fuzzy_match.py
--------------
Anchored fuzzy matching shared by the two detection engines (rule_intent.py and
virtual_agent.py).

WHY THIS EXISTS
    The lexicon engines need to survive typos and speech-to-text noise, so they
    fall back to SequenceMatcher when an exact phrase/keyword does not match. A
    naive similarity comparison, however, produces false positives on perfectly
    ordinary language, and every one of them escalates a harmless message:

        "I made a cake"       -> "mad"   (anger)
        "I said hello"        -> "sad"   (sadness, HIGH)
        "a wide range"        -> "rage"  (anger)
        "I want to sleep"     -> "i want to die"
        "I don't want to die" -> "i don't want to exist"   (a CRISIS, and a
                                statement that means the opposite)
        "I'm proud of myself" -> "off myself"              (a CRISIS)

    The last two are the worst: an unanchored phrase match of "of myself"
    against the suicide phrase "off myself" scores 0.947, and an unanchored
    match of "don't want to die" against "don't want to exist" scores ~0.85.
    Both fired the full crisis flow (hotline message + counselor alert).

    So both matchers here require the match to be *anchored*:

      * token_fuzzy  — only for keywords long enough to be unambiguous (>= 5
                       chars), sharing a first letter and within one character
                       in length. This kills sad/said, mad/made, rage/range.
      * phrase_fuzzy — the window must contain every non-function word of the
                       keyword (exactly, or fuzzily at the token level). A
                       one-letter function-word difference ("off" vs "of") or a
                       swapped content word ("die" vs "sleep") can no longer be
                       absorbed by the similarity score, because the missing
                       content word cannot be fuzzy-matched (it is too short or
                       too unlike).

    Shared, rather than duplicated, so the two engines cannot drift apart: the
    hard crisis path and the rule fallback have to agree on what counts as a
    match.
"""

from difflib import SequenceMatcher

# A token has to be at least this long before fuzzy matching is allowed at all.
# Short words carry too little signal: "mad" is one edit from "made", "sad" one
# from "said" and "sand", "rage" one from "range".
TOKEN_MIN_LEN = 5
# Spelling noise changes length by at most one character ("anxios" / "anxious").
TOKEN_LEN_SLACK = 1
TOKEN_FUZZY_THRESHOLD = 0.84
PHRASE_FUZZY_THRESHOLD = 0.85

# Function words may be missing from, or extra in, a fuzzy phrase window without
# invalidating it. Everything else is treated as content and must be present, so
# a window that drops or swaps a meaningful word is rejected.
FUNCTION_WORDS = frozenset({
    # English determiners / pronouns / auxiliaries / particles
    "a", "an", "the", "i", "im", "i'm", "i've", "i'll", "you", "your", "we",
    "us", "our", "it", "its", "is", "am", "are", "was", "were", "be", "been",
    "being", "to", "of", "on", "in", "at", "for", "with", "and", "or", "but",
    "so", "do", "does", "did", "doing", "not", "no", "just", "all", "will",
    "would", "can", "could", "should", "gonna", "wanna", "if", "that", "this",
    "there", "here", "as", "by", "from", "about", "up", "out", "still",
    # Tagalog / Taglish particles
    "na", "ng", "sa", "ko", "mo", "niya", "namin", "natin", "kami", "kayo",
    "sila", "ang", "mga", "lang", "pa", "ba", "si", "siya", "ay", "at", "yung",
    "ito", "iyan", "din", "rin", "naman", "nga", "eh", "po", "opo", "kasi",
    "para", "kung", "hindi", "di", "ayaw", "parang", "nang", "wala",
})


def token_fuzzy_match(keyword: str, token: str, threshold: float = TOKEN_FUZZY_THRESHOLD) -> bool:
    """Fuzzy-match a single-token keyword against one token, safely.

    Returns False for anything that could be a coincidence: a keyword shorter
    than TOKEN_MIN_LEN, a token with a different first letter, a token whose
    length is more than one character away, or a similarity under `threshold`.
    """
    if not keyword or not token:
        return False
    if len(keyword) < TOKEN_MIN_LEN:
        return False
    if token[:1] != keyword[:1]:
        return False
    if abs(len(token) - len(keyword)) > TOKEN_LEN_SLACK:
        return False
    return SequenceMatcher(None, keyword, token).ratio() >= threshold


def token_matches(keyword: str, tokens, threshold: float = TOKEN_FUZZY_THRESHOLD) -> bool:
    """Exact match first, then a constrained fuzzy match against each token."""
    if keyword in tokens:
        return True
    return any(token_fuzzy_match(keyword, t, threshold) for t in tokens)


def _window_covered(keyword_tokens, window_tokens, threshold: float) -> bool:
    """True when every content word of the keyword is present in the window.

    Function words are exempt, so an inserted "just" or a dropped "i" does not
    by itself reject the window; a missing or substituted content word does.
    """
    window = list(window_tokens)
    for kt in keyword_tokens:
        if kt in FUNCTION_WORDS or kt in window:
            continue
        if any(token_fuzzy_match(kt, wt, threshold) for wt in window):
            continue
        return False
    return True


def phrase_fuzzy_match(
    keyword: str, text: str, threshold: float = PHRASE_FUZZY_THRESHOLD
) -> bool:
    """Anchored windowed fuzzy match for a multi-word keyword.

    Slides a window the length of the keyword across `text`, and accepts it only
    when the window contains every content word of the keyword AND the overall
    similarity clears `threshold`.
    """
    keyword_tokens = keyword.split()
    n = len(keyword_tokens)
    if n < 2:
        return False
    text_tokens = (text or "").split()
    if len(text_tokens) < n:
        return False
    for i in range(len(text_tokens) - n + 1):
        window = text_tokens[i:i + n]
        if not _window_covered(keyword_tokens, window, TOKEN_FUZZY_THRESHOLD):
            continue
        if SequenceMatcher(None, keyword, " ".join(window)).ratio() >= threshold:
            return True
    return False
