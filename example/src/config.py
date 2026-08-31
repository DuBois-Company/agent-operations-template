"""Settings for the example auth service.

Node T7 moved these constants out of auth.py so a deployment can be
re-pointed without editing the signing code. Decision D1 in graph.yaml fixes
the session lifetime at 24 hours; DEFAULT_TTL_SECONDS is that decision
expressed once, and nothing else in the service is allowed to hard-code it.

Every setting can be overridden from the environment with the prefix below,
which is how the test suite exercises non-default values without touching
process state it does not own.
"""

import os

# D1: sessions use JWT-shaped tokens with a 24 hour expiry.
DEFAULT_TTL_SECONDS = 24 * 60 * 60

# The `iss` claim every token carries and every verify checks.
DEFAULT_ISSUER = "example-web-app"

# T8: how far a verifying clock may sit behind the issuing clock and still
# accept a token that has only just expired.
DEFAULT_CLOCK_SKEW_SECONDS = 60

# Placeholder only. A real deployment sets EXAMPLE_AUTH_SECRET; load_config()
# refuses to start with this value when EXAMPLE_AUTH_STRICT is set.
DEV_SECRET = "dev-secret-not-for-deployment"

ENV_PREFIX = "EXAMPLE_AUTH_"


class ConfigError(ValueError):
    """A setting was present but unusable. Raised at load, never at verify."""


class AuthConfig(object):
    """Immutable settings bundle handed to every auth call.

    Immutable on purpose: the middleware holds one instance for the life of
    a process, and a token issued under one lifetime must never be verified
    under another.
    """

    __slots__ = ("secret", "ttl_seconds", "issuer", "clock_skew_seconds")

    def __init__(self, secret=DEV_SECRET, ttl_seconds=DEFAULT_TTL_SECONDS,
                 issuer=DEFAULT_ISSUER,
                 clock_skew_seconds=DEFAULT_CLOCK_SKEW_SECONDS):
        if not secret:
            raise ConfigError("secret must not be empty")
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool):
            raise ConfigError("ttl_seconds must be an integer")
        if ttl_seconds <= 0:
            raise ConfigError("ttl_seconds must be positive")
        if not isinstance(clock_skew_seconds, int) or isinstance(clock_skew_seconds, bool):
            raise ConfigError("clock_skew_seconds must be an integer")
        if clock_skew_seconds < 0:
            raise ConfigError("clock_skew_seconds must not be negative")
        if not issuer:
            raise ConfigError("issuer must not be empty")
        object.__setattr__(self, "secret", secret)
        object.__setattr__(self, "ttl_seconds", ttl_seconds)
        object.__setattr__(self, "issuer", issuer)
        object.__setattr__(self, "clock_skew_seconds", clock_skew_seconds)

    def __setattr__(self, name, value):
        raise AttributeError("AuthConfig is immutable; build a new one instead")

    def replace(self, **changes):
        """Return a new config with some fields changed. Validation reruns."""
        fields = {
            "secret": self.secret,
            "ttl_seconds": self.ttl_seconds,
            "issuer": self.issuer,
            "clock_skew_seconds": self.clock_skew_seconds,
        }
        unknown = sorted(set(changes) - set(fields))
        if unknown:
            raise ConfigError("unknown setting(s): %s" % ", ".join(unknown))
        fields.update(changes)
        return AuthConfig(**fields)

    def __eq__(self, other):
        if not isinstance(other, AuthConfig):
            return NotImplemented
        return (self.secret == other.secret
                and self.ttl_seconds == other.ttl_seconds
                and self.issuer == other.issuer
                and self.clock_skew_seconds == other.clock_skew_seconds)

    def __repr__(self):
        # The secret is never rendered: this repr shows up in logs.
        return ("AuthConfig(secret=<redacted>, ttl_seconds=%d, issuer=%r, "
                "clock_skew_seconds=%d)"
                % (self.ttl_seconds, self.issuer, self.clock_skew_seconds))


def _read_int(env, name, default):
    raw = env.get(ENV_PREFIX + name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        raise ConfigError("%s%s is not an integer: %r" % (ENV_PREFIX, name, raw))


def load_config(env=None):
    """Build an AuthConfig from a mapping, defaulting to the process env.

    Passing `env` explicitly is what the tests do; production passes nothing.
    """
    env = os.environ if env is None else env
    secret = env.get(ENV_PREFIX + "SECRET") or DEV_SECRET
    if secret == DEV_SECRET and env.get(ENV_PREFIX + "STRICT"):
        raise ConfigError(
            "%sSTRICT is set but %sSECRET is not; refusing the placeholder secret"
            % (ENV_PREFIX, ENV_PREFIX))
    return AuthConfig(
        secret=secret,
        ttl_seconds=_read_int(env, "TTL_SECONDS", DEFAULT_TTL_SECONDS),
        issuer=env.get(ENV_PREFIX + "ISSUER") or DEFAULT_ISSUER,
        clock_skew_seconds=_read_int(env, "CLOCK_SKEW_SECONDS",
                                     DEFAULT_CLOCK_SKEW_SECONDS),
    )
