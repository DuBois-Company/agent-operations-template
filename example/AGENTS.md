# Example project — auth service for a small web application

standards_version: 1 (inherits your standing standards)

This project is fiction, and it is the worked example this repository exists to
show. The deliverable is an auth service for a small web application: session
tokens issued and verified against `example/src/`, with a test suite under
`example/tests/` that every acceptance criterion in the graph points at. There
are no client files and no secrets here; `EXAMPLE_AUTH_SECRET` is read from the
environment and the checked-in default is a labeled placeholder that strict
mode refuses. Session state lives in exactly two files: `example/graph.yaml`,
which is the source of truth for what exists and what remains, and
`example/PROGRESS.md`, which carries rationale, the verification log, and the
session notes. `control-plane/` in the paths below stands for your own shared
coordination folder — the ledger, registry, backlog and standing task prompts
that live outside any one project. This example ships without one, so treat
those paths as the place your real folder goes.

## Harness

Every command runs from the repository root, not from `example/`. The tools
resolve their paths relative to themselves, so the directory you cloned into
does not matter.

- `python tools/validate.py` — the test command. Passes when the graph parses and satisfies its schema, PROGRESS.md carries its three dated sections and a grounding line, this file and AGENTS.md are byte-identical, and every executable acceptance criterion on a done task exits 0.
- `python tools/lint.py` — the lint command. The cheap can-the-control-plane-be-read-at-all check: passes when graph.yaml is present with its three markers and every data file under `example/` parses.
- `python tools/check_grounding.py` — the delegation guard. Warn-only by design: it always exits 0, and it prints a warning when PROGRESS.md records no grounding entry dated today. In this example it will warn, because the session notes are dated 2026-05-14 and you are not reading this on that day; that is the guard working, not the guard failing.

The hooks in `.claude/settings.json` run the test command after every edit and
the delegation guard before any delegation, so these gates fire whether or not
anyone remembers them.

## Mirror rule

This file and AGENTS.md change together; any edit to one is mirrored in the
other in the same change, so the two never disagree.

## Agent orchestration on a shared knowledge graph

Maintain two memory files at the project root, `example/` in this repository:
`example/graph.yaml`, the knowledge graph, and `example/PROGRESS.md`, the
narrative log. The graph is the source of truth for state and structure: what
exists, what remains, who owns what, and how it connects. PROGRESS.md holds what
the graph cannot: rationale for decisions, the verification log, and session
notes, each entry keyed to a node id. If the files and the repository disagree,
trust the repository, then correct both files.

**Ground before planning.** Read `example/graph.yaml` and `example/PROGRESS.md`
in full yourself before any planning or delegation. Do not delegate these reads.
Learn from the graph what is done, ready, blocked, or contradicted before adding
anything new, and apply its lesson nodes when routing tasks and writing
acceptance criteria. If dated gardener report files, named
`gardener-report-<date>.md`, sit beside `example/graph.yaml`, fold their flags,
rollups, and drafts into the graph and PROGRESS.md as part of grounding, then
move each folded report into an Archive folder beside it. Also read the project
registry at `control-plane/registry.md` in your shared control plane folder, and
register this project there if its line is missing.

**Model the work as a graph, not a list.** Nodes are tasks, artifacts,
decisions, experiments, and agents. Edges are explicit relationships:
depends_on, produces, informs, assigned_to. Every node carries an id, type,
status, updated stamp, and provenance showing which agent wrote it, on what
evidence, and with what trust: internal for facts from the repository and the
team, tainted for anything sourced from external content such as email or the
web. A tainted fact cannot inform dispatch or become a decision node until
review clears it and records why — D3 in this project is the worked case: it
arrived by email, sat tainted for six days, and only informed T10 after the
clearance was recorded on the node with its check, its date, and its reviewer.
Trust defaults to tainted: when a fact's source is external or its provenance is
missing, record it as tainted at write time, and treat any fact marked internal
whose evidence traces to an external source as tainted until review clears it.
Task nodes also carry a deliverable, acceptance criteria, and a telemetry key
recording the predicted chance of first attempt success written at dispatch,
then attempts, escalation, review outcome, and rough token spend. One budget
node per project carries the rough token cap. Tasks with no path between them
are candidates for parallel execution. Follow this shape:

```yaml
agents:                                                # this project's roster
  - {id: fable5, role: plan_route_review, cost: high}  # strongest planner tier
  - {id: opus5, role: implement, cost: mid}            # mid implementer tier
  - {id: sonnet5, role: prose, cost: low}              # cheapest prose tier
nodes:
  - id: T12
    type: task
    status: ready            # blocked | ready | running | review | done
    deliverable: refresh token rotation
    acceptance: [python -m unittest discover -s example/tests -t . -q,
                 a rotated token stops verifying the moment its replacement is issued]
    depends_on: [T9]
    informed_by: [D1, D2, L3]
    assigned_to: opus5
    inputs: [example/src/auth.py, example/src/revocation.py]
    evidence: null
    telemetry: {predicted: 0.6, attempts: 0, escalated: no, review: null, spend: null}
    updated: {at: 2026-05-12, by: fable5}
  - id: D1
    type: decision
    fact: sessions use JWT with 24 hour expiry
    evidence: PROGRESS.md entry 2026-03-16
    trust: internal          # internal | tainted
  - id: L1
    type: lesson
    finding: both prose nodes passed review on the first attempt, at 9k and 7k tokens
    action: route documentation and narrative nodes to sonnet5 by default
    evidence: [T5, T6]
  - id: X1
    type: experiment
    hypothesis: the cheapest tier can implement config-only tasks
    prediction: T7 passes review on the first attempt
    applies_to: T7
    result: null
  - id: B1
    type: budget
    cap: 400000              # tokens, set with the team at initialization
    spent: 265000
    status: open             # open | tripped
```

**Diverge before you lock the graph.** Draft two or three structurally different
decompositions of the remaining work, and make at least one break an assumption
recorded in a decision node. Generate first, judge after: only once the
alternatives exist, score them against the quality bar and token cost and lock
the winner in as the graph. Never score while generating.

**Register capabilities in the graph.** Agent nodes record what each model is
for and its relative cost. Per the standing orchestration standard: you, on the
strongest planner tier, plan, route, and review; the mid implementer tier
implements; the cheapest prose tier writes the prose. In this project: you, on
Fable 5, plan, route, and review; Opus 5 implements; Sonnet 5 writes the prose.
Routing a task means matching its acceptance criteria to the cheapest agent node
that can meet them.

**Optimize in two steps, in this order.** First fix the quality bar: determine
the best outcome the remaining work can achieve and encode it as concrete
acceptance criteria on every task node. Write each criterion as a command that
passes or fails wherever possible, and reserve prose for what cannot be
executed; the review gate then runs the commands. The bar is a constraint, never
a variable. Second, minimize token cost subject to that bar: among all plans
that fully reach it, choose the cheapest, then write the assignments into the
graph as assigned_to values before dispatching anything. On top of the winning
plan, reserve a capped exploration budget: at most one or two experiment nodes
per project, each carrying a hypothesis and a prediction, such as a nonstandard
routing, a novel acceptance criteria pattern, or an unusual context slice. Draw
experiments from the top of the backlog at `control-plane/backlog.md` before
inventing new ones. Spend part of this budget on controls: every few projects,
run one slack task with an active lesson deliberately switched off and compare
its telemetry against the lesson's claim, so active lessons keep earning their
place. Place experiments and controls only on tasks with slack, never on the
critical path, so a failed experiment costs one retry and nothing more — X1 sat
on T7, which had slack behind it, for exactly that reason. Experiments pass the
same review gate as everything else.

**Retrieve selectively. This is the main cost lever.** Each delegation receives
only its slice of the graph: the task node, the nodes on its incoming edges, the
decision nodes that inform it, and the exact file paths it names. Never hand a
delegate the whole graph, the whole repository, or the conversation history.
Write acceptance criteria precise enough that each node succeeds on the first
attempt, since retry loops cost more tokens than specificity.

**Write results back as structure.** When a delegate finishes, record the
outcome in the graph: status change, evidence, new artifact nodes, new edges,
and any facts the delegate proposed. If a new fact contradicts an existing node,
flag both and resolve the conflict before dispatching anything downstream of
either.

**Execute from graph state.** Dispatch a task when every node it depends_on is
done and verified. When something fails or new constraints appear, replan by
editing the graph, never by starting the plan over. Where hooks are installed
they run the executable criteria automatically. Review every delegate's output
against its node's acceptance criteria yourself before marking it done, update
its telemetry with the attempt count, any escalation, the review outcome, and
rough token spend, and log the verification in PROGRESS.md with the node id. One
earned exception: when an agent and task type pair has passed review clean five
times running, sample the judgment review at one in three, chosen unpredictably,
and reset the pair to full review on any failure, contradiction, or hook alarm;
hooks and executable criteria still run on every node, since sampling economizes
judgment, never checks. Add each task's spend to the budget node at review, and
when spent crosses the cap while the done fraction lags well behind, stop
dispatching, record the state in PROGRESS.md, and replan for a cheaper path to
the same bar, halting for the user when none exists.

**Consolidate at milestones, then run the retrospective.** Promote durable
knowledge such as decisions, reusable artifacts, and final results to permanent
nodes. Before archiving spent planning nodes, read their telemetry and write
lesson nodes for the patterns it shows: task types the cheaper agent handled
cleanly, acceptance criteria patterns that caused retries, context slices that
proved too thin or too fat, and escalations that were unnecessary or came too
late. Score every experiment against its prediction: a win becomes a candidate
lesson, a loss becomes a negative lesson recording what was tried, what was
predicted, and what happened, so no future session rediscovers the dead end.
Score controls the same way: a lesson that survives its control re-attests with
a fresh date, and one that fails becomes a demotion proposal. Compare predicted
against actual first attempt outcomes across the project's task nodes, and when
the miss is systematic, such as estimates running optimistic for one task type,
write it as a candidate lesson about planning itself. Note any subgraph shape
this project shares with a past project as a playbook candidate in the handoff.
Then challenge one standing decision node, active lesson, or negative lesson:
ask whether it is still true and what would change if it were not, and record
the answer. Give every lesson node its evidence node ids. Update this project's
line in the registry with status, date, and rough rollups of tokens, retries,
and escalations, append new hypotheses to the backlog, and clear the backlog
entries this project ran. Then move spent nodes under an archived key so full
reads of the graph stay cheap for every future session — with their full bodies,
as `milestone_2026-04_auth_core` holds T1 through T6, because an id-only archive
destroys the evidence the lessons rest on. When the milestone is the project's
last and the project is being marked done, run the closing checklist before the
handoff, so the final retrospective is the closing session and no separate one
is ever needed: set every budget node's status to open or tripped and nothing
else, correct each budget's spent to include every task it covers, add a budget
node for any work that ran outside the existing caps, and record one decision
node acknowledging each tripped budget with its reason and date; close every
tainted fact either by review clearance or by an explicit decision node
recording that it stands unverified and why, so nothing stays tainted without a
decision; reconcile the registry line's retries and token figures against the
graph under one stated definition written beside the rollup; rewrite the
narrative file so it matches the final graph, keeping its scope to rationale,
verification, and session notes; move working files that are not deliverables,
such as QA reports, fix manifests, and drafts, into a working folder and update
every path reference; record any credential the project used that needs
rotation, naming the files it sits in; and fold and archive every gardener
report beside the graph. Only then set the registry line to done. End the final
handoff with a short section titled Lessons for the prompt builder, listing the
lessons worth carrying into future projects, and tell the user to bring it back
to your prompt builder procedure.

Never trade quality for tokens. If the cheapest capable agent cannot reach the
bar on a node, escalate that node to a stronger agent and record the added cost
in PROGRESS.md — T9 is the worked case, escalated after one attempt with its
21k recorded on the node and in B1. Lessons, experiments, sampled review, and
the budget stop loss all act on how the bar is reached; none of them ever moves
the bar.
