"""Request middleware for the example web application (nodes T2, T10).

There is no web framework here. A request is a dict with a `headers` mapping,
a response is a dict with a `status`; that is the whole contract, and it is
enough to test the decision the middleware actually makes -- who gets through
and who gets a 401 -- without pulling in a server.

    >>> from example.src.config import AuthConfig
    >>> from example.src.auth import issue_token
    >>> cfg = AuthConfig(secret="unit-test-secret")
    >>> guarded = require_token(lambda request, claims: {"status": 200,
    ...                                                  "sub": claims["sub"]}, cfg)
    >>> token = issue_token("user-42", cfg, now=1_777_000_000)
    >>> guarded({"headers": {"Authorization": "Bearer " + token}},
    ...         now=1_777_000_005)["status"]
    200

T10 (in review) added the login response headers. Decision D3 in graph.yaml
records why SameSite is Strict rather than Lax, and how that fact was cleared
before it was allowed to inform this node.
"""

from .auth import (TokenError, TokenExpired, TokenRevoked, issue_token,
                   verify_token)

SESSION_COOKIE = "example_session"
BEARER_PREFIX = "Bearer "

# Reasons are stable strings: the login throttle in T11 keys its counters on
# them, so renaming one is a breaking change to that node, not a wording fix.
REASON_MISSING = "no_bearer_token"
REASON_EXPIRED = "token_expired"
REASON_REVOKED = "token_revoked"
REASON_REJECTED = "token_rejected"


def header_value(headers, name):
    """Case-insensitive header lookup. HTTP does not promise casing."""
    if not headers:
        return None
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return value
    return None


def parse_bearer(headers):
    """Pull the token out of an Authorization header, or return None."""
    raw = header_value(headers, "Authorization")
    if not raw or not str(raw).startswith(BEARER_PREFIX):
        return None
    token = str(raw)[len(BEARER_PREFIX):].strip()
    return token or None


def unauthorized(reason):
    """The one place a 401 is built, so every rejection looks the same."""
    return {"status": 401, "error": "unauthorized", "reason": reason}


def require_token(handler, config, revocations=None):
    """Wrap a handler so it only runs for a request carrying a valid token.

    The wrapped handler is called as handler(request, claims). Anything that
    fails verification never reaches it -- the middleware fails closed, and
    the reason travels in the response rather than in a log line the caller
    cannot see.
    """

    def guarded(request, now=None):
        token = parse_bearer((request or {}).get("headers"))
        if token is None:
            return unauthorized(REASON_MISSING)
        try:
            claims = verify_token(token, config, now=now, revocations=revocations)
        except TokenExpired:
            return unauthorized(REASON_EXPIRED)
        except TokenRevoked:
            return unauthorized(REASON_REVOKED)
        except TokenError:
            # Malformed, forged, and wrong-issuer all collapse to one reason:
            # a caller who can tell them apart can probe the secret.
            return unauthorized(REASON_REJECTED)
        return handler(request, claims)

    guarded.__name__ = "guarded_" + getattr(handler, "__name__", "handler")
    guarded.wrapped = handler
    return guarded


def login_response_headers(subject, config, now=None, secure=True):
    """Headers for a successful login: the session cookie and its flags.

    Returns (headers, token). The token is handed back because the API
    clients send it as a bearer header while the browser clients ride the
    cookie; both are the same token, issued once.
    """
    token = issue_token(subject, config, now=now)
    attributes = [
        "%s=%s" % (SESSION_COOKIE, token),
        "Path=/",
        "Max-Age=%d" % config.ttl_seconds,
        "HttpOnly",
        "SameSite=Strict",          # D3, cleared 2026-05-04
    ]
    if secure:
        attributes.append("Secure")
    headers = {
        "Set-Cookie": "; ".join(attributes),
        "Cache-Control": "no-store",
    }
    return headers, token


def logout_response_headers(claims, revocations, secure=True):
    """Headers for a logout, after putting the session on the revocation list."""
    revocations.revoke_claims(claims)
    attributes = [
        "%s=" % SESSION_COOKIE,
        "Path=/",
        "Max-Age=0",
        "HttpOnly",
        "SameSite=Strict",
    ]
    if secure:
        attributes.append("Secure")
    return {"Set-Cookie": "; ".join(attributes), "Cache-Control": "no-store"}


__all__ = [
    "SESSION_COOKIE", "REASON_MISSING", "REASON_EXPIRED", "REASON_REVOKED",
    "REASON_REJECTED", "header_value", "parse_bearer", "unauthorized",
    "require_token", "login_response_headers", "logout_response_headers",
]
