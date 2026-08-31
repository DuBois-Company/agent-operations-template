"""The request wrapper and the login response headers (nodes T2, T10).

T2's tests are the four gate cases: no header, good token, expired token,
forged token. T10 added the cookie-flag cases and is still in review -- the
executable criteria pass, the judgment read has not happened yet.
"""

import unittest

from example.src.auth import issue_token, verify_token
from example.src.config import AuthConfig
from example.src.middleware import (REASON_EXPIRED, REASON_MISSING,
                                    REASON_REJECTED, REASON_REVOKED,
                                    SESSION_COOKIE, header_value,
                                    login_response_headers,
                                    logout_response_headers, parse_bearer,
                                    require_token)
from example.src.revocation import RevocationList
from example.tests import NOW

CONFIG = AuthConfig(secret="unit-test-secret", clock_skew_seconds=60)
DAY = 86400


def whoami(request, claims):
    return {"status": 200, "sub": claims["sub"]}


class HeaderTest(unittest.TestCase):

    def test_header_lookup_ignores_case(self):
        self.assertEqual(header_value({"authorization": "Bearer x"}, "Authorization"),
                         "Bearer x")

    def test_a_missing_header_reads_as_none(self):
        self.assertIsNone(header_value({}, "Authorization"))
        self.assertIsNone(header_value(None, "Authorization"))

    def test_bearer_parsing(self):
        self.assertEqual(parse_bearer({"Authorization": "Bearer abc.def.ghi"}),
                         "abc.def.ghi")
        self.assertIsNone(parse_bearer({"Authorization": "Basic abc"}))
        self.assertIsNone(parse_bearer({"Authorization": "Bearer   "}))
        self.assertIsNone(parse_bearer({}))


class GateTest(unittest.TestCase):

    def setUp(self):
        self.revocations = RevocationList(clock=lambda: NOW,
                                          grace_seconds=CONFIG.clock_skew_seconds)
        self.guarded = require_token(whoami, CONFIG, revocations=self.revocations)
        self.token = issue_token("user-42", CONFIG, now=NOW)

    def request(self, token):
        return {"headers": {"Authorization": "Bearer " + token}}

    def test_no_header_is_a_401(self):
        response = self.guarded({"headers": {}}, now=NOW)
        self.assertEqual(response["status"], 401)
        self.assertEqual(response["reason"], REASON_MISSING)

    def test_a_valid_token_reaches_the_handler(self):
        response = self.guarded(self.request(self.token), now=NOW + 5)
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["sub"], "user-42")

    def test_an_expired_token_is_a_401(self):
        response = self.guarded(self.request(self.token), now=NOW + DAY + 61)
        self.assertEqual(response["status"], 401)
        self.assertEqual(response["reason"], REASON_EXPIRED)

    def test_a_forged_token_is_a_401_without_saying_why(self):
        header, _, signature = self.token.split(".")
        forged = ".".join([header, issue_token("root", CONFIG, now=NOW).split(".")[1],
                           signature])
        response = self.guarded(self.request(forged), now=NOW)
        self.assertEqual(response["status"], 401)
        self.assertEqual(response["reason"], REASON_REJECTED)

    def test_a_revoked_token_is_a_401(self):
        self.revocations.revoke_claims(verify_token(self.token, CONFIG, now=NOW))
        response = self.guarded(self.request(self.token), now=NOW + 5)
        self.assertEqual(response["status"], 401)
        self.assertEqual(response["reason"], REASON_REVOKED)

    def test_the_wrapper_keeps_a_handle_on_the_handler(self):
        self.assertIs(self.guarded.wrapped, whoami)


class LoginHeaderTest(unittest.TestCase):

    def setUp(self):
        self.headers, self.token = login_response_headers("user-42", CONFIG, now=NOW)
        self.cookie = self.headers["Set-Cookie"]

    def test_the_cookie_carries_the_issued_token(self):
        self.assertIn("%s=%s" % (SESSION_COOKIE, self.token), self.cookie)
        self.assertEqual(verify_token(self.token, CONFIG, now=NOW)["sub"], "user-42")

    def test_the_cookie_is_http_only_and_secure(self):
        self.assertIn("HttpOnly", self.cookie)
        self.assertIn("Secure", self.cookie)

    def test_same_site_is_strict(self):
        # D3. Cleared on 2026-05-04 before this node was dispatched.
        self.assertIn("SameSite=Strict", self.cookie)
        self.assertNotIn("SameSite=Lax", self.cookie)

    def test_max_age_matches_the_configured_lifetime(self):
        self.assertIn("Max-Age=%d" % CONFIG.ttl_seconds, self.cookie)

    def test_the_login_response_is_not_cached(self):
        self.assertEqual(self.headers["Cache-Control"], "no-store")

    def test_an_insecure_deployment_can_drop_the_secure_flag(self):
        headers, _ = login_response_headers("user-42", CONFIG, now=NOW, secure=False)
        self.assertNotIn("Secure", headers["Set-Cookie"])
        self.assertIn("HttpOnly", headers["Set-Cookie"])

    def test_logout_clears_the_cookie_and_revokes_the_session(self):
        revocations = RevocationList(clock=lambda: NOW,
                                     grace_seconds=CONFIG.clock_skew_seconds)
        claims = verify_token(self.token, CONFIG, now=NOW)
        headers = logout_response_headers(claims, revocations)
        self.assertIn("Max-Age=0", headers["Set-Cookie"])
        self.assertTrue(revocations.is_revoked(claims["jti"], now=NOW + 5))


if __name__ == "__main__":
    unittest.main()
