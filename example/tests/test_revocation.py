"""The revocation list, and verify_token's use of it (node T9).

test_a_revoked_token_is_refused_inside_the_skew_window is the case the mid
tier missed on its first attempt and the escalated attempt fixed; it is
pinned here so the regression cannot come back quietly.
"""

import unittest

from example.src.auth import TokenRevoked, issue_token, verify_token
from example.src.config import AuthConfig
from example.src.revocation import RevocationList
from example.tests import NOW

CONFIG = AuthConfig(secret="unit-test-secret", clock_skew_seconds=60)
DAY = 86400


class RevocationListTest(unittest.TestCase):

    def setUp(self):
        self.revocations = RevocationList(clock=lambda: NOW)

    def test_an_unknown_id_is_not_revoked(self):
        self.assertFalse(self.revocations.is_revoked("nothing-here"))

    def test_a_revoked_id_reads_as_revoked(self):
        self.revocations.revoke("abc123", expires_at=NOW + DAY)
        self.assertTrue(self.revocations.is_revoked("abc123", now=NOW + 10))
        self.assertIn("abc123", self.revocations)

    def test_revoking_twice_keeps_the_later_expiry(self):
        self.revocations.revoke("abc123", expires_at=NOW + 60)
        self.revocations.revoke("abc123", expires_at=NOW + DAY)
        self.assertTrue(self.revocations.is_revoked("abc123", now=NOW + 600))

    def test_sweep_drops_only_expired_entries(self):
        self.revocations.revoke("stale", expires_at=NOW - 1)
        self.revocations.revoke("live", expires_at=NOW + DAY)
        self.assertEqual(self.revocations.sweep(now=NOW), 1)
        self.assertEqual(len(self.revocations), 1)
        self.assertTrue(self.revocations.is_revoked("live", now=NOW))

    def test_a_bad_id_is_refused(self):
        with self.assertRaises(ValueError):
            self.revocations.revoke("", expires_at=NOW)
        with self.assertRaises(ValueError):
            self.revocations.revoke("abc123", expires_at="soon")

    def test_the_retention_grace_outlives_the_token(self):
        held = RevocationList(clock=lambda: NOW, grace_seconds=60)
        held.revoke("abc123", expires_at=NOW + 100)
        self.assertTrue(held.is_revoked("abc123", now=NOW + 160))
        self.assertFalse(held.is_revoked("abc123", now=NOW + 161))

    def test_a_negative_grace_is_refused(self):
        with self.assertRaises(ValueError):
            RevocationList(grace_seconds=-1)


class VerifyWithRevocationTest(unittest.TestCase):

    def setUp(self):
        self.revocations = RevocationList(clock=lambda: NOW,
                                          grace_seconds=CONFIG.clock_skew_seconds)
        self.token = issue_token("user-42", CONFIG, now=NOW)
        self.claims = verify_token(self.token, CONFIG, now=NOW)

    def test_a_live_token_still_verifies(self):
        claims = verify_token(self.token, CONFIG, now=NOW + 5,
                              revocations=self.revocations)
        self.assertEqual(claims["sub"], "user-42")

    def test_a_revoked_token_is_refused(self):
        self.revocations.revoke_claims(self.claims)
        with self.assertRaises(TokenRevoked):
            verify_token(self.token, CONFIG, now=NOW + 5,
                         revocations=self.revocations)

    def test_a_revoked_token_is_refused_inside_the_skew_window(self):
        # T9, escalated attempt. The moment travels from the caller, so a
        # verifier one skew-width behind the sweep clock still sees the
        # revocation.
        self.revocations.revoke_claims(self.claims)
        with self.assertRaises(TokenRevoked):
            verify_token(self.token, CONFIG, now=NOW + DAY + 45,
                         revocations=self.revocations)

    def test_revoking_one_session_leaves_another_alone(self):
        other = issue_token("user-77", CONFIG, now=NOW)
        self.revocations.revoke_claims(self.claims)
        self.assertEqual(
            verify_token(other, CONFIG, now=NOW + 5,
                         revocations=self.revocations)["sub"], "user-77")


if __name__ == "__main__":
    unittest.main()
