"""
build_real_expert_sample.py
---------------------------
Builds the real-data Section A expert sample from real student messages
(real_student_messages.csv, pasted from the pilot transcripts).

Why this exists: the old Section A (sample_for_experts.csv) was made of
fabricated messages byte-identical to gold_key.csv, so it could not measure
anything about the real system. This sample is drawn from genuine pilot
messages instead.

Design:
  * Raw file          : real_student_messages.csv  (item_id, pid, session_ref,
                        msg_no, timestamp, message) -- real participant data,
                        must stay out of git (see .gitignore).
  * Output            : real_expert_sample.csv      (sample_id, context, text,
                        counselor_A_label, counselor_B_label) -- what ships to
                        counselors. Identifiers and timestamps are dropped.
                        `context` holds the earlier messages from the same
                        session (student-side only) so short replies like
                        "True true" or "4 years" can be judged in flow.
  * Filtering         : drop HTML / prompt-injection probes and meta questions
                        about the bot; drop duplicate texts (normalized); drop
                        the user-injected capture line.
  * Stratification    : lightweight keyword buckets (crisis > anger > sadness >
                        anxiety > loss > neutral) so the sheet covers all five
                        classifier labels plus loss without leaning on any one
                        participant (max `--max-per-pid` rows per pid).
  * Labels            : deliberately BLANK -- two counselors blind-label the
                        same sheet; agreement is scored by
                        compute_real_agreement.py (no gold key needed).

Gold key untouched: sample_for_experts.csv and gold_key.csv still back the
98.3% detection metric via score_detection.py. This sample is a separate,
decoupled artifact.

Usage (from backend/):
    python training/expert_validation/build_real_expert_sample.py [--n 100] [--seed 7]
"""

from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
RAW = BASE / "real_student_messages.csv"
OUT = BASE / "real_expert_sample.csv"

# --- messages that are NOT student distress signals -------------------------
# HTML / XSS probes, prompt-injection attempts, and meta "what are you?" chat.
PROBE_PATTERNS = [
    "<", ">",
    "ignore your safety",
    "what model are you",
    "gemini or claude",
    "what type of ai",
    "how secure are you",
    "what are you programmed",
    "what are you designed",
]
# The team's capture annotation was appended to a real message during data
# taking; match it as a substring because the student half varies.
CAPTURE_LINE = "this are real datas from students"

# --- messages with no evaluable content (drop as targets) -------------------
# A counsellor cannot meaningfully rate these: content-free
# acknowledgements/sign-offs, chat that is about the bot or off-topic, and the
# whole sessions that are bot-testing rather than help-seeking. They never
# become target messages (they can still appear as context).
FILLER_PATTERNS = [
    r"^(yes|yeah|no|nope|okay|ok|sure|sure thanks)$",
    r"^(hi|hi!|hello|hello!|hey)$",
    r"^(thanks|thank you|salamat|ikaw din)$",
    r"^(true true|not so much|that'?s all|good way)$",
    r"^(idk|i don'?t know|i'?m not sure|nothing|soon|a lot|oki ty)$",
    r"^(yes anytime|not really|a bit of everything)$",
    r"^(good|fine|good good|im fine|i'?m fine)( now| really| a little)?$",
    r"^(i am fine( really)?|i'?m fine( really)?|im fine( really)?)$",
    r"^(i'?m good( today)?|im good( today)?|im good really)$",
    r"^(that'?s all for today ?(thank you for coping me)?|thank you for coping me)$",
    r"^(everything happens for a reason)$",
    r"^(i ?(js|just) try to be optimistic)$",
    r"^(it'?s a surprise and a good surprise\.?)$",
    r"^(by studying more|how to deal with it|i can'?t say it|i'?m just fooling around)$",
    r"^(since last week|since yesterday|for a few weeks now|almost a week|around 1 week|1 week|"
    r"2 weeks?|3 weeks?|a few weeks?|probably several days already|several days( already)?|"
    r"4 years|3 years|2 years|2 years or 3|3 years as far as i know)$",
    r"^(the sleepless nights|not getting the lectures)$",
    r"^(anyways,? okay( na)? ako|okay na ako)$",
    r"^(i already told u|i already told you)$",
    r"^(heh+ ?(is that so\?)?|hehe+)$",
    r"^(what should i do\?|kinda messy i guess|this year|talk to my gf|math)$",
    r"^(a blank slate|not enough money|all my life for all i know)$",
    r"^(nothing really,? i ?(js|just) hope for the best)$",
    r"^quite a while now,? but i need to go get some work done.*$",
    r"^is it okay if the topic isn'?t about academics at all\?$",
    r"^hmm+$",
]
META_PATTERNS = [
    r"gaida", r"your name", r"your favorite", r"favorite (color|country)",
    r"who created you", r"chat ?gpt", r"programmed", r"designed for",
    r"tell me about yourself", r"acronym", r"what are you",
    r"how many languages", r"speak spanish", r"what country were made",
    r"ai intelligence", r"pilot testing", r"convo resetted",
    r"most powerful nuke", r"testing your ai", r"this system",
    r"amouage", r"fragrance", r"new scents", r"smells like freedom",
    r"wanna chat about what i did", r"developed you", r"scythe",
    r"3d modeling", r"weapon modeling", r"give me tips and trick",
    r"tell me relax during exams",
]
# Sessions where the student is testing the bot or off-topic, so no message in
# them is a genuine distress signal.
SESSION_BLOCK = {
    ("P040", "S0012"),   # "I am a student who is testing your AI intelligence"
    ("P011", "S0052"),   # fragrance chat
    ("P052", "S0014"),   # asks the bot about itself
    ("P051", "S0010"),   # "helping the higher levels for their pilot testing"
    ("P041", "S0042"),   # calm relaxation / scenery, no distress content
}

# --- heuristic buckets, checked in priority order ---------------------------
# Regexes: r"\b(stem)" matches any word starting with the stem (strangl ->
# Strangling, worr -> worry/worried), r"\bword\b" matches a whole word so
# "die" never matches inside "studied" and "mad" never matches in "made".
BUCKET_KEYWORDS = {
    "crisis": [
        r"\bgive up\b", r"\bmamatay", r"\bdie\b", r"\bkill\b", r"\bstrangl",
        r"suicid", r"\bend my life\b", r"\bend it all\b",
        r"\bwhen will it end\b", r"\bpatapon\b", r"\bsuko", r"\bcrashing out\b",
        r"\bself.harm\b",
    ],
    "anger": [
        r"\bgalit\b", r"\binis\b", r"\bmad\b", r"\bangry\b", r"\bhate\b",
        r"\bpissed\b", r"\bannoy",
    ],
    "sadness": [
        r"\bsad\b", r"\bdown\b", r"\bcry", r"\bcrying\b", r"\blungkot\b",
        r"\bmalungkot\b", r"\balone\b", r"\blonely\b", r"\bempty\b",
        r"\bnaiiyak\b", r"\bluha\b", r"\bgulong gulo\b", r"\boverwhelm",
        r"\bno motivation\b", r"\blosing interest\b",
    ],
    "anxiety": [
        r"\bstress", r"\banxious\b", r"\banxiety\b", r"\bworr",
        r"\bkaba\b", r"\bnervous\b", r"\boverthink", r"\bpanic\b",
        r"\bscared\b", r"\bpressure", r"\brestless\b", r"\bdread\b",
        r"\bhard time\b", r"\bfeeling so\b",
    ],
    "loss": [
        r"\bex ko\b", r"\bhiwalay", r"\bbroke up\b", r"\bbreakup\b",
        r"\bi lost\b", r"\blost a\b", r"\bloss\b", r"\bnamatay\b",
        r"\bpumanaw\b", r"\bi miss\b", r"\bmiss you\b", r"\bnawala\b",
        r"relationship", r"\bcrush\b", r"\bmy girl\b", r"\bgirlfriend\b",
        r"\bpartner\b", r"\bfamily problem", r"\bfinancial problem",
        r"\brecovering addict\b", r"\bimposter syndrome\b",
    ],
}
BUCKET_ORDER = ["crisis", "anger", "sadness", "anxiety", "loss", "neutral"]
# Minimum rows pulled from each bucket so small but critical classes survive.
BUCKET_MIN = {"crisis": 4, "anger": 4, "sadness": 6, "anxiety": 12, "loss": 5, "neutral": 3}
# Neutral targets must be an actual statement, not a one-word reply ("math",
# "this year"). Shortest useful neutral messages clear this; longer ones are
# preferred so the sheet carries substantive non-distress text.
NEUTRAL_MIN_LEN = 35

# Context window shown to counselors for each target message.
CONTEXT_PRIOR = 3      # how many earlier messages from the same session
CONTEXT_CAP = 100      # max chars of each context message (keep rows scannable)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def is_probe(text: str, norm: str) -> bool:
    if CAPTURE_LINE in norm:  # team's capture annotation, not a student message
        return True
    for pat in PROBE_PATTERNS:
        if pat in norm:
            return True
    return False


def is_low_value(norm: str) -> bool:
    """True for content-free filler or bot/off-topic chatter (no ratable text)."""
    if any(re.fullmatch(p, norm) for p in FILLER_PATTERNS):
        return True
    return any(re.search(p, norm) for p in META_PATTERNS)


def match_keyword(norm: str, pattern: str) -> bool:
    """Regex match (patterns carry their own word-boundary rules)."""
    return re.search(pattern, norm) is not None


def bucket_of(norm: str) -> str:
    for name in BUCKET_ORDER:
        if name == "neutral":
            continue
        if any(match_keyword(norm, k) for k in BUCKET_KEYWORDS[name]):
            return name
    return "neutral"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=100, help="target sample size")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-per-pid", type=int, default=4)
    args = parser.parse_args()

    with open(RAW, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    # 1) filter + dedupe
    seen: set[str] = set()
    eligible: list[dict] = []
    n_probes = 0
    n_low = 0
    n_dup = 0
    for r in rows:
        norm = normalize(r["message"])
        if is_probe(r["message"], norm):
            n_probes += 1
            continue
        if (r["pid"], r["session_ref"]) in SESSION_BLOCK:
            n_low += 1
            continue
        if is_low_value(norm):
            n_low += 1
            continue
        if norm in seen:
            n_dup += 1
            continue
        seen.add(norm)
        eligible.append(r)

    # 2) bucket
    buckets: dict[str, list[dict]] = {b: [] for b in BUCKET_ORDER}
    for r in eligible:
        buckets[bucket_of(normalize(r["message"]))].append(r)
    # neutral: drop one-line replies, then prefer the longest/most informative
    buckets["neutral"] = [r for r in buckets["neutral"]
                          if len(normalize(r["message"])) >= NEUTRAL_MIN_LEN]
    buckets["neutral"].sort(key=lambda r: -len(normalize(r["message"])))

    rng = random.Random(args.seed)
    total = len(eligible)
    for b in buckets:
        if b != "neutral":      # neutral is ordered by informativeness, above
            rng.shuffle(buckets[b])

    def pid_cap_ok(selected: list[dict], r: dict) -> bool:
        cnt = sum(1 for s in selected if s["pid"] == r["pid"])
        return cnt < args.max_per_pid

    # 2b) safety-critical rows MUST ship to counselors, regardless of random quota
    serious_selfharm = re.compile(
        r"\bstrangl|suicid|\bend my life\b|\bend it all\b|\bmamatay")
    must_include = [r for r in buckets["crisis"]
                    if serious_selfharm.search(normalize(r["message"]))]

    # 3) per-bucket quotas: cap neutral (short filler dominates real chat), then
    #    give the distress buckets the remaining budget proportionally to their
    #    real pool sizes, floored so small-but-critical classes survive.
    neutral_pool = len(buckets["neutral"])
    neutral_quota = min(neutral_pool, round(args.n * 0.40))
    distress_budget = args.n - neutral_quota
    distress_pools = {b: len(buckets[b]) for b in BUCKET_ORDER if b != "neutral"}
    distress_sum = sum(distress_pools.values()) or 1
    quota = {}
    for b in BUCKET_ORDER[:-1]:
        size = distress_pools[b]
        q = round(distress_budget * size / distress_sum)
        quota[b] = min(size, max(BUCKET_MIN[b], q))
    quota["neutral"] = neutral_quota

    selected: list[dict] = list(must_include)
    for b in BUCKET_ORDER:
        for r in buckets[b]:
            if len(selected) >= args.n:
                break
            if r in selected:
                continue
            if len([s for s in selected if s["pid"] == r["pid"]]) >= args.max_per_pid:
                continue
            if sum(1 for s in selected if bucket_of(normalize(s["message"])) == b) >= quota[b]:
                continue
            selected.append(r)

    # 4) top up from leftovers if short
    if len(selected) < args.n:
        leftovers = [r for b in BUCKET_ORDER for r in buckets[b]
                     if r not in selected]
        rng.shuffle(leftovers)
        for r in leftovers:
            if len(selected) >= args.n:
                break
            if pid_cap_ok(selected, r):
                selected.append(r)

    selected = selected[: args.n]
    rng.shuffle(selected)  # final order should not cluster by bucket

    # 4b) build conversation context for each target: earlier student messages
    #     from the same session (student-side only, chronological order).
    sessions: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        sessions.setdefault((r["pid"], r["session_ref"]), []).append(r)
    for lst in sessions.values():
        lst.sort(key=lambda x: int(x["msg_no"]))

    def context_for(target: dict) -> str:
        prior = [x for x in sessions.get((target["pid"], target["session_ref"]), [])
                 if int(x["msg_no"]) < int(target["msg_no"])]
        parts = []
        for x in prior[-CONTEXT_PRIOR:]:
            t = re.sub(r"\s+", " ", x["message"]).strip()
            if len(t) > CONTEXT_CAP:
                t = t[:CONTEXT_CAP].rstrip() + "..."
            parts.append(t)
        return " | ".join(parts)

    # 5) write counselor sheet (identifiers + timestamps dropped)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "context", "text",
                    "counselor_A_label", "counselor_B_label"])
        for i, r in enumerate(selected, 1):
            text = re.sub(r"\s+", " ", r["message"]).strip()
            w.writerow([f"R{i:03d}", context_for(r), text, "", ""])

    # report
    from collections import Counter
    cnt = Counter(bucket_of(normalize(s["message"])) for s in selected)
    pids = Counter(s["pid"] for s in selected)
    print(f"Raw rows read        : {len(rows)}")
    print(f"Probes removed       : {n_probes}")
    print(f"Low-value removed    : {n_low}")
    print(f"Duplicate texts      : {n_dup}")
    print(f"Eligible (deduped)   : {total}")
    print(f"Sample size          : {len(selected)}")
    print("Bucket breakdown in sample:")
    for b in BUCKET_ORDER:
        print(f"  {b:9s} {cnt.get(b, 0):3d}   (pool: {len(buckets[b])})")
    print(f"Participants covered : {len(pids)}")
    print(f"Max rows from one pid: {max(pids.values())}")
    print(f"Items with context   : {sum(1 for s in selected if context_for(s))}/{len(selected)}")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()