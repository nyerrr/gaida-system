"""
loss_detector.py
----------------
Attachment / relationship-loss detection.

Why this exists
---------------
GAIDA's taxonomy (and its whole severity ladder) was built around *anxiety*:
stress, academic pressure, panic, rumination. Every rule, every ML training
label (`anxiety_training.jsonl` = anxiety / suicidal / anger / sadness /
neutral), and every therapeutic response flow assumes the student's problem
is a distorted thought pattern that can be interrupted and reframed.

That assumption is wrong for grief. When a student says "we broke up and I
still want him back," routing that into the `moderate` anxiety flow gets GAIDA
to apply "interrupt the overthinking loop" and "introduce an alternative
explanation" to a real loss — which is how a system ends up quietly implying
the student is misthinking their breakup. Human guidance counselors are
careful not to do that, so GAIDA shouldn't either.

This module is a high-precision, rule-based topic detector for attachment loss
and breakup grief. It runs *before* the ML classifier (after the crisis hard
path, which always wins) so a breakup is never voted into a generic `sadness`
read that would hand the wrong response flow to the model.

Design contract — deliberately conservative:
  * Precision over recall. A missed breakup is handled no worse than today
    (the student still gets `sadness`/`stress`); a false "loss" on an anxious
    message would wrongly suppress legitimate anxiety framing. So a detection
    needs a *primary* signal (breakup event or being left/rejected), or a
    corroborated attachment pattern (two secondary signals).
  * Loss alone NEVER reaches Crisis, and only reaches High when an explicit
    despair marker co-occurs. See `detect_loss`.
  * Fiction, past-tense, and third-party mentions are excluded outright, and
    hypothetical phrasing is only discounted — "in the show they broke up" is
    not a disclosure, "my friend broke up with her" is not the speaker's loss,
    but "what if he already moved on, I still love him" from someone days into
    a breakup is rumination and must still get a grief-shaped reply.
  * English, Tagalog, and Taglish, because students write all three and the
    response flow has to know which language to mirror back.

It does NOT set severity or fire alerts. It returns a signal; `virtual_agent`
decides what to do with it, and `intent_router` records the sub-flags for the
counselor dashboard.
"""

import re
from typing import Dict, List

# ---------------------------------------------------------------------------
# Signal vocabulary
# ---------------------------------------------------------------------------

# A breakup *happened to the student*, or they were left. This is the primary
# signal — alone it is enough (with any confidence bump for recency).
BREAKUP_PATTERNS = [
    # English
    r"\bwe broke up\b", r"\bwe break(ed)? up\b", r"\bwe('?re)? (done|finished|over)\b",
    r"\bit('?s)? over\b", r"\bwe split up\b", r"\bwe separated\b",
    r"\bbreak(?:ing)? up with (me|him|her|us)\b", r"\b(broke|broke up) with me\b",
    r"\bshe (ended|left|broke up)\b", r"\bhe (ended|left|broke up)\b",
    r"\b(end|ended) (it|things|our relationship)\b",
    r"\bhe left me\b", r"\bshe left me\b", r"\bthey left me\b",
    r"\bmy ex\b", r"\bex[- ]?(boyfriend|girlfriend|partner)\b",
    r"\bwe used to be together\b", r"\bnot together anymore\b",
    r"\bno longer together\b", r"\bbroke up days ago\b",
    r"\blast (week|month|year)\b", r"\ba (week|month|year) ago\b",
    # Filipino / Taglish
    r"\bnaghihati\s+na\s+kami\b", r"\bhiwalay\s+na\s+kami\b",
    r"\bnaghihati\s+kami\b", r"\btapos\s+na\s+kami\b",
    r"\bhindi\s+na\s+kami\s+together\b",
    r"\b(i|siya|siya ay)\s+(umalis|umalis sa akin|ayaw na)\b",
    r"\bawala?\s+na\s+(siya|ako)\b",
    r"\bex\s+ko\b", r"\bmga\s+ex\s+ko\b",
]

# Being left, rejected, or betrayed specifically. Also primary.
ABANDONMENT_PATTERNS = [
    r"\b(he|she|they) don'?t want me back\b",
    r"\b(want|wants) (me|you) back\b",
    r"\b(he|she) (doesn'?t|does not|didn'?t|did not) (want|love) (me|us) (anymore|back)\b",
    r"\bnot (in love|with) (me|us) anymore\b",
    r"\bchose (someone|her|him|somebody) else\b",
    r"\b(left|leaving) me for (someone|her|him|another)\b",
    r"\b(cheated|cheating) on me\b",
    r"\b(he|she) (is|was) (seeing|with) someone else\b",
    r"\bmoving on (so fast|already|so quickly)\b",
    r"\b(he|she|they) (already |has )?moved on\b",
    r"\bhe already has someone\b",
    r"\b(rejected|dumped) me\b",
    r"\bfriendzoned\b", r"\bbeing used\b",
    # Filipino / Taglish
    r"\b(hindi|ayaw)\s+(na)?\s*(siya|niya|ako)\s+(gusto|ibig)\b",
    r"\bhindi na (niya|ko) gusto\b",
    r"\bgusto ko pa (rin|ngunit) (siya|siya)\b",
    r"\bnagpalit (ng|siya)\b", r"\bnagcoc cheat\b", r"\nangcheat\b",
    r"\bnag aaway kami\b", r"\naaway kami\b",
    r"\bipinagpalit (ako|niya)\b",
]

# Secondary — the attachment still being there. "I still want him" is the
# sentence human counselors always name explicitly, so it matters a lot that
# the response flow knows it's there.
UNREQUITED_PATTERNS = [
    r"\bstill (want|wanting|love|loving|care|caring|miss|missing)\b",
    r"\b(i )?still (have|feel) feelings\b",
    r"\bdon'?t want to (accept|move on|let go)\b",
    r"\bi can'?t stop (thinking|loving|missing)\b",
    r"\bnot over (him|her|it|this)\b",
    r"\bcan'?t accept (it|that|this)\b",
    # Filipino / Taglish
    r"\b(gusto|ibig|miss) (ko|natin) (pa|pa rin|na)\b",
    r"\bhindi ko pa (ma)aaway\b", r"\bhindi pa ko na sana makalimot\b",
    r"\bhindi ko (m)aaalis\b",
]

# Secondary — active rumination about the ex / a new partner. Rumination is
# the single biggest driver of a bad outcome in early grief, so it earns its
# own flag (the flow responds differently when it's present).
RUMINATION_PATTERNS = [
    r"\bkeep (checking|looking|refreshing|minding)\b",
    r"\b(still|always) check(ing)? (his|her|their)\b",
    r"\b(look at|looking at|stalk) (his|her|their) (profile|posts|feed|page)\b",
    r"\bkeep (thinking|replaying|running) (about|it|him|her|that)\b",
    r"\bthink about (him|her|it|that) (all|every)\b",
    r"\bevery time i (see|pass|hear)\b",
    r"\bsee (them|him|her) (together|with)\b",
    r"\bhe (posted|is posting) (with|and)\b",
    r"\bscrolling (his|her|their)\b",
    r"\bchek (ko|nag)\b", r"\nagb browse\b", r"\nag lalako\b",
    r"\bceke (yung|ang)\b", r"\nag tatanong (kay|sa)\b",
    r"\binvestigate (ko|ng)\b",
]

# Secondary — explicit despair. Alone this is ordinary sadness (handled by the
# existing `sadness` path); combined with a loss signal it is the one
# combination that justifies paging a counselor, because grief plus
# hopelessness is the profile that turns into risk.
DESPAIR_PATTERNS = [
    r"\bhopeless\b", r"\bnothing matters\b", r"\bno reason\b",
    r"\bdon'?t see the point\b", r"\bi don'?t see the point\b",
    r"\bnothing makes sense\b", r"\bempty (inside|of)\b",
    r"\bnumb\b", r"\bi feel nothing\b", r"\bpointless\b",
    r"\bnakatalo (yung|ang) lahat\b", r"\bwalang silbi\b", r"\bwalang saysay\b",
    r"\bwalang (kahulugan|point)\b", r"\bnakabunta\b", r"\bbinuang na ako\b",
    r"\bi don'?t care (about|anymore)\b",
]

# Recency bumps confidence — "days ago" / "kahapon" reads as acute grief
# rather than a long-processed loss.
RECENCY_PATTERNS = [
    r"\b\d+\s+(day|days|week|weeks|month|months)\s+(ago|since)\b",
    r"\b(days?|weeks?|months?)\s+ago\b",
    r"\bjust (broke up|got dumped|ended)\b",
    r"\b(few|couple|several|a few)\s+days?\b",
    r"\bjust (happened|broke up|last|recently)\b",
    r"\b(yesterday|tonight|last night|this week|recently|lately)\b",
    r"\bso (sad|recent) (now|these days)\b",
    r"\b(nasa)?\b(ilang|kahapon|mga)\s+araw\b",
    r"\bkahapon\b", r"\bkahapon ng gabi\b", r"\bngayong linggo\b",
    r"\bmga ilang araw\b",
]

# Third-party mentions — "my friend broke up", "my ate's ex". A breakup that
# isn't the speaker's is not their loss to be responded to with grief work.
THIRD_PARTY_PATTERNS = [
    r"\bmy (friend|best friend|kaklase|classmate|roommate|ate|kuya|bes|kapatid|"
    r"cousin|sister|brother|tita|tita|mother|mom|dad|father)\b",
    r"\b(si|kay)\s+(ate|kuya|bes|kapatid|kaibigan|kaklase)\b",
    r"\bmy classmate('?s)? (relationship|girlfriend|boyfriend)\b",
]

# First-person attachment markers — if one of these is present, the story is
# about the speaker even if a third-party name also appears ("my friend and
# I broke up", "my ex and his new girlfriend").
SELF_MARKERS = [
    r"\b(i|me|my|mine|ako|akin|ako'y)\b",
    r"\bi (still|keep|can'?t|did|do|want|feel)\b",
    r"\bstill (want|love|miss|care)\b",
]

_FICTION_PATTERNS = [
    r"\b(movie|film|show|series|episode|character|scene|story|novel|book|"
    r"anime|manga|fiction|fantasy|song|lyrics?|lyric|poem|poetry|essay|quote)\b",
    r"\b(pelikula|kwentong|kwento|episode|character)\b",
]

_PAST_TENSE_PATTERNS = [
    # Note: "already moved on" belongs to the *other* person being an
    # abandonment signal, so it is deliberately absent here — only the
    # speaker's own settled past counts as exclusion.
    r"\b(used to|back then|years ago|last year|i had|we had)\b",
    r"\b(i already (got over|moved on|am over|am okay with it|feel better))\b",
    r"\b(dati|noong dati|kahapon ng taon)\b",
    r"\b(before|previously)\b",
]

_HYPOTHETICAL_PATTERNS = [
    r"\b(what if|hypothetically|suppose|imagine|if i (were|was)|"
    r"in case|worst case)\b",
    r"\b(kung|paano kung|kung kaya|ano kaya)\b",
    r"\b(would it|should i|do you think i should)\b",
]

_PRIMARY = BREAKUP_PATTERNS + ABANDONMENT_PATTERNS

_FLAG_SPECS: Dict[str, List[str]] = {
    "breakup": BREAKUP_PATTERNS,
    "abandonment": ABANDONMENT_PATTERNS,
    "unrequited": UNREQUITED_PATTERNS,
    "rumination": RUMINATION_PATTERNS,
    "despair": DESPAIR_PATTERNS,
    "recency": RECENCY_PATTERNS,
}

# Weights: primary signals carry the decision, secondaries confirm and shape
# the response flow but can never open one on their own (see detect_loss).
W_PRIMARY = 0.55
W_UNREQUITED = 0.25
W_RUMINATION = 0.20
W_DESPAIR = 0.20
W_RECENCY = 0.10
# Any two corroborating secondaries together are diagnostic on their own —
# e.g. "I still love her" + "I keep checking his profile" is post-breakup
# rumination whether or not the student ever says the word "breakup".
W_SECONDARY_PAIR = 0.25

# Loss alone sits at Moderate: grief is real and deserves a grief-shaped
# response, but a keyword match must never auto-page a counselor. The one
# exception is despair co-occurring with loss — that combination is the
# profile that needs a human.
CAP_PLAIN = 0.74         # -> Moderate
CAP_WITH_DESPAIR = 0.78  # -> High

# Exactly one primary signal on its own (an explicit breakup statement) must
# clear this, so it is the primary weight.
DETECTION_FLOOR = 0.55

# Hedged/conditional phrasing is kept but scored down — see the exclusion
# block in detect_loss.
HYPOTHETICAL_DISCOUNT = 0.85


def _compile(patterns: List[str]) -> re.Pattern:
    return re.compile("|".join(patterns), re.IGNORECASE)


_COMPILED: Dict[str, re.Pattern] = {name: _compile(p) for name, p in _FLAG_SPECS.items()}
_RE_FICTION = _compile(_FICTION_PATTERNS)
_RE_PAST = _compile(_PAST_TENSE_PATTERNS)
_RE_HYPOTHETICAL = _compile(_HYPOTHETICAL_PATTERNS)
_RE_THIRD_PARTY = _compile(THIRD_PARTY_PATTERNS)
_RE_SELF = _compile(SELF_MARKERS)
# "still want him" / "gusto ko pa siya" — an unambiguous first-person
# attachment statement, strong enough to keep a third-party mention from
# suppressing a genuine disclosure.
_RE_SELF_ATTACHMENT = _compile([
    r"\bstill (want|love|miss|care)\b",
    r"\bi (still|can'?t|did)\b",
    r"\b(gusto|ibig|miss) ko (pa|pa rin|na)\b",
    r"\bhindi ko (pa|m)a[a]?w?a?y\b",
])


def _normalize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    txt = text.lower()
    txt = txt.replace("’", "'").replace("‘", "'")
    txt = re.sub(r"(.)\1{2,}", r"\1", txt)  # "soooo" -> "so"
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def _hits(pattern: re.Pattern, text: str) -> List[str]:
    return [m.group(0) for m in pattern.finditer(text)]


def detect_loss(text: str) -> Dict[str, object]:
    """Detect attachment/relationship loss in a message.

    Returns a dict that is always safe to inspect:
        {
            "is_loss":        bool,
            "confidence":     float in [0.0, 0.78],
            "flags":          {breakup, abandonment, unrequited, rumination,
                               despair, recency},
            "matched":        [matched phrases, lowercase],
            "excluded":       None | "fiction" | "past" | "hypothetical" | "third_party",
        }

    Callers that find `is_loss` False should behave exactly as they did before
    this module existed.
    """
    txt = _normalize(text)

    empty = {
        "is_loss": False,
        "confidence": 0.0,
        "flags": {name: False for name in _FLAG_SPECS},
        "matched": [],
        "excluded": None,
        "hypothetical": False,
    }
    if len(txt) < 8:
        return empty

    matched: List[str] = []
    flags = {name: False for name in _FLAG_SPECS}
    for name, pattern in _COMPILED.items():
        found = _hits(pattern, txt)
        if found:
            flags[name] = True
            matched.extend(found)

    has_primary = flags["breakup"] or flags["abandonment"]
    attachment = flags["unrequited"]
    checking = flags["rumination"]
    hopeless = flags["despair"]
    secondaries = sum(1 for k in ("unrequited", "rumination", "despair") if flags[k])

    # Eligible on a primary signal, or on a corroborated attachment pattern.
    # Two secondaries are enough; one alone is not (someone can check their
    # partner's profile or say they miss their mum without any loss here).
    corroborated = (
        (attachment and checking)
        or (attachment and hopeless)
        or (checking and hopeless)
    )
    if not (has_primary or corroborated or secondaries >= 2):
        result = dict(empty)
        result["matched"] = matched
        return result

    # ── Exclusions ──────────────────────────────────────────────────
    # Fiction: someone else's story. Past tense: already processed. Both
    # remove the signal outright — a student describing a plot or an old
    # memory should get the ordinary anxiety/sadness response.
    if _RE_FICTION.search(txt):
        result = dict(empty)
        result["matched"] = matched
        result["excluded"] = "fiction"
        return result

    if _RE_PAST.search(txt):
        result = dict(empty)
        result["matched"] = matched
        result["excluded"] = "past"
        return result

    # Hypothetical is discounted, not excluded — same reasoning as
    # crisis_guards.has_hypothetical_context. "What if he already moved on,
    # I still love him" from someone days into a breakup is acute rumination
    # phrased as a question, not idle musing.
    discounted = bool(_RE_HYPOTHETICAL.search(txt))

    # Third party: "my friend broke up with her" / "my ate's ex". Only an
    # explicit first-person attachment statement keeps it alive, because
    # "my friend and I broke up" is a real disclosure that merely mentions
    # another person.
    if _RE_THIRD_PARTY.search(txt) and not _RE_SELF_ATTACHMENT.search(txt):
        result = dict(empty)
        result["matched"] = matched
        result["excluded"] = "third_party"
        return result

    # ── Score ───────────────────────────────────────────────────────
    score = 0.0
    if has_primary:
        score += W_PRIMARY
    if attachment:
        score += W_UNREQUITED
    if checking:
        score += W_RUMINATION
    if hopeless:
        score += W_DESPAIR
    if flags["recency"]:
        score += W_RECENCY
    if secondaries >= 2:
        score += W_SECONDARY_PAIR

    if discounted:
        score *= HYPOTHETICAL_DISCOUNT

    confidence = min(CAP_WITH_DESPAIR if hopeless else CAP_PLAIN, round(score, 3))

    return {
        "is_loss": confidence >= DETECTION_FLOOR,
        "confidence": confidence,
        "flags": flags,
        "matched": matched,
        "excluded": None,
        "hypothetical": discounted,
    }


# ---------------------------------------------------------------------------
# Disclosure summary — gives the response flow concrete ground to stand on
# ---------------------------------------------------------------------------

# Human-readable notes, keyed by flag. The point is that GAIDA should respond
# to what was *actually disclosed*, not to the general category. Each note is
# written to be injected into the system prompt as counselor background.
_FLAG_NOTES = {
    "breakup": "the relationship has recently ended",
    "abandonment": "they feel left, rejected, or replaced by the other person",
    "unrequited": "they still want this person back even though it is over",
    "rumination": "they are actively checking or thinking about the other person",
    "despair": "hopelessness is mixed in with the loss",
    "recency": "this is recent, not settled",
}

# Filipino/Taglish renderings for the two notes that carry the most weight in
# the response (naming the contradiction, and the rumination).
_NOTES_FIL = {
    "breakup": "namatlang na ang relasyon",
    "abandonment": "parang iniwan o tinatamaan siya",
    "unrequited": "gusto pa rin niya yung tao kahit tapos na",
    "rumination": "sinusuri niya pa rin yung profile at naiisip yung tao",
    "despair": "may kasamang kawalang-hope",
    "recency": "bagong dating lamang",
}


def _is_tagalog(text: str) -> bool:
    filipino_markers = re.compile(
        r"\b(ako|akin|ako'?y|nang|ng|yung|siya|niya|kami|tayo|natin|natin|"
        r"gusto|kay|para|kasi|sobrang|grabe|ayoko|nais|ginawa|hindi|pero|"
        r"bakit|paano|ano|saan|kapag)\b",
        re.IGNORECASE,
    )
    return bool(filipino_markers.search(text or ""))


def describe_disclosure(loss_result: Dict[str, object], text: str) -> str:
    """Bullet summary of what the student actually disclosed.

    Returns "" when there is no loss signal. Rendered as bullets rather than a
    sentence because it is read by the model as background, not shown to the
    student — and bullets stay readable in Tagalog/Taglish without the
    conjunction that would otherwise mix languages mid-line.
    """
    if not loss_result or not loss_result.get("is_loss"):
        return ""

    flags = loss_result.get("flags") or {}
    notes = _NOTES_FIL if _is_tagalog(text) else _FLAG_NOTES
    present = [notes[k] for k in _FLAG_NOTES if flags.get(k)]

    if not present:
        return ""

    lines = "\n".join(f"  - {p}" for p in present)
    return (
        "WHAT THE STUDENT ACTUALLY DISCLOSED (ground your reply in these "
        "specific facts, not in the general category):\n"
        f"{lines}"
    )
