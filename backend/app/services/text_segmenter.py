"""
text_segmenter.py
-----------------
Segment-level text analysis for chat messages.

Splits a message into sentences ("segments"), scores each segment's
sentiment from a curated English + Taglish lexicon, and flags words or
phrases indicative of anxiety, stress, sadness, or crisis cues.

Design contract — deliberately additive and non-intrusive:

  * This module does NOT classify intent, change confidence, or alter
    severity. That stays in virtual_agent.py / rule_intent.py /
    ml_classifier.py. Nothing here can change a response or fire/withhold
    an alert.
  * Its only job is observability: the per-segment breakdown is stored in
    the interaction's `analysis` record, so a reviewer (or a panel) can
    see the segment-level breakdown behind a message.

Honesty note: sentiment here is a lightweight lexicon score (positive vs.
negative word counts with a light negation flip), not a trained model.
Describe it that way in any documentation.
"""

import re
from typing import Dict, List

# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

_SEGMENT_SPLIT_RE = re.compile(r"[.!?;]+|\n+")

# ---------------------------------------------------------------------------
# Sentiment lexicons (English + Taglish tokens)
# ---------------------------------------------------------------------------

POSITIVE_WORDS = {
    # English
    "happy", "glad", "good", "great", "better", "fine", "calm", "relieved",
    "relaxed", "excited", "grateful", "thankful", "hopeful", "blessed",
    "proud", "confident", "peaceful", "content", "loved", "safe", "okay",
    "ok", "alright", "wonderful", "amazing", "awesome", "joy", "enjoyed",
    "nice", "kind", "supported", "helped", "strong", "satisfied",
    "comfortable", "positive", "bright",
    # Filipino / Taglish
    "masaya", "saya", "magaan", "panatag", "kalmado", "nakakagaan",
    "nakakatulong", "laking-tulong", "ayos", "ganda", "galing", "salamat",
}

NEGATIVE_WORDS = {
    # English
    "sad", "sadness", "unhappy", "miserable", "hopeless", "helpless",
    "worthless", "depressed", "depression", "lonely", "empty", "broken",
    "afraid", "scared", "worried", "worry", "nervous", "anxious", "anxiety",
    "panic", "overwhelmed", "stressed", "stress", "tired", "exhausted",
    "drained", "burned", "burdened", "burden", "useless", "unwanted",
    "ignored", "abandoned", "hurt", "painful", "anger", "frustrated",
    "frustrating", "cry", "crying", "failing", "fail", "afraid", "terrible",
    "awful", "hate", "worst", "worse", "bad", "suffering", "struggling",
    "struggle", "fear", "scared", "numb", "lost", "trapped", "anxious",
    "pressure", "overwhelm", "drowning", "sleep", "dead", "dying", "die",
    # Filipino / Taglish
    "malungkot", "lungkot", "takot", "natatakot", "kinakabahan", "kabado",
    "balisa", "naiistress", "pagod", "napapagod", "hirap", "nahihirapan",
    "masakit", "sakit", "suko", "umiiyak", "iyak", "gulo", "problema",
    "problema", "mawala",
}

NEGATION_WORDS = {
    "not", "no", "never", "dont", "don't", "cannot", "cant", "can't",
    "hindi", "wala", "di", "diko", "ayoko", "ayaw",
}

# ---------------------------------------------------------------------------
# Distress flags — words/phrases indicative of anxiety, stress, sadness,
# or crisis. Reused/trimmed from the rule-engine keyword lists so the
# flagging vocabulary stays consistent with the classifier vocabulary.
# ---------------------------------------------------------------------------

_DISTRESS_PATTERNS: List[re.Pattern] = [
    re.compile(
        r"\b(anxious|anxiety|nervous|worried|worry|worries|panic\w*|"
        r"overthink\w*|restless|uneasy|kinakabahan|kabado|balisa|"
        r"natatakot|natataranta|nag-aalala|nag aalala)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(stress\w*|overwhelm\w*|pressure|burnout|drained|exhausted|"
        r"pagod|naiistress|ubos na energy|wala nang oras|deadlines)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(sad|sadness|depress\w*|hopeless\w*|lonely|worthless|"
        r"malungkot|lungkot|walang halaga|iyak\w*|umiiyak|wala nang gana)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(kill\w*|suicid\w*|die|dying|dead|self[- ]?harm\w*|hurt myself|"
        r"harm myself|cut myself|end my life|mamatay|magpapakamatay|"
        r"wawakasan|tatapusin|mawala na lang)\b",
        re.IGNORECASE,
    ),
    # Relationship / attachment loss. Observability only (see the module
    # contract) — this does not classify intent, change confidence, or fire
    # anything. It exists so a counselor reviewing a transcript can see that a
    # message carried "still love him" / "naghihati" as distinct cues rather
    # than reading as generic sadness.
    re.compile(
        r"\b(broke up|break up|breakup|my ex|ex-boyfriend|ex-girlfriend|"
        r"naghihati|hiwalay na|gusto ko pa|still (want|love|miss) (him|her)|"
        r"naiisip ko siya|checking his|checking her)\b",
        re.IGNORECASE,
    ),
]


def split_segments(text: str) -> List[str]:
    """Split a chat message into sentence segments.

    Splits on sentence punctuation (. ! ? ;) and newlines. Empty and
    whitespace-only input returns []. Keeps the underlying text untouched
    otherwise (chat messages rarely follow strict sentence grammar).
    """
    if not text or not text.strip():
        return []
    parts = [p.strip() for p in _SEGMENT_SPLIT_RE.split(text)]
    return [p for p in parts if p]


def _tokens(segment: str) -> List[str]:
    return re.findall(r"[a-z']+", segment.lower())


def sentiment_polarity(segment: str) -> float:
    """Lexicon sentiment score in [-1.0, 1.0].

    Positive over negative word counts in the segment, with a light
    negation flip: a negation token ("not", "hindi", "wala", ...) within
    the two preceding tokens inverts the word's contribution.
    """
    tokens = _tokens(segment)
    if not tokens:
        return 0.0

    score = 0.0
    hits = 0
    for i, tok in enumerate(tokens):
        if tok in NEGATION_WORDS:
            continue
        if tok in POSITIVE_WORDS:
            val = 1.0
        elif tok in NEGATIVE_WORDS:
            val = -1.0
        else:
            continue

        window_start = max(0, i - 2)
        if any(n in tokens[window_start:i] for n in NEGATION_WORDS):
            val = -val
        score += val
        hits += 1

    if hits == 0:
        return 0.0
    return round(max(-1.0, min(1.0, score / hits)), 3)


def flag_distress(segment: str) -> List[str]:
    """Return the distinct distress cue words matched in a segment.

    Empty/none matches return []. Matches are the actual flagged text
    (lowercased), so the stored analysis shows *which* words triggered
    the flag, not just a category.
    """
    if not segment:
        return []
    flags: List[str] = []
    for pattern in _DISTRESS_PATTERNS:
        for m in pattern.finditer(segment):
            word = m.group(0).strip().lower()
            if word not in flags:
                flags.append(word)
    return flags


def analyze_text_segments(text: str) -> List[Dict[str, object]]:
    """Full segment-level breakdown for a message.

    Returns a list of {"segment", "sentiment", "distress_flags"} entries,
    one per sentence, in order. Empty input returns [].
    """
    out: List[Dict[str, object]] = []
    for seg in split_segments(text):
        out.append(
            {
                "segment": seg,
                "sentiment": sentiment_polarity(seg),
                "distress_flags": flag_distress(seg),
            }
        )
    return out