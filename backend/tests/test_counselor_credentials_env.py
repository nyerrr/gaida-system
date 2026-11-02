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


def test_no_counselors_on_a_deployed_server_by_default():
    assert _counselors(build_test_credentials({})) == {}
    assert _counselors(build_test_credentials({"ENVIRONMENT": "production"})) == {}


def test_demo_counselors_available_in_development():
    accounts = build_test_credentials({"ENVIRONMENT": "development"})
    assert len(_counselors(accounts)) == 5


def test_demo_counselors_can_be_switched_on_explicitly():
    accounts = build_test_credentials({"GAIDA_ALLOW_DEMO_COUNSELORS": "1"})
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
        assert _counselors(build_test_credentials({"COUNSELOR_ACCOUNTS": bad})) == {}


def test_students_are_unaffected():
    assert "2024001" in build_test_credentials({})
