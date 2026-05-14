import os
import uuid

import jwt

# Must be set before importing jwt_helpers because JWT_SECRET is read at module load time
TEST_SECRET = "test-secret-for-testing-at-least-32-chars"
os.environ["JWT_SECRET"] = TEST_SECRET

from auth.jwt_helpers import create_match_ticket


def test_match_ticket_has_correct_claims():
    user_id = str(uuid.uuid4())
    match_id = str(uuid.uuid4())

    token = create_match_ticket(user_id, match_id)
    payload = jwt.decode(token, TEST_SECRET, algorithms=["HS256"])

    assert payload["sub"] == user_id
    assert payload["match_id"] == match_id
    assert payload["type"] == "match_ticket"
    assert "jti" in payload


def test_match_ticket_expires_in_60_seconds():
    token = create_match_ticket(str(uuid.uuid4()), str(uuid.uuid4()))
    payload = jwt.decode(token, TEST_SECRET, algorithms=["HS256"])

    assert payload["exp"] - payload["iat"] == 60
