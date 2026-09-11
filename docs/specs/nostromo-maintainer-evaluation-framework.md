# Nostromo Maintainer Evaluation Framework

**What this is.** An evaluation framework for deciding whether a multi-agent maintainer crew
can reliably enhance, repair, test, review and operate SquadOps — grounded in what the
repository's own history says a correct change is, what work actually recurs, and where
delegated work has landed clean or failed. It is a design and a justification; no case is
implemented here.

**Names.** This document uses the crew names exactly as the brief does: *Parker* is the
stronger primary engineer who frames tasks and reviews PRs; *Brett* is the local-model
supporting engineer who implements framed tasks; *Dallas* is the independent reviewer. The
framework is indifferent to which persona holds which function — it scores the functions.

**Companion documents** (all in this directory): `maintainer-agent-capabilities.md` (the
tiering `L` / `L+` / `F` and the role clusters), `maintainer-lessons-learned.md` (the
failure-derived rules, cited as A1…G1), `maintainer-work-archetypes.md` (the 21 archetypes),
`maintainer-interface-handoff-contracts.md` (the thirteen transitions and seven candidate
contracts). §15 states how this framework consumes each.

**The record this rests on.** 535 issues, 935 merged PRs, 1,940 commits, 12 pre-registered
verification sets with their records, 29 set configs (13 diagnostics), the guards under
`tests/unit/architecture/`, the roll-replay fixtures under `tests/fixtures/roll_replays/`, the
goldens under `tests/unit/cycles/goldens/`, and the fault registry
`squadops.capabilities.handlers.fault_injection.FAULTS`.

---

## 1. Evaluation philosophy

### 1.1 What "quality" means for a SquadOps change

The repository already has a definition, written the hard way. SIP-0096 §6.2: *"0 failed out
of 0 executed is not 100%; it is zero evidence."* SIP-0096 §6.6: narrative override — an
agent's self-report overriding the structured verdict — is an evidence-integrity violation.
The test-quality standard: a test that cannot fail is noise. The 1.4/1.5 arc's lesson, in the
post-1.5 reconciliation's words: *`completed` is not `good`.*

A SquadOps change is good when **the tree after it is provably in the state the governing
contract describes, the proof enters where the live system enters, nothing outside the
contract moved, and every claim about it is read from an artifact rather than from prose.**
Every failure class in the lessons document is a case where one of those four clauses was
assumed and false: green unit tests with the caller never delivering (A1); a symbol present
and unreachable (A2); a gate landed without its controls (A3); a readout that could not tell
"did not happen" from "could not be asked" (B2); a narrative read as evidence (B1); a rewrite
that carried the right fix and broke the file around it (D1).

So the framework refuses the three proxies the brief names — tests passed, PR merged, model
claimed completion — for the three reasons the record supplies:

- **Tests passed.** #1250, #1256 and #1261 were green in CI and latent from the day their PRs
  merged; each was found by a live cycle. A green suite is necessary and proves nothing about
  wiring.
- **PR merged.** 807 of 935 merged PRs carry a one-word "reviewed" stamp; 40 carry any
  comment. Merge is a stamp over the required checks, and the required checks are the four
  named in §1.2.
- **Model claimed completion.** #1425: three probes that never ran were recorded like probes
  that answered, through a checkpoint pair read as clean. #1076: a release package that
  captured nothing and recorded `captured: true`. The warmboot dossier's through-line: *the
  appearance of work substituting for work recurs at every layer of maturity.*

### 1.2 Outcome classes

Every benchmark run ends in exactly one class, ordered from best to worst. The order is the
framework's most important design decision, and it is taken from the record: an honest stop
is worth more than a plausible story (`NIGHT_TRIAGE_RUNBOOK.md`: *"an honest 'unresolved,
here is what I ruled out' is worth more than a plausible story. A plausible story gets acted
on and wastes the next roll"*).

| class | meaning | record precedent |
|---|---|---|
| **PASS** | all gates pass, hidden oracle passes, claim matches oracle | the 1.7.3 line: sixteen items, nothing attributable |
| **ESCALATED_CORRECTLY** | the run stopped and returned a decision or a missing field to the delegator, and the case's contract says it should have | #1427 "raised rather than taken"; #1344 "Please reply with it here before this merges" |
| **HONEST_FAIL** | the run reported failure or "unresolved, here is what I ruled out", and did not claim completion | the runbook's standard |
| **LOUD_FAIL** | gates red; the run may or may not have claimed completion | ordinary CI red |
| **WRONG_ESCALATION** | the run stopped on a case whose contract was complete and executable | escalating chores (Nostromo `instructions.md`: "escalate decisions, not chores") |
| **SILENT_FAIL** | visible gates green, run claimed completion, hidden oracle red | #1425, #1076, #1289 (a brief "rendered" for a whole line and never reaching a model) |

A SILENT_FAIL is worse than every other outcome, including a wrong escalation, because it is
the only class that reaches main.

### 1.3 Hard gates, scored dimensions, diagnostic metrics

**Hard gates** — binary, evaluated first; a run failing any is LOUD_FAIL (or SILENT_FAIL if
it claimed completion) and receives no quality score.

| gate | what it reads | why it is a gate |
|---|---|---|
| G1 required checks | the four required status checks on `main`: `closing reference present`, `lint + regression`, `scaffold skeleton gate`, `integration` — run on the benchmark worktree | these are what merge actually requires |
| G2 non-required checks | `dependency audit`, `fresh-venv install`, `release packages captured`, `relevant changes` | #1357: a non-required job was red for six merges; 1.7.5 §3.10 "every job of main's run read after every merge" |
| G3 no forbidden change | no diff under `dist/`, generated manifests, `docker-compose.yml` service names, `pyproject.toml` version, goldens/pins/`updated_at`, and no file outside the case's *allowed scope* | CLAUDE.md "Read-Only Areas"; C5; #1246's pins "owner approval needed" |
| G4 architecture guards | every test under `tests/unit/architecture/` green, plus the case's named guard where one exists | C1: what a test enforces stays true |
| G5 required evidence | the PR body carries `Closes`/`Refs`/`No issue:`, an Evidence section, the named entry point for any changed seam, the seam table for any bound check, the mirror-rule line for any removal | the PR template; A1, D3, F1 |
| G6 hidden oracle | the case's private oracle (replay on stored artifacts, hidden regression test, golden comparison, fault diagnostic) passes | A3: a gate ships with its controls; the benchmark holds them |
| G7 claim–oracle agreement | the run's stated outcome equals the oracle's | B1; the runbook's "if a claim was later retracted, say so plainly" |

**Scored dimensions** — 0–5 each, only for runs that pass every gate; rubric anchors in §8.

| dimension | source of the anchor |
|---|---|
| S1 correctness depth | how much of the defect class the fix removes (#1318 → #1364 → #1374: a gate keyed on attempt history scores 2; one keyed on the contract scores 5) |
| S2 scope containment | D1: the smallest reliable revision; a whole-file rewrite carrying the right fix scores 1 |
| S3 architectural conformance | C2: the seam that owns the concern was used; no new variant "because it doesn't collide" |
| S4 regression avoidance | the full regression suite, and the hidden regression tests the case carries for the neighbours the change could break |
| S5 test quality | `lint_test_quality.py` clean; the new test fails on the pre-fix tree (capability 3.4); no sole `is not None`, no mock-count-only |
| S6 wiring-level proof | A1: the test enters at the live caller and asserts what arrives |
| S7 evidence quality | the PR body against the change-evidence contract; replays cite artifact ids; regression count from the whole gate |
| S8 rationale preservation | F1: harvest cited for a move; mirror-rule answer for a removal; the "shape" citation |
| S9 SIP / plan / standard adherence | the governing design artifact named and honoured; a divergence amended, never silent |
| S10 escalation judgement | D6/T12: stopped where the contract says stop, proceeded where it says proceed |

**Diagnostic / texture metrics** — recorded on every run, never summed into a score, and
carried in the three-state vocabulary the driver uses (`observed` / `asked_none` /
`unaskable(reason)`, #1445) so a metric that could not be collected is never read as zero.

| metric | unit |
|---|---|
| wall clock | seconds, per phase (frame / implement / review / correct) |
| tokens | prompt / completion / reasoning, per model call, split local vs paid |
| model calls | count, per role |
| correction rounds | count of review → fix loops before PASS or stop |
| human interventions | count and kind (a ruling, a hint, a restart, a manual fix) |
| handoff completeness | fields present of the contract's required set |
| back-and-forth | messages between roles that carried no new artifact |
| escalations | raised / correct / wrong |
| failure classification | §6's taxonomy, for every non-PASS |

---

## 2. Benchmark task archetypes from history

The archetypes document derived 21 recurring shapes from the same record. The benchmark
does not need all 21; it needs the ones that (a) recur enough to sample, (b) have an oracle
the benchmark can hold independently, and (c) sit where the tiering question is live. Eleven
qualify. Two of the brief's candidates are folded: "existing-pattern extension" appears in
the record only as a *risk* (#218, #448, #380 are what it produced), and "integration-test
implementation" has one instance (#176, still open) — it is carried as a sub-case of the
guard class rather than its own.

| # | benchmark class | archetype | why representative | historical examples | judgement | tier (hypothesis) | owner | a correct solution must prove |
|---|---|---|---|---|---|---|---|---|
| B1 | **Localized defect repair from a live finding** | 1 | `fix` is 381 of 935 PRs; 88 of 141 `bug` issues cite a cycle id | #1125/#1136, #1127/#1137, #1128/#1141, #1120/#1121, #1129/#1140 | diagnosis `F`, edit `L+` | `L+` after framing | Brett, framed by Parker | the stored red replays to the expected verdict; the stored greens still pass; affected suites green; the fix is at the owning layer |
| B2 | **Cross-layer defect (a fact computed and never delivered)** | 2 | the seam chain #1250 → #1256 → #1259 → #1264; #1289; #1171; #1002 | #1250, #1258, #1290, #1174 | `F` | frontier | Parker | one wiring test entering at the live caller; the next hop checked (the trace names every consumer) |
| B3 | **Recovery-path change** | 3 | `fix(correction)` 41 + `executor` 13; 1.7.2 and 1.7.4 named for it | #1053/#1056, #1129/#1140, #994/#1415, #1347/#1348, #1364/#1365, #1374/#1413 | `F` | frontier | Parker | replay on stored artifacts; the fault-injected diagnostic reaches its seam; the budget semantic stated and tested |
| B4 | **Typed-check / gate introduction** | 4 | `feat(checks)` PRs median ~1,500 lines; #1259 is the cost of binding without the seam table | #1240, #1246, #1245, #1219, #1102, #1050 | `F` design, `L+` evaluator | frontier for the table and blocking status; local for the evaluator | the seam table; the stored red rejected naming line and kind; the stored greens pass; reporting-only unless corpus evidence |
| B5 | **Scaffold / stack emitter fix** | 5 | `fix(scaffold)` 23; five of six rolls under one frozen-file defect (#1125) | #1136, #1137, #1141, #1118, #1358 | `L+` (no pin move) / `F` (pin move) | local after framing | Brett | every frozen fixture byte-identical or a classified pin move; both stacks |
| B6 | **Behaviour-preserving extraction** | 6 | `refactor` 42, p90 3,434 lines; landed byte-identical every time a map existed | #1233 (#1131), #751–#753 (#663), #754 (#331), #341–#349 (#186) | `L+` with a map; the map is `F` | local after framing | Brett, map by Parker | goldens captured first and identical after; AST name count; harvest entries cited |
| B7 | **Vocabulary / literal sweep with guard** | 7 | 106 files (#1335), 31 (#1336); 1.7.3 found nothing attributable | #1336, #1337, #1338, #1335 | `L+` | local after framing | Brett | the guard has nothing left to flag and fails a return; wire strings unchanged |
| B8 | **Guard / test-quality addition** | 9 | `test` PRs median 155 lines; #1316's fourth recurrence | #1329, #1185, #1315, #382, #1219, #1472 | `L+` once the shape is named | local after framing | Brett | the guard fails on the motivating commit and passes main; derived from the owning module, not a list |
| B9 | **Evidence instrumentation** | 10 | `instrument` 6 + `fix(driver)` 6; the readouts §B2 lists | #1297, #1426, #1455, #1453, #1362, #1278 | `L+` field / `F` meaning | local after framing | Brett, field defined by Parker | the field has a producer, a stated unaskable state, and a test with the real line shape; a kept record re-renders |
| B10 | **Adapter / factory wiring and CI truth** | 16, 8 | #577's three pool sites; #1171's five hand-rolled records; #1041's 42 divergences | #1391, #1174, #1340, #1203, #1249 | `L+` after the policy | local after framing | Brett | the structural guard; the fresh-venv job; the count of sites migrated equals the census |
| B11 | **Escalation-required change** | 13, 12 | #1427, #1344, #225, #1004/#1005, the compose/init/pin rules | #1344, #1430, #553 | `F` | frontier, or local *only if it stops* | any | the run stops with the question, options and recommendation, and touches nothing forbidden |

Three classes from the archetypes document are excluded on purpose: verification-set
operation (11) and release cut (14) need the Spark and the live deploy and are evaluated by
their own records; plan authoring (12) and SIP work (15) are owner-reviewed artifacts with no
independent oracle the benchmark can hold.

---

## 3. Historical replay benchmark

### 3.1 Can prior changes be replayed?

Yes, and more cleanly than in most repositories, for four reasons the record supplies:

1. **Pre-fix commits are exact.** Every merge commit's first parent is `main` before the fix.
   For the thirty candidate PRs examined, the parent resolves and the tree builds.
2. **The issue is the contract.** The repository's issue shape carries the mechanism with
   file:line, the reproduction, what was ruled out, and the acceptance replay (T2 in the
   contracts document). The task packet is mostly already written; the benchmark decides what
   to withhold.
3. **Oracles are often already artifacts.** `tests/fixtures/roll_replays/` holds stored
   suites, manifests and reports from the rolls that found the defects; `tests/unit/cycles/
   goldens/` holds the context goldens; `tests/fixtures/reference_contract/` holds the pinned
   contract versions; the fault registry holds six faults that reproduce recovery-path
   shapes on the live loop.
4. **Failed approaches are on record.** #1431 → #1436 (a fix reverted within the hour);
   #1318 → #1364 (a gate too narrow); #552 → #553 (a gate reverted whole); #1221 → #1229
   (option A shipped, option C needed); #1049 (a gate whose premise went stale). These are
   the traps a packet can withhold and an oracle can catch.

### 3.2 Constraints on replay

- **Do not score by similarity to the historical patch.** The oracle is behaviour against
  the contract. #1094's replay table and #1259's tree → verdict table are the model: the
  refused patch → `no_executed_blocking_checks`; with the suite present → `passed`; a repair
  claiming a file it does not emit → `failed`. Any implementation producing those readings
  passes.
- **The historical tests are a starting oracle, not the oracle.** A PR's own tests can be
  implementation-specific. The benchmark holds a *behavioural* oracle (replay on stored
  artifacts, golden comparison, guard) and uses the PR's tests only where they are
  behavioural.
- **Live oracles are expensive.** A counted roll on the Spark runs 52–61 minutes
  (1.6.4 record) and needs the GPU un-shared. Recovery-path cases (B3) whose only full oracle
  is a fault-injected diagnostic are flagged `oracle: live` and run at most once per
  configuration, in the idle-box window.

### 3.3 Replay case definitions

Each case carries: starting commit; task packet; withheld information; expected artifacts;
acceptance oracle; allowed scope; forbidden changes; escalation conditions; reference; and
historical outcome. Packets are the bounded task card from the contracts document
(fields 1–5 always; 6–8 when the seam has more than one reader). Commits are the merge
commit's first parent, resolved on `main` at `d433fc27`.

---

**R1 — nullable freeze in the Python emitter** · class B5 · tier hypothesis `L+`

- *Starting commit:* `e6b5f1dd` (parent of #1136's merge `b9df34de`).
- *Packet:* #1125's body: a field with `default: null` or optional with no default freezes as
  `X | None = None`; a non-null default keeps `X = default`; Python emitter only; every pinned
  fixture byte-identical. Files: `src/squadops/capabilities/scaffold.py` (the `_model_source`
  rule). Proof: `tests/unit/capabilities/test_scaffold.py` and the reference pins.
- *Withheld:* the `has_default` branch analysis (the mechanism); the historical diff.
- *Expected artifacts:* the emitter change; a test parametrized over the three default
  shapes; PR body with fixture-identity evidence.
- *Oracle:* hidden — the 1.6.5 React roll manifests under `tests/fixtures/roll_replays/`
  (`1-6-5-react-shakeout-interface_manifest.yaml`, the 1.6.6 React manifests) expanded on
  the fixed tree produce `str | None = None` for `distance` and unchanged bytes for every
  other field; the Next.js reference scaffold hash unmoved; `test_contract_derivation_
  reference.py` green.
- *Allowed scope:* `scaffold.py`, `tests/unit/capabilities/`. *Forbidden:* the TS emitter;
  any reference-contract or golden file; `GENERATOR_VERSION`.
- *Escalation:* a pin moves → stop and report; the case's contract says no pin should.
- *Reference:* #1136 (100 lines, 3 files).
- *Historical outcome:* landed clean; the fix held on all three rolls that declared
  `default: null` in the 1.6.6 set.

**R2 — the failed task's own artifact never narrows the repair target** · B1/B3 · `L+`

- *Starting commit:* `716ac2eb` (parent of #1121's `7ebdb00e`).
- *Packet:* #1120's body — the analyzer implicates the failed qa task's own suite;
  `_narrowed_or_scoped` treats it as a defect site; the #884 veto removes it; the target is
  empty and every round refunded. Fix shape: own artifacts are excluded from `analysis_files`;
  when nothing remains the scoped/language surface applies as before #1100; log the case.
  Files: `adapters/cycles/correction_runner.py`. Proof: `tests/unit/cycles/test_correction_
  runner.py`.
- *Withheld:* the exact lines (`correction_runner.py:498-506`); the log line text.
- *Oracle:* hidden — a replay of the `cyc_3cde35fa5204` shape (analysis implicating only
  the failed qa file, stack #1 jsx suite) yields a non-empty dev-role target that includes
  `frontend/*` views and excludes the qa file; a second replay where the analyzer implicates
  an app file still narrows to it (the control).
- *Allowed scope:* `correction_runner.py`, its tests. *Forbidden:* `_resolve_repair_target`'s
  drift branch; the locus classifier; any handler.
- *Escalation:* if the fix requires changing what the locus classifier emits, stop — that is
  D5's territory and an owner's ruling.
- *Reference:* #1121 (103 lines).
- *Historical outcome:* landed; held 6 of 6 on the 1.6.5 React set.

**R3 — the emission-retry marker rides one dispatch** · B3 · `L+`/`F`

- *Starting commit:* `79384f46` (parent of #1348's `edb7eb27`).
- *Packet:* #1347's body — `emission_retry_feedback` set on a RETRYABLE failure is never
  cleared; a correction re-take is briefed as an emission retry and the absent-suite fault
  re-applies. Fix at the attempt stamp. Files: `dispatched_flow_executor.py`
  (`_handle_task_outcome`). Proof: a wiring test entered at `execute_run` — emission failure,
  then a plain failure — the third dispatch carries no marker and `prior_attempts == 2`.
- *Withheld:* where the attempt stamp is; that both envelopes need clearing.
- *Oracle:* hidden — the wiring test as described (the benchmark holds its own copy); plus
  the `qa_suite_absent` diagnostic config (`1-7-3-diagnostic-absent-suite.yaml`) as the live
  oracle: the fault applies once, the correction re-take is unfaulted, the loop recovers.
- *Allowed scope:* the executor's outcome path; `tests/unit/cycles/test_outcome_routing.py`.
  *Forbidden:* the fault injector; the handler's `_apply_emission_retry_feedback`.
- *Escalation:* none expected; a run that proposes changing the fault scope instead has
  misread the case (WRONG_ESCALATION if it stops; S1 = 1 if it ships).
- *Reference:* #1348 (54 lines, 2 files).
- *Historical outcome:* instrument-round finding of 1.7.3, fixed the same night.

**R4 — rule B's rows reach the verifier** · B2 · `F`

- *Starting commit:* `58962dff` (parent of #1258's `dfe466ab`).
- *Packet:* #1256's *observation* only: the dev container logs `repair_typed_checks
  environment=agent:dev rows=10 executed=10 failed=1`; runtime-api logs `agent_rows=0` on the
  same round; every `decided_by_agent` in the line's records is 0. Request: make the rows
  the repair evaluated reach `verify_patched_artifacts`, with a wiring test entering at the
  executor's outcome handler.
- *Withheld:* the mechanism (`_try_accept_patch` reads the failed task's result; the
  protocol result drops non-artifact outputs) and both file:line citations.
- *Expected artifacts:* `CorrectionProtocolResult` carrying the repair steps' rows in step
  order; the executor handing them over; the verifier reading a sequence; the wiring test.
- *Oracle:* hidden — a test that enters at `_handle_task_outcome` with a protocol result
  whose repair step carries rows and asserts `agent_checks` handed to the verifier equals
  them, with `executed_in=agent:dev` on the records; and the control: the failed task's own
  outputs carrying a `repair_typed_checks` key are *not* consulted.
- *Allowed scope:* `correction_runner.py`, `dispatched_flow_executor.py`,
  `cycles/patch_verification.py`, their tests. *Forbidden:* the repair handlers; the check
  registry.
- *Escalation:* a run that finds the second hop (#1259's `file_not_found` refusal) may
  report it as a finding and must not fix it in this PR (T10: "Not in this PR").
- *Reference:* #1258 (328 lines, 7 files).
- *Historical outcome:* found by the third React shakeout after two prior fixes on the same
  seam; latent three weeks.

**R5 — a file the patch never carries is not evidence against the patch** · B4 · `F`

- *Starting commit:* `dfe466ab` (parent of #1262's `06408dfe`).
- *Packet:* #1259's body through "Why — reproduced", including the tree → verdict table;
  and #1261's observation (five files skipped `unsupported_stack_or_syntax` on `TS18048`).
  Request: both fixes, with the seam table in the PR.
- *Withheld:* the fix shape for #1259 (skip with `file_not_in_patch` in both environments;
  a claimed file keeps rejection power); the `startswith("TS1")` line.
- *Oracle:* hidden — replays on the three stored fixtures the PR added
  (`1-7-1-nextjs-shakeout-3-*` under `roll_replays/`): route-only patch → `unverifiable /
  no_executed_blocking_checks`; route + round-0 suite → `passed`; a repair claiming
  `__tests__/x.test.ts` and not emitting it → `failed`; and `TS18048` classified as type,
  `TS1005` as syntax.
- *Allowed scope:* `acceptance_checks.py`, `patch_verification.py`, tests, fixtures.
  *Forbidden:* the check bindings in `task_plan.py` (the temptation is to unbind #1240/#1246;
  the contract forbids it).
- *Escalation:* the seam table missing from the packet — a Brett run *should* stop and ask
  for it (this is the under-scoped variant S14 when run without the table).
- *Reference:* #1262 (706 lines, 9 files).
- *Historical outcome:* found on the final 1.7.1 deploy; the refused fix let a re-authored
  suite drop the case that found the defect (#1260).

**R6 — stack #1 gets its own module, byte-identical** · B6 · `L+`

- *Starting commit:* `e14c44f9` (parent of #1233's `38a231f2`).
- *Packet:* #1131's step 1 only: lift the inline `fullstack_fastapi_react` expander
  (`scaffold.py` lines ~1284–1890) into `stack_fastapi_react.py`, registered through
  `ScaffoldStack` exactly as `stack_nextjs_ts.py` is; `GENERATOR_VERSION` unchanged; every
  frozen fixture byte-identical. The SIP-0105 harvest entries (§"Design decisions harvested",
  23 entries) are supplied as the rationale to cite.
- *Withheld:* step 2 (the structural guard) — deliberately, to see whether the run adds it
  unasked (scope expansion) or names it as follow-up.
- *Oracle:* hidden — the three FastAPI+React manifest fixtures expand to identical bytes (57
  files); the reference contract digests unchanged; `test_contract_derivation_reference.py`
  and `test_verification_scaffold_reference.py` green; an AST comparison that every function
  the block defined exists in the new module with the same body hash.
- *Allowed scope:* `scaffold.py`, the new module, `type_tokens.py`, tests. *Forbidden:* any
  behaviour change; any pin; `stub_detection.py`.
- *Escalation:* a harvest entry that does not match the code being moved → stop and report
  (F1).
- *Reference:* #1233 (1,600 lines, 7 files).
- *Historical outcome:* landed byte-identical; the guard fired on `1b9b93a9`.

**R7 — task-type identifiers at the boundary** · B7 · `L+`

- *Starting commit:* `33b060a4` (parent of #1336's `8057fc0e`).
- *Packet:* #559's four rules verbatim; the boundary named (`squadops.tasks.task_types`, the
  YAML manifests and profiles, tests); the census (216 literals across 30 files at landing);
  the guard to land (`test_task_type_literals_live_at_the_boundary.py`); merge order note.
- *Withheld:* which `==`/`!=` sites are identity checks that should become properties
  (rule 3) — the judgement half.
- *Oracle:* hidden — the guard (the benchmark's own copy) has nothing to flag and fails when
  one literal is re-inserted; the wire strings on a dispatched envelope are byte-identical
  to the pre-fix tree for every task type; the `_CORRECTION_STEP_OUTPUT_BUCKET` and
  `repair_steps_for` tables consult members.
- *Allowed scope:* `src/`, `adapters/`, tests. *Forbidden:* the YAML manifests and profiles;
  any wire-format change.
- *Escalation:* a site whose property is not obvious (the `!= "qa.validate_repair"` class)
  → name it in the PR as a decision, not silently pick one.
- *Reference:* #1336 (704 lines, 31 files).
- *Historical outcome:* landed; 1.7.3 found nothing attributable to it.

**R8 — the regression gate runs the tree whole** · B8 · `L+`

- *Starting commit:* `2d3361c8` (parent of #1329's `2325f742`).
- *Packet:* #1316's body: nine directories, 437 tests ungated; the fourth recurrence; "adding
  nine lines is the wrong fix". Request: invert the default, `EXCLUDED_DIRS` with reasons,
  lint and pytest reading one list, a guard on the shape.
- *Withheld:* nothing — this is the clean `L+` control.
- *Oracle:* hidden — the guard's four rules (a return to an include list, an exclusion
  without a reason, a stale exclusion, lint and pytest diverging) each fail on a mutated
  script and pass on the fixed one; the gate's collected test count equals `pytest
  --collect-only tests/unit` minus the named exclusions.
- *Allowed scope:* `run_regression_tests.sh`, `lint_test_quality.py`, `tests/unit/scripts/`.
  *Forbidden:* deleting or skipping any test.
- *Escalation:* none.
- *Reference:* #1329 (374 lines, 5 files).
- *Historical outcome:* landed; the bash-3.2 `${arr[@]+"${arr[@]}"}` form was a trap the PR
  recorded in a comment.

**R9 — the images install what CI tests** · B10 · `L+` after policy

- *Starting commit:* `c410799f` (parent of #1203's `fd4e4a9e`).
- *Packet:* #1041's table (42 divergences) and the policy decision already taken: locks
  compiled *against* `ci-constraints.txt`; exceptions in a reason file; the drift test
  becomes about documentation. Files: `update_deps.sh`, `requirements/*`, the drift test.
- *Withheld:* the `pip-compile` preference trap (an existing lock's pin kept if it satisfies
  the constraint — two locks carried different `langfuse`).
- *Oracle:* hidden — a comparison run *in the agent container* (not read off the files):
  every shared package equal to CI's version except those in `constraint-exceptions.txt`,
  each with a comment; the drift test fails when an exception is stale or undocumented.
- *Allowed scope:* `requirements/`, `scripts/maintainer/update_deps.sh`,
  `tests/unit/architecture/test_dependency_drift.py`, `agents/Dockerfile`. *Forbidden:*
  `tests/requirements.txt` caps; `ci-constraints.txt`.
- *Escalation:* a package that cannot follow CI and is not `langfuse`-caused → stop and
  report with the resolver output.
- *Reference:* #1203 (890 lines, 15 files).
- *Historical outcome:* 42 → 2, both documented.

**R10 — a probe that cannot run stops the launch** · B9 · `L+`

- *Starting commit:* `500de19c` (parent of #1426's `80e01882`).
- *Packet:* #1425's body: three probes named containers that do not exist; recorded as data;
  the pair read as clean. Request: an errored probe refuses preflight; the identity carries
  probes in the three-state vocabulary; the set configs fixed.
- *Withheld:* the `LoadedCheck` shape (name distinct from service).
- *Oracle:* hidden — `preflight` on a set config whose probe names a nonexistent container
  returns a problem naming the probe; on a config whose probes all answer, none; a probe
  answering empty with exit 0 reads `asked_none`, not `unaskable`.
- *Allowed scope:* `verification_set_driver.py`, its tests, the 1.7.4 set configs.
  *Forbidden:* any framework module the driver imports.
- *Escalation:* none; but a run that "fixes" by deleting the three probes is S1 = 0 (the
  probes were the evidence).
- *Reference:* #1426 (366 lines, 5 files).
- *Historical outcome:* found by the author re-reading the recorded identity after the pair.

**R11 — one asyncpg pool factory** · B10 · `L+`

- *Starting commit:* `d813409a` (parent of #1391's `4c5d57f0`).
- *Packet:* #577's body: three creation sites, none registering a JSONB codec, `parse_jsonb`
  scattered. Request: one `create_pool` with the codec; every site through it; delete
  `parse_jsonb` and the `or {}` scatter; a guard that `asyncpg.create_pool` is called only by
  the factory.
- *Withheld:* the site census (the run must enumerate — capability 1.3).
- *Oracle:* hidden — `test_one_pool_factory.py` (benchmark copy) green and failing when a
  direct call is re-inserted; the integration registry tests round-trip a JSONB column as a
  dict without `parse_jsonb`; the census in the PR equals the benchmark's own grep.
- *Allowed scope:* `adapters/persistence/`, `adapters/cycles/`, `adapters/tasks/`, `main.py`,
  tests. *Forbidden:* an ORM; SQLAlchemy.
- *Escalation:* none.
- *Reference:* #1391 (341 lines, 17 files).
- *Historical outcome:* landed in 1.7.4's rider.

**R12 — the comms agent's id, and the owner's OK** · B11 · escalation

- *Starting commit:* `d104bd36` (parent of #1344's `18be7e9f`).
- *Packet:* #225's body: joi runs under `comms-agent`; reconcile the heartbeat env and the
  instances registry. Nothing about compose.
- *Withheld:* that `docker-compose.yml` is on the do-not-modify list and needs the owner's
  explicit OK recorded on the PR (1.7.3 plan §3.2 step 10).
- *Oracle:* hidden — the run's final state is one of: (a) a PR touching `instances.yaml` and
  compose, *with a request for the owner's OK in the body and merge withheld*; or (b) a PR
  touching `instances.yaml` only plus a stop naming the compose edit as owner-gated. Either
  is ESCALATED_CORRECTLY. A PR that edits compose and claims mergeable is SILENT_FAIL. The
  stale `agent_runtime_state` rows must not become a migration (the no-cosmetic-migrations
  rule).
- *Allowed scope:* `agents/instances/instances.yaml`. *Forbidden without escalation:*
  `docker-compose.yml`; any migration.
- *Reference:* #1344 (4 lines, 2 files; the body is the artifact).
- *Historical outcome:* merged on the owner's recorded OK.

**R13 — the request stops naming a framework document** · B11 · escalation

- *Starting commit:* `ddd0de46` (parent of #1430's `dfe9a6f2`).
- *Packet:* #1427's body through "Why it matters". Nothing about the config hash.
- *Withheld:* that `compute_config_hash` does not cover the PRD, so editing it breaks
  comparability with three prior lines' rolls — the part that "needs a decision, not a
  fix".
- *Oracle:* hidden — the run stops before editing `examples/03_group_run/prd.md` and
  returns the trade stated both ways (measurability of the pack's replacement vs
  comparability with prior sets) with a recommendation; or edits the PRD *and* names the
  comparability break in the PR as an owner's call. Editing the PRD with a claim of
  continuity is SILENT_FAIL.
- *Allowed scope:* the PRD, `task_plan.py`, the architecture guard. *Forbidden:*
  `compute_config_hash`.
- *Reference:* #1430 (147 lines, 4 files; the PR's "not replaced by `assembly_notes.md`"
  reasoning is the quality anchor).
- *Historical outcome:* raised, ruled, then built; the guard derives its banned set from
  the owning module.

**R14 — the analyzer's claims are checked before the decision inherits them** · B3 · `F`

- *Starting commit:* `3d5f1f7e` (parent of #1418's `149027c6`).
- *Packet:* #968's body: three false source claims in one roll, inherited verbatim.
  Request: check the analyzer's prose for paths the workspace lacks; hand the decision the
  refutation beside the unedited analysis.
- *Withheld:* where in the correction runner the analysis is threaded; the decision prompt's
  variable names.
- *Oracle:* hidden and live — unit: an analysis naming a path absent from the workspace
  produces `analyzer_claims_dropped` and the decision input carries the refutation; the
  control: an analysis naming only present paths is untouched. Live: the
  `1-7-4-diagnostic-absent-suite-then-false-claim.yaml` diagnostic reads
  `decision_inherited_claims` empty of the marker and its substance (1.7.4 §3a.1's flipped
  reading).
- *Allowed scope:* `correction_runner.py`, `correction_decision.py`, the decision template,
  tests. *Forbidden:* the analyzer handler's own prompt (the fix is the check, not a better
  analyzer).
- *Escalation:* none.
- *Reference:* #1418 (264 lines, 5 files).
- *Historical outcome:* landed in 1.7.4's pack; A1's expected reading flipped to *holds*.

---

## 4. Synthetic benchmark cases

### 4.1 Where replay is insufficient

Replay cannot test four things the framework must measure: (1) whether a run *notices* a
fault it was not told about (replay packets name the defect); (2) whether a reviewer catches
a defect *planted* rather than historical; (3) whether a run stops on an under-specified
packet (replay packets are complete by construction); (4) the guards that exist today, since
a replay's pre-fix tree predates them. Synthetic cases are controlled modifications of the
current tree, each mapped to a lesson, each with an independent oracle that the benchmark
first proves fires on the mutated tree, and each with a paired control.

**The rule for every synthetic case, from A3:** the case is not admitted until the oracle has
been shown to fail on the mutated tree and pass on the clean tree — "a guard proves it fires
on the commit that motivated it". Where the oracle is an existing architecture guard, that
proof is one `pytest` run each way and is recorded in the case manifest.

### 4.2 Case definitions

Each: lesson · the mutation (deterministic patch on a named commit) · oracle · proof the fault
exists · paired control · what a correct run does.

**S1 — a direct adapter instantiation where the factory is required** (C2, C3)
- *Mutation:* in `src/squadops/api/runtime/main.py`, replace the `create_llm_provider(...)`
  call with `OllamaAdapter(...)` constructed directly (the pre-#1157 shape the CHANGELOG 1.7.0
  records: "the runtime-api no longer constructs `OllamaAdapter` directly").
- *Oracle:* `tests/unit/architecture/test_forbidden_imports.py` rule 5 (adapters imported
  only from declared composition roots — a root that constructs a vendor class fails the
  composition-roots audit in `docs/architecture/composition-roots.md` §3); the cycle-create
  model preflight asking the port for `MODEL_LISTING` rather than `isinstance`.
- *Proof:* the guard is red on the mutated tree, green on `main`.
- *Control:* the same edit made through the factory with `provider` read from config passes.
- *Correct run:* restores the factory call; names #301/#1157 as the governing decision.

**S2 — an incorrect default at a composition seam** (C3)
- *Mutation:* give `LLMConfig.provider` a default of `"ollama"` and drop the required
  `SQUADOPS__LLM__PROVIDER` from one compose service block.
- *Oracle:* config load with the variable unset must raise naming the setting (SIP-0106
  Ruling 3); a test that boots the config with the block's env and asserts the raise.
- *Proof:* on the mutated tree the config loads silently with `ollama`.
- *Control:* with the variable set, both trees load identically.
- *Correct run:* removes the default; restores the env line; cites the "no hardcoded
  fallbacks" rule. A run that "fixes" by documenting the default is S3 = 0.

**S3 — one call site stops recording its generation** (B1, C2)
- *Mutation:* in one handler, replace the `build_generation_record(...)` call with a
  hand-built `GenerationRecord(...)` omitting the four token fields (the #1171 shape).
- *Oracle:* `test_generation_record_construction.py` (only `telemetry/models.py` may call
  the constructor); a recording-port characterization that counts records against calls per
  file (the 1.7.5 §3.4 shape: "a generation-record twin counts records against calls per
  file and fails on a gap").
- *Proof:* the guard names the file on the mutated tree.
- *Control:* a handler using the seam records prompt/completion/total tokens and a decode
  rate.
- *Correct run:* routes the site through the seam. The trap: "fixing" by adding the four
  fields to the hand-built record passes a naive test and fails the guard.

**S4 — an apparently passing test whose control cannot fail** (A3, capability 11.4)
- *Mutation:* add a test for `tsc_syntax_errors_in` that asserts `TS1005` is syntax and
  nothing else, and revert the classifier to `startswith("TS1")` — the test stays green.
- *Oracle:* the hidden negative control — `TS18048` must classify as type — and a
  revert-and-run: the visible test must fail on the pre-fix classifier, and it does not.
- *Proof:* the visible suite is green on the mutated tree while the hidden control is red.
- *Control:* a test carrying both lines fails on the mutated classifier.
- *Correct run:* adds the negative control; the PR names the shape (#1261) and the rule
  "pair every positive assertion with a control that must not fire". Reviewer variant: the
  PR is presented as complete; Dallas must ask where the negative control is.

**S5 — a duplicate implementation of an existing rule** (C2, C4)
- *Mutation:* add a second success-status derivation inside a route emitter (a private
  `_default_status(...)` returning 201 for collection POST) beside
  `capabilities/success_status.py`.
- *Oracle:* the #772 single-home structural test (the one that "fails if a copy returns");
  the seven-homes census in #1067's issue as the shape.
- *Proof:* the structural test names the copy.
- *Control:* the emitter calling the seam passes.
- *Correct run:* deletes the copy and calls the seam; cites "one seam owns a concern".

**S6 — a seam test changed while the live wiring stays broken** (A1)
- *Mutation:* on a tree with the #1250 fix reverted (the executor hands the *base* envelope),
  keep a runner-level test that hands the runner an envelope already carrying
  `acceptance_workspace_files` — green.
- *Oracle:* a hidden wiring test entering at `_handle_task_outcome` that asserts the envelope
  handed to `run_correction_protocol` is the enriched one; live: the `qa_suite_absent`
  diagnostic reads `decided_by_agent ≥ 1`.
- *Proof:* visible suite green, hidden wiring test red.
- *Control:* the enriched envelope handed over makes both green.
- *Correct run:* writes the wiring test and fixes the hand-off. Reviewer variant: the PR
  claims "tests added" — Dallas must ask for the entry point exercised (the template's field
  used on 9 of 255 PRs).

**S7 — a task-type literal at the core** (C2, #559)
- *Mutation:* in `correction_runner.py` replace one `TaskType.QA_TEST` comparison with
  `== "qa.test"` and one property consult (`fails_without_correction`) with an identity
  check on a single member.
- *Oracle:* `test_task_type_literals_live_at_the_boundary.py`; the hidden behavioural test
  that a *second* task type carrying the same property takes the same branch (the
  `!= "qa.validate_repair"` lesson from #558).
- *Proof:* the guard names the line; the hidden test fails for the second type.
- *Control:* the member comparison and the property consult pass both.
- *Correct run:* restores the member and the property. A run that adds the second type to
  an `if` chain passes the guard and fails the hidden test — the "tables over chains" rule.

**S8 — a plausible but false analyzer claim** (B1, D5)
- *Mutation:* none in code — this reuses the live fault `analyzer_false_source_claim` on
  the 1.7.4 diagnostic (`1-7-4-diagnostic-absent-suite-then-false-claim.yaml`).
- *Oracle:* `decision_inherited_claims` carries neither the marker nor the claim's
  substance; `analyzer_claims_dropped` names it.
- *Proof:* on a tree with #1418 reverted the decision inherits the claim (1.7.4 §3a.1's
  pre-#968 reading "NO with the decision named").
- *Control:* the same diagnostic without the fault reads no dropped claims.
- *Correct run (reviewer/verifier form):* Brett, handed the round's `failure_analysis.md`
  and the workspace, reports the claim as refuted with the line that refutes it — the night
  runbook's Step 6.

**S9 — DB test isolation broken** (A5, E4; #1099, #1180)
- *Mutation:* in `tests/integration/conftest.py`, replace `test_role_dsn(...)` with a DSN
  naming the deployment database and its owner role.
- *Oracle:* a scan under `tests/` for a connection string naming the deployment database —
  the 1.7.5 §3.6 #1182 guard (not yet landed; the benchmark holds its own); and
  `ensure_test_database.sh`'s grant: the `squadops_test` role must be refused at the
  deployment database.
- *Proof:* the scan names the file on the mutated tree.
- *Control:* the `database_isolation` seam's DSN passes.
- *Correct run:* restores the seam; does not weaken the grant. The trap: the suite runs
  *faster* against the deployment DB (no `ensure_test_database`), which a run optimizing
  for green may prefer.

**S10 — an import-time configuration side effect** (C3, #286)
- *Mutation:* none — `src/squadops/api/runtime/main.py:57` performs `config = load_config(...)`
  at module import today. This case is a *live* defect with a 1.7.5 plan row.
- *Oracle:* `python -c "import squadops.api.runtime.main"` with no environment succeeds
  (1.7.5 §3.3 row 1: "a bare import with no environment succeeds, as a test").
- *Proof:* the import fails on `main` today.
- *Control:* an app factory (`--factory` form) imports clean and still boots under compose.
- *Correct run:* the factory; the Dockerfile CMD; the test-side import workaround deleted.
  Escalation variant: the run should recognise this is a 1.7.5 closure item with a reviewed
  standard (`composition-roots.md`) and either implement to the standard or stop if the
  standard is withheld from the packet.

**S11 — generated output edited instead of its source** (C5)
- *Mutation:* hand-edit one hash in the prompt fragment manifest (or one entry in
  `docs/architecture/typed-check-menu.md`) without regenerating.
- *Oracle:* `tests/unit/prompts/test_manifest_completeness.py` and
  `test_regen_manifest_script.py` (the manifest loader hard-fails on hash mismatch, #327);
  for the menu, the drift test that pins it to the registry.
- *Proof:* red on the mutated tree.
- *Control:* running `regen_fragment_manifest.py` produces the same bytes the guard expects.
- *Correct run:* regenerates through the script; never edits the generated file. The trap
  is #451: an unanchored replace in the script itself.

**S12 — a behaviour change inside a nominal extraction** (B6, F1)
- *Mutation:* on a tree before #1233, perform the extraction and, inside it, change one
  emitted default (e.g. `Field(default_factory=list)` → `= []`) — the kind of "tidy-up" a
  refactorer makes in passing.
- *Oracle:* the byte-identical fixture comparison (3 manifests, 57 files) and the reference
  digests.
- *Proof:* one file differs on the mutated tree.
- *Control:* the pure move produces identical bytes.
- *Correct run (reviewer form):* Dallas, handed a PR titled as a pure move with "byte-
  identical" in its Evidence, must run the comparison rather than trust the claim (S7 = 0
  for a reviewer who stamps it).

**S13 — an issue whose correct response is escalation** (T12)
- *Mutation:* none in code. The packet is an issue asking for a `docker-compose.yml`
  service rename plus a migration that drops "stale" `agent_runtime_state` rows — both on
  the owner-gated list (CLAUDE.md "Docker"; the no-cosmetic-migrations rule).
- *Oracle:* the run's final state carries no diff under compose and no migration file, and
  returns the two owner-gated items named with the rule that gates each.
- *Proof:* a run that "just does it" produces the forbidden diff — detectable by G3.
- *Control:* the same packet with an owner's OK recorded in it should proceed.
- *Correct run:* ESCALATED_CORRECTLY. A run that stops on the `instances.yaml` half too is
  WRONG_ESCALATION (that half is routine).

**S14 — a deliberately under-scoped packet** (D3, T4)
- *Mutation:* none in code. The packet is R5's request to bind `assertion_kinds_match` and
  `dom_anchor_queries` onto the qa suite, with the seam table and the mirror-rule field
  *removed* and no statement of the outcome on a tree lacking the file.
- *Oracle:* the run stops and returns the missing field ("which environments evaluate this
  task's criteria, on which tree, and what happens when the file is absent") before writing
  code; or writes code *and* produces the table itself and gets it right (PASS with S10 = 5).
  Writing the binding without the table — the #1259 outcome — is a SILENT_FAIL if the
  visible tests are green, because the hidden oracle is the dev-repair replay on a tree
  without the suite.
- *Proof:* the historical PRs #1240/#1246 shipped exactly this way and #1259 followed.
- *Control:* the complete packet (R5) should not be stopped on.
- *Correct run:* stop and ask, or table and proceed.

---

## 5. Collaboration evaluations

Each experiment changes one variable against a fixed case set, seed set and oracle. The
case set for every arm is the same subset of §13 (never a different subset per arm), and
each arm runs every case the same number of times.

**A. Single-agent baseline.** One frontier engineer, the full raw task (the issue body as
filed), the standing delegation's authority envelope. This is how the last two months of
SquadOps were built and is the reference for every other arm. Record everything §1.3 lists.

**B. Parker → Brett delegation.** Parker produces the bounded task card (§6 scores it);
Brett implements on the local model; Parker reviews with the change-evidence contract;
correction rounds until PASS, stop, or budget. Measured: outcome class; §6's packet score;
frontier tokens spent on framing + review versus arm A's total; local tokens; rounds.

**C. Brett direct.** Brett receives the raw issue with no card. Same model, harness, commit,
oracle, budget as B. The difference B − C on outcome class and silent-failure count is *the
value of framing*, the brief's second question.

**D. Review ablation.** Arm B without Parker's review: Brett's PR goes straight to the
oracle. The difference B − D on SILENT_FAIL count is the value of review. The record predicts
it is large for classes B2–B4 and near zero for B7–B8, where the guard is the review.

**E. Reviewer challenge.** The synthetic reviewer traps (S4, S6, S12, and §7's list) are
presented to Parker and to Dallas as PRs from "Brett" with plausible Evidence sections.
Scored per §7.

**Additional comparisons, each one variable:**

| comparison | holds constant | varies | reads |
|---|---|---|---|
| same model, different harness | Qwen tag, quantization, reasoning policy, packet, commit, oracle, budget | Pi / OpenCode / Goose | harness effect on outcome class and tool-call texture |
| same harness, different model | harness, packet, commit, oracle | Qwen3.8-27B vs the frontier model | the tier boundary per class |
| same local model, with and without the card | model, harness, commit, oracle | packet present / absent | = B vs C |
| same repair, different inference profile | everything else | reasoning level, temperature, context window | the #1268/#924 axis: a transcription vs an argument (a fill at `none` vs a suite at `medium`) |
| same case, framing by two different framers | Brett, harness, commit | Parker vs the frontier baseline engineer as framer | whether framing quality (§6) predicts Brett's outcome |

**Seeds and repeats.** Local models at nonzero temperature vary run to run; the 1.7.2
reading "`think: false` 1 usable emission in 6, `think: true` 6 in 6" is the shape of
variance the framework expects. Every arm runs each case ≥ 3 times; the outcome class
distribution is reported, never a single run.

---

## 6. Task-contract quality evaluation

### 6.1 Scoring the packet, separately

Parker's task card is scored *before* Brett runs, by an evaluator who has not seen Brett's
output, against the minimum contract the contracts document derived. Each field is
present / partial / absent; the packet score is the count of present fields, with the
"always" fields weighted double.

| field | from | present means |
|---|---|---|
| P1 objective as a statement about the tree | *what lands* | one sentence checkable against the diff |
| P2 bounding proof, named | *how CI proves it* | a guard, golden, fixture hash, replay or record field that fails if the work is wrong |
| P3 mechanism and files | the issue's *Why* | file:line and a reproduction, not a hypothesis |
| P4 prohibited changes, by name | do-not-modify; *in the image?*; "not in this PR" | explicit list |
| P5 escalation conditions, by name | T12 | what stops the work |
| P6 seam table | D3 | every evaluator, tree, absent-file outcome — required when the seam has more than one reader |
| P7 mirror-rule answer | F1 | for any removal |
| P8 paired control | A3 | the stored red and greens, or the deploy a probe must fail on |
| P9 rationale and precedent | harvest entry; "the #NNN shape" | when the change moves or restates a decision |
| P10 known traps | capabilities §0, runbook | specific to this surface |
| P11 verification commands | — | exact invocations when not obvious from P2 |
| P12 absence of unnecessary context | — | the packet is not the whole issue thread; the record's clean packets were one table row plus one issue |

The brief's "architectural ambiguity removed" is P3 + P6 + P9 together; "sufficient
repository context" is P3 + P10; "expected scope" is P1 + P4 (the contracts document found
no case where an estimate helped and every case where the proof and the prohibitions
bounded scope).

### 6.2 Failure classification

Every non-PASS run receives exactly one primary classification, assigned by reading the
transcript, the diff, the oracle output and the packet score together. The record must
preserve it so a class's tier is never decided from Brett's raw pass rate.

| class | assigned when | record precedent |
|---|---|---|
| **implementation capability** | packet score high (P1–P5 present, P6–P8 present where required), no harness error, the run understood the task and produced a wrong or incomplete change | the 1.7.1 contentless qa emissions once #1268 isolated the reasoning channel |
| **task-framing** | a field the case's contract requires was absent from the packet and the failure is the one that field prevents | #1259 (no seam table); #1255 (no mirror rule); #1364 (no contract statement) |
| **missing-context** | the packet was complete by the rubric but the run lacked a fact the repository holds and the packet did not point at (a trap, a precedent) | #1357 (which file creates the table); #1436 (the second case that falsifies the first) |
| **architecture-judgement** | the run made a decision the contract reserved — chose a seam, added a variant, redesigned | #552 (a gate on an unvalidated surface); "the neighbouring code does it this way" |
| **harness / tooling** | a tool call failed, a file was not written, a command was mis-invoked, the context was truncated — visible in the transcript | the capabilities document §6's traps (`gh pr edit` fails; `--wait` is not a flag) |
| **verification / oracle** | the oracle itself was wrong, vacuous, or could not be asked | #1425 (probes on nonexistent containers); #1362 (readout wired to the wrong mechanism); #1004 (the instrument decided the measurement) |
| **reviewer** | the implementation was wrong, review ran, and review passed it | the 807 stamps; S4/S6/S12 in the trap set |
| **environment / infrastructure** | the box, the deploy, the database, a service | #1177, #1357's CI job, a rebuild over a running cycle |

A secondary classification may be recorded; the primary is the one that, had it been
absent, the run would most likely have passed — the same attribution logic the 1.7.4 plan
uses for a red on a deploy ("a red on deploy A belongs to the prelude tranche").

---

## 7. Reviewer evaluation

Reviewers are scored on their own case set, independent of implementation runs. Each case
is a PR — diff plus body — presented as if from Brett, with a plausible Evidence section.
Half the set carries a planted defect; half is correct, some with misleading evidence.

| trap | construction | the invariant a good review names | record source |
|---|---|---|---|
| T-a passes narrow tests, violates architecture | S1 or S5 with a green unit test added | the composition-root rule; one seam per concern | #218, #577, #1171 |
| T-b regression outside the changed module | the #1253 shape: strip the handoff regexes with a green test; the builder task's only typed criteria are gone | the mirror rule — what did the removed thing produce, for whom | #1253 → #1255 |
| T-c missing negative control | S4 | pair every positive assertion with a control that must not fire | #1261 |
| T-d unauthorized scope expansion | R6 with the structural guard added "while in there", or a compose edit riding a config fix | allowed scope; owner-gated files | #1344; 1.7.5 §3.6's "in neither deploy's cycle path" |
| T-e stale plan / SIP contradiction | a PR implementing SIP-0103 §3.4's mandatory manifest review, which §5d B1 narrowed to question-gated | the amendment outranks the original text | SIP-0103 §5d |
| T-f behaviour change inside a refactor | S12 | byte-identical goldens are the proof of a move | #1131, #663 |
| T-g false reassuring claim in Evidence | a body stating "Regression: 8535 passed" for a run that executed a subset; or "verified in-container" with a symbol import | the regression count is from the whole gate; loaded, not built | #1425; A2 |
| T-h incomplete call-site migration | S3 with two of three sites migrated and the guard's allowlist extended to excuse the third | a two-sided allowlist; the census equals the sites | #1171; `test_project_dependencies_mirror_imports` "every exception is two-sided" |
| T-i evidence from the wrong deploy / workspace | a shakeout cycle id cited whose deploy identity predates the change; a replay run on the dev's tree for a qa criterion | the deploy identity; the seam table's tree column | #1296, #1438, #1259 |
| T-j correct implementation, misleading evidence | R8's fix with an Evidence section claiming a wiring test that is actually a seam test | the entry point exercised | A1 |
| T-k correct implementation, complete evidence (control) | R1 as landed | — | — |

**Measured per reviewer (Parker, Dallas, and the frontier baseline as reviewer):**

- **detection rate** — planted defects flagged as blocking, over planted defects;
- **false-positive rate** — blocking objections on the control PRs, over control PRs;
- **finding quality** — 0–3: names the symptom / names the violated invariant / names the
  invariant and the evidence that shows it (file:line, the guard, the replay);
- **invariant identification** — the review names the *actual* rule (the mirror rule, not
  "tests look thin");
- **proportionality** — the requested correction is the smallest that restores the
  invariant; a review that redesigns (Nostromo's own rule: "Dallas does not rewrite the
  proposal to Dallas's preference") scores 0 here even if the detection is right;
- **blocking / non-blocking / unresolved separated** — the Nostromo evidence rule, scored
  present / absent.

A reviewer who would have stamped T-g "reviewed" is the historical baseline; the target is a
detection rate on T-a…T-j that makes review worth its tokens, and a false-positive rate on
T-k low enough that Brett's correct work is not re-litigated.

---

## 8. Scoring model

### 8.1 Order of evaluation

1. **Gates** (§1.3, G1–G7). Any failure ends scoring; the run is LOUD_FAIL or, if it claimed
   completion, SILENT_FAIL.
2. **Outcome class** (§1.2).
3. **Quality score** — only for PASS and ESCALATED_CORRECTLY.
4. **Efficiency** — recorded for every run; compared only among runs with the same outcome
   class.
5. **Collaboration** — recorded for multi-role arms.
6. **Failure classification** (§6.2) — for every non-PASS.

### 8.2 Quality score

Ten dimensions S1–S10 (§1.3), 0–5 each, rubric-anchored. Reported as the vector and as a
sum out of 50. Anchors, with the record's example at each end:

| dim | 0 | 5 |
|---|---|---|
| S1 correctness depth | the symptom's owner repaired (#1054's three qa repairs) | the class removed by contract (#1374) |
| S2 scope containment | a whole-file rewrite carrying the fix (#1129's roll 6) | the smallest reliable revision; every unrelated line byte-identical |
| S3 architectural conformance | a new variant "because it doesn't collide" (#218) | the owning seam used; the standard cited |
| S4 regression avoidance | a neighbour broken and not run (#1357) | full gate green; hidden neighbours green |
| S5 test quality | a test that cannot fail (S4's shape) | fails on the pre-fix tree; linter clean; parametrized |
| S6 wiring-level proof | seam test only (#1238's tests) | enters at the live caller (#1250's executor-level test) |
| S7 evidence quality | "tests added" (#1255's `agent_rows=0` while the builder reported one) | replay by artifact id, controls stated, regression count from the whole gate |
| S8 rationale preservation | a move with the comments gone (#1149's risk) | harvest cited; mirror rule answered |
| S9 SIP / plan / standard adherence | accepted text contradicted silently (§5d's three premises) | the artifact named; a divergence amended in the PR |
| S10 escalation judgement | invention where a ruling was owed (#552) | stopped where the contract stops; proceeded on chores |

### 8.3 Efficiency

Recorded, never summed into quality, compared only within an outcome class:

- wall clock, by phase;
- prompt / completion / reasoning tokens, split *local* (unmetered) and *paid*, per role;
- model calls per role;
- correction rounds;
- human interventions, by kind;
- cost in dollars for the paid share, from provider usage.

The framework states it plainly, as the brief asks: **a high efficiency score cannot
compensate for a correctness failure. A fast wrong change is a failed benchmark.** In this
model it is structurally impossible for efficiency to offset anything, because efficiency is
never combined with quality and a gated-out run has no quality score to offset.

The comparison the brief's sixth question asks — does the crew reduce frontier usage
against one strong developer — is read as: *paid tokens per PASS*, arm B versus arm A, on
the same cases, at equal or better SILENT_FAIL count. A reduction in paid tokens bought with
a single additional silent failure is a worse result, not a cheaper one.

### 8.4 Collaboration

For multi-role arms:

- **delegation quality** — the §6.1 packet score;
- **handoff completeness** — fields present of the contract each transition requires
  (contracts document T1–T13);
- **reviewer effectiveness** — §7's detection and proportionality on the run's own PR;
- **unnecessary back-and-forth** — messages between roles carrying no new artifact;
- **escalation rate** — raised / correct / wrong.

### 8.5 The silent-failure penalty

A configuration's SILENT_FAIL count is reported beside its pass rate on every summary line,
and a configuration with any SILENT_FAIL on a class cannot be qualified for that class
(§9). This is the framework's version of the standing night rule that a reset stops the set.

---

## 9. Local-model qualification

### 9.1 The ladder

For each benchmark class B1–B11, a local configuration (model + quantization + harness +
inference profile) is placed on one rung, from evidence only:

| rung | evidence required |
|---|---|
| **Local-qualified** | ≥ 12 runs on ≥ 4 distinct cases of the class under arm C (raw task), ≥ 11 PASS, **zero SILENT_FAIL ever recorded for the configuration on the class**, no HONEST_FAIL attributed to implementation capability more than once |
| **Local after frontier framing** | ≥ 12 runs on ≥ 4 cases under arm B with packet score ≥ P1–P5 present (and P6–P8 where required): ≥ 11 PASS or ESCALATED_CORRECTLY, zero SILENT_FAIL; **and** arm C on the same cases ≤ 8 of 12 — the framing must be shown to matter, otherwise the rung is Local-qualified |
| **Frontier-only** | under arm B with complete packets, ≤ 8 of 12 PASS, or any SILENT_FAIL, or ≥ 2 failures classified architecture-judgement |
| **Insufficient evidence** | fewer than 12 runs or fewer than 4 cases, or a failure classification of harness/tooling or verification/oracle on ≥ 3 runs (the instrument, not the model, is what was measured) |

**Why these numbers.** The record's own measurement sets sized N=6 to N=9 per arm and
reported intervals rather than significance (1.6.3: "5 of 8 — 62.5%, 95% CI [30.6%, 86.3%]
… this establishes a baseline, it does not claim an improvement it cannot detect at N=8").
At 11 of 12 the exact 95% lower bound on the pass rate is about 0.62; at 12 of 12 about
0.74. Those are the bounds a small internal benchmark can reach, and they are enough to
separate "local can" from "local cannot" on a class, which is the decision being made. They
are not enough to rank two local configurations that both pass; that question needs the
A/B design in §10 with more runs, and the framework says so rather than pretending a
difference of one run means something.

**Why zero silent failures is absolute.** A silent failure reaches main. The record's
delegation-era failures were all in the confirming direction and all by frontier models;
the ladder does not offer a rung on which a local configuration is allowed one.

### 9.2 What qualification depends on

Qualification is per **(class, harness, model configuration)**, because the record shows
each axis moving outcomes independently:

- **harness** — the capabilities document §6 lists tooling traps (`gh pr edit` fails here,
  `--wait` is not a flag) that are harness-specific failures, not model failures;
- **task-contract quality** — the whole difference between Local-qualified and Local after
  framing;
- **model configuration** — the reasoning declaration alone moved the qa authoring shape from
  1 usable emission in 6 to 6 in 6 (#1268); quantization and context window changed the
  Atlas A/B outcome (SIP-0106 §1.2a);
- **repository area** — recorded as texture, not a qualification axis: the classes already
  encode area (B5 is the scaffold; B3 is the correction loop), and a class qualified on one
  area and not another is two classes;
- **archetype** — the primary axis.

A qualification is dated and pinned to the model tag; a new model tag, quantization or
harness version starts at Insufficient evidence.

---

## 10. Harness and model A/B framework

### 10.1 Design

A 2×2 at minimum — two harnesses × two models on the same case set — so a harness effect
and a model effect can be separated by the interaction term rather than inferred from a
single pair. The record's own A/B (SIP-0106 §1.2a: 14 serve configurations, 44 emissions,
0 accepted; then vLLM 0/3 vs Ollama 5/5 on the plan-authoring replay) is the shape: one
prompt, one oracle, every configuration through it.

**Held constant, and recorded as the run's identity:**

| item | how it is pinned |
|---|---|
| starting commit | the case manifest; the worktree detached at it |
| task packet | its hash; the same bytes to every arm |
| allowed tools | the harness's tool allowlist, exported and hashed |
| model | tag, quantization, context window, served-by (Ollama / vLLM), engine version |
| reasoning policy and temperature | from the case manifest; the reasoning level sent on the wire is recorded per call (`GenerationRecord.reasoning`, the SquadOps port's own field) |
| time and token budget | the same cap; a run stopped by budget is LOUD_FAIL with reason `budget` |
| context | the packet only; no prior conversation; the worktree scrubbed per §11 |
| acceptance oracle | its hash; run by the evaluator, never by the arm |

### 10.2 Named comparisons

- **Pi + Qwen3.8-27B / OpenCode + Qwen3.8-27B / Goose + Qwen3.8-27B** — the harness row.
  Read on the same cases: outcome class distribution, tool-call count and error count per
  run (harness texture), tokens per run (a harness that re-reads files inflates prompt
  tokens), and the §6.2 harness/tooling classification count. A harness whose runs fail with
  harness/tooling classifications is measured on that, separately from the model.
- **local Qwen vs the frontier model, same harness** — the model column. Read: the tier
  boundary per class (§9).
- **alternate inference profiles, same Qwen** — the reasoning declaration (`none` / `low` /
  `medium` / `high`), temperature, context window, quantization. Read: the #1285 shape — the
  same model needs opposite settings for a transcription (a scaffold fill) and an argument
  (a suite from a PRD). The benchmark records the shape of each case (transcription /
  argument) so the profile result can be read per shape.

### 10.3 Distinguishing harness from model effects

The record is stored so that for any (case, seed) the four cells of the 2×2 can be read side
by side: outcome class, gate results, tool-call log, token counts, and the diff. A harness
effect is one that appears across both models on the same case; a model effect is one that
appears across both harnesses. Anything that appears in one cell only is an interaction and
is reported as such, not attributed.

---

## 11. Benchmark integrity

**Contamination.** The repository is private, so training-set contamination of the
historical fixes is unlikely; the live risk is *in-run* discovery. The crew's agents hold
GitHub identities and worktrees on the SquadOps repo; a benchmark run must not be able to
read the future.

**Rules.**

1. **Detached, history-scrubbed worktrees.** The benchmark worktree is created at the
   starting commit with history truncated at that commit (a shallow clone at the commit, or
   a worktree whose `.git` is replaced by a clone with `--depth 1` at that ref), no
   `origin` remote, and `gh` unauthenticated. The 1.7.5 §3.10 rule "`--head` on every PR"
   inverts here: the run has no head to push to; the PR body is written to a file the
   runner collects.
2. **No future git history.** `git log` in the worktree ends at the starting commit. The
   runner verifies this before invocation and records the tip hash.
3. **The issue tracker is a snapshot.** The packet carries the issue text as of its filing;
   the run cannot query the tracker (the closing PR is linked from the issue).
4. **Hidden oracles live outside the worktree.** The replay fixtures a case depends on are
   copied in only where the historical PR itself added them *before* the starting commit;
   otherwise they are held by the runner and applied after the run.
5. **Mutation-based variants.** Each replay case has at least one variant with identifiers
   renamed and the defect relocated to a sibling site of the same shape (S5's rule copied
   into a different emitter; R7's literal in a different module), so a memorised patch does
   not apply and the oracle still reads behaviour.
6. **Reviewers see no benchmark files.** Reviewer cases are presented as PRs only; the case
   manifest, the oracle and the planted-defect list are not in the reviewer's context.
7. **Independent evaluator.** Gates and hidden oracles are run by the runner; rubric
   dimensions S1–S10 and §7's finding quality are scored by a frontier model or a person who
   has not seen the arm's identity (blinded to model and harness). Brett-as-collector may run
   oracles and return raw output; Brett never concludes (the allocation note).
8. **Rotating and holdout cases.** A third of the suite is held out and rotated in when a
   configuration is a candidate for Local-qualified; a qualification is not granted on the
   published cases alone.
9. **Generated tests cannot expose the solution.** A case whose hidden oracle is a test file
   is never given that test file; the visible packet carries the *behavioural* description
   (the tree → verdict table) and the run writes its own test. The runner checks that the
   run's test is not a copy of the hidden one (normalised AST hash).

The benchmark measures engineering capability, and it says so in the record: every run's
manifest records the worktree tip, the remote status, and the tracker snapshot hash.

---

## 12. Benchmark runner and evidence format

### 12.1 The smallest useful automation

Reuse the shape that already exists: the verification-set driver reads a set config as data,
asserts the identity, runs, collects, renders a record, and refuses to launch when the
identity is wrong. The benchmark runner is that shape at a smaller scale — a case manifest
instead of a set config, a worktree instead of a deploy, an oracle instead of a roll.

**v1 consists of:**

```text
bench/
  cases/<case-id>.yaml         the case manifest
  packets/<case-id>/           the task card (and its raw-issue variant for arm C)
  oracles/<case-id>/           hidden tests, replay scripts, expected outputs, controls
  setup.sh                     worktree at the starting commit, history-scrubbed, venv linked
  run.sh                       invokes one harness/model/arm on one case; captures everything
  evaluate.py                  gates → outcome class → hidden oracle → rubric inputs
  records/<run-id>/            one directory per run (below)
```

**The case manifest** carries: `id`, `class` (B1–B11), `kind` (replay / synthetic /
reviewer / escalation), `starting_commit`, `mutation` (a patch file, for synthetic cases),
`packet` (path and hash), `withheld` (list), `allowed_paths`, `forbidden_paths`,
`expected_outcome` (PASS or ESCALATED_CORRECTLY), `oracles` (visible gates; hidden scripts;
`oracle_kind: offline | live`), `controls` (the paired control and its expected reading),
`fault_proof` (the command that shows the oracle fails on the mutated tree — recorded once at
admission), `budget` (tokens, wall clock), `shape` (transcription / argument), and
`source` (the historical issue and PR).

**`run.sh`** records the identity before invocation — worktree tip, remote status, model tag
and quantization, harness version, tool allowlist hash, packet hash, reasoning policy,
temperature — and refuses to run if any is missing (the preflight rule: an identity that
cannot be established is refused, not passed).

### 12.2 What is stored per run

| artifact | content |
|---|---|
| `identity.json` | everything `run.sh` recorded, plus arm (A–E), seed, evaluator id |
| `packet.md` + hash | the task card as given |
| `transcript.jsonl` | every model call (prompt hash, completion, tokens, reasoning tokens, latency) and every tool event (command, exit code, bytes), in order — the ACP event stream where the harness exposes it |
| `diff.patch`, `changed_files.txt` | the resulting change |
| `pr_body.md` | the PR body the run wrote (its Evidence section is scored) |
| `gates.json` | G1–G7, each `observed(value)` / `asked_none` / `unaskable(reason)` |
| `oracle.json` | hidden oracle and control readings, same vocabulary |
| `outcome.txt` | the outcome class |
| `rubric.json` | S1–S10 with the evaluator's one-line anchor per dimension |
| `review.json` | for arms with review: findings, blocking/non-blocking/unresolved, §7 scores |
| `metrics.json` | wall clock by phase; tokens local/paid by role; calls; rounds; interventions |
| `classification.json` | §6.2 primary and secondary, with the sentence that justifies the primary |
| `record.md` | the rendered summary, in the per-roll record's shape: headline, gates, oracle, what this run does not show |

Two configurations are compared by joining `records/*/identity.json` on (case, seed) and
reading outcome class, gates, oracle, and metrics side by side. Nothing else is needed for
v1, and nothing in this list requires a service.

---

## 13. Candidate initial benchmark suite

Fourteen cases. The historical source and the reason each is worth its place.

| # | case | class | kind | expected tier | why it is valuable |
|---|---|---|---|---|---|
| 1 | **R1** nullable freeze (#1125/#1136) | B5 | replay | local-safe | the cleanest emitter fix in the record: 100 lines, byte-identical fixtures as the whole proof; the `L` control |
| 2 | **R8** regression gate inversion (#1316/#1329) | B8 | replay | local-safe | a guard with four named rules and a fully specified shape; tests whether a local model writes a guard that fails on the motivated shape |
| 3 | **R11** one pool factory (#577/#1391) | B10 | replay | local after framing | adapter/factory wiring with a census the run must produce; the guard is the oracle |
| 4 | **R7** task-type literals (#559/#1336) | B7 | replay | local after framing | 31 files, mechanical once framed, with one judgement half (properties over identity) that separates `L+` from `L` |
| 5 | **R6** stack #1 extraction (#1131/#1233) | B6 | replay | local after framing | the required behaviour-preserving extraction; the harvest is supplied; step 2 withheld to read scope discipline |
| 6 | **R2** own artifact never narrows (#1120/#1121) | B1 | replay | local after framing | a correction-runner fix small enough to frame and with a stored control (an app-file analysis still narrows) |
| 7 | **R3** retry marker rides one dispatch (#1347/#1348) | B3 | replay | boundary | 54 lines with a wiring test at `execute_run`; the smallest recovery-path case; reads whether a local model reaches the live entry point |
| 8 | **R4** rule B's rows reach the verifier (#1256/#1258) | B2 | replay | frontier | the required architecture/wiring case; mechanism withheld; the next hop (#1259) must be reported, not fixed |
| 9 | **R5** absent file is not evidence (#1259/#1262) | B4 | replay | frontier | typed-check binding with the seam table; run once complete and once as S14 (table withheld) |
| 10 | **R10** unrunnable probe stops the launch (#1425/#1426) | B9 | replay | local after framing | the verification/test-quality case in the instrument: three-state readouts; "fixing by deleting the probes" is the trap |
| 11 | **R9** locks against constraints (#1041/#1203) | B10 | replay | local after framing | the operational/integration case whose oracle runs in the container, not on the files; the `pip-compile` preference trap withheld |
| 12 | **R12** compose edit needs the owner's OK (#225/#1344) | B11 | escalation | any (must stop) | the escalation case with a four-line diff; the whole score is whether the run asks |
| 13 | **S6** seam test green, wiring broken | B2 | synthetic + reviewer trap | — | the lesson the line paid for three times; as a reviewer case, tests whether Parker/Dallas ask for the entry point |
| 14 | **S12** behaviour change inside a nominal extraction | B6 | synthetic + reviewer trap | — | tests whether a reviewer runs the byte-identical comparison or trusts the Evidence claim |

Held out for rotation (not in the published fourteen): R13 (the PRD/config-hash
escalation), R14 (analyzer claims, live oracle), S4 (the uncontrolled test), S9 (DB
isolation), S10 (the live #286 import-time side effect), S13 (owner-gated packet).

Nothing here is implemented; each case's admission requires the §4.1 proof (oracle fails on
the pre-fix or mutated tree, passes on the fixed one), recorded in its manifest.

---

## 14. Recommended first experiment

**Question.** Does a Parker-framed task card change a local Brett's outcome on SquadOps work,
holding everything else fixed?

**Design.** Arm B (Parker frames; Brett implements; Parker reviews) versus arm C (Brett
receives the raw issue), on three cases with fully offline oracles and one escalation case:

| case | why |
|---|---|
| R1 (nullable freeze) | expected local-safe; if arm C passes it, framing adds nothing here and that is a finding |
| R2 (own artifact never narrows) | expected local-after-framing; the case where the card should matter most |
| R8 (regression gate inversion) | a guard-writing case; reads whether the card's P2 (the bounding proof) is what a local model needs |
| R12 (compose edit) | reads whether the card's P4/P5 (prohibited, escalation) produce a stop, and whether the raw issue produces a compose edit |

**Held constant.** Qwen3.8-27B at one tag and quantization; one harness (the one Brett is
being commissioned on); the four starting commits; the hidden oracles; the same token and
wall-clock budget per run; temperature and reasoning policy from the case manifests (R1 and
R8 as transcription-shaped, R2 as argument-shaped).

**Runs.** Each case × each arm × 3 seeds = 24 Brett runs, all on local inference (unmetered).
Parker's framing and review are the only paid calls — four cards and up to 12 reviews. The
whole experiment fits inside one idle-box window and a small fraction of a monthly cap.

**Measured.**

- outcome class per run, and the SILENT_FAIL count per arm — the headline;
- §6.1 packet score for each of Parker's four cards, scored before Brett runs;
- §6.2 classification for every non-PASS;
- paid tokens (Parker) and local tokens (Brett) per PASS;
- correction rounds in arm B;
- for R12, whether each arm stopped, and on what.

**What justifies continuing the local supporting-engineer experiment.**

- Arm B: zero SILENT_FAIL across all 12 runs; ≥ 9 of 12 PASS or ESCALATED_CORRECTLY; R12
  stopped in 3 of 3.
- Arm B − Arm C ≥ 3 in PASS count, or arm C shows ≥ 1 SILENT_FAIL where arm B shows none —
  either result is the framing effect the brief asks about.
- Every arm-B failure classifies as something other than implementation capability on at
  least half its instances (a failure the card could have prevented is a framing result, and
  the card is cheap to improve).

**What ends it, for this model and harness.** Any SILENT_FAIL in arm B; or arm B ≤ arm C on
PASS count with no difference in silent failures (the card is not what the local model
lacks); or ≥ 2 harness/tooling classifications on the same trap (the harness is measured
first, then the experiment re-run).

**What the result feeds.** §9's ladder for B1, B5 and B8 — three of twelve runs each toward
the twelve required — and the first packet-score data for §6. It does not qualify anything
by itself; it decides whether the next 12 runs are worth their window.

---

## 15. Relationship to the other maintainer documents

The four companion documents make claims. This framework is the instrument that tests them,
and it borrows their vocabulary rather than inventing a second taxonomy.

**Capabilities of a SquadOps Maintainer Agent.** Every `L`, `L+` and `F` tier in its tables
is a hypothesis about a local model, and §9's ladder is how each is confirmed or refuted per
class. Its allocation notes are the framework's rules: "the local/frontier line is cost of
being wrong" is §1.2's outcome ordering; "anything concluding clean, green, passing or safe
is frontier" is why Brett collects and never concludes (§11 rule 7); "every delegation needs
a paired control" is §4's admission rule; "long-running work must outlive its supervisor" is
how `run.sh` launches. Its §6 tooling traps are §10's harness/tooling classification and
§6.2's third row.

**SquadOps Maintainer Lessons Learned.** Each synthetic case in §4 is one lesson made
executable: S1/S2 (C3), S3/S5 (C2), S4 (A3), S6 (A1), S7 (C2's task-type rule), S8 (B1/D5),
S9 (A5/E4), S10 (C3), S11 (C5), S12 (B6/F1), S13/S14 (T12/D3). §1.3's gates G3–G7 are the
lessons' enforcement surfaces; the rubric anchors in §8.2 are the lessons' worst and best
examples. If a lesson has no synthetic case, the framework has not yet tested it — that gap
is listed, not hidden: A4 (gate coverage) is R8 only; B3 (instrument before fixing) has no
case yet; E1/E2 (pre-registration, the shakeout loop) are evaluated by their own records.

**SquadOps Maintainer Work Archetypes.** §2's benchmark classes B1–B11 are eleven of its
twenty-one archetypes, chosen by samplability and independent oracle; its "looks easy but
needed high judgement" table is where §4's under-scoped and escalation cases come from; its
"expand scope unexpectedly" list is why R4 withholds the next hop and scores reporting it;
its delegation section's claim — the bounded engineer's work begins where the evaluation
surface has been tabled — is the hypothesis §14 tests first.

**SquadOps Maintainer Interface and Handoff Contracts.** §6.1's packet rubric is that
document's minimum useful contract, field for field (P1–P5 always, P6–P8 when the seam has
more than one reader, P9–P11 when they earn their place). §8.4's handoff completeness reads
its thirteen transitions. G5's required evidence is its change-evidence contract. The
escalation cases' oracles are its ruling record — a run passes by producing the question,
options and recommendation that record requires. The runner's per-run record is its
measurement pair, at benchmark scale.

**The test of the framework itself.** If a configuration qualifies on a class under §9 and
then produces a silent failure on real work of that class, the framework was wrong, and the
correction is written into it the way the 1.6.3 record §6 and SIP-0106 §1.2f were written:
in place, dated, beside the reading it replaces, with the evidence that falsified it.
