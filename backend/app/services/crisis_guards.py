"""
crisis_guards.py
----------------
Context guards that decide whether a matched suicidal keyword is REAL risk or is
being diluted by surrounding context. Used by both rule_intent.py (rule fallback)
and virtual_agent.py (hard crisis path) so the whole pipeline agrees.

Guards:
    1. SOFT_VENTING_PHRASES  — colloquial "I give up" phrases. These are only
       treated as suicidal when NO school/work context surrounds them. With
       school/work context they are venting → reclassified as stress.
    2. FICTION_CONTEXT       — essays, movies, songs, stories, poems. The death
       talk is about content, not the speaker → tone down, no auto-alert.
    3. HYPOTHETICAL_CONTEXT  — hedged/conditional musing ("what if", "kung").
       Still concerning, but not yet an active plan → keep alert at HIGH.
"""

import re

# Colloquial "give up" phrases. Normalized keys; compare via is_soft_venting_phrase.
SOFT_VENTING_PHRASES = {
    "i can't do this anymore",
    "cant do this anymore",
    "i give up on everything",
    "i'm done with everything",
    "im done with everything",
    "i just want it to stop",
    "no point in trying anymore",
    "tired of it all",
    "make everything stop",
    "make it all stop",
    "ayoko na ng lahat",
    "ayoko na sa lahat",
    "nagpaalam na ako",
}

_APOS_TRANSLATE = str.maketrans({"’": "'", "‘": "'"})


def is_soft_venting_phrase(keyword: str) -> bool:
    """True if the matched keyword is a colloquial give-up phrase (not an
    explicit self-harm statement). Fuzzy-match tags are stripped first."""
    norm = keyword.lower().replace(" (fuzzy)", "").translate(_APOS_TRANSLATE).strip()
    return norm in SOFT_VENTING_PHRASES


TONING_CONTEXTS = (
    "school", "classes", "class", "exams", "exam", "tests", "test", "quiz",
    "finals", "thesis", "assignments", "assignment", "projects", "project",
    "homework", "requirements", "deadlines", "deadline", "grades", "grade",
    "professor", "teacher", "subjects", "subject", "classmate", "classmates",
    "aral", "pag aaral", "mag aral", "magaral", "pumasok", "pasok", "studying",
    "studies", "study", "semester", "sem", "curriculum", "syllabus",
    "recitation", "plates", "defense", "groupwork", "activity", "activities",
    "utang", "tuition", "work", "job", "workload", "overtime", "shift", "boss",
    "client", "meeting",
)

TONING_CONTEXT_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in TONING_CONTEXTS) + r")\b",
    re.IGNORECASE,
)


def has_venting_context(text: str) -> bool:
    """True when the message is clearly about school/work (a known FP vector
    for colloquial give-up phrases)."""
    return bool(TONING_CONTEXT_RE.search(text or ""))


FICTION_CONTEXTS = (
    "movie", "film", "show", "series", "episode", "character", "scene", "story",
    "novel", "book", "anime", "manga", "fiction", "fantasy", "song", "lyrics",
    "lyric", "poem", "poetry", "essay", "quote", "kwento", "pelikula",
)

FICTION_CONTEXT_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in FICTION_CONTEXTS) + r")\b",
    re.IGNORECASE,
)


def has_fiction_context(text: str) -> bool:
    """True when the message is about media/creative content rather than the
    speaker's own life (essay, movie, story, song...)."""
    return bool(FICTION_CONTEXT_RE.search(text or ""))


HYPOTHETICAL_CONTEXTS = (
    "what if", "if i", "hypothetically", "suppose", "supposedly", "imagine",
    "if someone", "if you", "kunwari", "parang", "kung",
)

HYPOTHETICAL_CONTEXT_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in HYPOTHETICAL_CONTEXTS) + r")\b",
    re.IGNORECASE,
)


def has_hypothetical_context(text: str) -> bool:
    """True when the death-talk is hedged/conditional. Risk is still real, so
    callers should keep the alert but avoid the full crisis protocol."""
    return bool(HYPOTHETICAL_CONTEXT_RE.search(text or ""))


# ─────────────────────────────────────────────────────────────────────────────
# Guards the hard keyword path was missing
#
# NEGATIVE_CONTEXTS in virtual_agent.py carries a retrospective list ("used to",
# "dati") and a joking list ("lol", "haha"), but it is only ever consulted on
# the ML branch. A message that matched a crisis KEYWORD skipped it entirely
# and went straight to 0.99 — so "i used to want to die lol" paged a counselor,
# and "sana mamatay na lang siya" (a death wish aimed at someone else) did too.
#
# Both belong here, beside the fiction and hypothetical guards that already
# apply to the hard path, so every route into a crisis verdict passes the same
# set of questions.
# ─────────────────────────────────────────────────────────────────────────────

JOKING_RE = re.compile(
    r"\b(lol|lmao|haha|hehe|joke|joking|kidding|jk|char|dies laughing|"
    r"nakakatawa)\b",
    re.IGNORECASE,
)

RETROSPECTIVE_RE = re.compile(
    r"\b(used to|i used to|before|back then|last time|yesterday|last week|"
    r"last month|previously|former|dati|noon|noong| dati)\b",
    re.IGNORECASE,
)

# Someone other than the speaker. Combined with the absence of a first-person
# marker, this separates "sana mamatay na lang siya" (hostile speech about a
# third party) from "mamamatay na lang ako" (a disclosure).
THIRD_PARTY_RE = re.compile(
    r"\b(siya|sila|niya|nila|kanila|kanya|nang kanila|kanila|them|him|her|"
    r"they|this person|that person)\b",
    re.IGNORECASE,
)

SELF_REFERENTIAL_RE = re.compile(
    r"\b(ako|akin|ako'y|ayoko|hindi ko|di ko|ko na|sa akin|ng sa akin|"
    r"i|i'm|im|me|my|myself|i'll|i will)\b",
    re.IGNORECASE,
)


def has_joking_context(text: str) -> bool:
    """True when the message marks itself as not-serious."""
    return bool(JOKING_RE.search(text or ""))


def has_retrospective_context(text: str) -> bool:
    """True when the death-talk is placed in the past or a stated interval ago."""
    return bool(RETROSPECTIVE_RE.search(text or ""))


def is_self_referential(text: str) -> bool:
    return bool(SELF_REFERENTIAL_RE.search(text or ""))


def is_third_party_death_wish(text: str) -> bool:
    """A death wish aimed at someone else. Not self-harm, so not a crisis —
    though it may still be worth hearing, which is why it lands on anger at a
    low band rather than being discarded."""
    text = text or ""
    return bool(THIRD_PARTY_RE.search(text)) and not is_self_referential(text)


# Anger that belongs to somebody else. Same reasoning as the death-wish guard:
# "my mom is angry every time I come home late" reports another person's anger,
# and handing the student an anger-management flow for it answers the wrong
# question. The possessive is what separates it from "I'm angry" — a bare "my"
# plus an anger word is a report, not a disclosure.
OTHER_PERSON_ANGER_RE = re.compile(
    r"\b(my|our|his|her|their)\s+"
    r"(mom|mother|dad|father|parents|brother|sister|friend|classmate|"
    r"roommate|teacher|prof|boss|classmate|kapit|kaibigan|kapatid|"
    r"ina|ama|magulang|mananatili|guro)\b",
    re.IGNORECASE,
)

# Possessive + anger word in either order, which covers "ang galit niya sa akin"
# (the anger of him/her at me) where the owner comes after the noun.
FILIPINO_OTHER_ANGER_RE = re.compile(
    r"\b(ang\s+)?(galit|buga|matam|bahala)\s+(niya|nila|kanya|nilang|kanila)\b",
    re.IGNORECASE,
)

# Anger the student owns, even when a third party is also in the sentence.
# "my brother keeps taking my stuff and it makes me so furious" is a report
# *about* the brother but a disclosure *of* the student's anger, and the flow
# they need is the student's. Without this, the possessive guard above would
# swallow it.
SELF_ANGER_RE = re.compile(
    r"\b(i'?m|i am|i feel|i get|it makes me|makes me|"
    r"ako|akin|sa sarili ko)\b[^.?!]{0,40}"
    r"\b(angry|mad|furious|annoyed|irritated|raging|rage|galit|buga|matam)\b"
    r"|"
    r"\b(angry|mad|furious|annoyed|irritated|raging|rage|galit|buga|matam)\b"
    r"[^.?!]{0,20}\b(me|ako|akin)\b",
    re.IGNORECASE,
)


def is_other_persons_anger(text: str) -> bool:
    """True when the anger in the message belongs to someone other than the student.

    Two guards have to agree before reported anger is accepted, because a
    possessive alone is not enough:

      - "my mom is angry every time I come home late" reports the mother's
        anger. The student is describing a household climate, and an
        anger-management flow answers a question they did not ask.
      - "my brother keeps taking my stuff and it makes me so furious" also has
        a possessive, but the anger is the student's. Self-directed anger
        anywhere in the sentence keeps it.

    Note this deliberately does not use is_self_referential: that matches the
    bare "i" in "every time I come home late", which is not the student
    claiming the anger.
    """
    text = text or ""
    if not (
        OTHER_PERSON_ANGER_RE.search(text) or FILIPINO_OTHER_ANGER_RE.search(text)
    ):
        return False
    return not SELF_ANGER_RE.search(text)


def resolve_crisis_level(matched_keywords, text: str) -> dict:
    """Decide the crisis verdict from the matched suicidal keywords + message
    context. This is the ONE place that converts a suicidal-string match into a
    0.30–0.99 verdict + intent, shared by the hard path and the rule fallback.

    Order of precedence (safety first):
      1. explicit-self-harm keyword → full crisis
      2. third-person disclosure ("kill themselves") → HIGH unless fiction
      3. joking context → neutral, no alert
      4. third-party death wish ("sana mamatay siya") → anger, no alert
      5. retrospective context ("i used to want to die") → sadness, no alert
      6. soft give-up phrase + venting context → stress (false-positive guard)
      7. fiction context → angry fiction (no alert; low risk)
      8. hypothetical/hedged, or any give-up phrase with no vent → MODERATE alert
      9. explicit keyword in hypothetical → HIGH (still real, but not plan)
    """
    text = text or ""

    # Third-person suicide disclosure: "my friend said she wants to kill
    # herself" / "my cousin killed himself". Not first-person intent, but a
    # disclosure that still deserves a counselor alert — except when the
    # context is clearly fiction/media ("the character kills herself in that
    # movie"), which drops it to a low-key anger read instead.
    if matched_keywords and any(k == "kill themselves" for k in matched_keywords):
        if has_fiction_context(text):
            return {"intent": "anger", "confidence": 0.55}
        if has_hypothetical_context(text):
            return {"intent": "suicidal", "confidence": 0.88}
        return {"intent": "suicidal", "confidence": 0.85}

    if any(not is_soft_venting_phrase(k) for k in matched_keywords):
        # Order matters: a joke or a retrospective mention is a statement about
        # the past or about nothing, and it outranks the keyword that matched.
        # Checked here rather than in NEGATIVE_CONTEXTS because that list is
        # only consulted on the ML branch — a keyword match bypassed it, which
        # is how "i used to want to die lol" became a crisis.
        if has_joking_context(text):
            return {"intent": "neutral", "confidence": 0.3}
        if is_third_party_death_wish(text):
            return {"intent": "anger", "confidence": 0.55}
        if has_retrospective_context(text):
            return {"intent": "sadness", "confidence": 0.55}
        if has_hypothetical_context(text):
            return {"intent": "suicidal", "confidence": 0.88}
        return {"intent": "suicidal", "confidence": 0.99}

    if has_venting_context(text):
        return {"intent": "stress", "confidence": 0.60}

    if has_fiction_context(text):
        return {"intent": "anger", "confidence": 0.55}

    if has_hypothetical_context(text):
        return {"intent": "suicidal", "confidence": 0.88}

    return {"intent": "suicidal", "confidence": 0.99}