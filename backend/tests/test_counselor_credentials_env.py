"""Counselor accounts come from the environment, not from source code.

The demo counselors (COUNSELOR01 / counsel123 ...) used to be hardcoded and
always on, which meant anyone who read the repo could sign in to the counselor
dashboard on a deployed server.
"""

import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.constants import build_test_credentials


def _counselors(accounts):
    return {k: v for k, v in accounts.items() if v.get("role") == "counselor"}


def test_demo_counselors_are_available_by_default():
    assert len(_counselors(build_test_credentials({}))) == 5
    assert len(_counselors(build_test_credentials({"ENVIRONMENT": "production"}))) == 5


def test_demo_counselors_can_be_disabled_explicitly():
    accounts = build_test_credentials({"ALLOW_DEMO_ACCOUNTS": "0"})
    assert _counselors(accounts) == {}


def test_demo_counselors_can_be_switched_on_explicitly():
    accounts = build_test_credentials({"ALLOW_DEMO_ACCOUNTS": "1"})
    assert "COUNSELOR01" in accounts


def test_configured_accounts_replace_the_demo_ones():
    env = {
        "ENVIRONMENT": "development",
        "COUNSELOR_ACCOUNTS": json.dumps(
            [{"id": "g.lim", "password": "long-random-pw", "name": "G. Lim",
              "email": "G.Lim@ue.edu.ph"}]
        ),
    }
    counselors = _counselors(build_test_credentials(env))
    assert list(counselors) == ["G.LIM"]
    assert counselors["G.LIM"]["access_code"] == "long-random-pw"
    assert counselors["G.LIM"]["email"] == "g.lim@ue.edu.ph"


def test_malformed_config_gives_no_counselors_instead_of_crashing():
    for bad in ("not json", "{}", "[1, 2]", '[{"id": "", "password": ""}]'):
        assert _counselors(build_test_credentials({
            "COUNSELOR_ACCOUNTS": bad,
            "ALLOW_DEMO_ACCOUNTS": "0",
        })) == {}


def test_students_are_loaded_from_the_configured_roster():
    accounts = build_test_credentials({
        "STUDENT_ACCOUNTS": json.dumps([{
            "student_number": "2024001",
            "email": "student1@ue.edu.ph",
            "access_code": "ACCESS123",
        }]),
    })
    assert accounts["2024001"]["email"] == "student1@ue.edu.ph"


def test_demo_student_roster_is_available_by_default_and_can_be_overridden():
    demo = json.dumps([{
        "student_number": "2024001",
        "email": "student1@ue.edu.ph",
        "access_code": "ACCESS123",
    }])
    assert "2024001" in build_test_credentials({"DEMO_STUDENT_ACCOUNTS": demo})
    assert "2024001" in build_test_credentials({
        "ALLOW_DEMO_ACCOUNTS": "1",
        "DEMO_STUDENT_ACCOUNTS": demo,
    })
    assert "2024001" not in build_test_credentials({"ALLOW_DEMO_ACCOUNTS": "0"})
