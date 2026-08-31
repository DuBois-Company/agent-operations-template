# Control-plane schemas

This file carries the shapes of the shared coordination files the control plane runs on — the lessons ledger, the project registry, the experiment backlog, and the playbook library — together with the one-writer table and the archive rule that make a sync-based shared state safe. Copy each header paragraph verbatim into the top of your own file: the headers are the documentation, so a file that carries its own rules travels with them.

Nothing here is a live entry. Every entry shape below is an illustrative example; fill it with your own projects.

---

## The lessons ledger (`ledger.md`)

The cross-project memory of what works. The file opens with a header paragraph that doubles as its documentation — copy it verbatim:

> Canonical cross-session ledger for the two prompt builders. Lessons come from the retrospectives the knowledge-graph orchestration block runs at consolidation. Active lessons are applied during prompt assembly whenever that block is included. Candidates wait for attestation from a second separate project before promotion, and nothing is promoted without the user's approval. Negative lessons record what was tried and rejected, with evidence, so exploration budget is never spent rediscovering a dead end. Active lessons carry a last-verified date refreshed by control runs, and the gardener proposes demoting any that go stale. Lessons adjust routing, scope, criteria and contract templates, and context slicing; they never move the quality bar. Update this file only through the intake and promotion rules in the two prompt builders.

Entry shape:

```yaml
- lesson: route documentation tasks to the prose-tier agent by default
  domain: coding          # coding | cowork | both
  basis: prose tasks passed review on the first attempt
  attested: [{project: example, date: 2026-08}]
  last_verified: null     # refreshed by controls; the gardener proposes decay when stale
  origin: coding          # coding | cowork | translated
  status: candidate       # candidate | active | negative | retired
```

The file has three sections: `## Active lessons`, `## Negative lessons`, `## Candidates`.

### Lifecycle

1. **Intake.** The user brings lessons from a finished project (from the handoff section, or carried in the project's graph). The prompt builder records each as a candidate with project and date. *One attestation makes a candidate.*
2. **Attestation.** A second, genuinely separate project (verified against the registry) attesting the same lesson makes it *eligible for promotion*.
3. **Promotion.** The builder presents each eligible lesson to the user **as a plain diff**: a universal lesson diffs the standards file (and applying it bumps `standards_version`); a graph-mechanics lesson diffs the builder's own routing defaults, acceptance-criteria/contract templates, or context-slicing guidance. "Apply nothing without explicit approval. Approved lessons move to active."
4. **Application.** Whenever the knowledge-graph block is included in a project, active lessons are read and applied to routing, criteria, and slicing.
5. **Verification and decay.** Every active lesson carries `last_verified`, refreshed when a *control run* re-attests it (every few projects, run one slack task with the lesson deliberately switched off and compare telemetry against the lesson's claim). The gardener proposes demoting any active lesson aged "a few projects unverified"; demotions travel the same diff-and-approval path as promotions.
6. **Negative lessons.** A failed experiment lands in the negative section *immediately*, with its evidence — "so no future project spends exploration budget on a known dead end." Only a retrospective's assumption audit may resurrect one when conditions change.
7. **Pruning.** At each promotion, propose retiring active lessons that are stale, superseded, or unused, "so the ledger stays cheap to read."
8. **Cross-pollination.** At intake, check whether a lesson from one domain suggests an analog in the other; if so, record the translated candidate under the other domain with `origin: translated`. If translation needs more thought, park the raw idea in the backlog instead.

### Guard rail

Lessons adjust routing, scope, criteria and contract templates, and context slicing — "they never move the quality bar. Reject any lesson that would lower acceptance criteria, skip review, or weaken a standing standard."

### Representation notes

*Eligible* is never a stored status — it is derived, when the `attested` list names two genuinely separate projects. `retired` entries are never deleted: flip the status in place (or move them to a dedicated section), consistent with archive-never-delete. Each prompt builder also keeps a small offline-fallback file: if the canonical ledger is unreachable at intake time, entries are recorded there and reconciled into the canonical ledger as soon as it is reachable again; the fallback otherwise stays empty.

---

## The project registry (`registry.md`)

One line per project. The file's header paragraph — copy it verbatim:

> One line per project. Any session can find and resume work from here, the lessons loop uses it to verify that attestations come from genuinely separate projects, and the rollup fields show whether cost is falling over time. The initializer records the standards_version the project starts on, and the gardener flags any line older than the canonical standards file's current version.

Entry shape:

```yaml
- {project: example, location: ~/repos/example, status: active, standards: 1,
   last: 2026-08, tokens: mid, retries: 2, escalations: 1, notes: one line of context}
```

Status vocabulary: `status: active | paused | done`.

The initializer writes the line with the `standards_version` the project starts on; the retrospective updates the rollups; the gardener consolidates lines, flags any whose standards value is older than the canonical file's current version, and stamps a done project's line once its final report is folded. A project the gardener cannot reach "gets that fact and the date written into its registry line, never silently skipped." Lines grow long in practice — a closed project's line can carry budgets, retry counts under a stated definition, open items, and fold stamps — but keep the one-line brace-map shape so simple parsers can match on the `project:` field.

---

## The experiment backlog (`backlog.md`)

A ranked queue of hypotheses waiting for exploration budget. The file's header paragraph — copy it verbatim:

> A ranked queue of hypotheses waiting for exploration budget. Each project draws its one or two experiments from the top of this queue instead of improvising, and cross-pollination candidates wait here until translated. The prompt builder reads it whenever a prompt spends exploration budget; retrospectives append new hypotheses, and run entries are cleared as stated below.

Entry shape:

```yaml
- hypothesis: the prose-tier agent can implement config-only tasks
  domain: coding           # coding | cowork | both
  priority: high           # high | mid | low
  source: project alpha retrospective
```

Each project draws its one or two experiments **from the top of this queue** instead of improvising, and retrospectives append new hypotheses.

**Clearing.** Two conventions are defensible — the retrospective clears the entries its own project ran, or the gardener performs the authoritative clear at consolidation. Pick one and state it in the file header; the convention assumed by the one-writer table below is that retrospectives annotate outcomes and the gardener performs the clear. In either convention, **only an entry with a recorded outcome is ever cleared**: "an experiment with an unrecorded outcome stays queued — it is never counted as run." An experiment whose outcome was not recorded (no spend logged, no verdicts saved) is annotated and stays queued. The gardener adds dated notes to entries rather than rewriting their content, and marks its own proposed hypotheses as gardener proposals the user may prune.

---

## Playbooks (`Playbooks/`)

Reusable decompositions. When the gardener sees the same subgraph shape — the structural pattern of a project's decomposition — recur in a **third distinct project**, it drafts a named playbook file describing the decomposition, its unit types, its contract pattern, and the projects that used it, with `status: draft` in its header.

The status convention is the whole of the gate:

```markdown
status: draft        # draft | approved
```

**Only the user flips a playbook to `approved`.** Only approved playbooks may seed a new project's decomposition — and even then they "never override task-specific judgment." The gardener keeps the running shape tally in its memory file.

---

## One writer per coordination file

The rule, stated as a design principle: **one writer per coordination file.** "This is what makes a sync-based (no locking) shared state safe." The gardener below is the scheduled audit agent; every other actor reads these files and proposes changes through its own writer.

| Coordination file | Sole writer | What everyone else may do |
|---|---|---|
| `ledger.md` — lessons ledger | The prompt builders, and nothing else | The gardener *stages* ready-made candidate diffs in its own run log for one-tap approval, but never writes the ledger itself. Orchestrators and delegates only read it. |
| `registry.md` — project registry | A project's own initializer and retrospective write that project's line; the gardener consolidates | Other projects never touch a line that is not their own; the lessons loop reads the file to verify that two attestations come from genuinely separate projects. |
| `backlog.md` — experiment backlog | Retrospectives append hypotheses and annotate outcomes; the gardener clears run entries at consolidation | Prompt builders read it whenever a prompt spends exploration budget; nothing else writes. |
| `gardener.md` — the audit agent's run log | The gardener alone | Read-only to everyone else, including the user, who acts on its staged diffs and flags through the builders' approval path. |

The standards file sits outside this table only because it changes through a different gate: the promotion path, with the user's explicit approval and a `standards_version` bump on every change.

---

## Never delete; archive

The archive rule applies to every file above:

> **Never delete; archive.** Superseded files move to an `Archive/` folder under a timestamped name. Superseded decisions get `superseded_by`, not deletion. Wrong historical figures are reconciled in a definitions block, not edited away.

Concretely, in these files: a retired lesson keeps its entry with `status: retired` rather than being cut; a done project keeps its registry line; a cleared backlog entry keeps its recorded outcome; a superseded playbook moves to `Archive/` under a timestamped name rather than being overwritten in place. The history is the evidence, and evidence is never deleted to make a file shorter.
