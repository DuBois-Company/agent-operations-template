"""Test suite for the example auth service.

Run the whole thing from the repository root:

    python -m unittest discover -s example/tests -t . -q

Every test pins its own clock. Nothing here reads the wall clock, so a suite
that passes today passes in a year, and an expiry test that fails is failing
about expiry rather than about when it ran.
"""

# One fixed instant, reused everywhere, so every date in a failure message
# points at the same fictional afternoon rather than at "now".
NOW = 1_777_000_000
