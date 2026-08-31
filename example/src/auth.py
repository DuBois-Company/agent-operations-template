"""Session tokens for the example web application.

Shape: three base64url segments joined by dots, `header.payload.signature`,
signed with HMAC-SHA256 over the first two segments. That is the JWS compact
form decision D1 settled on, implemented against the standard library so the
example repository keeps zero dependencies.

    >>> from example.src.config import AuthConfig
    >>> cfg = AuthConfig(secret="unit-test-secret")
    >>> token = issue_token("user-42", cfg, now=1_777_000_000)
    >>> verify_token(token, cfg, now=1_777_000_100)["sub"]
    'user-42'

Failure is always an exception, never a falsy return: a caller that forgets
to check a boolean would let a forged token through, and a caller that
forgets to catch an exception fails closed. Every failure mode gets its own
subclass of TokenError so the middleware can log the reason without
inspecting message text.
"""

import base64
import hashlib
import hmac
import json
import time

from .config import AuthConfig

ALGORITHM = "HS256"
HEADER = {"alg": ALGORITHM, "typ": "JWT"}


class TokenError(Exception):
    """Base class. Catching this catches every rejection reason."""


class TokenMalformed(TokenError):
    """The string is not a token: wrong segment count, bad base64, bad JSON."""


class TokenSignatureInvalid(TokenError):
    """The signature does not match the payload under this secret."""


class TokenExpired(TokenError):
    """`exp` is in the past by more than the configured clock skew."""


class TokenNotYetValid(TokenError):
    """`iat` is in the future by more than the configured clock skew."""


class TokenIssuerMismatch(TokenError):
    """`iss` is not the issuer this config verifies for."""


class TokenRevoked(TokenError):
    """`jti` is on the revocation list this verify consulted."""


def _b64encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(segment):
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(segment + padding)
    except (ValueError, TypeError) as exc:
        raise TokenMalformed("segment is not base64url: %s" % exc)


def _encode_json(obj):
    # sort_keys so the same claims always produce the same bytes: a signature
    # that depends on dict ordering is a signature that fails at random.
    return _b64encode(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _decode_json(segment):
    try:
        obj = json.loads(_b64decode(segment).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise TokenMalformed("segment is not JSON: %s" % exc)
    if not isinstance(obj, dict):
        raise TokenMalformed("segment did not decode to an object")
    return obj


def _sign(signing_input, secret):
    return hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"),
                    hashlib.sha256).digest()


def token_id(subject, issued_at, issuer):
    """Stable id for one issuance, used as `jti` and by the revocation list.

    Derived rather than random so a caller holding the same three inputs can
    revoke a token it did not keep a copy of.
    """
    seed = "%s|%d|%s" % (subject, issued_at, issuer)
    return _b64encode(hashlib.sha256(seed.encode("utf-8")).digest()[:12])


def issue_token(subject, config, now=None, claims=None):
    """Return a signed token for `subject`, expiring config.ttl_seconds later."""
    if not isinstance(config, AuthConfig):
        raise TypeError("config must be an AuthConfig")
    if not subject or not isinstance(subject, str):
        raise ValueError("subject must be a non-empty string")
    issued_at = int(time.time() if now is None else now)
    payload = dict(claims or {})
    reserved = sorted(set(payload) & {"sub", "iss", "iat", "exp", "jti"})
    if reserved:
        raise ValueError("claims may not overwrite %s" % ", ".join(reserved))
    payload.update({
        "sub": subject,
        "iss": config.issuer,
        "iat": issued_at,
        "exp": issued_at + config.ttl_seconds,
        "jti": token_id(subject, issued_at, config.issuer),
    })
    signing_input = "%s.%s" % (_encode_json(HEADER), _encode_json(payload))
    return "%s.%s" % (signing_input, _b64encode(_sign(signing_input, config.secret)))


def decode_unverified(token):
    """Read the claims without checking anything. For logging only.

    Named so that a reader of a call site can see the danger; verify_token is
    the only function whose result may be trusted.
    """
    parts = str(token).split(".")
    if len(parts) != 3:
        raise TokenMalformed("expected 3 segments, found %d" % len(parts))
    return _decode_json(parts[1])


def verify_token(token, config, now=None, revocations=None):
    """Return the claims of a valid token, or raise a TokenError subclass.

    Order matters and is deliberate: signature before claims, so an attacker
    learns nothing about claim contents from a forged token; expiry before
    revocation, so the revocation list is only consulted for tokens that are
    otherwise live.
    """
    if not isinstance(config, AuthConfig):
        raise TypeError("config must be an AuthConfig")
    parts = str(token).split(".")
    if len(parts) != 3:
        raise TokenMalformed("expected 3 segments, found %d" % len(parts))
    header_segment, payload_segment, signature_segment = parts

    header = _decode_json(header_segment)
    if header.get("alg") != ALGORITHM:
        # Refusing `alg` from the token is the whole point: a token that
        # names its own algorithm can name "none".
        raise TokenMalformed("unsupported alg: %r" % (header.get("alg"),))

    expected = _sign("%s.%s" % (header_segment, payload_segment), config.secret)
    if not hmac.compare_digest(expected, _b64decode(signature_segment)):
        raise TokenSignatureInvalid("signature does not match")

    claims = _decode_json(payload_segment)
    for required in ("sub", "iss", "iat", "exp", "jti"):
        if required not in claims:
            raise TokenMalformed("claim %r is missing" % required)
    for numeric in ("iat", "exp"):
        if not isinstance(claims[numeric], int) or isinstance(claims[numeric], bool):
            raise TokenMalformed("claim %r is not an integer" % numeric)

    if claims["iss"] != config.issuer:
        raise TokenIssuerMismatch("token was issued by %r" % (claims["iss"],))

    moment = int(time.time() if now is None else now)
    skew = config.clock_skew_seconds

    # T8, second attempt: the tolerance is applied to the side of each bound
    # that widens the accepted window. The first attempt subtracted it from
    # `exp`, which narrowed the window and rejected tokens a skewed clock had
    # every right to accept.
    if moment > claims["exp"] + skew:
        raise TokenExpired("expired at %d, now %d" % (claims["exp"], moment))
    if claims["iat"] - skew > moment:
        raise TokenNotYetValid("issued at %d, now %d" % (claims["iat"], moment))

    if revocations is not None and revocations.is_revoked(claims["jti"], now=moment):
        raise TokenRevoked("jti %s is revoked" % claims["jti"])

    return claims
