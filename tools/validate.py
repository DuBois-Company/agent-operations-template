#!/usr/bin/env python3
"""Knowledge-graph harness: state validator. This is the repo's test command.

    Run from the repo root:  python tools/validate.py [--quick]

Exit 0 means the example project's recorded state is internally consistent.
Exit 1 means at least one check failed; every failure prints with the node or
file it belongs to. `--quick` prints nothing on success -- that is the mode the
edit hook and the acceptance criteria use -- but failures always print.

Everything is resolved relative to this file: tools/ -> repo root -> example/.
No path in this file is absolute, so the repo works wherever it is cloned.

WHAT IT CHECKS (all against ./example/)
  1. graph.yaml parses. With PyYAML installed the real parser runs; without it
     a reduced structural pass runs instead and says so on stdout. Both paths
     produce the same node records and both exit nonzero on failure.
  2. Top-level keys agents:, nodes:, archived: are all present.
  3. Every node carries an id and a type, and the type is one of
     task, decision, lesson, experiment, budget, artifact.
  4. Every task node's status is one of blocked, ready, running, review, done
     -- a closed vocabulary, so a typo is a failure rather than a new state.
  5. Every task node carries telemetry with all five keys:
     predicted, attempts, escalated, review, spend.
  6. At least one budget node exists, and each budget node carries cap, spent,
     and a status of open or tripped.
  7. archived holds at least one milestone, each milestone holds nodes:, and
     every archived node body is a full body -- it carries id and type, and its
     task bodies face checks 4 and 5 like any other.
  8. PROGRESS.md carries the three required sections, every top-level entry in
     them is dated, and at least one session note carries the grounding marker.
  9. Every node id cited in PROGRESS.md exists in the graph. Citations are
     recognised by the id prefixes the graph actually uses, so prose is safe.
 10. CLAUDE.md and AGENTS.md are byte-identical. Two agent runtimes, one set of
     instructions; drift between them is the bug this catches.
 11. Every done task's executable acceptance criteria actually run. Each is a
     literal command string starting with "python ", executed from the repo
     root via shlex.split; any nonzero exit fails this script. That is the
     design point of the harness: acceptance criteria are exit codes, not
     adjectives, so "done" is a claim the test command can refute.

FORMAT COUPLINGS (contracts -- both sides must change together)
  example/graph.yaml   top-level keys `agents:`, `nodes:`, `archived:`;
                       node keys `id:`, `type:`, `status:`, `acceptance:`,
                       `telemetry:` with the five keys above; budget nodes with
                       `cap:`, `spent:`, `status:`; each archived milestone
                       holding full node bodies under `nodes:`.
  example/PROGRESS.md  headings exactly "## Rationale", "## Verification log",
                       "## Session notes"; every top-level entry beginning
                       "- YYYY-MM-DD"; at least one session note containing the
                       grounding marker (em dash, space, "Grounding:").
  example/CLAUDE.md    byte-identical to example/AGENTS.md.
  acceptance criteria  executable ones are literal strings starting "python "
                       and exit 0 when run from the repo root.

RECURSION GUARD
  An acceptance criterion may legitimately be `python tools/validate.py
  --quick`, so this script sets KG_HARNESS_NO_EXEC=1 in the environment of
  every command it runs. When that variable is set, step 11 is skipped and
  says so; the nested run still performs checks 1-10. Without the guard the
  harness would recurse forever.

Dependencies: the Python standard library. PyYAML is used when importable and
is never required.
"""

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "example"
GRAPH = EXAMPLE / "graph.yaml"
PROGRESS = EXAMPLE / "PROGRESS.md"
CLAUDE_MD = EXAMPLE / "CLAUDE.md"
AGENTS_MD = EXAMPLE / "AGENTS.md"

NODE_TYPES = {"task", "decision", "lesson", "experiment", "budget", "artifact"}
TASK_STATUSES = {"blocked", "ready", "running", "review", "done"}
TELEMETRY_KEYS = ("predicted", "attempts", "escalated", "review", "spend")
BUDGET_STATUSES = {"open", "tripped"}
BUDGET_FIELDS = ("cap", "spent", "status")

PROGRESS_SECTIONS = ("## Rationale", "## Verification log", "## Session notes")
SESSION_SECTION = "## Session notes"
GROUNDING_MARK = "— Grounding:"          # em dash, space, "Grounding:"
GROUNDING_LABEL = 'the grounding marker (em dash + " Grounding:")'
ENTRY_DATE_RE = re.compile(r"^- \d{4}-\d{2}-\d{2}\b")

NO_EXEC_ENV = "KG_HARNESS_NO_EXEC"
COMMAND_PREFIX = "python "
COMMAND_TIMEOUT = 300

QUIET = "--quick" in sys.argv[1:]
errors = []


def say(msg):
    """Print without ever dying on a console that cannot encode a character."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(str(msg).encode("ascii", "replace").decode("ascii"))


def note(msg):
    if not QUIET:
        say(msg)


def fail(msg):
    errors.append(msg)


# --------------------------------------------------------------------------
# Parsing. Two paths, one output shape: a list of node records plus metadata
# about the top level. Everything downstream is written against that shape,
# so the checks do not care which path produced the records.
# --------------------------------------------------------------------------

def new_record(node_id, node_type, milestone=None):
    return {
        "id": node_id,
        "type": node_type,
        "status": None,
        "has_telemetry": False,
        "telemetry_keys": set(),
        "acceptance": [],
        "budget_fields": {},
        "milestone": milestone,
    }


def iter_bodies(container):
    """Yield node bodies from either a YAML list or an id-keyed mapping."""
    if isinstance(container, list):
        for body in container:
            if isinstance(body, dict):
                yield body
    elif isinstance(container, dict):
        for key, body in container.items():
            if isinstance(body, dict):
                merged = dict(body)
                merged.setdefault("id", key)
                yield merged


def record_from_body(body, milestone=None):
    node_id = body.get("id")
    node_id = str(node_id) if node_id is not None else None
    node_type = body.get("type")
    node_type = str(node_type) if node_type is not None else None
    rec = new_record(node_id, node_type, milestone)

    status = body.get("status")
    if status is not None:
        rec["status"] = str(status).strip()

    telemetry = body.get("telemetry")
    if isinstance(telemetry, dict):
        rec["has_telemetry"] = True
        rec["telemetry_keys"] = {str(k) for k in telemetry}

    acceptance = body.get("acceptance")
    if isinstance(acceptance, str):
        acceptance = [acceptance]
    if isinstance(acceptance, list):
        rec["acceptance"] = [str(a) for a in acceptance]

    for field in BUDGET_FIELDS:
        if field in body and body[field] is not None:
            rec["budget_fields"][field] = str(body[field]).strip()

    return rec


def parse_strict(text):
    """PyYAML path. Returns (records, meta) or raises."""
    import yaml  # imported lazily: absence selects the fallback path

    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("graph.yaml did not parse to a mapping")

    records = []
    for body in iter_bodies(data.get("nodes")):
        records.append(record_from_body(body))

    milestones = []
    archived = data.get("archived")
    if isinstance(archived, dict):
        for name, milestone in archived.items():
            milestones.append(str(name))
            if not isinstance(milestone, dict) or "nodes" not in milestone:
                fail("graph.yaml: archived milestone '%s' holds no nodes:" % name)
                continue
            bodies = list(iter_bodies(milestone.get("nodes")))
            if not bodies:
                fail("graph.yaml: archived milestone '%s' has an empty nodes: block" % name)
            for body in bodies:
                records.append(record_from_body(body, milestone=str(name)))

    meta = {
        "mode": "yaml",
        "has_agents": bool(data.get("agents")),
        "has_nodes": data.get("nodes") is not None,
        "has_archived": isinstance(archived, dict) and bool(archived),
        "milestones": milestones,
    }
    return records, meta


TOP_KEY_RE = re.compile(r"^([A-Za-z_][\w.-]*):", re.M)
ITEM_START_RE = re.compile(r"^([ \t]*)-[ \t]*\{?[ \t]*[A-Za-z_][\w.-]*:", re.M)
ID_RE = re.compile(r"(?<![\w-])id:[ \t]*([^\s,#}]+)")
NESTED_KEY_RE = re.compile(r"^([ \t]+)([A-Za-z_][\w.-]*):", re.M)


def indent_of(line):
    stripped = line.lstrip(" \t")
    return len(line[: len(line) - len(stripped)].expandtabs(4))


def top_blocks(text):
    """Map every column-0 key to the raw text of its block."""
    blocks = {}
    marks = list(TOP_KEY_RE.finditer(text))
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        blocks[mark.group(1)] = text[mark.end():end]
    return blocks


def sub_block(chunk, key):
    """Raw text of `key:` inside one node chunk: the rest of the key's own line
    plus every following line indented deeper than the key."""
    mark = re.search(r"^([ \t]*)%s:(.*)$" % re.escape(key), chunk, re.M)
    if not mark:
        return None
    base = len(mark.group(1).expandtabs(4))
    parts = [mark.group(2)]
    for line in chunk[mark.end():].splitlines():
        if not line.strip():
            continue
        if indent_of(line) <= base:
            break
        parts.append(line)
    return "\n".join(parts)


def clean_item(text):
    """One sequence item, unquoted and stripped of a trailing YAML comment."""
    item = text.strip()
    if item[:1] in ("\"", "'"):
        quote = item[0]
        end = item.find(quote, 1)
        if end > 0:
            return item[1:end]
        return item.strip(quote).strip()
    if " #" in item:
        item = item.split(" #", 1)[0]
    return item.strip().rstrip(",").strip()


def split_flow(text):
    """Split a flow sequence body on its top-level commas, honouring quotes."""
    items, buf, depth, quote = [], [], 0, None
    for char in text:
        if quote:
            buf.append(char)
            if char == quote:
                quote = None
            continue
        if char in ("\"", "'"):
            quote = char
            buf.append(char)
            continue
        if char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        if char == "," and depth == 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(char)
    if buf:
        items.append("".join(buf))
    return items


def sequence_items(raw):
    """Items of a YAML sequence written either flow ([a, b]) or block (- a)."""
    if raw is None:
        return []
    body = raw.strip()
    if body.startswith("["):
        body = body[1:]
        if body.endswith("]"):
            body = body[:-1]
        return [i for i in (clean_item(part) for part in split_flow(body)) if i]
    items = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(clean_item(stripped[2:]))
    return [i for i in items if i]


def split_node_chunks(block):
    """Split a nodes: block into one raw chunk per sequence entry.

    Entries are found by indentation, not by key order: only `- ` items at the
    sequence's own (shallowest) indent open a node, so a nested list inside a
    node body cannot be mistaken for the next node, and a body that happens to
    put some key before id: is still read correctly.
    """
    marks = list(ITEM_START_RE.finditer(block))
    if not marks:
        return []
    base = min(len(m.group(1).expandtabs(4)) for m in marks)
    heads = [m for m in marks if len(m.group(1).expandtabs(4)) == base]
    chunks = []
    for i, mark in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(block)
        chunk = block[mark.start():end]
        found = ID_RE.search(chunk)
        node_id = found.group(1).strip().strip("\"'") if found else None
        chunks.append((node_id, chunk))
    return chunks


def record_from_chunk(node_id, chunk, milestone=None):
    type_mark = re.search(r"(?<![\w-])type:[ \t]*([A-Za-z_]+)", chunk)
    rec = new_record(node_id, type_mark.group(1) if type_mark else None, milestone)

    status_mark = re.search(r"(?<![\w-])status:[ \t]*([^\s,#}]+)", chunk)
    if status_mark:
        rec["status"] = status_mark.group(1).strip().strip("\"'")

    telemetry = sub_block(chunk, "telemetry")
    if telemetry is not None:
        rec["has_telemetry"] = True
        for key in TELEMETRY_KEYS:
            if re.search(r"(?<![\w-])%s[ \t]*:" % key, telemetry):
                rec["telemetry_keys"].add(key)

    rec["acceptance"] = sequence_items(sub_block(chunk, "acceptance"))

    for field in BUDGET_FIELDS:
        found = re.search(r"(?<![\w-])%s:[ \t]*([^\s,#}]+)" % field, chunk)
        if found:
            rec["budget_fields"][field] = found.group(1).strip().strip("\"'")

    return rec


def parse_structural(text):
    """No-PyYAML path: the same records, read structurally from the text.

    It is deliberately reduced -- it trusts indentation and key names rather
    than a real parser -- but it exercises every check below, so a repo with a
    bare interpreter still gets a real exit code.
    """
    blocks = top_blocks(text)
    records = []
    for node_id, chunk in split_node_chunks(blocks.get("nodes", "")):
        records.append(record_from_chunk(node_id, chunk))

    milestones = []
    archived_block = blocks.get("archived", "")
    if archived_block.strip():
        marks = [m for m in NESTED_KEY_RE.finditer(archived_block)]
        if marks:
            top = min(len(m.group(1).expandtabs(4)) for m in marks)
            heads = [m for m in marks if len(m.group(1).expandtabs(4)) == top]
            for i, mark in enumerate(heads):
                end = heads[i + 1].start() if i + 1 < len(heads) else len(archived_block)
                name = mark.group(2)
                body = archived_block[mark.end():end]
                milestones.append(name)
                nodes_text = sub_block(body, "nodes")
                if nodes_text is None:
                    fail("graph.yaml: archived milestone '%s' holds no nodes:" % name)
                    continue
                chunks = split_node_chunks(nodes_text)
                if not chunks:
                    fail("graph.yaml: archived milestone '%s' has an empty nodes: block" % name)
                for node_id, chunk in chunks:
                    records.append(record_from_chunk(node_id, chunk, milestone=name))

    meta = {
        "mode": "structural",
        "has_agents": bool(blocks.get("agents", "").strip()),
        "has_nodes": "nodes" in blocks,
        "has_archived": bool(archived_block.strip()),
        "milestones": milestones,
    }
    return records, meta


def load_graph():
    if not GRAPH.exists():
        fail("example/graph.yaml is missing")
        return [], {"mode": "none", "milestones": []}
    text = GRAPH.read_text(encoding="utf-8")
    if not text.strip():
        fail("example/graph.yaml is empty")
        return [], {"mode": "none", "milestones": []}
    try:
        records, meta = parse_strict(text)
        note("graph.yaml parsed with PyYAML")
        return records, meta
    except ImportError:
        note("graph.yaml: PyYAML not installed -- running the reduced structural checks")
    except Exception as exc:
        fail("example/graph.yaml did not parse: %s" % exc)
        return [], {"mode": "none", "milestones": []}
    try:
        records, meta = parse_structural(text)
        return records, meta
    except Exception as exc:
        fail("example/graph.yaml failed the structural read: %s" % exc)
        return [], {"mode": "none", "milestones": []}


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_graph(records, meta):
    start = len(errors)
    if meta.get("mode") == "none":
        return          # the file itself failed to load; that is the finding
    for key, present in (("agents", meta.get("has_agents")),
                         ("nodes", meta.get("has_nodes")),
                         ("archived", meta.get("has_archived"))):
        if not present:
            fail("example/graph.yaml has no %s: block" % key)

    if not records:
        if not errors:
            fail("example/graph.yaml holds no nodes")
        return

    seen = {}
    tasks = budgets = 0
    for rec in records:
        where = rec["id"] or "<node with no id>"
        if rec["milestone"]:
            where = "%s (archived: %s)" % (where, rec["milestone"])

        if not rec["id"]:
            fail("graph.yaml: a node body carries no id")
            continue
        if rec["milestone"] is None:
            if rec["id"] in seen:
                fail("graph.yaml: duplicate node id %s" % rec["id"])
            seen[rec["id"]] = True

        if not rec["type"]:
            fail("%s: node body carries no type" % where)
            continue
        if rec["type"] not in NODE_TYPES:
            fail("%s: type '%s' is outside the vocabulary (%s)"
                 % (where, rec["type"], ", ".join(sorted(NODE_TYPES))))

        if rec["type"] == "task":
            tasks += 1
            if not rec["status"]:
                fail("%s: task carries no status" % where)
            elif rec["status"] not in TASK_STATUSES:
                fail("%s: status '%s' is outside the closed vocabulary (%s)"
                     % (where, rec["status"], "|".join(sorted(TASK_STATUSES))))
            if not rec["has_telemetry"]:
                fail("%s: task carries no telemetry block" % where)
            else:
                missing = [k for k in TELEMETRY_KEYS if k not in rec["telemetry_keys"]]
                if missing:
                    fail("%s: telemetry is missing %s" % (where, ", ".join(missing)))

        if rec["type"] == "budget":
            budgets += 1
            missing = [f for f in BUDGET_FIELDS if f not in rec["budget_fields"]]
            if missing:
                fail("%s: budget node is missing %s" % (where, ", ".join(missing)))
            status = rec["budget_fields"].get("status")
            if status and status not in BUDGET_STATUSES:
                fail("%s: budget status '%s' is outside open|tripped" % (where, status))

    if budgets == 0:
        fail("example/graph.yaml holds no budget node -- spend has nowhere to land")
    if not meta.get("milestones"):
        if meta.get("has_archived"):
            fail("example/graph.yaml: archived: holds no milestone")
    if len(errors) == start:
        note("graph OK: %d node(s) -- %d task(s), %d budget(s), %d archived milestone(s)"
             % (len(records), tasks, budgets, len(meta.get("milestones") or [])))


def split_sections(text):
    sections = {}
    marks = list(re.finditer(r"^##[ \t]+.*$", text, re.M))
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        sections[mark.group(0).strip()] = text[mark.end():end]
    return sections


def check_progress(records):
    start = len(errors)
    if not PROGRESS.exists():
        fail("example/PROGRESS.md is missing")
        return
    text = PROGRESS.read_text(encoding="utf-8")
    sections = split_sections(text)

    for heading in PROGRESS_SECTIONS:
        if heading not in sections:
            fail('example/PROGRESS.md has no "%s" section' % heading)

    undated = []
    for heading in PROGRESS_SECTIONS:
        body = sections.get(heading)
        if body is None:
            continue
        for line in body.splitlines():
            if line.startswith("- ") and not ENTRY_DATE_RE.match(line):
                undated.append("%s: %s" % (heading, line.strip()[:70]))
    if undated:
        subject = "1 entry does not start" if len(undated) == 1 \
            else "%d entries do not start" % len(undated)
        fail("example/PROGRESS.md: %s '- YYYY-MM-DD': %s"
             % (subject, "; ".join(undated[:5]) + (" ..." if len(undated) > 5 else "")))

    session = sections.get(SESSION_SECTION)
    if session is not None and GROUNDING_MARK not in session:
        if GROUNDING_MARK in text:
            fail('example/PROGRESS.md carries %s but not under "%s"'
                 % (GROUNDING_LABEL, SESSION_SECTION))
        else:
            fail("example/PROGRESS.md: no session note carries %s" % GROUNDING_LABEL)

    # Citation check. Only tokens shaped like the ids this graph actually uses
    # are treated as citations, so ordinary prose cannot trip the check.
    ids = {rec["id"] for rec in records if rec["id"]}
    prefixes = sorted({m.group(1) for m in
                       (re.match(r"^([A-Za-z]+)\d", i) for i in ids) if m},
                      key=len, reverse=True)
    if prefixes:
        pattern = re.compile(r"\b(?:%s)\d+[a-z]?\b" % "|".join(prefixes))
        unknown = sorted({t for t in pattern.findall(text) if t not in ids})
        if unknown:
            fail("example/PROGRESS.md cites %d node id(s) absent from the graph: %s"
                 % (len(unknown), ", ".join(unknown[:10]) + (" ..." if len(unknown) > 10 else "")))
    if len(errors) == start:
        note("PROGRESS.md OK: %d section(s), every entry dated, citations resolve"
             % len(sections))


def check_instruction_pair():
    missing = [p.name for p in (CLAUDE_MD, AGENTS_MD) if not p.exists()]
    if missing:
        fail("example/: %s missing -- the two runtimes must ship the same instructions"
             % ", ".join(missing))
        return
    if CLAUDE_MD.read_bytes() != AGENTS_MD.read_bytes():
        fail("example/CLAUDE.md and example/AGENTS.md differ -- they must be byte-identical")
        return
    note("CLAUDE.md and AGENTS.md are byte-identical")


def check_acceptance(records):
    """Run every done task's executable acceptance criteria from the repo root."""
    pending = []
    for rec in records:
        if rec["type"] != "task" or rec["status"] != "done":
            continue
        for criterion in rec["acceptance"]:
            command = criterion.strip()
            if command.startswith(COMMAND_PREFIX):
                pending.append((rec, command))

    if not pending:
        note("acceptance: no executable criteria on done tasks")
        return

    if os.environ.get(NO_EXEC_ENV) == "1":
        note("acceptance: %d command(s) skipped -- nested harness run (%s is set)"
             % (len(pending), NO_EXEC_ENV))
        return

    env = dict(os.environ)
    env[NO_EXEC_ENV] = "1"
    passed = 0
    for rec, command in pending:
        where = rec["id"] or "<node with no id>"
        argv = shlex.split(command)
        if argv and argv[0] in ("python", "python3"):
            argv[0] = sys.executable          # survives a PATH without `python`
        try:
            proc = subprocess.run(argv, cwd=str(ROOT), env=env,
                                  capture_output=True, text=True,
                                  timeout=COMMAND_TIMEOUT)
        except subprocess.TimeoutExpired:
            fail("%s: acceptance command timed out after %ds: %s"
                 % (where, COMMAND_TIMEOUT, command))
            continue
        except OSError as exc:
            fail("%s: acceptance command could not run (%s): %s" % (where, exc, command))
            continue
        if proc.returncode != 0:
            detail = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
            tail = " | ".join(line.strip() for line in detail[-3:]) if detail else "no output"
            fail("%s: acceptance command exited %d: %s\n      %s"
                 % (where, proc.returncode, command, tail))
        else:
            passed += 1
    if passed == len(pending):
        note("acceptance OK: %d command(s) exited 0" % passed)


def main():
    if not EXAMPLE.is_dir():
        fail("example/ is missing -- nothing to validate")
    else:
        records, meta = load_graph()
        check_graph(records, meta)
        check_progress(records)
        check_instruction_pair()
        check_acceptance(records)

    if errors:
        say("VALIDATE FAIL:")
        for err in errors:
            say("  - %s" % err)
        return 1
    note("VALIDATE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
