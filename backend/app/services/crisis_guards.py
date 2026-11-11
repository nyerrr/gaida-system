"""
crisis_guards.py
----------------
Context guards that decide whether a matched suicidal keyword is REAL risk or is
being diluted by surrounding context. Used by both rule_intent.py (rule fallback)
and virtual_agent.py (hard crisis path) so the whole pipeline agrees.

Guards:
    1. SOFT_VENTING_PHRASES  — ambiguous give-up and passive death-wish phrases.
       Clear school/work venting can be reclassified as stress; otherwise they
       alert at HIGH (not Crisis) with a `clarify` flag. A negated give-up ("I
       don't want to give up") is not a risk at all.
    2. FICTION_CONTEXT       — essays, movies, songs, stories, poems. The death
       talk is about content, not the speaker → tone down, no auto-alert.
    3. HYPOTHETICAL_CONTEXT  — hedged/conditional musing ("what if", "kung").
       Still concerning, but not yet an active plan → keep alert at HIGH.

Explicit death/harm statements ("I want to die", "kill myself") bypass the
soft-warning path entirely and remain a full Crisis.
"""

import re

# Ambiguous give-up and passive death-wish phrases. These merit a High alert
# and a clarifying question, but do not by themselves establish intent or a
# plan. Normalized keys; compare via is_soft_venting_phrase.
SOFT_VENTING_PHRASES = {
    "i can't do this anymore",
    "cant do this anymore",
    "i give up",
    "give up",
    "i just want to give up",
    "i want to give up",
    "i give up on everything",
    "i'm done with everything",
    "im done with everything",
    "i just want it to stop",
    "no point in trying anymore",
    "i don't see the point anymore",
    "i dont see the point anymore",
    "better off without me",
    "no one would notice if i was gone",
    "no one would notice if i were gone",
    "nobody would notice if i was gone",
    "nobody would notice if i were gone",
    "no one would miss me",
    "nobody would miss me",
    "i don't want to be here anymore",
    "i do not want to be here anymore",
    "i dont want to be here anymore",
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


# "give up" followed by an everyday thing to quit or let go of ("give up
# smoking", "should I give up my scholarship"). The object is named explicitly,
# so this is a decision or a habit, not hopelessness. Kept to an explicit
# object list on purpose: "give up drinking" or "give up on everything" must
# still reach the clarifying-question path.
GIVE_UP_OBJECT_RE = re.compile(
    r"\bgiv(?:e|ing|en) up (?:on )?(?:my |the |this |that |our |his |her )?"
    r"(smoking|smoke|vaping|vape|sugar|sweets|soda|coffee|caffeine|junk food|"
    r"fast food|milk tea|chocolate|diet|gym|workout|gaming|games|scholarship|"
    r"yosi|sigarilyo)\b",
    re.IGNORECASE,
)


def is_give_up_on_everyday_thing(text: str) -> bool:
    """True for "give up smoking" / "give up my scholarship" style messages."""
    return bool(GIVE_UP_OBJECT_RE.search(text or ""))


# A school/work word normally means "I'm venting", but not when the same message
# also names a loss or despair. "I just try to focus on my studies... loss of
# family members... I just really want to give up" mentions studies and is not
# a vent; one counselor rated it suicidal and another asked for a follow-up.
LOSS_OR_DESPAIR_RE = re.compile(
    r"\b(loss of|lost (?:my|a|our|someone|both)|passed away|pass away|died|"
    r"death of|namatay|pumanaw|hopeless|worthless|burden|family problems?|"
    r"better off without me|no one would notice|nobody would notice|"
    r"no one would miss me|nobody would miss me|"
    r"no point anymore|don't see the point anymore|"
    r"dont see the point anymore|no reason to)\b",
    re.IGNORECASE,
)


def has_loss_or_despair_context(text: str) -> bool:
    return bool(LOSS_OR_DESPAIR_RE.search(text or ""))


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

_RISK_CLAUSE_SPLIT_RE = re.compile(
    r"[,;:.!?\u2026\u2014\u2013\r\n]+|\b(?:but|pero|yet|however|although)\b",
    re.IGNORECASE,
)
_CURRENT_FIRST_PERSON_SELF_HARM_RE = re.compile(
    r"\b(?:i|i'm|im|i am|ako|ako'y)\s+"
    r"(?:(?:really|just|still|na)\s+)?"
    r"(?:want(?:\s+to)?|wanna|wish(?:\s+to)?|plan(?:ning)?\s+to|"
    r"intend(?:ing)?\s+to|will|am\s+going\s+to|gonna|should|ready\s+to|"
    r"might\s+as\s+well)\s+"
    r"(?:just\s+)?(?:die|kill\s+(?:myself|my\s+self)|hurt myself|"
    r"harm myself|cut myself|end my life|end it all|kms|"
    r"off myself|end myself|"
    r"be alive|live anymore)\b"
    r"|\bi\s+(?:do not|don't|dont)\s+(?:want to|wanna)\s+live\b"
    r"|\bi\s+(?:really\s+)?(?:am\s+|['’]?m\s+)?tired of living\b"
    r"|\bi\s+feel like dying\b"
    r"|\bgusto ko (?:na|nang) mamatay\b"
    r"|\b(?:magpapakamatay|papatayin ko (?:na )?sarili ko)\b"
    r"|\b(?:ma|mama)?matay na lang ako\b",
    re.IGNORECASE,
)
_REPORTED_SPEECH_RE = re.compile(
    r"\b(?:(?:my|our)\s+(?:friend|classmate|roommate|sister|brother|"
    r"cousin|partner|parent)|someone|a friend|he|she|they|character|narrator)\b"
    r"[^.!?\r\n]{0,50}\b(?:said|says|told|texted|wrote|writes|"
    r"mentioned|confessed)\b",
    re.IGNORECASE,
)
_REPORTED_SELF_HARM_RE = re.compile(
    r"\b(?:i\s+(?:really\s+)?(?:want|wanna|wish|plan|intend)\s+(?:to\s+)?"
    r"(?:die|kill myself|end my life|hurt myself)|"
    r"(?:she|he|they)\s+(?:want|wants|wanted|plan|plans)\s+(?:to\s+)?"
    r"(?:die|kill herself|kill himself|kill themselves)|"
    r"kill\s+(?:myself|herself|himself|themselves)|suicid\w*|"
    r"self[- ]harm)",
    re.IGNORECASE,
)
_INFORMATIONAL_SELF_HARM_CONTEXT_RE = re.compile(
    r"\b(?:essay|class|school|research|study|studying|lesson|assignment|"
    r"presentation|prevention|awareness|definition|article|news|documentary|"
    r"psychology|clinical|ideation|symptom|movie|film|show|character|story|"
    r"novel|book|song|lyrics|poem)\b",
    re.IGNORECASE,
)
_FIRST_PERSON_SUICIDAL_DISCLOSURE_RE = re.compile(
    r"\b(?:i am|i'm|im|i feel|i have|i've been|i am having)\s+"
    r"(?:currently\s+)?(?:suicidal|thinking about suicide|"
    r"considering suicide|suicidal thoughts?)\b"
    r"|\bi\s+(?:think|keep thinking|have been thinking)\s+about suicide\b",
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


def has_current_first_person_self_harm_intent(text: str) -> bool:
    """True for an active first-person disclosure, not a past-tense recollection."""
    if _FIRST_PERSON_SUICIDAL_DISCLOSURE_RE.search(text or ""):
        return True
    for clause in _RISK_CLAUSE_SPLIT_RE.split(text or ""):
        if RETROSPECTIVE_RE.search(clause):
            continue
        if _CURRENT_FIRST_PERSON_SELF_HARM_RE.search(clause):
            return True
    return False


def is_reported_self_harm(text: str) -> bool:
    """True when a speaker attributes a self-harm disclosure to another person."""
    text = text or ""
    report = _REPORTED_SPEECH_RE.search(text)
    return bool(report and _REPORTED_SELF_HARM_RE.search(text, report.end()))


def is_informational_self_harm_context(text: str) -> bool:
    """True when self-harm language is discussed as an academic/media topic."""
    return bool(_INFORMATIONAL_SELF_HARM_CONTEXT_RE.search(text or ""))


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


# ─────────────────────────────────────────────────────────────────────────────
# Negation guard
#
# "I don't want to die", "i'm not going to kill myself" and "I don't want to
# hurt myself" all reached a crisis — the first two through the ML self-harm
# floor and the phrase "kill myself" is a literal substring of the third. Each
# one says the OPPOSITE of a death wish, but the keyword matchers cannot see the
# "don't". So a matched harm phrase paged a counselor for a student who had just
# said they did not want to die.
#
# The guard is deliberately narrow: it fires only when EVERY death/harm word in
# the message is negated. The reverse construction is left completely alone — a
# negated LIFE verb ("i don't want to live", "i don't want to exist", "i don't
# want to wake up") is still a death wish, and live/exist/wake are not in the
# harm set.
# ─────────────────────────────────────────────────────────────────────────────

_WORD_RE = re.compile(r"[a-z0-9']+")

# Punctuation that ends a clause. The guard has to see clause boundaries —
# "Ayoko na, lulunukin ko lahat ng gamot" is a plan, but "Ayoko na" is an idiom
# for giving up and would otherwise cancel the verb in the next clause. The
# pipeline's own normalizer strips this punctuation, so the guard is always fed
# the RAW message.
_CLAUSE_SPLIT_RE = re.compile(r"[,;:.!?\u2026\u2014\u2013\r\n]+")

# True negators only. "wala" (none/absent) and "ayoko" (I don't want — but also
# the give-up idiom "ayoko na") were removed after they suppressed "wala nang
# pag-asa, mamamatay na lang ako" and "Ayoko na, lulunukin ko ... gamot".
NEGATORS = frozenset({
    "not", "no", "never", "none", "nobody", "nothing", "nowhere",
    "dont", "don't", "doesnt", "doesn't", "didnt", "didn't",
    "wont", "won't", "wouldnt", "wouldn't", "cant", "can't", "cannot",
    "couldnt", "couldn't", "shouldnt", "shouldn't",
    "hindi", "di", "dili", "ayaw",
})

# Words whose negation means "I do NOT want to die / hurt myself". Life verbs
# (live, exist, wake up, be here) are deliberately absent: negating those is a
# death wish, not a denial of one.
DEATH_HARM_WORDS = frozenset({
    "die", "died", "dies", "dying", "dead", "death", "kill", "killed",
    "killing", "suicide", "suicidal", "kms", "harm", "harmed", "harming",
    "hurt", "hurting", "cut", "cutting", "overdose", "overdosing", "pills",
})

# Filipino crisis stems (virtual_agent.FILIPINO_CRISIS_STEMS plus the explicit
# losing/ending verbs). Matched as substrings, because the guard has to see the
# same conjugations the stem path fires on ("mamatay" inside "mamamatay").
_FILIPINO_HARM_STEMS = (
    "mamatay", "magpakamatay", "kamatayan", "patayin", "papatayin",
    "mawala", "makamatay", "wakasan", "wawakasan", "tapusin", "tatapusin",
    "lunuk", "bitbit", "sundok",
)

# Coordinators that end a negator's reach, so a "not" in one clause cannot
# cancel a death word in the next ("I'm not sad, I want to die").
_CLAUSE_BREAKS = frozenset({
    "but", "pero", "yet", "however", "although", "though", "because",
    "kasi", "dahil", "so", "then", "tapos", "and", "or", "if", "kung",
})

_NEGATION_LOOKBACK = 4

# "Give up (on) (this|my) life" is a death wish built from words none of the
# harm sets above can see: "give", "up" and "life" are all ordinary. It is
# recognised as a phrase here so the negation guard can tell a plan apart from
# its denial — "i want to give up this life" pages, "i don't want to give up
# this life" does not. Past tense ("gave up") is deliberately excluded: it
# reads as retrospective resignation ("i gave up on my dreams"), not a plan.
_GIVE_UP_LIFE_WORDS = frozenset({"life", "buhay"})
_GIVE_UP_LIFE_LINKERS = frozenset({
    "up", "on", "sa", "to", "this", "my", "ang", "na", "nang",
})


def _starts_give_up_life(tokens, i) -> bool:
    """True when tokens[i] begins a "give up ... life/buhay" construction."""
    if tokens[i] not in ("give", "giving"):
        return False
    if i + 1 >= len(tokens) or tokens[i + 1] != "up":
        return False
    j = i + 2
    for _ in range(3):
        if j >= len(tokens):
            return False
        if tokens[j] in _GIVE_UP_LIFE_WORDS:
            return True
        if tokens[j] in _GIVE_UP_LIFE_LINKERS:
            j += 1
            continue
        return False
    return False


def _harm_positions(tokens):
    """Indexes of death/harm words, including the "off myself" construction."""
    positions = []
    for i, tok in enumerate(tokens):
        if tok in DEATH_HARM_WORDS or any(s in tok for s in _FILIPINO_HARM_STEMS):
            positions.append(i)
        elif tok in ("off", "end") and i + 1 < len(tokens) and tokens[i + 1] in (
            "myself", "self", "my", "it"
        ):
            positions.append(i)
        elif _starts_give_up_life(tokens, i):
            positions.append(i)
    return positions


def _is_negated(tokens, pos) -> bool:
    for j in range(pos - 1, max(-1, pos - 1 - _NEGATION_LOOKBACK), -1):
        if tokens[j] in _CLAUSE_BREAKS:
            return False
        if tokens[j] in NEGATORS:
            return True
    return False


def negated_death_wish(text: str) -> bool:
    """True when every death/harm word in the message is negated.

    Evaluated clause by clause, so a negator cannot reach across punctuation:
    "Ayoko na, lulunukin ko lahat ng gamot" stays a crisis even though "ayoko"
    looks like a negator, and "i'm not sad, i want to die" stays one too.

    "i don't want to die" -> True (do not escalate the model's vote).
    "i want to die"       -> False (a real wish).
    "i don't want to live"       -> False ("live" is not a harm word).
    """
    text = (text or "").lower()
    saw_harm = False
    for clause in _CLAUSE_SPLIT_RE.split(text):
        tokens = _WORD_RE.findall(clause)
        positions = _harm_positions(tokens)
        if not positions:
            continue
        saw_harm = True
        if not all(_is_negated(tokens, p) for p in positions):
            return False
    return saw_harm


def contains_harm_keyword(keyword: str) -> bool:
    """True when a matched keyword is a death/harm phrase (so the negation guard
    can tell it apart from a life-negation phrase like "i don't want to live")."""
    return bool(_harm_positions(_WORD_RE.findall((keyword or "").lower())))


# The negation guard above only covers death/harm words. A bare "give up" is not
# harm vocabulary, so "i don't want to give up" would otherwise match the soft
# give-up phrase and alert. That sentence is the opposite of surrender — it is
# the student saying they are still trying — so it must stay neutral.
_NEGATED_SOFT_RE = re.compile(
    r"\b(?:i\s+)?(?:do\s*n[o']?t|don'?t|didn'?t|won'?t|wouldn'?t|never|not)\b"
    r"[^.?!]{0,30}\b(?:give|giving)\s+up\b"
    r"|"
    r"\b(?:hindi|di)\s+(?:ako\s+)?(?:susuko|sumusuko|mag-?give\s*up)\b",
    re.IGNORECASE,
)


def negated_soft_give_up(text: str) -> bool:
    """True when the message denies giving up ("I don't want to give up").
    Such a message is coping, not risk, and must not raise an alert."""
    return bool(_NEGATED_SOFT_RE.search(text or ""))


def resolve_crisis_level(matched_keywords, text: str) -> dict:
    """Decide the crisis verdict from the matched suicidal keywords + message
    context. This is the ONE place that converts a suicidal-string match into a
    0.30–0.99 verdict + intent, shared by the hard path and the rule fallback.

    Order of precedence (safety first):
      1. informational self-harm mention → neutral
      2. reported self-harm disclosure → HIGH unless fiction
      3. third-person disclosure ("kill themselves") → HIGH unless fiction
      4. joking, third-party, retrospective, and hypothetical context guards
      5. soft give-up phrase + venting context → stress
      6. fiction context → no alert
      7. negated soft give-up ("i don't want to give up") → neutral
      8. ambiguous passive/give-up phrase → HIGH + clarify

    A bare give-up phrase used to escalate to a full Crisis. That over-reacted
    to ambiguous language: "i just want to give up" and "everyone would be
    better off without me" are warning signs, but do not by themselves establish
    intent or a plan. They alert at HIGH and ask a clarifying question, while an
    explicit death statement ("i want to die") remains Crisis.

    The counselor decision behind this: prefer a false alert over a missed
    student, but do not let a vague phrase collapse the conversation into a
    crisis script the student never asked for.
    """
    text = text or ""

    if (
        any(
            k in {"suicide", "suicidal", "self-harm", "self harm"}
            for k in matched_keywords
        )
        and is_informational_self_harm_context(text)
        and not has_current_first_person_self_harm_intent(text)
        and not is_reported_self_harm(text)
    ):
        return {"intent": "neutral", "confidence": 0.3}

    if is_reported_self_harm(text):
        if has_fiction_context(text):
            return {"intent": "neutral", "confidence": 0.3}
        return {"intent": "suicidal", "confidence": 0.85}

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
        if (
            has_joking_context(text)
            and not has_current_first_person_self_harm_intent(text)
        ):
            return {"intent": "neutral", "confidence": 0.3}
        if is_third_party_death_wish(text):
            return {"intent": "anger", "confidence": 0.55}
        if has_retrospective_context(text):
            return {"intent": "sadness", "confidence": 0.55}
        if has_hypothetical_context(text):
            return {"intent": "suicidal", "confidence": 0.88}
        return {"intent": "suicidal", "confidence": 0.99}

    if has_venting_context(text) and not has_loss_or_despair_context(text):
        return {"intent": "stress", "confidence": 0.60}

    m = GIVE_UP_OBJECT_RE.search(text)
    if m:
        # A decision about a named thing, not hopelessness. A scholarship is a
        # real stressor; a habit ("give up smoking") is just a topic.
        if m.group(1).lower() == "scholarship":
            return {"intent": "stress", "confidence": 0.60}
        return {"intent": "neutral", "confidence": 0.30}

    if has_fiction_context(text):
        return {"intent": "anger", "confidence": 0.55}

    if negated_soft_give_up(text):
        return {"intent": "neutral", "confidence": 0.3}

    if has_hypothetical_context(text):
        if any(is_soft_venting_phrase(k) for k in matched_keywords):
            return {"intent": "suicidal", "confidence": 0.88, "clarify": True}
        return {"intent": "suicidal", "confidence": 0.88}

    return {"intent": "suicidal", "confidence": 0.88, "clarify": True}


# ─────────────────────────────────────────────────────────────────────────────
# Non-distress guard
#
# Added after the Section A expert audit (Oct 2026). Four licensed counselors
# rated 100 real pilot messages against the five-class scheme and kept landing
# on the same complaint: a message that states a goal, describes a coping
# strategy, reports relief, or narrates an ordinary activity was being handed a
# distress label anyway. The classifier is not hallucinating a signal — "I'm
# trying to stay focused" really does share surface vocabulary with anxiety —
# but a faint signal with no distress word anywhere in the message is not a
# classification, and on the gold key it paged a counselor for a student who
# said they were prioritising their workload to avoid burnout.
#
# The guard is conservative in the only direction that matters: it fires only
# when a positive/coping or routine marker is present AND no distress
# vocabulary appears at all. A negated marker ("not doing fine") is not
# evidence of calm, so it does not count. It runs after the crisis path and
# after loss detection, so it can never silence a crisis or a bereavement.
# ─────────────────────────────────────────────────────────────────────────────

# Genuine distress vocabulary. Over-inclusive on purpose: every extra word here
# only makes the guard quieter, never louder.
DISTRESS_SIGNAL_RE = re.compile(
    r"\b("
    r"worry|worries|worrying|worried|struggl\w*|uncertain|"
    r"anxious|anxiety|nervous|nerbiyos|"
    r"panic|panicky|panicking|overthink|overthinking|overwhelmed|overwhelming|"
    r"kaba|kinakabahan|kakabahan|takot|natatakot|scared|afraid|fear|fearful|"
    r"terrified|restless|racing|pounding|shaking|trembling|nanginginig|"
    r"stress|stressed|burnout|"
    r"sad|sadness|lonely|alone|empty|hopeless|hopelessness|"
    r"cry|crying|umiiyak|iiyak|tears|lungkot|malungkot|"
    r"feel(?:ing)? (?:so |a little |really |very |kinda )?(?:down|low|blue)|"
    r"a little down|losing interest|lose interest|"
    r"hurt|hurts|sakit|broken|heartbroken|"
    r"argu(?:e|ing|ment)|"
    r"worthless|failure|ashamed|disappointed|meaningless|numb|"
    r"no energy|no motivation|exhausted|drained|"
    r"can'?t function|can'?t get out|can'?t get up|can'?t concentrate|"
    r"can'?t handle|can'?t do anything|can'?t eat|can'?t move|"
    r"angry|anger|mad|furious|rage|raging|annoyed|irritated|frustrated|"
    r"galit|inis|bwisit|nakakainis|nakakagalit|sasabog|"
    r"die|died|dying|dead|death|kill|killed|killing|suicide|suicidal|"
    r"end it|end my|off myself|off my self|kms|cut myself|"
    r"self.?harm|hurt myself|harming myself|better off dead|not worth living|"
    r"hate|pissed|fed up|"
    r"mamatay|magpakamatay|kamatayan|patayin|papatayin|mawala|wakasan|tapusin|"
    r"wala nang|"
    r"i miss|miss them|miss him|miss her|give up|gave up|"
    r"can'?t cope|can'?t take|can'?t sleep|can'?t focus|can'?t breathe|"
    r"no point|pointless"
    r")\b",
    re.IGNORECASE,
)

# Coping, relief and a positive turn. Multi-word on purpose so a negated
# positive ("i don't enjoy") does not match the bare marker ("i enjoy").
_POSITIVE_COPING_MARKERS = (
    "i enjoy", "enjoying my", "enjoy it now", "enjoying it", "i enjoyed",
    "relieved", "relief", "nakaluwag", "nakahinga", "gumaan", "gumagaan",
    "doing fine", "doing okay", "doing ok", "i'm fine", "im fine",
    "okay na ako", "ok na ako", "i'm okay", "im okay",
    "proud of", "looking forward", "excited",
    "decided to focus", "decided to prioritize", "decided to prioritise",
    "trying to relax", "try to relax", "to relax myself", "relax myself",
    "stay focused", "staying focused", "keep focused",
    "taking a break", "take a break", "taking it one", "one at a time",
    "my priority", "my priorities", "prioritiz", "prioritis",
    "manage my time", "managing my time",
    "i passed", "passed my", "pumasa", "nakatapos", "finished my",
    "better now", "getting better",
)

# Ordinary daily activity. These are the "is this even a distress message?"
# items the counselors kept marking Neutral.
_ROUTINE_MARKERS = (
    "homework", "my project", "school project", "video games", "videogame",
    "netflix", "scrolling", "ate lunch", "eating lunch", "go to the mall",
    "at the mall", "cleaning", "cleaned", "chores", "errands",
    "played basketball", "watching netflix",
)

_NEGATOR_WORDS = frozenset({
    "not", "no", "never", "dont", "don't", "doesnt", "doesn't", "didnt",
    "didn't", "cant", "can't", "cannot", "wont", "won't", "isnt", "isn't",
    "wasnt", "wasn't", "hindi", "di", "dili", "ayaw",
})

_WORD_RE_GENERIC = re.compile(r"[a-z']+")


def _marker_without_negation(text: str, markers) -> bool:
    """True if any marker appears without a negator in the three words before it."""
    for marker in markers:
        start = 0
        while True:
            idx = text.find(marker, start)
            if idx == -1:
                break
            before = _WORD_RE_GENERIC.findall(text[max(0, idx - 18):idx])
            if not any(w in _NEGATOR_WORDS for w in before[-3:]):
                return True
            start = idx + len(marker)
    return False


def has_distress_signal(text: str) -> bool:
    """True when the message names any distress/anxiety/sadness/anger/crisis word."""
    return bool(DISTRESS_SIGNAL_RE.search(text or ""))


def is_non_distress(text: str) -> bool:
    """True when a message only reports coping, relief or routine activity and
    names no distress anywhere. Used to keep such messages Neutral instead of
    letting a faint classifier signal stamp them as anxiety/sadness/anger."""
    normalised = (text or "").lower().translate(_APOS_TRANSLATE)
    if DISTRESS_SIGNAL_RE.search(normalised):
        return False
    return (
        _marker_without_negation(normalised, _POSITIVE_COPING_MARKERS)
        or _marker_without_negation(normalised, _ROUTINE_MARKERS)
    )


ACADEMIC_SETBACK_RE = re.compile(
    r"\b(fail|failed|failing|fails|flunk|flunked|bagsak|bumagsak|nabagsak)\b"
    r"|\b(low|mababa|mababang)\s+(grade|grades|mark|marks|score)\b",
    re.IGNORECASE,
)


def is_academic_setback_without_distress(text: str) -> bool:
    """A bare academic outcome ("I failed math") is a fact about a stressor, not
    a disclosure of an emotion. The counselors did not read these as anxiety,
    and the classifier only reaches anxiety on them by latching onto the word
    "fail". Any co-occurring distress vocabulary vetoes the guard, so
    "I'm terrified I'll fail everything" is left to the normal path.
    """
    neutralized = (text or "").lower().translate(_APOS_TRANSLATE)
    if DISTRESS_SIGNAL_RE.search(neutralized):
        return False
    return bool(ACADEMIC_SETBACK_RE.search(neutralized))