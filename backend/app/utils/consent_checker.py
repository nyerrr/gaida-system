from app.database.database import supabase
from datetime import datetime


def log_consent(session_id: str, consent_given: bool):
    """
    Insert or update a consent record for a session.
    """
    try:
        existing = supabase.table("consents")\
            .select("*")\
            .eq("session_id", session_id)\
            .execute()

        if existing.data:
            supabase.table("consents")\
                .update({
                    "consent_given": consent_given,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("session_id", session_id)\
                .execute()
        else:
            supabase.table("consents")\
                .insert({
                    "session_id": session_id,
                    "consent_given": consent_given,
                })\
                .execute()
    except Exception as e:
        print(f"Supabase consent error: {e}")


def has_consent(session_id: str) -> bool:
    """
    Check if a session has given consent.
    Returns True only if consent was explicitly recorded as True.
    """
    try:
        result = supabase.table("consents")\
            .select("consent_given")\
            .eq("session_id", session_id)\
            .eq("consent_given", True)\
            .execute()

        return len(result.data) > 0
    except Exception as e:
        print(f"Supabase consent check error: {e}")
        return False