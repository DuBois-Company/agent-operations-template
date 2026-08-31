#!/usr/bin/env python3
"""Knowledge-graph harness: structural lint. This is the repo's lint command.

    Run from the repo root:  python tools/lint.py

Exit 0 means the example project's files are structurally sound. Exit 1 means
at least one file is missing, empty, or unparseable, and each one prints.

This is the cheap check. It answers "can the control plane be read at all?" and
nothing more; validate.py is the one that reads what it says. Keeping the two
separate means a broken file gives a short, obvious failure instead of a long
one buried in semantic complaints.

Everything is resolved relative to this file: tools/ -> repo root -> example/.

WHAT IT CHECKS (all against ./example/)
  1. graph.yaml exists and is not empty.
  2. graph.yaml carries the three markers that make it a control plane at all:
     `agents:`, `nodes:`, and at least one `type: budget`. A graph with no
     budget node has nowhere to record spend, so it is malformed by definition.
  3. Every .yaml and .yml file under example/ parses. With PyYAML installed the
     real parser runs; without it a reduced structural read runs instead and
     says so on stdout -- it rejects tab indentation, which YAML forbids, and
     files with no top-level key. Both paths exit nonzero on failure.
  4. Every .json file under example/, if any, parses.

FORMAT COUPLINGS (contracts -- both sides must change together)
  example/graph.yaml   must contain the literal substrings `agents:`, `nodes:`,
                       and `type: budget`.
  file layout          the harness lints example/ and nothing else, so a new
                       data file only comes under lint by living there.

Dependencies: the Python standard library. PyYAML is used when importable and
is never required.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "example"
GRAPH = EXAMPLE / "graph.yaml"

# (what a reader would call it, how it is actually recognised). The patterns are
# anchored so that a near miss -- `type: budgetary`, or an `agents:` key nested
# inside some other block -- fails instead of passing on a substring.
REQUIRED_MARKERS = (
    ("agents:", re.compile(r"^agents:", re.M)),
    ("nodes:", re.compile(r"^nodes:", re.M)),
    ("type: budget", re.compile(r"type:[ \t]*budget\b")),
)

errors = []


def say(msg):
    """Print without ever dying on a console that cannot encode a character."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(str(msg).encode("ascii", "replace").decode("ascii"))


def rel(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def load_yaml_module():
    try:
        import yaml
        return yaml
    except ImportError:
        return None


def structural_yaml_problems(text):
    """The reduced read used when PyYAML is absent.

    It cannot validate YAML, so it checks the two things that are cheap and
    unambiguous: indentation never uses tabs (YAML forbids them outright), and
    the file opens at least one top-level key.
    """
    problems = []
    if not text.strip():
        problems.append("file is empty")
        return problems
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip(" ")
        if stripped.startswith("\t") or (line[:1] == "\t"):
            problems.append("line %d indents with a tab (YAML forbids tabs)" % number)
            break
    if not re.search(r"^[A-Za-z_][\w.-]*:", text, re.M):
        problems.append("no top-level key found")
    return problems


def main():
    if not EXAMPLE.is_dir():
        say("LINT FAIL:")
        say("  - example/ is missing -- nothing to lint")
        return 1

    if not GRAPH.exists():
        errors.append("example/graph.yaml is missing")
    elif GRAPH.stat().st_size == 0:
        errors.append("example/graph.yaml is empty")
    else:
        text = GRAPH.read_text(encoding="utf-8")
        if not text.strip():
            errors.append("example/graph.yaml holds only whitespace")
        for label, pattern in REQUIRED_MARKERS:
            if not pattern.search(text):
                errors.append("example/graph.yaml lacks '%s'" % label)

    yaml = load_yaml_module()
    if yaml is None:
        say("PyYAML not installed -- running the reduced structural checks")

    yaml_files = sorted(
        p for p in EXAMPLE.rglob("*")
        if p.is_file() and p.suffix.lower() in (".yaml", ".yml")
    )
    for path in yaml_files:
        text = path.read_text(encoding="utf-8")
        if yaml is None:
            for problem in structural_yaml_problems(text):
                errors.append("%s: %s" % (rel(path), problem))
        else:
            try:
                yaml.safe_load(text)
            except Exception as exc:
                errors.append("%s: does not parse (%s)" % (rel(path), exc))

    json_files = sorted(p for p in EXAMPLE.rglob("*")
                        if p.is_file() and p.suffix.lower() == ".json")
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append("%s: bad JSON (%s)" % (rel(path), exc))

    if errors:
        say("LINT FAIL:")
        for err in errors:
            say("  - %s" % err)
        return 1
    say("LINT PASS: %d YAML file(s), %d JSON file(s)" % (len(yaml_files), len(json_files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
