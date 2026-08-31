<!-- banner: marketing integration inserts the picture element here -->

# agent-operations-template

A runnable template for orchestrating multi-agent work on a shared knowledge graph.

[![CI](https://github.com/DuBois-Company/agent-operations-template/actions/workflows/ci.yml/badge.svg)](https://github.com/DuBois-Company/agent-operations-template/actions/workflows/ci.yml)

## What This Is

agent-operations-template is a complete, runnable template for orchestrating multi-agent work on a shared knowledge graph. It carries four things, each checked against the others rather than merely asserted: the standard itself, the orchestration block that turns a project's memory into a graph instead of a list; a harness, three scripts that turn a task's acceptance criteria into exit codes instead of adjectives; the control-plane file schemas, the shapes of the shared coordination files a team of projects reads and writes; and a synthetic worked example, a fourteen-task auth-service graph caught at a real mid-project state, with a source tree and a test suite its own acceptance criteria run against.

The DuBois Company publishes this repository as a companion to its implementer's guide, [agent-operations-handbook](https://github.com/DuBois-Company/agent-operations-handbook), which walks through applying the standard by hand. This repository is the standard's own text, plus the tooling that checks a project is actually following it.

## Who It Is For

Anyone running more than one agent against a shared body of work across more than one session: a team using Claude Code or Cowork to delegate implementation and prose to separate models, a solo builder who wants acceptance criteria that fail loudly instead of quietly, or anyone who has watched a project's recorded state drift away from its own instructions and wants a structure that catches the drift instead of hoping someone notices it.

## Five-Minute Quickstart

1. **Copy the block.** Open `standard/orchestration-block.md` and copy the fenced block under "The block, repository-surface rendering" into your project's `CLAUDE.md` and `AGENTS.md`, verbatim. Replace `<control-plane>/` with the path to your own shared coordination folder, everywhere it appears.
2. **Run the initializer checklist.** The block's "Initializer session" section is a checklist, not prose: verify your global instructions carry the standard, write the project's instruction files, register the project in your registry, scaffold `graph.yaml` and `PROGRESS.md`, build the harness, install the hooks, and prove every check runs before any feature work starts.
3. **Scaffold from `example/`.** Copy the shapes in `example/graph.yaml` and `example/PROGRESS.md`, the agent roster, the node types, the telemetry keys, the three `PROGRESS.md` sections, and replace the auth-service content with your own domain.
4. **Run the three tools.** From the repository root: `python tools/lint.py`, `python tools/validate.py`, `python tools/check_grounding.py`. All three exit 0 against this repository's own `example/` as shipped; run them again once you have replaced `example/` with your own project to confirm your files hold the same shapes.

## Contents

```
agent-operations-template/
├── standard/
│   ├── orchestration-block.md     the standard itself: the block, its initializer session, its scheduled gardener, and the surface-rendering deltas
│   └── control-plane-schemas.md   the shapes of ledger.md, registry.md, backlog.md, and Playbooks/, plus the one-writer table and the archive rule
├── tools/
│   ├── lint.py                    the structural check: can the control plane be read at all
│   ├── validate.py                the state validator: does the recorded state hold, and does a "done" task's acceptance criteria actually run
│   └── check_grounding.py         the delegation guard: warns, never blocks
├── example/
│   ├── CLAUDE.md                  the block installed for this project, plus its specifics
│   ├── AGENTS.md                  byte-identical to CLAUDE.md, checked by validate.py
│   ├── graph.yaml                 a fourteen-task, mid-project graph for a fictional auth service
│   ├── PROGRESS.md                rationale, verification log, and session notes, keyed to the graph's node ids
│   ├── src/                       the auth service the graph describes: auth.py, config.py, middleware.py, revocation.py
│   └── tests/                     the suite every acceptance criterion in the graph points at
├── .claude/
│   ├── settings.json              hooks: validate.py after every edit, check_grounding.py before delegation
│   └── agents/                    implementer.md (opus, one task node per dispatch) and writer.md (sonnet, prose from verified inputs only)
└── .github/workflows/ci.yml       runs validate.py, lint.py, and check_grounding.py on every push and pull request
```

## The Harness

The harness is three scripts, each doing one job, each resolving its own paths relative to itself so the repository works wherever it is cloned. All three read only `example/`; a template whose own checks fail against its own example would be worse than no template at all.

### `tools/lint.py`, the structural check

The cheap check: can the control plane be read at all. It confirms `example/graph.yaml` exists and is not empty, carries the three markers that make it a control plane, `agents:`, `nodes:`, and at least one `type: budget`, and that every `.yaml`, `.yml`, and `.json` file under `example/` parses. With PyYAML installed the real parser runs; without it a reduced structural read runs instead and says so, rejecting tab indentation and files with no top-level key.

Invocation: `python tools/lint.py`. Exit 0 and a pass line means every check held; exit 1 prints each failure.

Format couplings, the contract both sides have to change together: `example/graph.yaml` must contain the literal substrings `agents:`, `nodes:`, and `type: budget`. The tool lints `example/` and nothing else, so a new data file only comes under lint by living there.

### `tools/validate.py`, the state validator

The repository's test command, and the harness's central claim made concrete: acceptance criteria are exit codes, not adjectives, so "done" is a claim the test command can refute. It checks that `graph.yaml` parses and carries `agents:`, `nodes:`, and `archived:`; that every node carries an id and a type from the closed vocabulary, task, decision, lesson, experiment, budget, artifact; that every task's status is one of blocked, ready, running, review, done; that every task's telemetry carries all five keys, predicted, attempts, escalated, review, spend; that at least one budget node carries cap, spent, and a status of open or tripped; that every archived milestone holds full node bodies rather than bare ids; that `PROGRESS.md` carries its three sections with every entry dated and at least one session note carrying the grounding marker; that every node id cited in `PROGRESS.md` exists in the graph; that `CLAUDE.md` and `AGENTS.md` are byte-identical; and that every done task's executable acceptance criteria, the ones written as literal `python ...` commands, actually exit 0 when run.

Invocation: `python tools/validate.py`, or `python tools/validate.py --quick` to print nothing on success while still printing every failure. A `KG_HARNESS_NO_EXEC` environment variable guards against the recursion an acceptance criterion of `python tools/validate.py --quick` would otherwise cause: when it is set, the nested run skips re-executing acceptance commands and says so, while still performing every other check.

Format couplings: `example/graph.yaml` top-level keys `agents:`, `nodes:`, `archived:`; node keys `id:`, `type:`, `status:`, `acceptance:`, `telemetry:` with its five keys; budget nodes with `cap:`, `spent:`, `status:`; each archived milestone holding full node bodies under `nodes:`. `example/PROGRESS.md` headings exactly `## Rationale`, `## Verification log`, `## Session notes`; every top-level entry beginning `- YYYY-MM-DD`; at least one session note carrying the grounding marker, an em dash, a space, and "Grounding:". `example/CLAUDE.md` byte-identical to `example/AGENTS.md`. Executable acceptance criteria are literal strings starting `python ` that exit 0 when run from the repository root.

### `tools/check_grounding.py`, the delegation guard

The one script that never fails a build. Wired as a pre-delegation hook, it asks one question: does `example/PROGRESS.md` record a grounding entry dated today. If not, it prints a warning naming exactly what to read and what to write. It always exits 0: grounding is a habit the guard reminds you of, not a gate that can be blocked past, since a hook that stops delegation on a missing line teaches people to remove the hook.

Invocation: `python tools/check_grounding.py`.

Format couplings: a grounding entry is a line carrying today's date in ISO form, followed by a space, an em dash, a plain hyphen is also accepted here though not by `validate.py`, a space, and "Grounding". Loosening the punctuation this one way keeps a hyphen typo warning about the missing date rather than about punctuation.

## The Example

`example/` is fiction: a small team's auth service, three months into a project that is nowhere near its first day and nowhere near done. It exists to show what the standard looks like once it has been lived in rather than freshly scaffolded, so every shape the harness checks appears at least once with a real history behind it.

- **An archived milestone with full bodies.** `milestone_2026-04_auth_core` holds six task nodes, T1 through T6, archived with their complete bodies rather than bare ids, because an id-only archive would have destroyed the telemetry two of the graph's lessons rest on.
- **Telemetry with an escalation and a retry.** T9 needed a second attempt after the first left revoked tokens verifying inside the clock-skew window, and was escalated rather than accepted with a known hole; the added cost is recorded on the node and rolled into the budget. T8 needed a second attempt for a different reason, a tolerance subtracted from an expiry instead of added to it, and that pair, together with an earlier retry on T3, is the recorded evidence behind lesson L3.
- **A cleared tainted fact.** D3 arrived by email, a framework advisory about a cookie default. External content is tainted by default, so it was written down tainted the day it arrived and barred from informing dispatch until it was re-derived from the framework's own documentation, pinned by a test, and cleared on the node with a date, a check, and a reviewer.
- **A scored experiment.** X1 tested whether the cheapest tier could implement a config-only task; it won, and the win became candidate lesson L2, which the ledger schema is explicit needs a second, separate project's attestation before it can be promoted to active.
- **A budget with spend.** B1 carries a 400,000 token cap against 265,000 spent, sixty-six percent, with nine of fourteen task nodes done and four still to run: ahead of plan, not tripped, and the note on the node says what the next review does either way.

One more thing worth knowing before you run the tools yourself: `check_grounding.py`'s warning is expected to fire on a fresh clone. `PROGRESS.md`'s session notes are dated inside the fiction's own timeline, so unless you happen to run the guard on that exact date, it will report no grounding entry for today. That is not a broken example. It is the guard doing its one job, on a day the entry genuinely is not there.

## Continuous Integration

`.github/workflows/ci.yml` runs on every push to `main` and every pull request against it. It checks out the repository, sets up Python 3.12, installs PyYAML so the stricter parsing path runs rather than the structural fallback, and then runs the same three commands a contributor would run locally from the repository root: `python tools/validate.py`, `python tools/lint.py`, `python tools/check_grounding.py`. The workflow requests only `contents: read`.

## License

This repository is licensed under the MIT License. See [LICENSE](LICENSE) for the full text.

The DuBois Company name, logos, and brand assets are trademarks of The DuBois Company and are not licensed under the repository license.
