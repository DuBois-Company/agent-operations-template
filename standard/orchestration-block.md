# Knowledge graph orchestration block

This file is the canonical, self-contained text of the knowledge graph orchestration standard: the block itself, the initializer session that installs it, the scheduled gardener that tends it, and the changes that adapt it to a working-folder surface. An initializer installs the block into each project's instruction files verbatim, adapting only task-specific details such as file paths and example node content, so working prompts reference the installed copy instead of repeating it. Throughout, `<control-plane>/` marks your own shared coordination folder, the synced directory where your lessons ledger, project registry, experiment backlog, and standing task prompts live; substitute your real path for it once, everywhere it appears. Named models and named product surfaces appear only as a labeled reference deployment, and the generic tier roles sit beside them so you can map the standard onto whatever agents and surfaces you actually run.

## When to use this block

This is the expanded rendering of the plain agent orchestration block. Use it in place of that plain block whenever the work involves subagent delegation, work expected to span more than one session, or enough remaining tasks that dependency tracking matters. It carries the full substance of the plain block and extends the memory file rule: when this block is active, the graph file `graph.yaml` holds state and structure, and the memory file narrows to rationale, verification, and session notes. Never paraphrase this block from memory. The initializer installs it into the project's CLAUDE.md and AGENTS.md, adapting only task specific details such as file paths and example node content; working prompts reference it instead of repeating it. For portable renders outside your standing file system, copy it into the prompt in full.

## The block, repository-surface rendering

Reference deployment: Claude Code. The text between the fences below is the installed text; everything the initializer changes is task specific detail, never a rule.

````markdown
## Agent orchestration on a shared knowledge graph

Maintain two memory files at the repository root: graph.yaml, the knowledge graph, and PROGRESS.md, the narrative log. The graph is the source of truth for state and structure: what exists, what remains, who owns what, and how it connects. PROGRESS.md holds what the graph cannot: rationale for decisions, the verification log, and session notes, each entry keyed to a node id. If the files and the repository disagree, trust the repository, then correct both files.

**Ground before planning.** Read graph.yaml and PROGRESS.md in full yourself before any planning or delegation. Do not delegate these reads. Learn from the graph what is done, ready, blocked, or contradicted before adding anything new, and apply its lesson nodes when routing tasks and writing acceptance criteria. If dated gardener report files, named gardener-report-<date>.md, sit beside graph.yaml, fold their flags, rollups, and drafts into the graph and PROGRESS.md as part of grounding, then move each folded report into an Archive folder beside it. Also read the project registry at <control-plane>/registry.md in your shared control plane folder, and register this project there if its line is missing.

**Model the work as a graph, not a list.** Nodes are tasks, artifacts, decisions, experiments, and agents. Edges are explicit relationships: depends_on, produces, informs, assigned_to. Every node carries an id, type, status, updated stamp, and provenance showing which agent wrote it, on what evidence, and with what trust: internal for facts from the repository and the team, tainted for anything sourced from external content such as email or the web. A tainted fact cannot inform dispatch or become a decision node until review clears it and records why. Trust defaults to tainted: when a fact's source is external or its provenance is missing, record it as tainted at write time, and treat any fact marked internal whose evidence traces to an external source as tainted until review clears it. Task nodes also carry a deliverable, acceptance criteria, and a telemetry key recording the predicted chance of first attempt success written at dispatch, then attempts, escalation, review outcome, and rough token spend. One budget node per project carries the rough token cap. Tasks with no path between them are candidates for parallel execution. Follow this shape:

```yaml
agents:                                                # reference deployment; substitute your own tiers
  - {id: fable5, role: plan_route_review, cost: high}  # strongest planner tier
  - {id: opus5, role: implement, cost: mid}            # mid implementer tier
  - {id: sonnet5, role: prose, cost: low}              # cheapest prose tier
nodes:
  - id: T2
    type: task
    status: ready            # blocked | ready | running | review | done
    deliverable: auth middleware with passing tests
    acceptance: [npm test exits 0, npx tsc --noEmit exits 0]
    depends_on: [T1]
    informed_by: [D1]
    assigned_to: opus5
    inputs: [src/auth.ts]
    evidence: null
    telemetry: {predicted: 0.8, attempts: 0, escalated: no, review: null, spend: null}
    updated: {at: 2026-08-27, by: fable5}
  - id: D1
    type: decision
    fact: sessions use JWT with 24 hour expiry
    evidence: PROGRESS.md entry 2026-08-20
    trust: internal          # internal | tainted
  - id: L1
    type: lesson
    finding: prose tasks passed review on the first attempt
    action: route documentation tasks to sonnet5 by default
    evidence: [T4, T7]
  - id: X1
    type: experiment
    hypothesis: sonnet5 can implement config only tasks
    prediction: T5 passes review on the first attempt
    applies_to: T5
    result: null
  - id: B1
    type: budget
    cap: rough token ceiling set at initialization
    spent: 0
    status: open             # open | tripped
```

**Diverge before you lock the graph.** Draft two or three structurally different decompositions of the remaining work, and make at least one break an assumption recorded in a decision node. Generate first, judge after: only once the alternatives exist, score them against the quality bar and token cost and lock the winner in as the graph. Never score while generating.

**Register capabilities in the graph.** Agent nodes record what each model is for and its relative cost. Per the standing orchestration standard: you, on the strongest planner tier, plan, route, and review; the mid implementer tier implements; the cheapest prose tier writes the prose. Reference deployment: you, on Fable 5, plan, route, and review; Opus 5 implements; Sonnet 5 writes the prose. Routing a task means matching its acceptance criteria to the cheapest agent node that can meet them.

**Optimize in two steps, in this order.** First fix the quality bar: determine the best outcome the remaining work can achieve and encode it as concrete acceptance criteria on every task node. Write each criterion as a command that passes or fails wherever possible, and reserve prose for what cannot be executed; the review gate then runs the commands. The bar is a constraint, never a variable. Second, minimize token cost subject to that bar: among all plans that fully reach it, choose the cheapest, then write the assignments into the graph as assigned_to values before dispatching anything. On top of the winning plan, reserve a capped exploration budget: at most one or two experiment nodes per project, each carrying a hypothesis and a prediction, such as a nonstandard routing, a novel acceptance criteria pattern, or an unusual context slice. Draw experiments from the top of the backlog at <control-plane>/backlog.md before inventing new ones. Spend part of this budget on controls: every few projects, run one slack task with an active lesson deliberately switched off and compare its telemetry against the lesson's claim, so active lessons keep earning their place. Place experiments and controls only on tasks with slack, never on the critical path, so a failed experiment costs one retry and nothing more. Experiments pass the same review gate as everything else.

**Retrieve selectively. This is the main cost lever.** Each delegation receives only its slice of the graph: the task node, the nodes on its incoming edges, the decision nodes that inform it, and the exact file paths it names. Never hand a delegate the whole graph, the whole repository, or the conversation history. Write acceptance criteria precise enough that each node succeeds on the first attempt, since retry loops cost more tokens than specificity.

**Write results back as structure.** When a delegate finishes, record the outcome in the graph: status change, evidence, new artifact nodes, new edges, and any facts the delegate proposed. If a new fact contradicts an existing node, flag both and resolve the conflict before dispatching anything downstream of either.

**Execute from graph state.** Dispatch a task when every node it depends_on is done and verified. When something fails or new constraints appear, replan by editing the graph, never by starting the plan over. Where hooks are installed they run the executable criteria automatically. Review every delegate's output against its node's acceptance criteria yourself before marking it done, update its telemetry with the attempt count, any escalation, the review outcome, and rough token spend, and log the verification in PROGRESS.md with the node id. One earned exception: when an agent and task type pair has passed review clean five times running, sample the judgment review at one in three, chosen unpredictably, and reset the pair to full review on any failure, contradiction, or hook alarm; hooks and executable criteria still run on every node, since sampling economizes judgment, never checks. Add each task's spend to the budget node at review, and when spent crosses the cap while the done fraction lags well behind, stop dispatching, record the state in PROGRESS.md, and replan for a cheaper path to the same bar, halting for the user when none exists.

**Consolidate at milestones, then run the retrospective.** Promote durable knowledge such as decisions, reusable artifacts, and final results to permanent nodes. Before archiving spent planning nodes, read their telemetry and write lesson nodes for the patterns it shows: task types the cheaper agent handled cleanly, acceptance criteria patterns that caused retries, context slices that proved too thin or too fat, and escalations that were unnecessary or came too late. Score every experiment against its prediction: a win becomes a candidate lesson, a loss becomes a negative lesson recording what was tried, what was predicted, and what happened, so no future session rediscovers the dead end. Score controls the same way: a lesson that survives its control re-attests with a fresh date, and one that fails becomes a demotion proposal. Compare predicted against actual first attempt outcomes across the project's task nodes, and when the miss is systematic, such as estimates running optimistic for one task type, write it as a candidate lesson about planning itself. Note any subgraph shape this project shares with a past project as a playbook candidate in the handoff. Then challenge one standing decision node, active lesson, or negative lesson: ask whether it is still true and what would change if it were not, and record the answer. Give every lesson node its evidence node ids. Update this project's line in the registry with status, date, and rough rollups of tokens, retries, and escalations, append new hypotheses to the backlog, and clear the backlog entries this project ran. Then move spent nodes under an archived key so full reads of the graph stay cheap for every future session. When the milestone is the project's last and the project is being marked done, run the closing checklist before the handoff, so the final retrospective is the closing session and no separate one is ever needed: set every budget node's status to open or tripped and nothing else, correct each budget's spent to include every task it covers, add a budget node for any work that ran outside the existing caps, and record one decision node acknowledging each tripped budget with its reason and date; close every tainted fact either by review clearance or by an explicit decision node recording that it stands unverified and why, so nothing stays tainted without a decision; reconcile the registry line's retries and token figures against the graph under one stated definition written beside the rollup; rewrite the narrative file so it matches the final graph, keeping its scope to rationale, verification, and session notes; move working files that are not deliverables, such as QA reports, fix manifests, and drafts, into a working folder and update every path reference; record any credential the project used that needs rotation, naming the files it sits in; and fold and archive every gardener report beside the graph. Only then set the registry line to done. End the final handoff with a short section titled Lessons for the prompt builder, listing the lessons worth carrying into future projects, and tell the user to bring it back to your prompt builder procedure.

Never trade quality for tokens. If the cheapest capable agent cannot reach the bar on a node, escalate that node to a stronger agent and record the added cost in PROGRESS.md. Lessons, experiments, sampled review, and the budget stop loss all act on how the bar is reached; none of them ever moves the bar.
````

## Initializer session

When the project has no graph.yaml yet, the initializer runs before any working session. On both surfaces the session runs it itself by following your procedure library's initializer procedure, as the standing file directs; assemble it as a prompt only for portable renders where the standing files cannot exist. Reference deployment: Claude Code and Cowork both run it in session rather than handing the user a prompt to paste. Its job is environment setup, not feature work. The initializer must: verify the agent's global instruction file carries the canonical standing standards from `<control-plane>/CLAUDE.md` and tell the user to link or copy it when it does not; write the project's CLAUDE.md and AGENTS.md together, carrying this block and project specifics; read the repository and register the project in the registry, recording the standards_version it starts on; scaffold graph.yaml with the agents list and a budget node whose cap is set with the user or defaulted to a stated rough ceiling, and PROGRESS.md with its sections; build or verify the harness that makes acceptance criteria executable, at minimum a test command and a lint or type check command that exit cleanly on the current code; install hooks in the agent's settings file, `.claude/settings.json` in the reference deployment, that enforce the gates mechanically, at minimum running the test command after every edit and blocking or warning on delegation before grounding is recorded; and finish by proving every hook and check runs. Only after the initializer completes does a working prompt plan the graph.

## Scheduled gardener

The gardener is one standing scheduled cloud task on the working folder surface, tending every project in the registry; reference deployment: Cowork. Its duties, hard limits, and run procedure live in exactly one place: the canonical prompt at `<control-plane>/gardener-task.md`, which carries its own task_version. Revise it there when the user asks and paste the change into the scheduled task in the same change; the prompt's own access and version proof halts a run when the two drift. Keep each project's graph.yaml and PROGRESS.md where the cloud task can reach them, such as under your synced control plane folder; a project the gardener cannot reach gets that fact noted in its registry line, never silently skipped. When a new project registers, confirm the standing gardener task exists instead of creating another. The gardener never dispatches work nodes, never edits code, never writes to `<control-plane>/ledger.md`, and never touches the quality bar. It folds its own report into a project's graph and narrative file only when that project's registry line says done, where no other writer exists; active and paused projects fold gardener reports themselves at their next grounding.

## Working-folder rendering changes

When the target is the working folder surface rather than the repository surface, reference deployment Cowork, make these changes and use everything else unchanged:

- Replace "repository root" with the root of the working folder, and "trust the repository" with trusting the actual files in the working folder.
- Roles are enforced by scope rather than by model. The agents list records the main session as plan_route_review and each subagent with the single scope it may touch, such as one document, one batch, one deliverable, or one concern. Routing means matching a node's acceptance criteria to the narrowest capable scope, and escalation means widening scope or strengthening inputs rather than switching models.
- Swap the code example for the domain of the task, for example a report section with source documents as inputs, and use output contract language where acceptance criteria refers to documents rather than tests.
- In the closing model reminder, point to the surface's model picker with the strongest planner tier selected, Cowork's model picker with Fable 5 selected in the reference deployment, and drop the note about subagent definitions in `.claude/agents/`.
- Hooks do not exist on this surface. The initializer runs as an ordinary first task, and executable criteria become the written checklist the completeness proof runs. The gardener already lives on this surface as the standing scheduled cloud task.
- The sampling exception applies to the judgment read only: the contract checklist still runs on every unit, and any checklist miss resets the pair to full review.
