import base64

import bcrypt

from smartstore_blog_automation.commerce_client import _build_client_secret_sign


def test_build_client_secret_sign_matches_manual_bcrypt():
    client_id = "test-client-id"
    timestamp_ms = 1700000000000
    salt = bcrypt.gensalt()
    client_secret = salt.decode("utf-8")

    signature = _build_client_secret_sign(client_id, client_secret, timestamp_ms)

    expected = base64.b64encode(
        bcrypt.hashpw(f"{client_id}_{timestamp_ms}".encode("utf-8"), salt)
    ).decode("utf-8")
    assert signature == expected


def test_build_client_secret_sign_changes_with_timestamp():
    client_id = "test-client-id"
    salt = bcrypt.gensalt()
    client_secret = salt.decode("utf-8")

    sig1 = _build_client_secret_sign(client_id, client_secret, 1700000000000)
    sig2 = _build_client_secret_sign(client_id, client_secret, 1700000000001)

    assert sig1 != sig2
