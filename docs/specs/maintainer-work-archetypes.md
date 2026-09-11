# SquadOps Maintainer Work Archetypes

**What this is.** The recurring shapes of engineering and maintenance work that have
actually occurred while developing SquadOps, clustered from the repository's own record and
described by what each shape demands, what it touches, how it fails, and how it is proven.
Each archetype is tiered on the scale the capabilities document uses — `L` (a local model
can own it end to end), `L+` (local execution after frontier framing), `F` (frontier
judgement, because being wrong is expensive, silent, or hard to detect) — and the tiering is
argued from history, not asserted.

**What it is not.** A generic software taxonomy. An archetype appears here only where the
tracker, the merged PRs, the plans or the operational record show it recurring. Where the
prompt's candidate list named a shape the history does not support as a distinct cluster,
it is folded into the one it actually belongs to, and that is stated.

**The record this was clustered from.** 535 issues (Feb–Sep 2026; `bug` 141, `tech-debt`
73, `enhancement` 53, `arch-review` 28, 246 unlabeled), 935 merged PRs (`fix` 381, `docs`
201, `feat` 173, `refactor` 42, `chore` 41, `test` 16, `sip` 14, `ci` 8, `instrument` 6,
`release` 5, `ops` 4), 1,940 non-merge commits, 19 migrations, 89 prompt-fragment files, 29
verification-set configs (13 of them diagnostics), 12 pre-registrations and their records,
the 1.6.x–1.7.x plans, and the guard docstrings under `tests/unit/architecture/`. The median
merged PR is 198 lines across 4 files; the 90th percentile is 917 lines across 14.

**How the project itself classifies work.** Since 1.7.0 every line's plan sorts its items by
*how they are proven*: a **measured pack** (roll-verified on a frozen deploy), a
**CI-verified rider** (guards and tests, "in neither deploy's cycle path"), an **ops rider**
("live reads, not CI"), **instrument** work (driver and record fields, which by rule never
supersede a deploy), **preconditions**, and — in 1.7.5 — **closures** gated on a reviewed
design artifact. That is the native taxonomy; the archetypes below are cut finer than it,
and each names which of those lanes it usually lands in.

**Where a finding comes from.** Across all 535 issue bodies: 263 cite a specific cycle id or
a live cycle; 115 a counted roll or set record; 101 a measurement window; 73 the artifact
vault; 61 a shakeout or diagnostic; 56 CI or a red on main; 56 LangFuse or a container log;
49 a cut or release; 34 an independent health assessment or the bespoke-inventions sweep;
22 "found on the way"; 14 an owner's question or ruling. **The live cycle is the dominant
source of work**, ahead of CI and review combined, and that fact shapes almost every
archetype's verification column.

---

## The archetypes

Grouped by what the work is *about*. Each carries the same fields.

### 1. Localized defect repair from a live-cycle finding

**Description.** A roll, shakeout or window produced a wrong verdict or a wasted round; the
cause is read from the stored artifacts and the code path; the fix lands at the layer that
owns the defect, with a replay of the stored case and, where a seam moved, a wiring test.
This is the single largest shape in the record: `fix` is 381 of 935 merged PRs, median 179
lines across 4 files, and 88 of the 141 `bug` issues cite a cycle id.

**Typical trigger.** A per-roll record's rejection or void; a shakeout's red; a readout that
cannot be right; the owner reading a roll ("the owner noticed the red before I did", #1357).

**Typical input artifacts.** `cyc_…`/`run_…` ids; the vault (`data/artifacts/…`,
`test_report.md`, `failure_analysis.md`, `typed_check_evaluation_task_N.json`, banked
failed emissions); runtime-api and agent container logs over a UTC window; the LangFuse
generation; the per-roll record.

**Typical files / subsystems.** The owning handler under `capabilities/handlers/cycle/`;
`cycles/acceptance_checks.py`; `cycles/patch_verification.py`; the scaffold expander for
the stack; the executor's outcome path.

**Kind of judgement.** Which layer owns the defect (capability 2.1); "read from the code,
not inferred" (#1256's own phrasing); distinguishing a real defect of the application from
a harness defect (SIP-0096's `failed` vs `blocked_unverified`). The diagnosis is the
judgement; the edit is usually small.

**Common hidden risks.** Fixing the symptom's owner rather than the cause (#1054); a fix
keyed on the attempt's history rather than the contract, so the next shape is uncovered
(#1318 → #1364 → #1374); a fix whose premise was inferred rather than read (#691's original
filing, rewritten before it was built); a correct fix in one environment refused in another
(#1259).

**Typical failure modes.** The seam is fixed and the caller never delivers (#1250, #1256);
the fix is right and a sibling gate on the same seam refuses it next roll; the fix lands and
the record still cannot see it (#1002's family).

**Best verification.** Replay on the stored artifacts (the refused patch → the expected
verdict, with the suite present → `passed`, as #1259's table does); one wiring test entering
at the live caller; the affected suites; a shakeout on the rebuilt deploy. The PR's Evidence
names all three.

**Representative history.** #1125/#1136, #1127/#1137, #1128/#1141 (the 1.6.6 pack — six
fixes built from six rejections); #1259/#1262; #1252/#1253; #1364/#1365; #1120/#1121;
#1129/#1140; #1094/#1102.

**Tier.** `L+` for the edit once a frontier diagnosis names the layer, the case to replay
and the entry point; `F` for the diagnosis. The record shows why the split is there: the
1.6.6 pack's six fixes were each small and each right, and the diagnosis behind each
(#1125's `has_default` branch, #1126's inverted predicate) was the whole of the work.

**Owner / approver.** Investigator diagnoses (never merges); Implementer writes; Verifier
owns whether the replay and the wiring test can fail; Integrator merges after reading every
CI job.

---

### 2. Cross-layer defect tracing — a fact computed and never delivered

**Description.** A value is produced at one seam and consumed at another, and somewhere
between them it is dropped, mislabelled, read off the wrong object, or rendered into a
placeholder nobody filled. Nothing errors; a readout reads zero or green. The work is to
trace the value across every boundary to every consumer and find where it dies.

**Typical trigger.** A readout that is impossible ("every `decided_by_agent` in the line's
records is 0", #1256); a log line that contradicts another (`rows=10 executed=10` in the
agent, `agent_rows=0` in runtime-api); a measurement over LangFuse showing a whole class at
zero (#1171); an owner's question about whether two identities may diverge (#1438).

**Typical input artifacts.** Paired log lines from two containers; the stored prompt from
LangFuse; the envelope and result objects as the executor holds them; the driver's record
schema.

**Typical files / subsystems.** `adapters/cycles/dispatched_flow_executor.py` (the outcome
handler, `_try_accept_patch`), `adapters/cycles/correction_runner.py`, the repair handlers'
`_build_render_variables`, `normalize_task_checks`, the driver's readouts.

**Kind of judgement.** Capability 1.2 — trace a value across module boundaries to every
consumer — and 1.3, enumerate every site broader than the change. Both are `F` in the
capabilities document, and this archetype is why.

**Common hidden risks.** Fixing one hop and leaving the next: rule B's rows needed #1250
(the envelope), then #1256 (the protocol result), then #1259 (the verdict rule), then #1264
(the tree), then #1406 (the other role's criteria), then #1350 (the grants). A readout that
reads a log line about a thing never rendered (#1289's R4). A record header that prints a
typed value as if measured (#1296).

**Typical failure modes.** Latent for weeks with green CI; found by a live cycle; the fix's
own test hands the seam its input and misses the next hop.

**Best verification.** The wiring test at the live entry point (`TEST_QUALITY_STANDARD` §6a);
instrumentation so the next such diagnosis is a log line rather than a code-path reading
(#1250 added `agent_rows`/`agent_executed`; #1289 confirmed on the stored prompt); a live
shakeout with the fault injected (#1251).

**Representative history.** #1250, #1256, #1289, #1002, #995, #999, #597, #1021, #1171,
#1406, #1350, #1296.

**Tier.** `F`. Every instance in the record was found by a person reading two sources
against each other, and the fix's blast radius was unknown until the trace was complete.

**Owner / approver.** Investigator; the fix goes to Implementer with the trace attached;
Verifier requires the wiring test.

---

### 3. Recovery-path change — the correction loop's semantics

**Description.** A change to what the correction loop counts, routes, refunds, retries,
verifies, or carries forward: budget semantics, locus routing, marker lifecycle, the
accepted-patch path, the rewind. `fix(correction)` is the largest single fix scope (41 PRs,
plus `correction-loop` 5 and `executor` 13), and 1.7.2 and 1.7.4 were named "Loop Honesty"
for it.

**Typical trigger.** A roll that exhausted its budget on non-events (#1053), ended
`plan_defect` after zero applied repairs (#1129), destroyed a working deliverable (#994), or
was accepted with a defect still in the file (#1323); a diagnostic whose fault re-applied to
the recovery it was watching (#1347).

**Typical input artifacts.** The vault's per-round artifacts (0-byte `repair_output.md`,
the refused patch, the passing retest); `runtime_activities`; the correction decision and
failure analysis documents; the record's loop texture.

**Typical files / subsystems.** `correction_runner.py` (`run_correction_protocol`, the
terminals, `_resolve_repair_target`), `dispatched_flow_executor.py` (`_handle_task_outcome`,
`_try_accept_patch`), `cycles/patch_verification.py`, `capabilities/handlers/cycle/base.py`
(the emission seam), `TaskType` properties.

**Kind of judgement.** What counts as an attempt, a round, evidence, a repair's owner; the
three-part contract the 1.7.5 map states — *truthful failure → truthful correction →
durable repaired state*. Several of these were owner's rulings (rule B 2026-09-01; #1269
2026-09-03; the L1 split in 1.7.4 §3a).

**Common hidden risks.** A change here changes what a corrected result carries, so it sits
beside a prediction and cannot ride a CI-only rider (1.7.4 plan §3.3; #1374's placement
note). State set on an envelope with no clearing rule (#1347). A conservative classifier
whose "safe" error is the wrong chain every time (#1054, #1120). Fixing gate by gate
(#1374's finding).

**Typical failure modes.** The loop spends its budget on nothing; a correct repair is
discarded; a symptom-owner is repaired three times; a diagnostic's red is manufactured.

**Best verification.** Replay on stored artifacts; a fault-injected diagnostic that runs the
roll's own path (`qa_suite_absent`, `repair_prose_only`, `contentless_builder`,
`false_source_claim`) read by the seam it reached; a counted set with the prediction named;
the record's `refunded_rounds`, `retried_with_fact`, `framework_rows_rederived`.

**Representative history.** #1053/#1056, #1129/#1140, #994/#1415, #1347/#1348,
#1372/#1414, #1374/#1413, #1318/#1319, #1364/#1365, #1120/#1121, #1054/#1419, #968/#1418,
#1273/#1288, #1269/#1287, #435, #1221/#1225.

**Tier.** `F`. Every one of these changed a semantic the next roll would be judged by, and
five of them were owner's rulings.

**Owner / approver.** Implementer with Investigator's trace; Measurement steward names the
prediction and the diagnostic; the owner rules on semantics.

---

### 4. Typed-check and gate introduction

**Description.** A new check on emitted artifacts (or a promotion from reporting-only to
blocking), bound at plan time or injected at the handler seam, with its finding rendered
back to the author. `feat(checks)` PRs are large — median around 1,500 lines across 17
files — because a check carries an evaluator, a registry entry with governance metadata,
plan-time injection, prompt rendering of the finding, the regenerated typed-check menu,
goldens, and vault replays.

**Typical trigger.** A defect class a roll paid for that a check could have caught at
emission (#1153 from 1.6.6 roll 3; #939 from `cyc_58d92ca2b407`); a check present on one
stack and absent on the other (#1216); a rule shipped reporting-only whose corpus evidence
now supports blocking (#1022).

**Typical input artifacts.** Stored suites, fills and recipes from the vault (the red to
catch and the greens to pass); the manifest's declared kinds and anchors; the check
registry; `docs/architecture/typed-check-menu.md`.

**Typical files / subsystems.** `cycles/acceptance_checks.py`, the check registry
(`CheckSpec`, `required_tooling`, `blocking_default`), `cycles/task_plan.py` injection
(`_assertion_kind_criteria`, `_harness_boundary_criteria`), `capabilities/handlers/
stub_detection.py`, prompt appendix assets, `tests/fixtures/roll_replays/`, the goldens.

**Kind of judgement.** The seam table (capability 3.9; CLAUDE.md "Typed checks") — every
environment that will evaluate the task's criteria and the outcome on a tree lacking the
file; the false-positive cost ("a false positive in a blocking check recreates the unwinnable
loop this exists to end", #1240); stack-awareness; reporting-only vs blocking.

**Common hidden risks.** A check that executes on a missing file counts `file_not_found` as
an executed failure in a repair's tree (#1259 — the direct consequence of #1240/#1246); a
gate whose premise later goes false (#1049); a check that silently skips a stack (#1216); a
root-anchor rule that would have flagged seven accepted suites (#1246 measured it first);
goldens that must be regenerated in their own owner-approved commit.

**Typical failure modes.** A correct repair refused round after round; a green suite
discarded (#1126); an unwinnable contract (#1128, #1094).

**Best verification.** The stored red rejected with the line and the kind named, the stored
greens passing under their own manifests, a vault-wide count (#1246's nine suites; #598's
203 recipes); the seam table in the PR; the menu regenerated; a live roll on both stacks.

**Representative history.** #1240 (#1153), #1246 (#668), #1245 (#1022), #1244 (#598),
#1235 (#939), #1239 (rule B's environment axis), #1218, #1219 (#1216), #656 (#648), #630
(#628), #533, #1102 (#1094), #1040 (#1029), #1028 (#913), #1026 (#1013), #1457 (#820),
#1460 (#668 second half).

**Tier.** `F` for the rule, its seam table and its blocking status; `L+` for the extractor
and evaluator once the shape, the replays and the controls are named. The history is
unambiguous on the first half: #1259 came from binding two well-tested checks without the
table.

**Owner / approver.** Implementer with Verifier; the owner approves a blocking promotion
and any pinned-fixture move.

---

### 5. Scaffold, stack and contract change

**Description.** A change to what the frozen skeleton emits, what the contract derives, or
which stack facts live where — including a new stack. `feat(scaffold)` 14 and
`fix(scaffold)` 23, plus the SIP-0098/0099/0104 phase PRs.

**Typical trigger.** A frozen-file defect under several rolls' round 0 (#1125 under five of
six); a store handle no correct app writes (#1087); a harness that can only reject
(#1127); a second stack (#822, #836); a derived fact with seven homes (#772).

**Typical input artifacts.** The reference manifest and contract pair, the context goldens,
the seeded-tree hashes, the rolls' round-0 reports.

**Typical files / subsystems.** `capabilities/scaffold.py`, `stack_fastapi_react.py`,
`stack_nextjs_ts.py`, `scaffold_contract.py`, `success_status.py`, `response_shape.py`,
`ScaffoldStack` and `AppInvocation`, the reference fixtures and their hashes.

**Kind of judgement.** Whether the change moves a pin (`GENERATOR_VERSION`, the contract
version, `expanded_tree_hash`) and how it is classified (`reference_defect`,
`ambiguity_removal`); "remove the ambiguity, do not document it" (1.6.4 plan on #1087);
parity between stacks (#1087's stack-1 half was a follow-up, #1112).

**Common hidden risks.** A pin moved silently; comparability with prior sets broken by an
edit the config hash does not cover (#1427's PRD question, raised rather than taken); a
stack-shaped literal placed in shared code (#1126, guarded since #1131); a fix in place
that the following extraction then has to preserve (#1131 deliberately after 1.6.6).

**Typical failure modes.** Five of six rolls opening with the same 500; an unsatisfiable
contract; a working app rejected on a phantom table.

**Best verification.** Frozen fixtures byte-identical for a pure move (3 manifests, 57 files
for #1131); a deliberate, once, owner-cleared pin move with the classification recorded;
the driver's P0 seeded-tree check per stack; a live roll on both stacks.

**Representative history.** #1136 (#1125), #1137 (#1127), #1141 (#1128), #1346
(#1087/#1112), #1118 (#772), #1027 (#795), #1040 (#1029), #1064 (#1055), #1358 (#1351),
#1293 (#1292), #836 (#822), #1458/#1464 (#906/#1463), #1233 (#1131).

**Tier.** `L+` for a fully specified emitter fix with byte-identical fixtures as the proof;
`F` for anything that moves a pin or a hash, or that changes what a set compares to.

**Owner / approver.** Implementer; the owner clears every pin move (1.6.4: "owner-cleared
2026-08-25").

---

### 6. Behaviour-preserving extraction and decomposition

**Description.** A god-file or a duplicated sequence is split or moved with the behaviour
held constant, proven by goldens, replays and AST-verified name counts. `refactor` is 42
PRs, median 469 lines across 9 files, 90th percentile 3,434 lines; the odd-minor lanes
(1.3, 1.5, 1.7) exist to quarantine this shape.

**Typical trigger.** A size measurement (the executor at 4,668 lines with a 511-line
method, 1.7.5 map §2; `cycle_tasks.py` at 3,276 lines; `planning_tasks.py` at 1,887); a
duplication census (#929's thirteen call sites); a stabilization release opening.

**Typical input artifacts.** The file, its comment rationale, the goldens
(`tests/unit/cycles/goldens/`), the replay corpus, the extraction map or standard.

**Typical files / subsystems.** `dispatched_flow_executor.py`, `correction_runner.py`,
`capabilities/handlers/cycle/`, `handlers/planning/`, `scaffold.py`, the context-assembly
registry.

**Kind of judgement.** The map — what moves, in what order, where the core/tail split is,
what the proof is (1.7.5 recovery extraction map; the SIP-0097 slice plan). Harvesting the
rationale first (#1149: 23 entries into SIP-0105 before #1131).

**Common hidden risks.** Rationale lost in comments that no one reads during the move
(#1149); a silent-omission trap discovered mid-move (S1's `fill_slot_paths` returned
FastAPI's map to any unregistered stack); the "pure move" that quietly fixes something and
so cannot be proven byte-identical; a tail that outlives the budget (1.7.5 §3.5's rule).

**Typical failure modes.** Historically few once framed — the record's extractions landed
byte-identical (#1131: 57 files; #747: build-profile narratives), AST-verified (#754:
20/20 names), or golden-first (#663: 19 goldens captured before each of three slices).
The failures are upstream, in framing: an extraction started without a map.

**Best verification.** Goldens captured *before* the refactor and byte-identical
(canonical-JSON-identical, 1.7.5 rev 5) after; AST name counts; every pre-split test passing
unmodified; for the recovery path, the five fault diagnostics reaching their seams on the
pinned deploy.

**Representative history.** #341, #344, #347–#349 (SIP-0097, #186); #338/#339 (#152);
#754 (#331); #751–#753 (#663); #1233/#1234 (#1131); #747 (#452); #403 (#401); #356
(#234); #1200; #1152/#1443 (1.7.5).

**Tier.** `L+` — reliably mechanical once the map exists; the map is `F` and is reviewed
by the owner before the first PR (1.7.5 §7 step 3).

**Owner / approver.** Implementer; the architect writes the map; the owner reviews it.

---

### 7. Vocabulary and identifier convention sweep

**Description.** A wide, mechanical rename or literal-to-constant sweep that establishes one
vocabulary and lands the guard that keeps it. Wide (#1335: 106 files; #1336: 31; #1337: 19;
#164: 22) and semantically flat.

**Typical trigger.** A leak found in review that had already propagated (#380's
`terminal_status` across three SIPs); a name about to freeze into a distribution format
(#922 before capability packs); a domain module reasoning in a vendor's words (#377).

**Typical input artifacts.** An AST or grep census of every site (216 task-type literals
across 30 files; 13 enum-shadow hits, not 324); the wire surfaces that legitimately keep
strings (YAML manifests, request profiles, tests).

**Typical files / subsystems.** Everything under `src/` and `adapters/` that names the
thing; `squadops/tasks/task_types.py`; the guard under `tests/unit/architecture/`.

**Kind of judgement.** Where the boundary is — which literals are the wire's and which
are the core's (#559's rules 1–2); which property replaces which identity check (rule 3);
the merge order ("the widest rename first, so the Spark lane and the remaining PRs rebase
once", 1.7.3 plan).

**Common hidden risks.** A user-visible config break hidden inside an internal rename
(`--set dev_capability=…` was a required override, #922); artifacts that stop working on
the new deploy (1.7.3 §9: the 1.7.2 set configs' loaded checks used the old key and could
not run post-#922); a comparison that is silently never true after a typo (#559's first
failure mode).

**Typical failure modes.** Historically clean: 1.7.3 shipped eight structural items and
"found nothing attributable to the sixteen items". The risk is in what the rename touches
outside `src/` — configs, set configs, compose.

**Best verification.** A structural guard with "nothing left to flag" that fails a return
(the enum-shadow family; the retired-spellings guard; the task-type literal guard); the
full regression suite; the wire strings unchanged on the envelope.

**Representative history.** #1335 (#922), #1336 (#559), #1337 (#377), #1338 (#381), #164
(#82), #267 (#79), #74, #204, #118, #302 (#231).

**Tier.** `L+` — the guard frames the edit, and the record shows these land clean; `F` at
the boundary decision and for the config/compose fallout.

**Owner / approver.** Implementer; Verifier owns the guard; the owner rules on the
user-visible break.

---

### 8. Architecture-rule introduction — a standard plus its enumerating guard

**Description.** A surface that accreted conventions with no owner gets a written standard
and a test that enumerates the whole surface and holds it to the rule. The standard is
reviewed before the first PR it constrains.

**Typical trigger.** Needing a rule while adding a surface and finding none (#218 arose
while adding the SIP-0089 assignment API); a third recurrence (#336); an independent
health assessment or sweep (`arch-review` issues: 28, twelve of them from assessments);
the naive-review reflex that a bespoke shape is a defect (`defended-bespoke-decisions.md`).

**Typical input artifacts.** An enumeration of the whole surface — every registered
router, every `asyncpg.create_pool` call, every construction of `GenerationRecord`, every
stack-shaped literal, the four composition roots audited on one commit.

**Typical files / subsystems.** `docs/architecture/*.md` (`api-route-lanes.md`,
`composition-roots.md`, `defended-bespoke-decisions.md`, `typed-check-menu.md`),
`tests/unit/architecture/test_*.py`, CLAUDE.md's condensed rule.

**Kind of judgement.** The rule's boundary and its allowlisted exceptions with reasons;
whether an off-the-shelf lint covers it (#380: ruff `PLR2004` is numeric-only); making the
allowlist two-sided so it cannot outlive what it excuses; what the standard does *not* fix.

**Common hidden risks.** A guard that scans docstrings and fails on its own docs
(capability 3.7); an allowlist that is a hand-copied list ("the same drift one layer down",
#1427); a standard written without the audit that shows what it will break.

**Typical failure modes.** Rare once landed — the guards in the record have held. The
failure is before: surfaces drifting for months because no rule existed (#218's four
conventions; #1144's audit wired to nothing).

**Best verification.** The guard fails on the offending commit (`1b9b93a9`; the old 1150;
a synthetic hollow package) and passes main; the standard names the commit it was audited
against.

**Representative history.** #218 → `test_route_lanes.py`; #154/#1340; #380/#382; #559;
#577 → `test_one_pool_factory.py`; #1171 → `test_generation_record_construction.py`;
#1131; #1216/#1219; #1229/#1239; `composition-roots.md` (#301, #286, #637); #583.

**Tier.** `F` for the rule; `L+` to write the guard against a fully stated rule with its
allowlist and the commit it must fire on.

**Owner / approver.** The architect (primary engineer) writes the standard; the owner
reviews it before the first constrained PR (1.7.5 §3.1); Verifier owns the guard.

---

### 9. Guard strengthening and test-quality work

**Description.** A test or guard added or hardened after a recurrence or a "found by the
window, not the tests" incident: gate coverage, drift ratchets, pin guards, revert-and-run
proofs, linter enforcement. `test` PRs are small (median 155 lines, 2 files).

**Typical trigger.** The fourth filing of one defect (#1316); a red that CI could not see
(#1041); a probe or pin the line is about to depend on (#1315); a linter backlog (#20:
235 violations resolved, linter made blocking).

**Typical input artifacts.** The recurrence list; the shape that must fail; the live
registry to parametrize over.

**Typical files / subsystems.** `tests/unit/architecture/`, `tests/unit/scripts/`,
`scripts/dev/run_regression_tests.sh`, `scripts/dev/lint_test_quality.py`,
`.claude/hooks/lint-test-quality.sh`, `pyproject.toml` markers.

**Kind of judgement.** "What bug would this catch?" (capability 3.1); deriving the guarded
set from the owning module rather than listing it (3.5; #1427's guard; #1472's
parametrization over `FRAMEWORK_CHECKS`); proving the test fails on pre-fix code (3.4).

**Common hidden risks.** A test that cannot fail (11.4); an include list where an exclusion
list belongs (#1316); a guard that tracks the machine (the xdist gate, #1037); a coverage
claim that is a hard-coded baseline rather than a reason file (#1185 → #1203's exceptions).

**Typical failure modes.** The guard passes vacuously; the list drifts again.

**Best verification.** Revert the fix and watch the test fail; run the guard against the
commit that motivated it; the whole suite when a loop-scope or marker change is involved
(1.7.5 §3.6 on #580).

**Representative history.** #1316 → `test_regression_gate_coverage.py`; #201, #238
(#200, #207); #1185; #1315; #1037 (the xdist gate); #909 (Guards 1a/1b); #851; #382;
#1472; #1476; #20.

**Tier.** `L+` once the shape to guard is named; `F` to decide the shape and to judge
whether a red pre-existed (5.4/5.5).

**Owner / approver.** Verifier.

---

### 10. Evidence instrumentation — records, readouts and log lines

**Description.** Making a fact observable in the record without changing what the system
does: a new driver field, a readout read by reason, a log line carrying the fact, a check's
provenance surviving normalization. `instrument` 6, `fix(driver)` 6, `tooling(driver)` 2,
plus the `feat(verification)` trio (#1282 fault injection, #1278 by-reason, #1455
three-state) and the `fix(qa)`/`fix(observability)` items that "record what the runner
actually did".

**Typical trigger.** A readout that could not answer the question the prediction asked
(#1276); a texture field declared with no producer (#1285's blocker); a fact computed at
the handler and dropped before the record (#995/#999/#1002); a probe that could not run
recorded as data (#1425).

**Typical input artifacts.** The pre-registration's texture list; the real log-line shapes;
a kept record to re-render; the driver's record schema.

**Typical files / subsystems.** `scripts/dev/verification_set_driver.py`; handler log
lines in `handlers/cycle/`; `CheckResult.provenance`; `telemetry/models.py`;
`docs/plans/verification-sets/*.yaml`.

**Kind of judgement.** What the field reads when unaskable (#1445; 1.7.4 record §9);
whether an inference belongs in an evidence instrument at all (#1436: "a heuristic in an
evidence instrument, which is the class this line keeps finding"); which log window is the
fact (the producing agent's, not the runtime-api's token).

**Common hidden risks.** A readout that counts artifacts and calls them emissions (#1431);
a readout wired to the wrong mechanism (#1362: L4 read the #1129 exclusion, not the
refund); a header that prints a typed value as identity (#1296); a probe keyed on a name
that is docker-exec'd verbatim (#1425); the driver importing framework modules from a tree
the deploy never ran (#1438).

**Typical failure modes.** The instrument reports success while measuring nothing (#1076's
family); a fix falsified by the next day's data (#1436).

**Best verification.** A test with the real line shape; re-rendering a kept record from its
stored identity and the still-present logs (a driver-only fix does not supersede a deploy,
1.7.2 pre-registration §2); the field's three states demonstrated.

**Representative history.** #1378, #1379, #1398, #1401–#1403; #1297 (#1296), #1331, #1334,
#1362, #1320, #1199; #1282 (#1251), #1278 (#1276), #1455 (#1445); #1036, #989, #962, #960,
#1345, #1057; #928, #932, #797, #1303; #1117, #1119.

**Tier.** `L+` for adding a field with a stated producer, a stated unaskable state and the
real line shape in its test; `F` for deciding what a readout means and whether a finding
supersedes a deploy.

**Owner / approver.** Measurement steward; the owner rules on supersession.

---

### 11. Verification-set operation

**Description.** Running a pre-registered set: preflight, launch (detached), gate approval
with the pre-registered constant, collection, the per-roll record, the counted/void/reset
reading at each roll boundary, the shakeout loop with its exit rule, the diagnostics, the
cut record. Twelve pre-registrations and their records since 1.6.3; 29 set configs; four
overnight delegations recorded in the pre-registrations' §5.

**Typical trigger.** A line's pack is merged; a deploy is rebuilt; a shakeout finds a fix.

**Typical input artifacts.** The pre-registration by commit hash; the set config with its
pins; `.head_pin`; the seven image ids and container start times; the previous roll's
record.

**Typical files / subsystems.** `verification_set_driver.py`
(`preflight`/`shakeout`/`render`), `docs/plans/verification-sets/`,
`var/verification_sets/<set>/`, the gate CLI, Postgres reads (`focus_leases`,
`cycle_runs`).

**Kind of judgement.** The roll-boundary reading — counted, void, reset — and whether a
finding supersedes the deploy (capabilities 9.10–9.12, all `F`); when to stop the set for
the owner ("a reset or a falsified prediction stops the set", 1.6.5 §5); the exit rule's
"new seam finding" test.

**Common hidden risks.** Launching before the previous roll is read (1.7.1 record §3.3 —
the early stop should have fired); a session-bound driver stopped from outside three times
in a day; a rebuild over a running cycle leaving `running` in the registry; a hand-edited
pin (#1296); a diagnostic counted (#1251's non-counting rule); merging to main while a set
is open.

**Typical failure modes.** A roll counted that should have been void; a record with `?`
for its deploy; evidence destroyed by a rebuild (9.13).

**Best verification.** The record itself, rendered from what the driver collected; preflight
refusals; image ids and `StartedAt` checked at the close (SIP-0104 P6 record); the cut
record's "what the evidence does not cover".

**Representative history.** The 1.6.3–1.7.4 records; #1124, #1142/#1143, #1266/#1267,
#1104/#1105; 1.7.1 §3.3; the 1.6.4 §5 standing night rules ("no pushes; detections
recorded, not fixed; deploy frozen, work not frozen; gates are the §6 constant").

**Tier.** `L`/`L+` for preflight, detached launch, collection and render (capabilities 9.2,
9.8); `F` for every reading and every supersede call. The delegation record is exactly this
split: the assistant launched, gated with the constant and collected overnight; the
counted/void/reset reading was made per roll, and a falsified prediction stopped the set.

**Owner / approver.** Measurement steward operates; the owner is the approver of readings
that void or reset and of any change while a set is open.

---

### 12. Plan authoring, revision and re-placement

**Description.** Writing a line's plan from the prior record and the tracker; revising it on
the owner's written review; recording decisions taken under delegation; re-placing items by
name with a count of how many plans have carried them. Around seventy `docs(plan)` PRs; the
1.7.5 plan went through five revisions in one morning.

**Typical trigger.** A line closes; an owner's review; a ruling; a finding that changes a
prediction's expected reading before the diagnostics run (1.7.4 §3a).

**Typical input artifacts.** The prior record's §-by-§ findings; every open issue on the
morning of writing; the prior plans' placement sections; the ROADMAP identity for the line.

**Typical files / subsystems.** `docs/plans/<line>-plan.md`, `-preregistration.md`,
`-record.md`, `-cut-record.md`; the design artifacts a plan points at (the extraction map,
the composition-roots standard).

**Kind of judgement.** Placement and sequencing; what may share a deploy ("a measured
tranche and a structural tranche do not share a deploy"); what is non-droppable; the
attribution structure (rider-then-pack behind a checkpoint pair); what the plan owns versus
what the design artifact owns (1.7.5 rev 5).

**Common hidden risks.** Plan text that never becomes an issue (#1251: "three lines of plan
text, never filed"); items carried across five plans (1.7.5 §3.8); a plan citing a path
that exists only in a working copy (`test_docs_version_sync` rule 3); a "re-place-by-name
escape" used as a drop; a plan's expected reading corrected after the run.

**Typical failure modes.** A divergence recorded only in the plan and lost at the cut
(SIP-0103 §5d); a decision taken under delegation and not written where the tree and the
plan would otherwise disagree (1.7.3 §9 exists to prevent it).

**Best verification.** The owner's review; the §3.8 count table; the revision history
naming what changed and on whose ruling; the docs-drift guard.

**Representative history.** #1146, #1156, #1230, #1232, #1277, #1284; the 1.7.3 plan §9
(eight decisions under delegation, each "the owner's to overrule"); the 1.7.5 plan §10.

**Tier.** `F`. Every revision in the record was on the owner's review or ruling.

**Owner / approver.** Recorder / architect writes; the owner approves every revision.

---

### 13. Finding → issue: filing, triage and re-placement

**Description.** Turning a live finding into an issue with the mechanism, the evidence, the
scope and what is deliberately excluded; splitting a deferral out of a closed issue's
comments; triaging the open set against the roadmap; closing by verification. 535 issues
with a stable structure — `Summary`/`What happened` (124), `Fix`/`Fix direction`/`Fix
shape` (143), `Evidence` (43), `Root cause` (32), `Acceptance` (26), `Placement` (18) — and
263 citing a cycle id.

**Typical trigger.** A roll's readout; a diagnostic; an audit ("verify-then-close at the
head of the line with the record's own readings", 1.7.5 §3.1); a deferral in a closed
issue's comments (#1229).

**Typical input artifacts.** The record, the vault, the logs, the tracker, the current plan.

**Kind of judgement.** Capability 10.1 — defect, mechanism, evidence, scope, exclusions; the
premise check before the fix (#691 rewritten); the class ("this is the shape of #1261 and of
the hollow release capture in #1076"); placement in a lane.

**Common hidden risks.** An issue whose premise was inferred (#691); an issue that names a
fix its evidence does not support; a deferral that disappears; a title that no longer
describes the body (the 2026-09-08 audit found ten drifted bodies).

**Best verification.** The issue's own Evidence section cites artifact ids and log lines;
the closing PR's `Closes` line is enforced (`pr-closure.yml`).

**Representative history.** #1250's "read from the executor", #1256's "read from the code,
not inferred", #1229 (split for durability), #1251, #691, #1312's "what it is NOT — each
ruled out with evidence", #1427's "the part that needs a decision, not a fix".

**Tier.** `F` for filing and triage (the mechanism claim is the expensive part); `L+` for
the closure bookkeeping.

**Owner / approver.** Investigator files; Recorder triages; the owner rules on placement.

---

### 14. Release cut and package capture

**Description.** The seven-step procedure: bump, markers, CHANGELOG rotation, ROADMAP entry,
SIP sweep, tag (the Release publishes itself), package capture. `chore(release)` 20,
`release` 5, `docs(release)` 11 — twenty-four tagged releases from v1.0.0 to v1.7.4.

**Typical trigger.** The cut criterion met; the line's record written.

**Typical input artifacts.** The record, the tag range, the cycle ids the record cites, the
CHANGELOG's `[Unreleased]`.

**Typical files / subsystems.** `pyproject.toml` via `version_cli.py`, CLAUDE.md, README,
ROADMAP, `CHANGELOG.md`, `site/content/releases/vX.Y.Z/`, the SIP folders.

**Kind of judgement.** The SIP promotion sweep (what is genuinely implemented; a phased SIP
with open children stays accepted); "what the evidence does not cover"; reading the package
preview before `--write` (#1076); the Closes column read against the tracker (#1113).

**Common hidden risks.** A step held by discipline (#789, #1061); a hollow capture; a merge
in the release window (1.6.2); a cycle count that is the number of `--cycle` flags typed
(#1369); a SIP renamed at promotion breaking a frozen link (#1237).

**Typical failure modes.** Tagged and never advertised; the site not deploying for five
merges; a package of nulls.

**Best verification.** The guards — `test_docs_version_sync` rules 1–4,
`check_release_packages.py` on every push, `release.yml`, the `SIP sweep:` line — and the
preview read.

**Representative history.** #1440, #1368, #1327, #1274, #1227 (the 1.7.x cuts); #1441,
#1371, #1370 (packages); #1095 (a corrected package); #1248 (#1151); #1114 (#1113).

**Tier.** `L+` for steps 1–3 and 6, which are guarded; `F` for the sweep, the disclosure and
the preview read.

**Owner / approver.** Recorder executes; the owner's explicit word for every promotion.

---

### 15. SIP authoring, amendment and promotion

**Description.** Proposing a design, revising it against main, accepting it (number
assigned, registry row updated), amending it in the PR that diverges, promoting it at a
cut. `sip` 14, `sips` 3, `chore(sip*)` and `docs(sip)` scopes; 125 SIP files at #1144's count.

**Typical trigger.** A design decision that outlives a plan; an implementation that
contradicts accepted text (§5d); a disposition deliberately not built; a rename.

**Typical input artifacts.** Main at a named commit ("deep review against main
`df29d45c`", SIP-0103 §5b); the measured facts the SIP asserts; `sips/registry.yaml`.

**Typical files / subsystems.** `sips/proposed|accepted|implemented/`, `sips/registry.yaml`,
`scripts/maintainer/update_sip_status.py`, `audit_sip_registry.py`, the site's SIP pages.

**Kind of judgement.** Design (the owner's review); whether a premise still holds against
main (§5d A1–A3 found three that did not); what to say about what was not built.

**Common hidden risks.** Accepted text that no longer describes main; `updated_at` edited by
hand; a rename that breaks a frozen release link; a registry that indexes only numbered
SIPs (#1144).

**Best verification.** `test_sip_registry_audit.py`, `test_site_sip_links.py`,
`test_docs_version_sync` (Targets parity); the amendment naming evidence and who ruled it.

**Representative history.** #1416 (§1.2f), #1409 (§1.2e/f and promotion), SIP-0103 §5a–§5d,
#685 (promotion audit: nothing promoted, gaps named), #1242 (#1144), #477, #596, #617,
#1325 (proposed, awaiting review).

**Tier.** `F` for design and amendment content; `L+` for the promotion mechanics through
the script.

**Owner / approver.** Recorder / architect; the owner accepts and promotes.

---

### 16. CI, dependency and packaging correction

**Description.** Making CI test what ships and the package install from its own metadata:
constraints, locks compiled against them, documented exceptions, required checks, the
fresh-venv job, the closure check, the vulnerability audit. `ci` 8 plus `chore(deps|
packaging)`, `fix(deps)` and `test(architecture)` ratchets.

**Typical trigger.** A red on main that only a non-required job showed (#1357); a measured
divergence (#1041: 42 packages); a fresh-venv failure (#582); an unbounded pin drifting
(#198); a job that a docs-only PR pays for (#1220).

**Typical input artifacts.** `ci-constraints.txt`, `requirements/*.lock`, the diff between
them run in the container, the workflow files.

**Typical files / subsystems.** `.github/workflows/`, `requirements/`,
`scripts/maintainer/update_deps.sh`, `pyproject.toml` `[project.dependencies]`,
`tests/unit/architecture/test_dependency_drift.py`.

**Kind of judgement.** By construction over by detection (#1203); what genuinely cannot
follow CI and why (`constraint-exceptions.txt`); the non-required job read after every
merge (1.7.5 §3.10).

**Common hidden risks.** Green locally, red in CI (#198); `pip-compile` keeping a stale pin
as a preference (#1203's second defect); a CI lane that skips for docs-only PRs hiding a
change that was not docs-only.

**Best verification.** The drift guard; the fresh-venv install and import; the comparison
run inside the running container, not read off the files.

**Representative history.** #203, #1114, #1248, #1377, #1382, #1390, #1249 (#582), #1203
(#1041), #1183 (#1099/#1182), #268, #237, #1185.

**Tier.** `L+` for the recompile and the workflow edit once the policy is set; `F` for the
policy ("not just pin them together", #1041) and for judging a new red.

**Owner / approver.** Integrator / Platform operator; Verifier for the guard.

---

### 17. Deployment, host and infrastructure operation

**Description.** Rebuilding and deploying, provisioning images, host timers, memory
containment, disk reclaim, backups, the identity provider, the broker, the test database
role — the "ops rider" lane, read live rather than in CI. `ops` 4 plus the scripts under
`scripts/dev/ops/` and `infra/`.

**Typical trigger.** The box (65% disk, #1465; a 95-minute livelock, #1177/#1178); a deploy
that printed success and left stale agents (#370); a check inert for want of a tool (#306);
a realm export not re-synced (#372).

**Typical input artifacts.** `docker system df`, `sar` logs, `docker compose ps`, image
ids and start times, `systemctl` state read from the running process.

**Typical files / subsystems.** `scripts/dev/ops/rebuild_and_deploy.sh`, `prune_docker.sh`,
`install_timer.sh`, `backup_db.sh`, `keycloak_realm_sync.py`, `infra/systemd/`,
`infra/00-create-databases.sh`, `docker-compose.yml`, `agents/Dockerfile` and the per-role
package files, `sandbox/environment.py`.

**Kind of judgement.** Anything destructive or root-adjacent (capabilities 7.8, 7.9, 8.10,
8.11); the pruning order that decides what is freed; whether a compose or init edit is
allowed at all (#225 and #1180 both on the owner's recorded OK).

**Common hidden risks.** One flag away from data loss (`-a`, `volume prune`); a rebuild over
a running cycle; a `--rm` container losing the boot reason (#1214); a unit template with a
placeholder the installer refuses (#1465's guard).

**Typical failure modes.** Irreversible, and silent until the next cycle: a lost volume, a
box that pages forever, stale agents behind a green banner.

**Best verification.** Read the running process, not the declared unit; before/after
figures; the honest exit code; the host-timer guard; a live cycle after the deploy.

**Representative history.** #1388 (#581), #1395 (#372), #1396 (#330), #1397 (#560); #1465;
#1177/#1178; #370; #306; #1197; #1180; #529/#704.

**Tier.** `L` for status reads (7.5); `L+` for a scripted rebuild with the log read; `F` for
everything that can remove data, change the host, or touch compose.

**Owner / approver.** Platform operator; the owner for sudo, compose, init and anything
destructive.

---

### 18. Migration, configuration and profile change

**Description.** A schema migration, a squad or request profile edit, a config variable
introduced or made required, a bootstrap profile, a model registry entry. 19 migrations in
reserved ranges; the profile and config edits are small PRs with outsized consequences.

**Typical trigger.** A SIP's schema need (1100–1130 for SIP-0089; 1400 for SIP-0096); a
per-agent override (1.6.5 E: eve's completion budget); a provider switch (#1157); a
health-assessment finding (#333).

**Typical input artifacts.** `infra/migrations/README.md` (ranges, idempotency, one concern
per file); `config/squad-profiles.yaml`; `.env.example`; the compose service blocks.

**Kind of judgement.** Which identity hash the edit moves (a per-agent override moves the
squad snapshot, not `resolved_config_hash` — the driver asserts both); whether a table is
`init.sql`'s or a migration's (#1357); whether the change breaks comparability with prior
sets (#1427); require rather than default (#333, #1157).

**Common hidden risks.** A migration altering a table only `init.sql` creates — red in CI's
integration job for six merges (#1357); a default that masks a missing value; an edit the
config hash does not cover so the record claims continuity it lost.

**Typical failure modes.** Every DB-backed integration test erroring at setup; an adapter
unreachable by any configuration; a set silently comparing across a changed request.

**Best verification.** The migration-runner idempotency test and the DDL↔model drift guard
(now: a migration may only `ALTER` a table a migration creates); `squadops doctor`; the
driver's two hash assertions; a live cycle.

**Representative history.** 1150 (#305, PR #1343, #1357); 1030 (#682); 1010 (#427);
1020 (#735–#737); #1157; #333; #85, #105, #175; #1180; #1197.

**Tier.** `L+` when fully specified and idempotent; `F` when it moves a hash, touches
compose or `init.sql`, or changes what a set compares to.

**Owner / approver.** Platform operator / Implementer; the owner for compose and init
edits and for anything affecting comparability.

---

### 19. Prompt, authoring-asset and contract-vocabulary change

**Description.** Changing what an agent is told or shown: a fragment, an appendix asset,
the authoring rules, the rendered vocabulary, a derived fact threaded into a brief. Four
`(prompts)`-scoped PRs and many more inside fixes; 89 fragment files under
`src/squadops/prompts/`.

**Typical trigger.** An author invented a fact it was never shown (#911); restated a fact
the system derives (#1067, #1254); was taught the wrong stack's seam (#912, #902); omitted
a section it was never asked for (#1312's replacement); a fragment missing from the manifest
(#131).

**Typical input artifacts.** The stored prompt from LangFuse (under the 10,000-character
cap, or not — #1110); the fragment manifest; the plan-authoring rules registry.

**Typical files / subsystems.** `src/squadops/prompts/fragments/`, the appendix assets,
`plan_authoring_rules`, the manifest and `regen_fragment_manifest.py`, the render-variable
builders in the handlers, the LangFuse sync at deploy.

**Kind of judgement.** Teach or derive (the C4 lesson — derive when the system holds the
fact); the fragment seam, never an inline literal (#448); byte-equivalence when moving
prose (#452, #747); whether the change reached the model (#1289).

**Common hidden risks.** A placeholder declared and never filled; an asset version bump
(v4, v6) that a stored replay depends on; a rule that is "a list of past guesses"
(#1254); a boot against a registry lacking an asset the image ships (#352 → #1394).

**Typical failure modes.** The instruction never reaches a model; two documents disagree
about a fact neither needed to decide; every documented fill fails (#936).

**Best verification.** The rendered prompt read from LangFuse; render-variable tests; the
byte-equivalence pin; the registry boot check; a live roll reading the emission shape.

**Representative history.** #450 (#448), #747 (#452), #1043 (#1042), #1063, #1290
(#1289), #686, #848/#857/#917/#919/#891 (authoring rules), #1254, #1394 (#352), #131,
#351 (#327).

**Tier.** `L+` for a specified wording change through the fragment system with its pin; `F`
for teach-versus-derive and for confirming the prompt rendered.

**Owner / approver.** Implementer; Verifier reads the rendered prompt.

---

### 20. Feature implementation along a SIP's phase ladder

**Description.** Building an accepted SIP in phases or slices, each with its own acceptance,
pins and live validation — SIP-0096's slices, SIP-0100's phases 0–4, SIP-0103's M-ladder,
SIP-0102's phases, SIP-0106's P0–P6. `feat` is 173 PRs, median 403 lines across 8 files, 90th
percentile 2,218 lines; 1.4.0 alone was 133 merges.

**Typical trigger.** An accepted SIP with an implementation plan; a phase's predecessor
landed and live-validated.

**Typical input artifacts.** The SIP text (read as spec — "read accepted SIP spec text, not
just code"); the implementation plan's phase list; the goldens and hash pins each phase
must hold or move.

**Kind of judgement.** The seam each phase introduces; whether a premise still holds against
main (SIP-0103 §5d: "authored mode was dead on arrival"); when a phase narrows the design
and must amend the SIP; when a spike becomes a baseline (#429 → 99.1–99.3).

**Common hidden risks.** Premise drift between acceptance and implementation; a phase
landing without the live proof its predecessor had; scope that expands into the correction
loop (1.4.0's volume "dominated by the correction/repair loop, which had to converge before
any of the scaffold work could be measured at all").

**Typical failure modes.** A feature that stores, validates and promotes an artifact and
then silently does not carry it (#796); a mandatory gate rubber-stamped (§5d B1).

**Best verification.** Phase acceptance criteria; golden pins; a live cycle per phase
(shakedowns shk-1…shk-5 in 1.4.x); the SIP amended in the diverging PR.

**Representative history.** #369, #378, #386, #412, #416, #418 (SIP-0096); #541–#550
(SIP-0100); #777–#812 (SIP-0103 M-ladder); #620–#631 (SIP-0102); #800, #805, #1161, #1165
(SIP-0106).

**Tier.** `F` for the ladder and each new seam; `L+` for a phase whose plan fully specifies
the edit and the pins.

**Owner / approver.** The primary engineer; the owner accepts the design and rules on
narrowing.

---

### 21. Dead-code and debt removal

**Description.** Deleting a layer, backend or component with zero production callers, with
the caller census as the proof and the mirror rule applied.

**Typical trigger.** An audit (#401's skill layer; #234's `DbRuntime` factory "only ever
constructed by its own tests"); a component never constructed (#1200: `LLMRouter`, 139
lines maintained four times); a step whose verdict was never read (#558).

**Kind of judgement.** Capability 1.3 (enumerate every site) and 11.5 (what it produced and
for whom) — the census is the judgement; #1253 → #1255 is what happens when the second
question is skipped.

**Common hidden risks.** The removed thing was the only carrier of something (the handoff
regexes were a builder task's only typed criteria); a breadcrumb referencing a method that
never existed misread as a caller (#234).

**Best verification.** AST/grep census in the PR; regression green; the PR template's
"Removed: … produced … for …" line.

**Representative history.** #403 (#401), #356 (#234), #1200, #558, #1241, #406 (#404),
#175.

**Tier.** `L+` once the census and the mirror-rule answer are written; `F` for both.

**Owner / approver.** Implementer; Investigator for the census; Verifier for the mirror
rule.

---

## Shapes named in the prompt that the history does not support as separate archetypes

- **"Existing-pattern extension."** The record contains it only as a *risk* inside other
  archetypes — "the neighbouring code does it this way" is named in CLAUDE.md as never a
  justification, and #218, #448 and #380 are what extension-by-neighbour produced. Where a
  pattern is legitimately extended (a new `stack_*` module, a new check on the registry), it
  is archetype 4 or 5 with the seam's rules applied.
- **"Bounded mechanical implementation."** Real, but not a shape of its own: it is the `L+`
  half of archetypes 5, 6, 7, 9, 16 and 18 after a frontier framing. The record does not
  contain a mechanical change that arrived pre-bounded; every one was bounded by a map, a
  guard, a census or a plan row first.
- **"Integration failure diagnosis."** Folded into 2 (cross-layer tracing) and 16 (CI).
  The integration-test failures in the record (#211, #1099) were stale fixtures and mocks,
  diagnosed the same way as any CI red.

---

## Work that looks easy but historically required high judgement

| what it looked like | what it was | evidence |
|---|---|---|
| a one-line gate on the accepted-patch path | keyed on the attempt's history instead of the contract; two counted rolls voided across two lines | #1318 → #1364 → #1374 |
| binding two well-tested checks onto a task's suite | evaluated on a tree without the file; `file_not_found` counted as an executed failure; a correct fix refused | #1240/#1246 → #1259 |
| stripping brittle plan-authored regexes | they were a builder task's only typed criteria; the next repair was discarded unheard | #1253 → #1255 |
| a gate that "just" checks two documents agree | its premise had been made false by an earlier fix; one to two re-rolls per cycle | #1013 → #1042 → #1049 |
| renaming probe keys to allow two per service | the key was docker-exec'd verbatim; three probes never ran through a checkpoint pair read as clean | #1425 |
| grouping banked artifacts by task id to count emissions | falsified within the hour by a case with two attempts and one artifact each; reverted | #1431 → #1436 |
| dropping one column | the table is `init.sql`'s, not a migration's; the integration job red for six merges | #1343 → #1357 |
| editing seven lines of a PRD | the config hash does not cover the PRD; comparability with three prior lines — raised as the owner's call | #1427 |
| an agent id string in compose | needs the owner's explicit OK, recorded on the PR | #225 |
| the record's deploy header string | typed, never measured, dead fallback; a shakeout rendered `?` | #1296 |
| a terminal condition "signature repeated" | could not tell "did not help" from "was never applied" | #1129 |
| a default provider, a default agent id | an adapter unreachable since it landed; identity fabricated | #1157, #333 |
| "is this red pre-existing?" | a wrong answer is invisible and propagates (capability 5.4/5.5, `F`) | `maintainer-agent-capabilities.md` allocation notes |

The pattern: the edit is small; the *evaluation surface* the edit sits on is not, and the
surface was never tabled. Every row above is a seam with more than one reader.

## Work that looked complex but was reliably mechanical once framed

| what it looked like | what framed it | evidence |
|---|---|---|
| rename across 106 files | the guard that fails the retired spellings; merge order "widest first" | #1335 (#922) |
| 216 literals across 30 files to a `StrEnum` | four stated rules; the literal guard | #1336 (#559) |
| split a 3,276-line handler monolith | hoist first (#338), then a pure move behind a shim | #339 (#152) |
| split an 1,887-line planning handler | AST-verified 20/20 top-level names; every pre-split test unmodified | #754 (#331) |
| decompose a 3,358-line executor | six slices with one collaborator each; live-validated per slice | #341–#349 (#186) |
| replace five tables and three branches with a registry | golden-first: 19 goldens captured before each slice, byte-identical through | #751–#753 (#663) |
| extract a 651-line inline expander | byte-identical fixtures: 3 manifests, 57 files; rationale harvested first | #1233 (#1131), #1149 |
| reconcile 42 dependency divergences | compile the locks against the constraints; a reason file for the rest | #1203 (#1041) |
| index 24 unindexed proposals and fix 19 audit findings | the audit script already existed; wire it to the gate | #1242 (#1144) |
| delete a dead skill layer end to end | a caller census showing zero | #403 (#401) |
| resolve 235 test-quality violations | the AST linter, made blocking | #20 |
| eight structural items on one deploy | a checkpoint pair between them and the behavioural block; a guard per item | 1.7.3 plan §3.2, §9 |

The pattern: a stated rule, a guard that enumerates the surface, and a proof that is a
comparison (byte-identical, AST count, "nothing left to flag") rather than a judgement.

## Archetypes that often expand scope unexpectedly

- **Recovery-path change (3) and cross-layer tracing (2)** — every rule-B PR exposed the
  next hop: #1229 → #1238 → #1250 → #1256 → #1259 → #1264 → #1406 → #1350. #1323 →
  #1350. #1268's contentless emission reached four recovery seams for the first time
  (#1269, #1271, #1272, #1273). #994 → #1415.
- **Retiring a document or a rule (21, 19)** — #1312 → #1254, #1255, #1427/#1430, and
  then #1364/#1372/#1374 on the builder's contentless attempt.
- **Derive-don't-author (19)** — #1067 → #1070 A/B → #772 → #1049: one integer, four
  PRs.
- **CI truth (16)** — #1041 found #1203's second defect (`pip-compile` preferences); #582
  found #1241; #1099 found #1182 and #1183.
- **Audits (13, 15)** — #1144 named four findings and the fix found fifteen more once the
  file's own field was read; #1465's disk reclaim produced a host-timer guard.
- **Verification-set operation (11)** — the 1.7.1 loop budgeted one pair and ran six
  deploys; 1.7.2 ran five rounds against a budget of three.

## Archetypes that historically caused rework or multiple correction rounds

- **Evidence instrumentation (10):** #1431 → #1436 (reverted within the hour); #1296 →
  #1297 (dead fallback); #1362 (readout wired to the wrong mechanism); #1425.
- **Gate introduction without controls (4):** #552 → #553 (reverted whole); #1013 → #1049
  → #1070 (four fixes for one fact); #1004 → #1005 (instrument fix as an owner's ruling).
- **Gate coverage by list (9):** #200 → #220 → #207 → #1316, each an append.
- **Accepted-patch derivation (3):** #1318 → #1364 → #1374, "patched gate by gate".
- **Repair verifiability (3):** #1221 (option A) → #1229 (option C) → the six-PR chain.
- **The shakeout loop (11):** six deploys in 1.7.1; seven harness/instrument defects in
  1.7.3; five instrument fixes while 1.7.4 ran.
- **Plan carry (12):** #301, #286, #567, #579, #820, #376, #929, #353 each on their fifth
  plan by 1.7.5 §3.8.

Rework in this record clusters where a change's evaluation surface had more than one
reader and only one was tested, or where an instrument encoded an inference. It does not
cluster in the mechanical archetypes.

---

## Implications for Delegation

The capabilities document's tiering rule applies here without modification: **the
local/frontier line is cost of being wrong, not difficulty.** The archetypes sort onto it
as follows, and the sort is what the record shows rather than what the shapes look like.

**Safest for a bounded local-model supporting engineer — end to end or after framing.**

1. **Vocabulary sweeps (7)** against a landed guard: the guard bounds the edit, the proof is
   "nothing left to flag", and the 1.7.3 line's eight items found nothing attributable. The
   frontier retains the boundary decision and the config fallout.
2. **Behaviour-preserving extraction (6)** against a reviewed map: goldens captured first,
   AST counts, byte-identical fixtures. The map is the frontier's; the move is not.
3. **Guard authoring (9)** against a named shape with the commit it must fire on: the
   revert-and-run proof is mechanical. Deciding the shape is not.
4. **Verification-set collection (11)**: preflight, detached launch, gate approval with the
   pre-registered constant, collection, render. This is exactly what the standing night
   rules already delegate — "no pushes; detections recorded, not fixed; gates are the §6
   constant" — and it has run four overnight sets. The roll-boundary reading is not
   delegable.
5. **Instrument fields (10)** with a stated producer, a stated unaskable state and the real
   line shape in the test. Deciding what a readout means is frontier.
6. **Prompt wording changes (19)** through the fragment system with a byte-equivalence pin
   and a rendered-prompt check. Teach-versus-derive is frontier.
7. **Release steps 1–3 and 6 (14)** — guarded by tests and a workflow; the sweep and the
   preview read are frontier.
8. **Scaffold emitter fixes (5)** whose proof is byte-identical fixtures and no pin moves.
9. **Dependency recompiles and workflow edits (16)** after the policy is set.

Every one of these carries the allocation note's condition: **a paired control.** A local
engineer reporting success on a task it could not have failed is the same defect as a test
that can only pass; the guard, the golden, the fixture hash or the fired probe is what makes
the report checkable.

**Stays with a stronger primary engineer or architect.**

1. **Recovery-path changes (3)** — every one changed a semantic the next roll is judged by;
   five were owner's rulings; the chain from #1229 to #1350 is the cost of one seam read
   incompletely.
2. **Cross-layer tracing (2)** — found by reading two sources against each other; blast
   radius unknown until the trace is complete.
3. **Typed-check and gate design and blocking promotion (4)** — the seam table, the
   false-positive cost, and #1259 as the price of skipping it.
4. **Architecture rules and standards (8)** — reviewed by the owner before the first
   constrained PR, by the 1.7.5 procedure.
5. **Plan authoring and placement (12), issue filing and triage (13), SIP design and
   amendment (15)** — every revision in the record was on the owner's review or ruling; a
   wrong mechanism claim in an issue propagates into a wrong fix (#691).
6. **Roll-boundary readings and supersede decisions (11)** — counted/void/reset; whether a
   finding supersedes the deploy. 1.7.1 §3.3 is what a premature release costs.
7. **Host and compose operations with destructive potential (17, 18)** — one flag from
   data loss; every compose and init edit in the record carried the owner's recorded OK.
8. **Anything that concludes "clean", "green", "passing" or "safe"** — the allocation
   note's rule, and the record's sharpest evidence for it: the four delegation-era failures
   that made it into the tracker (#1425's unrun probes read as data, #1357's six merges
   read on three required checks, 1.7.1 §3.3's early release, #1436's heuristic) were all
   *frontier* delegate errors in the confirming direction. A bounded engineer is not
   proposed for those classes because a stronger one already missed them; it returns raw
   evidence and lets the frontier conclude.

**The one structural rule the record adds.** The archetypes that expand scope and cause
rework are the ones whose evaluation surface has more than one reader — the correction
loop, the check seams, the instrument. Delegation to a bounded engineer is safe precisely
where that surface has been tabled and turned into a guard, a golden or a probe: the
frontier's job is to produce that table, and the bounded engineer's job begins when it
exists. Delegating before the table is written is how #1259, #1255 and #1425 happened,
and the model doing the work did not change that.
