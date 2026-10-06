"""Researcher-run deletion of ONE research participant's data.

Why this exists: student-number (identified) participants have no login and no
self-serve delete screen. The consent form tells them to contact the research
team to request deletion; this is the tool the team uses to honor that.
(Anonymous-code participants can still use the in-app "Delete my data" page.)

Run from the backend/ folder, with backend/.env present (needs SUPABASE_URL
and SUPABASE_KEY, same as the server):

    # 1. DRY RUN (default) - shows what WOULD be deleted, changes nothing
    venv\\Scripts\\python.exe tools\\delete_participant.py 20240001234

    # 2. Actually delete (asks you to type DELETE first)
    venv\\Scripts\\python.exe tools\\delete_participant.py 20240001234 --confirm

    # Anonymous participant, by code (same effect as the in-app page)
    venv\\Scripts\\python.exe tools\\delete_participant.py --code AB12CD34EF --confirm

Scope: only RESEARCH sessions (sessions.is_research = true) are touched. If the
same student number also has ordinary counseling sessions, those are left alone
and reported, because they are counseling records, not study data.

Deletion is permanent. Verify the person's identity through the research
team's own process before running this.
"""
import argparse
import re
import sys
from pathlib import Path

# Allow `python tools/delete_participant.py` from backend/ to import `app`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.database import supabase  # noqa: E402

# Keep in sync with _WITHDRAW_SESSION_CHILD_TABLES in app/api/research.py.
CHILD_TABLES = [
    "interactions",
    "consents",
    "gad7_responses",
    "sus_responses",
    "message_feedback",
    "session_ratings",
    "session_notes",
    "counselor_alerts",
    "acoustic_logs",
]

_STUDENT_NUMBER_RE = re.compile(r"^\d{11}$")


def _mask(value: str) -> str:
    return value if value.startswith("anon_") else value[:4] + "*" * (len(value) - 6) + value[-2:]


def _count(table: str, session_ids: list[str]) -> int | str:
    try:
        rows = supabase.table(table).select("session_id").in_("session_id", session_ids).execute()
        return len(rows.data or [])
    except Exception as e:  # table missing / column missing: report, don't hide
        return f"error: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("student_number", nargs="?", help="11-digit student number (identified participant)")
    ap.add_argument("--code", help="anonymous participant code (without the 'anon_' prefix)")
    ap.add_argument("--confirm", action="store_true", help="really delete (default is a dry run)")
    args = ap.parse_args()

    if bool(args.student_number) == bool(args.code):
        ap.error("give either a student number or --code, not both/neither")

    if args.code:
        participant_id = f"anon_{args.code.strip()}"
        sess_query = supabase.table("sessions").select("session_token, is_research").eq("participant_code", args.code.strip())
    else:
        number = args.student_number.strip()
        if not _STUDENT_NUMBER_RE.match(number):
            ap.error("student number must be exactly 11 digits")
        participant_id = number
        sess_query = supabase.table("sessions").select("session_token, is_research").eq("student_id", number)

    rows = sess_query.execute().data or []
    research_ids = [r["session_token"] for r in rows if r.get("is_research")]
    left_alone = [r for r in rows if not r.get("is_research")]

    print(f"Participant: {_mask(participant_id)}")
    print(f"Research sessions found: {len(research_ids)}")
    if left_alone:
        print(f"Non-research (counseling) sessions left untouched: {len(left_alone)}")

    existing = supabase.table("research_participants").select("participant_id").eq("participant_id", participant_id).execute().data
    print(f"research_participants row: {'present' if existing else 'absent'}")

    if research_ids:
        print("Rows that would be deleted, by table:")
        for t in CHILD_TABLES:
            print(f"  {t}: {_count(t, research_ids)}")
        print(f"  sessions: {len(research_ids)}")

    if not research_ids and not existing:
        print("Nothing to delete.")
        return 0

    if not args.confirm:
        print("\nDRY RUN - nothing was deleted. Re-run with --confirm to delete.")
        return 0

    if input("\nThis is PERMANENT. Type DELETE to proceed: ").strip() != "DELETE":
        print("Aborted.")
        return 1

    errors = []
    if research_ids:
        for t in CHILD_TABLES:
            try:
                supabase.table(t).delete().in_("session_id", research_ids).execute()
            except Exception as e:
                errors.append(f"{t}: {e}")
        try:
            supabase.table("sessions").delete().in_("session_token", research_ids).execute()
        except Exception as e:
            errors.append(f"sessions: {e}")
    try:
        supabase.table("research_participants").delete().eq("participant_id", participant_id).execute()
    except Exception as e:
        errors.append(f"research_participants: {e}")

    if errors:
        print("\nFINISHED WITH ERRORS - some data may remain:")
        for e in errors:
            print("  -", e)
        return 2
    print("\nDone. All research data for this participant has been deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
