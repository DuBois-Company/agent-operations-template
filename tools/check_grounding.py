#!/usr/bin/env python3
"""Knowledge-graph harness: the delegation guard. Warns, never blocks.

    Run from the repo root:  python tools/check_grounding.py

Wired as a PreToolUse hook on delegation (see .claude/settings.json), it fires
before an agent is dispatched and asks one question: does example/PROGRESS.md
record a grounding entry dated today? If not, it prints a warning.

It ALWAYS exits 0. That is deliberate and is the whole design of this guard.
Grounding is a habit, not a gate; a hook that blocks delegation on a missing
line teaches people to delete the hook. A warning that costs nothing to read
and cannot stop work is the version that survives contact with a deadline.
Compare validate.py, which exits nonzero and is meant to: it checks facts,
this checks a practice.

IN THIS TEMPLATE THE WARNING IS EXPECTED TO FIRE. The example project's
PROGRESS.md is dated the day the example was written, so unless you happen to
run this on that date the guard will report no entry for today -- which is the
point: it demonstrates the guard working rather than a guard that never speaks.
The exit code stays 0, so CI stays green either way.

Everything is resolved relative to this file: tools/ -> repo root -> example/.

FORMAT COUPLINGS (contracts -- both sides must change together)
  example/PROGRESS.md  a grounding entry is a line carrying today's date in
                       ISO form followed by the grounding marker: the date,
                       a space, an em dash (a plain hyphen is also accepted),
                       a space, then "Grounding". validate.py enforces the
                       em-dash form inside "## Session notes"; this script
                       accepts either so a hyphen typo warns about the date
                       rather than about punctuation.

Dependencies: the Python standard library.
"""

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRESS = ROOT / "example" / "PROGRESS.md"

EM_DASH = "—"
ADVICE = ("Ground before delegating: read example/graph.yaml and "
          "example/PROGRESS.md in full, then record the grounding entry.")


def say(msg):
    """Print without ever dying on a console that cannot encode a character."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(str(msg).encode("ascii", "replace").decode("ascii"))


def main():
    today = datetime.date.today().isoformat()
    try:
        text = PROGRESS.read_text(encoding="utf-8")
    except FileNotFoundError:
        say("WARNING: example/PROGRESS.md is missing. " + ADVICE)
        return 0
    except OSError as exc:
        say("WARNING: example/PROGRESS.md could not be read (%s). %s" % (exc, ADVICE))
        return 0

    marks = ("%s %s Grounding" % (today, EM_DASH), "%s - Grounding" % today)
    if not any(mark in text for mark in marks):
        say("WARNING: example/PROGRESS.md records no grounding entry dated %s. %s"
            % (today, ADVICE))
    return 0


if __name__ == "__main__":
    # Always 0. See the module docstring: this guard warns, it does not block.
    sys.exit(main())
