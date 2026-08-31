"""The revocation list verify_token consults (node T9).

A logged-out or compromised session has to stop working before its 24 hour
expiry runs out, so verify_token takes an optional revocation list and
rejects any token whose `jti` sits on it.

The list is in-memory and per-process: enough for the example, and honest
about it. Entries carry the revoked token's own expiry, so the list can be
swept instead of growing without bound -- once a token has expired, the
expiry check rejects it anyway and the entry is dead weight.

Escalation note: the first implementation of this module let a revoked token
through inside the clock-skew window. Two mistakes, one symptom -- is_revoked()
compared against the sweep clock rather than the caller's moment, and entries
were dropped the instant the token's own `exp` passed, which is exactly when a
lagging verifier is still accepting it. The escalated attempt threaded `now`
through from verify_token and gave the list a retention grace, which is why
both appear below with the reason attached.
"""

import time


class RevocationList(object):
    """Set of revoked token ids, each remembered past its own expiry.

    `grace_seconds` should be the clock-skew tolerance the verifiers run
    with: a token is acceptable until `exp + skew`, so a revocation that
    stops covering it at `exp` leaves a window where the token is live and
    the list has forgotten it.
    """

    __slots__ = ("_entries", "_clock", "_grace")

    def __init__(self, clock=None, grace_seconds=0):
        if not isinstance(grace_seconds, int) or isinstance(grace_seconds, bool):
            raise ValueError("grace_seconds must be an integer")
        if grace_seconds < 0:
            raise ValueError("grace_seconds must not be negative")
        self._entries = {}
        self._clock = clock or time.time
        self._grace = grace_seconds

    def _now(self, now):
        return int(self._clock() if now is None else now)

    def revoke(self, jti, expires_at):
        """Mark one token id revoked until `expires_at` plus the grace."""
        if not jti or not isinstance(jti, str):
            raise ValueError("jti must be a non-empty string")
        if not isinstance(expires_at, int) or isinstance(expires_at, bool):
            raise ValueError("expires_at must be an integer epoch second")
        held_until = expires_at + self._grace
        # Keep the later expiry if the same id is revoked twice: dropping the
        # entry early is the one mistake that would un-revoke a session.
        previous = self._entries.get(jti)
        if previous is None or held_until > previous:
            self._entries[jti] = held_until
        return self._entries[jti]

    def revoke_claims(self, claims):
        """Revoke the token these verified claims came from."""
        return self.revoke(claims["jti"], int(claims["exp"]))

    def is_revoked(self, jti, now=None):
        """True while `jti` is on the list and its own expiry has not passed."""
        expires_at = self._entries.get(jti)
        if expires_at is None:
            return False
        return self._now(now) <= expires_at

    def sweep(self, now=None):
        """Drop entries whose tokens have expired. Returns how many went."""
        moment = self._now(now)
        dead = [jti for jti, expires_at in self._entries.items() if expires_at < moment]
        for jti in dead:
            del self._entries[jti]
        return len(dead)

    def __contains__(self, jti):
        return self.is_revoked(jti)

    def __len__(self):
        return len(self._entries)
