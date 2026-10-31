"""Google sign-in must never grant a role the client asked for.

The old endpoint used the request body's `role` as the issued role, so any
verified @ue.edu.ph account could become a counselor. These tests pin the
replacement contract: identity comes from the verified email / allowlist only.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.auth import resolve_google_role


def test_ordinary_university_email_gets_student_role():
    assert resolve_google_role("random.student@ue.edu.ph") == "student"


def test_student_credential_email_is_never_a_counselor():
    assert resolve_google_role("student1@ue.edu.ph") == "student"


def test_allowlisted_email_gets_counselor_role(monkeypatch):
    monkeypatch.setenv(
        "COUNSELOR_EMAILS",
        "counselor.one@ue.edu.ph, second.counselor@ue.edu.ph",
    )
    assert resolve_google_role("Counselor.One@UE.edu.ph") == "counselor"
    assert resolve_google_role("second.counselor@ue.edu.ph") == "counselor"


def test_placeholder_counselor_ids_are_not_promoted():
    # TEST_CREDENTIALS uses "counselor01" placeholders, not real addresses.
    assert resolve_google_role("counselor01") == "student"
