#!/usr/bin/env python3
"""Analyze a GAIDA fine-tuning JSONL file.

Reports structure, language mix, topic coverage, crisis coverage, response
style, and duplicate/near-duplicate examples. Intended to be run before and
after adding training batches:

    python training/analyze_finetune.py
    python training/analyze_finetune.py training/batches/batch1.jsonl
"""

import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

TRAINING_DIR = Path(__file__).resolve().parent

TAGALOG = {
    "ang", "ng", "mga", "sa", "na", "ko", "mo", "ka", "ako", "ikaw", "siya",
    "kami", "tayo", "kayo", "sila", "niya", "namin", "natin", "ninyo", "nila",
    "ito", "iyon", "yun", "yung", "dito", "diyan", "doon", "wala", "hindi",
    "oo", "opo", "pero", "kasi", "kaya", "para", "kung", "kapag", "dahil",
    "habang", "tapos", "lang", "lamang", "nga", "naman", "din", "rin", "po",
    "mula", "tungkol", "isa", "sobra", "grabe", "talaga", "siguro", "baka",
    "dapat", "gusto", "ayaw", "kailangan", "alam", "salamat", "pasensya",
    "kuya", "ate", "nanay", "tatay", "pamilya", "magulang", "kapatid",
    "kaibigan", "jowa", "pera", "pagod", "lungkot", "takot", "galit", "iyak",
    "umiiyak", "tulog", "sakit", "buhay", "mamatay", "patay", "problema",
    "eskwela", "aral", "guro", "klase", "trabaho", "utang", "baon", "gutom",
    "pagkain", "bahay", "aking", "iyong", "kanilang", "naiiyak", "kinakabahan",
    "kabado", "mag-isa", "nag-iisa", "hiwalay", "selos", "mahal", "pag-ibig",
    "barkada", "kaklase", "kulang", "hirap", "mahina", "bagsak", "pasa",
}

# Each bucket is a regex over user + assistant text (lowercased).
TOPICS = {
    "academic": r"exam|grade|subject|teacher|professor|school|college|university|thesis|scholarship|deadline|assignment|project|quiz|recit|\bgwa\b|dean|failing|drop|ojt|internship|graduat|aral|eskwela|guro|klase|bagsak|pasa|quiz|pagsusulit|propesor|teach",
    "family": r"family|parent|mom|dad|mother|father|nanay|tatay|pamilya|magulang|kuya|\bate\b|kapatid|sibling|tita|tito|lola|lolo|household|pinapagalitan|pinapagalitan",
    "relationship": r"boyfriend|girlfriend|partner|jowa|\bex\b|breakup|break-up|heartbreak|relationship|relasyon|asawa|hiwalay|cheat|selos|crush|pag-ibig|mahal ko|long distance|lq",
    "social": r"friend|kaibigan|barkada|classmate|kaklase|org\b|social|group|blockmate|bully|bullied|introvert|shy|mahiyain|loner|peer|clique|circle",
    "financial": r"money|pera|financial|tuition|baon|allowance|bayad|utang|bills|rent|sweldo|salary|part-time|job|trabaho|mahal ang|gastos|budget|kasal",
    "overthinking": r"overthink|over-think|iniisip|isipin|spiral|what if|paulit-ulit|kaisipan|negative thoughts|self-doubt|intrusive|can't stop thinking|hindi ko maiwasan|bumabalik",
    "loneliness": r"lonely|alone|mag-isa|nag-iisa|no one|walang kasama|isolation|isolated|empty|emptiness|walang makausap|lumalayo|left out|invisible",
    "anxiety": r"anxiety|anxious|nervous|kinakabahan|kabado|panic|nerbiyos|takot|fear|worry|pag-aalala|stress|stressed|tension|overwhelm|atake",
    "sadness": r"depress|sad|malungkot|lungkot|hopeless|walang pag-asa|umiiyak|\biyak\b|cry|numb|manhid|down|bumaba|mood|wala akong gana|empt",
    "crisis": r"suicid|kill myself|end my life|mamatay|magpatiwakal|patayin|self-harm|self harm|saktan|sugat|\bcut\b|pills|overdose|hang|jump|wakasan|ayaw nang mabuhay|gusto nang mamatay|may plano na|nagsasaktan|pasa sa braso|tinatago.*gamot",
    "anger": r"angry|galit|inis|irita|rage|frustrat|bent|furious|pikon|nanggagalit|burst",
    "grief": r"died|death|namatay|patay|loss|grief|funeral|lamay|passed away|wala na siya|namimiss",
    "body_image": r"body|weight|taba|payat|pangit|diet|kain|bulimia|anorexia|itsura|mirror|skin|acne",
    "sleep": r"sleep|tulog|insomnia|puyat|gabi|nightmare|bangungot|can't sleep|hindi makatulog",
    "identity": r"identity|lgbtq|\bgay\b|bakla|tomboy|\btrans\b|self-esteem|self-worth|worthless|halaga ko|kung sino ako|\bconfidence\b|\bkumpiyansa\b",
    "abuse": r"abuse|sinasaktan|sinaktan|binubugbog|harass|rape|molest|violence|pananakit|bugbog|threat|pinagbantaan|hinahawakan",
    "substance": r"alcohol|alak|inom|drugs|droga|smoke|vape|sigarilyo|marijuana|shabu",
    "physical_health": r"sakit|illness|hospital|doctor|gamot|medicine|checkup|diagnos|chronic|paglilihi",
    "work_career": r"career|trabaho|work|boss|coworker|employ|interview|resume|rakets|sideline",
    "spirituality": r"\bgod\b|diyos|faith|prayer|pray|simbahan|church|pananampalataya|spiritual",
}

BASE_TOPICS = [
    "academic", "family", "relationship", "social", "financial",
    "overthinking", "loneliness", "anxiety", "sadness", "crisis",
    "anger", "grief", "body_image", "sleep", "identity",
    "abuse", "substance", "physical_health", "work_career", "spirituality",
]

CRISIS_MARKERS = re.compile(
    r"suicid|kill myself|end my life|mamatay|magpatiwakal|patayin|"
    r"self-harm|self harm|saktan|ayaw nang mabuhay|gusto nang mamatay|"
    r"wakasan|overdose|pills|jump off|hang myself|may plano na|nagsasaktan|"
    r"pasa sa braso|tinatago.*gamot",
    re.I,
)

HOTLINES = re.compile(r"1553|0917|2919|911|ncmh|in touch|hotline", re.I)


def load(path: Path) -> list[tuple[int, dict, str]]:
    rows = []
    for lineno, raw in enumerate(path.open(encoding="utf-8"), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            rows.append((lineno, json.loads(line), line))
        except json.JSONDecodeError as exc:
            print(f"  !! line {lineno}: invalid JSON ({exc.msg})")
    return rows


def words(text: str) -> list[str]:
    return re.findall(r"[a-zA-ZñÑáéíóúÁÉÍÓÚ-]+", text.lower())


def language(text: str) -> str:
    ws = words(text)
    if not ws:
        return "unknown"
    ratio = sum(1 for w in ws if w in TAGALOG) / len(ws)
    if ratio >= 0.35:
        return "Filipino"
    if ratio >= 0.05:
        return "Taglish"
    return "English"


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else TRAINING_DIR / "finetune.jsonl"
    if not path.is_absolute():
        path = TRAINING_DIR / path.name if path.parent == Path(".") else path
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    rows = load(path)
    print(f"\n=== FILE ===\n{path}\nexamples: {len(rows)}")

    systems: Counter[str] = Counter()
    role_shapes: Counter[tuple] = Counter()
    user_langs: Counter[str] = Counter()
    asst_langs: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    multi_label: Counter[int] = Counter()
    crisis_rows, hotline_rows, multi_turn = [], [], []
    user_words, asst_words, q_marks, sentences = [], [], [], []
    first_words: Counter[str] = Counter()
    openings: Counter[str] = Counter()
    users: list[tuple[int, str]] = []
    assistants: list[tuple[int, str]] = []

    for lineno, row, _raw in rows:
        msgs = row.get("messages", [])
        role_shapes[tuple(m.get("role") for m in msgs)] += 1
        if len(msgs) != 3:
            multi_turn.append(lineno)
        sys_txt = next((m.get("content", "") for m in msgs if m.get("role") == "system"), "")
        systems[sys_txt] += 1
        user = next((m.get("content", "") for m in msgs if m.get("role") == "user"), "")
        asst = next((m.get("content", "") for m in msgs if m.get("role") == "assistant"), "")
        users.append((lineno, user))
        assistants.append((lineno, asst))

        user_langs[language(user) + " / " + language(asst)] += 1
        asst_langs[language(asst)] += 1
        user_words.append(len(word_list := words(user)))
        asst_words.append(len(words(asst)))
        sentences.append(len([s for s in re.split(r"[.!?]+", asst) if s.strip()]))
        q_marks.append(asst.count("?"))

        combined = (user + " " + asst).lower()
        matched = [t for t in BASE_TOPICS if re.search(TOPICS[t], combined)]
        for t in matched:
            topic_counts[t] += 1
        multi_label[len(matched)] += 1
        if CRISIS_MARKERS.search(user):
            crisis_rows.append(lineno)
        if HOTLINES.search(asst):
            hotline_rows.append(lineno)

        fw = re.match(r"[\"']?([A-Za-z]+)", asst.strip())
        if fw:
            first_words[fw.group(1).lower()] += 1
        op = re.match(r"([^.!?\n]{0,40})", asst.strip())
        if op:
            openings[op.group(1).strip().lower()] += 1

    print("\n=== STRUCTURE ===")
    print("role sequences:", dict(role_shapes))
    print(f"system prompt variants: {len(systems)}")
    for prompt, count in systems.most_common(3):
        print(f"  x{count} ({len(prompt)} chars): {prompt[:110]}...")
    print(f"examples with != 3 messages: {len(multi_turn)}")

    print("\n=== LANGUAGE (user / assistant) ===")
    for combo, count in user_langs.most_common():
        print(f"  {combo:<24} {count:>4}  ({count/len(rows)*100:5.1f}%)")

    print("\n=== TOPIC COVERAGE (regex, multi-label) ===")
    for t in BASE_TOPICS:
        c = topic_counts[t]
        flag = "  <-- MISSING" if c == 0 else ""
        print(f"  {t:<16} {c:>4}  ({c/len(rows)*100:5.1f}%){flag}")
    print("labels per example:", dict(sorted(multi_label.items())))

    print("\n=== SAFETY ===")
    print(f"explicit crisis language in user msg : {len(crisis_rows)} ({len(crisis_rows)/len(rows)*100:.1f}%)")
    print(f"assistant cites a hotline             : {len(hotline_rows)} ({len(hotline_rows)/len(rows)*100:.1f}%)")
    print(f"crisis examples WITHOUT hotline       : {len(set(crisis_rows) - set(hotline_rows))}")

    print("\n=== RESPONSE STYLE ===")
    print(f"user words      : mean {sum(user_words)/len(user_words):.1f}, "
          f"min {min(user_words)}, max {max(user_words)}")
    print(f"assistant words : mean {sum(asst_words)/len(asst_words):.1f}, "
          f"min {min(asst_words)}, max {max(asst_words)}")
    print(f"sentences/reply : mean {sum(sentences)/len(sentences):.1f}")
    print(f"questions/reply : mean {sum(q_marks)/len(q_marks):.2f}, "
          f"replies with 0 questions: {q_marks.count(0)}")
    print("top opening words:", first_words.most_common(10))
    print("most repeated openings:")
    for op, c in openings.most_common(5):
        if c > 1:
            print(f"  x{c}: {op!r}")

    # Exact + near duplicates
    print("\n=== DUPLICATES ===")
    exact_users = Counter(norm(u) for _, u in users)
    dup_users = [(k, c) for k, c in exact_users.items() if c > 1 and k]
    print(f"duplicate user messages (exact) : {len(dup_users)}")
    for k, c in dup_users[:5]:
        print(f"  x{c}: {k[:70]!r}")

    near = []
    for a in range(len(users)):
        for b in range(a + 1, len(users)):
            ua, ub = norm(users[a][1]), norm(users[b][1])
            if not ua or not ub or abs(len(ua) - len(ub)) > 40:
                continue
            if ua == ub:
                continue
            r = SequenceMatcher(None, ua, ub).ratio()
            if r >= 0.85:
                near.append((r, users[a][0], users[b][0]))
    print(f"near-duplicate user pairs (>=0.85): {len(near)}")
    for r, a, b in sorted(near, reverse=True)[:5]:
        print(f"  {r:.2f} lines {a}/{b}")

    exact_asst = Counter(norm(x) for _, x in assistants)
    print(f"duplicate assistant replies      : "
          f"{sum(1 for k, c in exact_asst.items() if k and c > 1)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
