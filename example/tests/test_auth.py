"""Token issue and verify (nodes T1, T4, T8).

The expiry cases are the reason node T8 needed a second attempt: the first
implementation applied the clock-skew tolerance to the wrong side of the
bound. test_expiry_boundary_is_inclusive_of_skew is the criterion that was
missing from T8's original acceptance list, added at review.
"""

import unittest

from example.src.auth import (TokenExpired, TokenIssuerMismatch,
                              TokenMalformed, TokenNotYetValid,
                              TokenSignatureInvalid, decode_unverified,
                              issue_token, token_id, verify_token)
from example.src.config import AuthConfig
from example.tests import NOW

CONFIG = AuthConfig(secret="unit-test-secret", clock_skew_seconds=60)
DAY = 86400


class RoundTripTest(unittest.TestCase):

    def test_a_fresh_token_verifies(self):
        token = issue_token("user-42", CONFIG, now=NOW)
        claims = verify_token(token, CONFIG, now=NOW + 5)
        self.assertEqual(claims["sub"], "user-42")
        self.assertEqual(claims["iss"], CONFIG.issuer)

    def test_expiry_is_one_lifetime_after_issue(self):
        claims = decode_unverified(issue_token("user-42", CONFIG, now=NOW))
        self.assertEqual(claims["exp"] - claims["iat"], DAY)

    def test_token_has_three_segments(self):
        self.assertEqual(len(issue_token("user-42", CONFIG, now=NOW).split(".")), 3)

    def test_extra_claims_ride_along(self):
        token = issue_token("user-42", CONFIG, now=NOW, claims={"role": "editor"})
        self.assertEqual(verify_token(token, CONFIG, now=NOW)["role"], "editor")

    def test_extra_claims_may_not_overwrite_reserved_ones(self):
        with self.assertRaises(ValueError):
            issue_token("user-42", CONFIG, now=NOW, claims={"exp": NOW + 10 * DAY})

    def test_empty_subject_is_refused_at_issue(self):
        with self.assertRaises(ValueError):
            issue_token("", CONFIG, now=NOW)

    def test_token_id_is_stable_for_one_issuance(self):
        token = issue_token("user-42", CONFIG, now=NOW)
        self.assertEqual(decode_unverified(token)["jti"],
                         token_id("user-42", NOW, CONFIG.issuer))


class ExpiryTest(unittest.TestCase):

    def test_a_token_past_its_lifetime_is_expired(self):
        token = issue_token("user-42", CONFIG, now=NOW)
        with self.assertRaises(TokenExpired):
            verify_token(token, CONFIG, now=NOW + DAY + 61)

    def test_expiry_boundary_is_inclusive_of_skew(self):
        # T8's missing criterion. A verifier whose clock sits inside the
        # tolerance must still accept a token that has just expired.
        token = issue_token("user-42", CONFIG, now=NOW)
        self.assertEqual(verify_token(token, CONFIG, now=NOW + DAY + 60)["sub"],
                         "user-42")

    def test_a_token_from_the_future_is_not_yet_valid(self):
        token = issue_token("user-42", CONFIG, now=NOW + 600)
        with self.assertRaises(TokenNotYetValid):
            verify_token(token, CONFIG, now=NOW)

    def test_a_token_from_a_slightly_ahead_clock_is_accepted(self):
        token = issue_token("user-42", CONFIG, now=NOW + 30)
        self.assertEqual(verify_token(token, CONFIG, now=NOW)["sub"], "user-42")

    def test_a_shorter_lifetime_expires_sooner(self):
        short = CONFIG.replace(ttl_seconds=900, clock_skew_seconds=0)
        token = issue_token("user-42", short, now=NOW)
        self.assertEqual(verify_token(token, short, now=NOW + 900)["sub"], "user-42")
        with self.assertRaises(TokenExpired):
            verify_token(token, short, now=NOW + 901)


class TamperTest(unittest.TestCase):

    def test_a_changed_payload_fails_the_signature(self):
        header, payload, signature = issue_token("user-42", CONFIG, now=NOW).split(".")
        forged = issue_token("root", CONFIG, now=NOW).split(".")[1]
        with self.assertRaises(TokenSignatureInvalid):
            verify_token(".".join([header, forged, signature]), CONFIG, now=NOW)

    def test_another_secret_cannot_verify(self):
        token = issue_token("user-42", CONFIG, now=NOW)
        with self.assertRaises(TokenSignatureInvalid):
            verify_token(token, CONFIG.replace(secret="a-different-secret"), now=NOW)

    def test_the_alg_none_trick_is_refused(self):
        import base64
        import json
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode("utf-8")).rstrip(b"=").decode()
        _, payload, signature = issue_token("user-42", CONFIG, now=NOW).split(".")
        with self.assertRaises(TokenMalformed):
            verify_token(".".join([header, payload, signature]), CONFIG, now=NOW)

    def test_a_wrong_issuer_is_refused(self):
        token = issue_token("user-42", CONFIG.replace(issuer="other-app"), now=NOW)
        with self.assertRaises(TokenIssuerMismatch):
            verify_token(token, CONFIG, now=NOW)

    def test_garbage_is_malformed_not_a_crash(self):
        for junk in ("", "not-a-token", "a.b", "a.b.c.d", "a.b.c"):
            with self.assertRaises(TokenMalformed):
                verify_token(junk, CONFIG, now=NOW)


if __name__ == "__main__":
    unittest.main()
