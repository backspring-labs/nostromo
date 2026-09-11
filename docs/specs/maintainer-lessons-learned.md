# SquadOps Maintainer Lessons Learned

**What this is.** The failure-derived engineering lessons that shaped how SquadOps is
developed, each grounded in the repository's own record: issues, PRs, commits, plans,
SIP amendments, verification records, guards and operational incidents. It explains the
rule *and* the failure that made the rule necessary, so the next maintainer — human or
agent — can tell a load-bearing rule from a convention.

**What it is not.** A retrospective, or a list of good practices. A lesson appears here
only when the repository history supports it with a named failure and a named remedy.
Where a remedy is still proposed rather than landed, that is stated.

**Sources read for this document.** `CHANGELOG.md` (1.1.0 → 1.7.4), every guard under
`tests/unit/architecture/`, `docs/TEST_QUALITY_STANDARD.md`,
`docs/plans/verification-sets/README.md`, the 1.6.x–1.7.x plans, pre-registrations and
records, SIP-0096, SIP-0103 §5d, SIP-0106 §1.2, `.github/PULL_REQUEST_TEMPLATE.md`, the
CI workflows, `scripts/dev/verification_set_driver.py`, and roughly ninety issues and PRs
cited inline. Bare `#NNN` references are issues unless marked as a PR; the CHANGELOG's
1.4.0 section uses PR numbers, which is noted where it matters.

**Reading the entries.** Each lesson carries the same fields: the rule; what happened; why
the original approach was reasonable; how it failed; how the failure was found; what
emerged; where it is encoded (code, guard, test, plan, SIP, maintainer script, procedure);
where it does not apply; references. The last section ranks the lessons that should most
strongly steer an AI maintainer.

---

## A. What a test proves

### A1. A seam test proves the seam; only a wiring test proves the cycle reaches it

**Rule.** Any change to a seam another component calls — a new output key, a new
parameter, a row another environment consumes — ships with two tests: the seam's own,
and one that enters at the caller the live cycle uses and asserts what arrives. The PR's
Evidence section names the entry point.

**What happened.** Three defects in the 1.7.1 line were latent from the day their PRs
merged, each with green unit tests, and each was found by a live cycle rather than CI:

- #1250 — the correction runner's tests (#1238) handed it an envelope that already
  carried `acceptance_workspace_files`. The executor handed the runner the *base*
  envelope, which never has it. Rule B's repair evaluated its patch in a patch-only
  tree; `frontend_compiles` skipped for want of a frontend; runtime-api returned
  `unverifiable / no_executed_blocking_checks`.
- #1256 — the verifier's tests passed the repair's rows straight in.
  `_try_accept_patch` read `repair_typed_checks` off the *failed task's* result, where
  the repair handler never writes it. Rule B ran for three weeks without delivering a
  single row in a live round; every `decided_by_agent` in the line's records was 0.
- #1261 — the tsc classifier was tested with a `TS1005` line. The live tree carried
  `TS18048` ("possibly undefined"), which `startswith("TS1")` also matched, so five of
  nine accepted test files were never checked for undefined names — as *skipped* rows,
  invisible to a readout that counts failures.

**Why it seemed reasonable.** Each seam had a real test with real inputs, and the inputs
were the correct shape. A test that constructs the seam's input by hand is the ordinary
unit-test form; nothing about it looks incomplete.

**How it failed.** The seam was correct and the caller never delivered what the seam was
tested with. The unit tests could not fail, because they never involved the caller.

**How it was detected.** The 1.7.1 shakeout loop: each deploy's shakeout pair found the
next seam defect (`cyc_3ac86805439f`, `cyc_c6db3ffc1f4e`, `cyc_9c379355b5e8`). The
pre-registration's R7 diagnostic had *also* passed — it was an in-container replay of
the verifier with the rows in hand, which is a replay of the function, not the path.

**What emerged.** Anti-pattern 6a, "seam tests that hand the seam its input", and a
"seam wiring" row in the minimum-coverage table. The diagnostic rule that follows from
it: a diagnostic runs the roll's own path with the fault injected, is recorded with the
entry point it used, and a call into the seam with its input in hand is named as a
replay and never stands in for a prediction.

**Where it is encoded.**
- Test standard: `docs/TEST_QUALITY_STANDARD.md` §6a and the coverage table's "Seam
  wiring" row; CLAUDE.md "A changed seam needs a wiring test".
- PR template: `.github/PULL_REQUEST_TEMPLATE.md` Evidence — "Entry point exercised:
  <executor method / protocol / registry> — <test name>".
- Procedure: `docs/plans/verification-sets/README.md` "What a diagnostic is".
- Instrument: `#1251` fault injection, so a recovery-path prediction is exercised on
  the roll's own path rather than waited for.
- Examples of the form: #1347's wiring test enters at `execute_run`; #1250's
  executor-level test pins which envelope `_handle_task_outcome` hands over.

**Where it does not apply.** A pure function with no new caller. The seam test remains
necessary; the wiring test is owed when the seam's *callers* or *outputs* change.

**References.** #1250 (PR), #1256, #1261, #1238, #1251, #1289; CHANGELOG 1.7.1
"Changed — what the 1.7.1 shakeouts taught".

---

### A2. Verify loaded, not merely built

**Rule.** Before a measurement or a merge that depends on deployed behaviour, verify the
code is *reachable in the running container* — a live call with its paired control,
never a symbol import, never the rebuild's exit code — and record the output with the
deploy identity. A probe that cannot run stops the launch.

**What happened.** The pattern recurred across a year in different clothes:

- #270 / #272 (1.1.1) — post-merge live verification of the 1.1.0 stack found every
  cycle route returning 403 (scopes the realm never issues) and duty windows never
  opening (poll-lag read as a missed window). Both had green unit suites.
- #306 — the qa image had no Node, so the frontend build check and vitest were inert in
  every deployment; a frontend that did not build shipped green.
- #327 — every role agent logged a prompt-manifest hash mismatch at startup and
  continued. The LangFuse registry had been seeded once and never re-synced;
  SIP-0093's templates were missing at runtime while the files shipped in the image.
- #710 — six agents sat in `mode=cycle` holding zero leases for 64 cycles over two
  weeks, including a green confirmation roll. Focus arbitration was silently inert.
- #370 — `rebuild_and_deploy.sh` printed its success banner and exited 0 after a
  swallowed agent restart failure, leaving stale agents running.
- #1289 — the qa repair's failing-cases brief and frozen-client surface were computed,
  threaded onto the inputs, and dropped at `_build_render_variables`. Neither had ever
  reached a model; the R4 readout was reading a log line about a brief that was never
  rendered. Confirmed on the stored prompt (LangFuse `35f698cd`, 8,550 chars, under
  the store cap, no `REPAIR SCOPE` in it).
- #1425 — three of seven 1.7.4 loaded-check probes named containers that do not exist
  (`squadops-bob-1-7-4`), recorded `No such container` on every launch, and the deploy
  B checkpoint pair was read as clean with three surfaces unverified.

**Why it seemed reasonable.** Built and green in CI reads as deployed. The unit suites
were real; the images were rebuilt; the exit code was 0. A symbol present in a module is
the natural proxy for a feature present in a container.

**How it failed.** Presence and reachability came apart. A symbol can exist and be
unreachable (#1289); an image can be rebuilt and not restarted (#370); a check can run
and skip because its tool is absent (#306); a registry can be pinned and stale (#327).
Each read as green.

**How it was detected.** Live cycles and pre-deploy captures, every time: the 1.1.0
live verification, `cyc_2ecf5f0e5bd1` for #306, a container log sweep for #327, a
pre-deploy `agent_runtime_state` query for #710, LangFuse for #1289, and — for #1425 —
the author re-reading the recorded identity after the pair had already been read.

**What emerged.** The "Loaded, not built" row of every pre-registration since 1.6.3,
verified per container as a live call with its paired control; the driver's
`loaded_checks` as data on the set config, output recorded in every record; and, after
#1425, a preflight that refuses to launch when any probe errors. The freeze itself is
verified rather than assumed — image ids *and* container start times, because an
identical id on a container restarted mid-window is still a moved boundary (SIP-0104
P6 record). The repo-level form: runtime-affecting PRs get a live smoke or lite cycle on
the deployed stack before merge (the 1.2.0 plan's "1.1 lesson").

**Where it is encoded.**
- Instrument: `scripts/dev/verification_set_driver.py` — `LoadedCheck`,
  `SetConfig.loaded_checks`, `loaded_check_problems` in `preflight` (#1425), the
  record's "Loaded, not built" block.
- Procedure: every `docs/plans/*-verification-set-preregistration.md` carries the
  "Loaded, not built" row; `docs/plans/1-6-0-v7-fay-window-preregistration.md` §"Deploy-
  prove before roll 1, in-container … not the rebuild's exit code".
- Script: `scripts/dev/ops/rebuild_and_deploy.sh` honest completion banner and exit
  code (#370); deploys re-sync prompts to LangFuse and the manifest loader hard-fails on
  hash mismatch (#327, PR #351).
- Image provisioning as data: `agents/instances/<role>/system-packages.txt` and
  `npm-global-packages.txt`, guarded by
  `tests/unit/architecture/test_typed_check_tooling_is_provisioned_where_checks_run.py`.

**Where it does not apply.** Docs-only and driver-only changes: by the 1.7.2
pre-registration §2 an instrument fix does not supersede a deploy, which is what let four
1.7.4 instrument fixes land mid-line without a rebuild (#1438).

**References.** #270, #272, #306, #327, #370, #710, #712, #1289, #1425, #1297;
`docs/plans/sip-0104-p6-window-record.md` ("The freeze was verified, not assumed").

---

### A3. A gate ships with its positive and negative controls, and a guard proves it fires on the commit that motivated it

**Rule.** A new check, gate or guard is landed with (a) the stored red it catches, named,
and (b) the stored greens it passes, named — replayed from the artifact vault before it
gates anything. A structural guard demonstrates that it fails on the offending commit.
"Two controls, stated" is acceptable; zero controls is not.

**What happened.** The repository's record shows both directions:

- Landed *with* controls: #1029 (the frozen shell floor) was replayed against banked
  green trees before it gated anything; #913 was sandbox-proven — no false rejection on
  a green app, and exactly the pinned shells fail on a mutated envelope; #1082 was run
  over all 4,513 scannable source artifacts — 8 flags, every one a genuine truncation,
  and the two false positives found *during* validation drove real fixes rather than a
  tuned threshold; #1094 was replayed over all 72 banked fill slots of the 1.6.3 set;
  #1240 replayed 1.6.6 roll 3's suite (rejected at line 167) with rolls 1 and 5 as
  controls; #1246 measured nine accepted-roll suites first and found the root-anchor
  form would have flagged seven of them — so the rule was written as "any anchor".
- Landed *without*: #552 (PR) shipped a plan-authorization gate validated only against
  synthetic fixtures, never the live seeded contract, with a recovery path that was not
  firing live. #553 reverted it whole, "an unvalidated new rejection gate sitting in the
  path of a measurement". #1049's framing-omission gate enforced a premise (#1042 had
  made false) that nothing had re-checked against real traffic; it cost one to two
  re-rolls per cycle and dead-ended two.
- Instruments too: #1004 — the boot audit's UI-path extractor handled template literals
  and not `+` concatenation; rolls 1–5's authors used one style, the deciding roll's
  author used the other, and the instrument's coverage of author styles decided the
  window's headline.

**Why it seemed reasonable.** A gate that rejects the defect it was written for looks
finished. Synthetic fixtures are quicker than a vault replay and exercise the same code.

**How it failed.** Without the greens, a gate's false-positive rate is unknown until a
counted roll pays for it. Without the red on the motivating commit, a guard may be
holding a shape nothing ever produced.

**How it was detected.** Counted rolls and window rolls: #1004 on V7's deciding slot,
#1049 across three cycles, #552's hazard in review before it reached a roll.

**What emerged.** Every check PR's Evidence names its replays and controls; structural
guards state the commit they fire on (`test_stack_shaped_literals_live_behind_the_seam`
"run against `1b9b93a9` it fires"; `test_ddl_model_drift` "fails on the old 1150";
`check_release_packages.py` "passes on the real package; fails on a synthetic hollow
one"). The loaded-check probes are "a live call with its paired control". A new hard
gate on an unvalidated surface is refused (the reverted-#552 rule in
`docs/plans/pf31-correction-convergence-fixes.md`); reporting-only first, promotion on
corpus evidence (#1022 promoted on the V7 corpus and two lines of accepted suites;
#598 shipped `warning` severity with a 203-recipe readout).

**Where it is encoded.**
- Check governance: `CheckSpec.blocking_default`, `row_is_blocking_failure` (#598) —
  a warning-row failure is banked and never rejects.
- Fixtures: `tests/fixtures/roll_replays/` with README rows naming each replay.
- PR bodies: the Evidence section (replays, controls, regression counts).
- Guards: the docstrings above, each naming the commit or shape it fails on.

**Where it does not apply.** A check whose motivating shape has no stored instance yet
(#1123's undeclared-anchor signal) lands with "a synthetic exercise and a stored control,
not a stored red" — and says so.

**References.** #1029, #913, #1082, #1094, #1240 (PR), #1246 (PR), #552 (PR), #553 (PR),
#1049, #1004, #1005 (PR), #1022, #598, #1131, #1357 (PR), #1151.

---

### A4. The regression gate runs the tree by default; what it leaves out is named with a reason

**Rule.** The gate runs all of `tests/unit`. `EXCLUDED_DIRS` names what is deliberately
left out, each with a reason, and the lint and pytest read the same list. A documented
tolerance for failing tests is removed, not kept.

**What happened.** #1316: `REGRESSION_DIRS` named 21 directories; there were 30. Nine
directories — 38 files, 437 tests, including `tests/unit/auth` and `tests/unit/memory`
named in CLAUDE.md as current suites — had never run in the job CI marks Required, for
up to ten months. It was the fourth filing of the same defect: #200 (`comms`, `agents`),
#220 (`runtime`, `architecture`), #207 (`adapters`), each fixed by appending to the
array. `tests/unit/maintainer` was created the day #207 closed. Separately, #1099: sixteen
integration tests had failed identically on every run of main for months, covered by
CLAUDE.md's "includes legacy tests, some may fail".

**Why it seemed reasonable.** An include list is explicit; adding a directory when it is
created is a small, obvious step. "Some may fail" was true.

**How it failed.** The fact "which tests are gated" had two authors — the filesystem and
the list — and nothing reconciled them. A documented tolerance is how a red stays red.

**How it was detected.** A count of directories against the list (#1316); a full
`pytest tests/integration` run on main and a branch, identical failure sets (#1099).

**What emerged.** The default inverted: pytest and the test-quality lint run `tests/unit`
whole; `EXCLUDED_DIRS` is the exception list; a guard fails a return to an include list,
an exclusion without a reason, or a stale exclusion. Integration debt is dated per skip.
And a process rule from #1357, where main's `integration` job was red for six merges
because it is not a Required check: every merge is followed by a read of the whole CI
run on main (1.7.5 plan §3.10).

**Where it is encoded.**
- Script: `scripts/dev/run_regression_tests.sh` (`EXCLUDED_DIRS`, shared with the lint).
- Test: `tests/unit/scripts/test_regression_gate_coverage.py`,
  `tests/unit/scripts/test_run_regression_preflight.py` (#972: the gate no longer exits
  0 when ruff is absent).
- Procedure: `docs/plans/1-7-5-plan.md` §3.10 "every job of main's run read after every
  merge".

**References.** #1316, #200, #220, #207, #1099, #242, #1357 (PR), #972.

---

### A5. Tests isolate what they measure

**Rule.** A test's verdict must not depend on the machine, the shell, sibling tests, or
the event loop that happened to create a fixture.

**What happened.**
- #239 — the `BrokenExporter` test leaked a global OpenTelemetry provider into sibling
  tests.
- #345 — shells exporting `FORCE_COLOR` broke CLI assertions (rich token-splits digits
  under forced colour).
- The blueprint falsification gate passed at 4 xdist workers and failed at 20 on the
  same commit, so its verdict tracked the machine (1.6.2).
- `tests/integration/llm/test_llm_port_conformance_live.py` — a module-scoped adapter
  handed every test after the first an `httpx.AsyncClient` bound to a closed loop, and
  `refresh_models` swallowed the error, so the failure *presented* as "the backend
  listed no models".
- #1099 — the postgres registry fixture deleted `cycle_runs` while `run_checkpoints`
  rows still referenced them; the checkpoints table was added after the fixture was
  written.

**Why it seemed reasonable.** Each is the shortest correct-looking form: one adapter per
module, plain string assertions, a fixture that cleans the tables it knows about.

**How it failed.** The shared state was invisible until a neighbour changed — a new
table, a new env var, a different worker count.

**How it was detected.** CI on a different machine, a developer's shell, a fresh worker
count, and the false "no models" reading on a live conformance run.

**What emerged.** Fixtures are function-scoped where they hold a loop-bound client, with
the reason in the docstring; assertions ANSI-strip first; the gate was made independent
of xdist's distribution; teardown learns every dependent table.

**Where it is encoded.** The conformance module's `adapter` fixture docstring; the
`pyproject.toml` `asyncio_default_fixture_loop_scope=function` setting it cites; the
fixed tests above.

**References.** #239, #345, #211, #1099; CHANGELOG 1.6.2 "The blueprint falsification
gate stops depending on xdist's work distribution".

---

## B. Evidence, readouts and records

### B1. Verification evidence outranks narrative — read the stored artifact, not the prose about it

**Rule.** Only an executed-and-passed row credits a criterion; not-executed is disclosed
separately and never improves a percentage; agent narrative, self-report and wrap-up
prose cannot override the structured verdict. A reading of a run is made from its stored
artifacts, and a claim about source cites the source.

**What happened.**
- #597 — a *passing* `development.develop` task recorded no verification evidence; its
  typed-acceptance results were persisted to the task's artifact and never reached
  `CycleOutcome`. Seven dev tasks contributed zero rows on the first green roll while
  three routes criteria demonstrably ran and passed.
- #1021 — per-file compile criteria dropped out of `criteria_verified` with no failure
  and no disclosure: a third state the evidence model was not supposed to have.
- The 1.6.3 record §2–§3 read two of three rejections as the framework wrongly rejecting
  working apps (#1087). §6, written the same day, corrected it: the seven per-round
  `test_report.md` files say all three applications failed the frozen response floor at
  every round; the phantom-table assertion was a second failure. The wrong reading came
  from inferring "the app was fine" from a boot audit that cannot see response bodies.
- #968 — the failure analyzer made three confidently-worded false claims about source
  in one roll ("declares a local shadow store array" against `import { all, insert,
  nextId } from '@/lib/store'` on line 3), and the correction decision inherited the
  first verbatim.
- 1.6.3 pre-registration §2: a census of failure classes built on analyzer prose
  inherited the analyzer's misattributions — 4 of 17 runs before a fix date, 0 of 25
  after, once each class was dated against its fixing commit.
- SIP-0096's promotion PR (1.5) found the plan had dropped the audit's fourth normative
  item — a SKIP-only pulse is zero evidence, not a pass — and implemented it rather than
  waving it through.

**Why it seemed reasonable.** The narrative is the readable surface: the analysis
document, the wrap-up, the audit's PASS. Counting `verified` rows is the obvious roll-up.
An analyzer that reads the failing test and names a cause is doing its job.

**How it failed.** A count cannot tell a criterion that never ran from one that ran and
was credited elsewhere; prose can be internally consistent and false; an oracle's blind
spot (bodies) reads as its verdict (fine).

**How it was detected.** Reading the banked per-round reports against the narrative;
reading the source the analyzer described; comparing `run_verification_summaries` to
the task's own typed-check artifact.

**What emerged.** SIP-0096's integrity invariant — three layers deliberately separate,
"0 failed out of 0 executed is not 100%; it is zero evidence", narrative override named
as an evidence-integrity violation — and its 1.5 completion (waivers recorded above the
evidence, never a rewritten verdict; wrap-up *clamped* to the evidence it cites, #683;
inert-cycle detection). The functional-yield measurement verifies "in-cycle green"
against stored evidence, never the roll-up counter ("the #597 lesson"). The analyzer's
prose is now checked for paths the workspace lacks and the decision is handed the
refutation beside the analysis (#968, PR #1418). Records cite artifact ids.

**Where it is encoded.**
- SIP: `sips/implemented/SIP-0096-*.md` §6.1–§6.6, §9, §10.
- Code: `CycleOutcome` roll-up; `criteria_unevidenced` (#1021); the ledger identity
  including the criterion (1.6.4); #683's clamp; `decision_inherited_claims` /
  `analyzer_claims_dropped` (#968).
- Plan: `docs/plans/functional-app-yield-measurement.md` ("verified against stored
  evidence, never the roll-up counter").
- Record: `docs/plans/1-6-3-repeatability-set-record.md` §6 — the correction, in place,
  dated, with the evidence that produced it.

**References.** #597, #1021, #1087, #968, #683, #684, #1418 (PR); SIP-0096; CHANGELOG
1.5.0 "SIP-0096 implemented, not merely promoted"; 1.6.3 record §6.

---

### B2. A readout that cannot tell "did not happen" from "could not be asked" is not evidence

**Rule.** Every recorded field carries one of three states — `observed(value)`,
`asked_none`, or `unaskable(reason)` — and a summary never folds `unaskable` into a
zero. Every readout counts non-execution (skips, by reason) beside failure, and is read
by its reason, never by its count. A probe that cannot run is an unasked question. An
emission fact is read from the emission, not from a downstream token.

**What happened.** The same defect in different clothes across two lines:

- #1261 — five accepted test files silently skipped `undefined_names`; R6's readout
  counted failed rows and could not see it.
- #1276 — three 1.7.1 readouts were misread because the reason was thrown away where
  the rows were counted: "1 kind-gate rejection" was `assertion_kinds_match` failing
  with `file_not_found`; "unverifiable — toolchain absent" was an absent *file*; "0
  empty repair emissions" was two prose-only repairs the runtime-api token never named.
- #1425 — three loaded-check probes recorded `No such container` and were read like
  probes that answered, through a checkpoint pair read as clean.
- #1431 / #1436 — "failed emissions banked" counted artifacts and called them
  emissions; the first fix grouped by `task_id`, was falsified within the hour by a case
  where two attempts banked one artifact each, and was reverted. Timestamp clustering was
  refused as "a heuristic in an evidence instrument".
- The 1.7.4 H1 readout read empty on every roll and meant "structurally unpopulated"
  (the framework's `required_files` row is filtered from the typed-check artifact at
  `validation.py:252`), not "nothing found".
- #1216 — an acceptance check that does not cover a stack was silently skipped, where two
  neighbouring layers (#818, #838) refuse an unregistered stack loudly.
- #1300 — a fault that could not bite (the suite imported no `userEvent`) was logged
  `APPLIED` with `chars 11645 -> 11645`; L7, L4 and L5 were all unexercised while the
  record would have said a fault was applied.
- #1021 — a criterion with no result row: neither credited nor failed nor disclosed.

**Why it seemed reasonable.** An integer is the natural readout: rows failed, emissions
banked, probes run. An empty field reads as "none". `APPLIED` reads as applied.

**How it failed.** Each integer or absence was consistent with two incompatible facts,
and the record kept the one that flattered the roll.

**How it was detected.** Re-reading recorded identities and logs against the record
(#1425 by the author, after the fact); reproducing #1261 with `tsc` in the qa image;
comparing artifact timestamps 42 ms apart against attempts 6.3 s apart (#1436); the
1.7.4 record's own §9.

**What emerged.** The driver's three-state `Evidence` vocabulary (#1445), with the
pre-registration stating for every field what it reads when unaskable — as a schema
property, not a paragraph. Readouts as `{reason: count}` maps (#1276). A probe error
stops the launch (#1425). A fault that changes nothing refuses rather than logs APPLIED
(#1300). A stack with no registered check is refused, never silently passed. SIP-0096
§6.2 is the same rule at the verdict layer: not-executed results are excluded from the
numerator and separately disclosed.

**Where it is encoded.**
- Instrument: `verification_set_driver.py` — `ASKED_NONE`, `UNASKABLE`,
  `Evidence.asked_none` / `Evidence.unaskable`, `unaskable_reason`;
  `loaded_check_problems`; readouts by reason; the emission-shape line read from the
  producing agent's window.
- Tests: `tests/unit/cycles/test_verification_set_driver.py` — "a structurally silent
  producer reads unaskable, not zero"; "an unrunnable probe is unaskable, not answered".
- Procedure: `docs/plans/verification-sets/README.md` "Readouts"; 1.7.4 record §9 "Rule
  for the next record"; 1.7.5 plan preamble ("every field carries one of three states").
- SIP: SIP-0096 §6.2, §7 (mandatory machine-readable skip reason).
- Code: `is_check_applicable` gap made visible (#1216); `FAULTS` refusal (#1300).

**References.** #1261, #1276, #1425, #1431, #1436, #1445, #1216, #1300, #1021; 1.7.4
record §9.

---

### B3. Instrument before fixing, and count the recurrence before the fourth fix

**Rule.** Before choosing a fix for a behaviour whose mechanism is unread, read the stored
generations or artifacts and record the reading in the plan as an amendment. When the
same fact has been fixed more than twice, count the incidents and ask whether the
recurrence is structural.

**What happened.**
- #1268 — the qa role's first attempt became "a sentence of intent and nothing else":
  fourteen attempts across the 1.7.1 counted rolls, zero in 1.6.6's eight, dated to the
  1.7.0 tree. The issue carried three candidate mechanisms and the label "instrument
  first". The 1.7.2 plan §2.1 gated any fix on reading three contentless generations
  from LangFuse with prompt, response, usage, finish reason and the reasoning split; §8
  recorded the reading. Measured live: `think: false` produced 1 usable emission in 6;
  `think: true` 6 in 6. The fix (restore the reasoning channel for the authoring shape)
  followed from the reading, and the bar it set — L1, no contentless qa first attempt —
  held at 0 of 172 and then 0 of 163 emissions.
- #1067 — the success status was fixed four times (#1013, #1042, #1049, #1031) for five
  incidents in three weeks before anyone counted. It existed in seven places, three
  independently authored. The count was the finding; the fix removed the class.
- #1436 — the first fix for #1431 was a plausible inference from timestamps. It was
  falsified by the next day's data and reverted, because an inference in an evidence
  instrument fails silently the first time the data's shape changes.

**Why it seemed reasonable.** A visible symptom with a plausible cause invites the fix.
Each success-status incident looked like a different symptom.

**How it failed.** Fixes aimed at symptoms leave the mechanism in place; the 1.6.x line
records "five incidents, four fixes, one integer".

**How it was detected.** Dating the shape against stored artifacts (#1268's table by
set and tree); tabulating incidents (#1067); the falsifying case (#1436).

**What emerged.** "Instrument first" as a plan step recorded before the fix is chosen;
the emission-shape log carrying finish reason and reasoning tokens so the next roll's
record reads the shape without a LangFuse visit; and the two-shape finding behind
#1285 — a capability id can have two output shapes (a fill is a transcription, a suite
is an argument) that need opposite reasoning levels, decided from measured token
texture rather than from the issue's reasoning alone.

**Where it is encoded.**
- Plan: `docs/plans/1-7-2-plan.md` §2.1 ("Instrument first"), §8 (the reading and the
  fix it selects).
- Code: the emission-shape line (`chars`, `completion_tokens`, `fences`, finish reason);
  `capabilities/reasoning_policy.py` (#927, #1285).
- Practice: #1067's incident table as the shape a recurrence count takes.

**References.** #1268, #924, #927, #1285, #1067, #1070, #1431, #1436; 1.7.2 plan §2.1, §8.

---

## C. Ownership, composition and configuration

### C1. What a test enforces stays true; what discipline enforces drifts

**Rule.** A rule that has been written down and still missed is enforced by a guard, not
restated. The guard lives where it fails CI: an architecture test, a required workflow,
a script the gate runs.

**What happened.** The pattern is recorded in the repository's own words at least six
times:

- #336 — version/doc drift happened three separate times despite the sync rule in
  CLAUDE.md (CLAUDE.md + README stuck at 1.0.5 through 1.1.x; the ROADMAP stats block
  stuck at 1.0.6 through 1.2.0; an accepted SIP targeting a stabilization minor).
- #789 / #1061 — five consecutive releases tagged and never advertised. The CHANGELOG
  guard (#789) then held for two cuts while the adjacent unguarded step — the GitHub
  Release — was missed at both, eleven days after it was written into the checklist.
  #1061's table is a natural experiment: every guarded step performed, the one unguarded
  step missed twice, by someone holding the checklist.
- #1113 — six 1.6.4 fix PRs shipped without `Closes` lines; the second recurrence of
  the #133/#205 gap CLAUDE.md already recorded.
- #1144 — `audit_sip_registry.py` found every defect the issue lists and was wired to
  nothing; nineteen findings accumulated unreported.
- #1316 — the fourth filing of an ungated test directory (A4).
- #380 — `terminal_status == "COMPLETED"` propagated across three SIPs because the
  reviewer reflex "matches existing code → approve" is the propagation mechanism.
- #1427 — the group_run PRD's §0 rule ("product content only") was prose; `qa_handoff`
  survived a sweep in seven places; "prose does not hold".

**Why it seemed reasonable.** The rule was clear, short, and in the file every session
reads. Writing it down is the cheapest fix and, for a while, works.

**How it failed.** Attention is the least reliable gate; each recurrence arrived at a
cut, under delegation, or on a PR whose body bypassed the template.

**How it was detected.** Cut-time audits (#789), the release package's Closes column
(#1113), a count against the folder (#1144, #1316), a live roll (#1427).

**What emerged.** `tests/unit/architecture/` as the home for ratchets; CI workflows for
what the tree cannot see (`release.yml`, `pr-closure.yml`); the regression gate running
the SIP audit; a guard derived from the owning module rather than a hand-copied list
("a hand-copied list in a test is the same drift one layer down", #1427). The general
statement is CLAUDE.md's "guardrails over discipline".

**Where it is encoded.**
- Guards: `test_docs_version_sync.py` (#336, #789 rule 4), `test_sip_registry_audit.py`
  (#1144), `test_regression_gate_coverage.py` (#1316),
  `test_no_enum_shadow_comparisons.py` (#380), `test_request_fixtures_carry_product_
  content_only.py` (#1427), `test_site_sip_links.py`.
- Workflows: `.github/workflows/release.yml` (#1061), `pr-closure.yml` +
  `scripts/dev/check_pr_closure.sh` (#1113, #1151), `check_release_packages.py` (#1151).
- Procedure: CLAUDE.md "Release cut" — "A step with that record needs removing, not
  restating".

**References.** #336, #335, #789, #1061, #1113, #133, #205, #1144, #1316, #380, #1427.

---

### C2. One seam owns a concern — conform or flag before extending any cross-cutting surface

**Rule.** Before adding content, config or a pattern to any file, find the seam that owns
that concern and use it; if none does, surface the gap and propose it before adding.
"The neighbouring code does it this way" is never justification. Content edits get the
same scrutiny as logic.

**What happened.**
- #218 — the runtime-api surface accreted four URL-prefix conventions, each chosen
  per-SIP in isolation; a doc claimed `/api/v1` was "consistent". #326 then put
  unauthenticated *write* routes on the no-auth `/health` lane.
- #448 — two fixes shipped as inline prompt literals while the fragment system sat
  unused for build handlers.
- #577 — three pool creation sites, none registering a JSONB codec, which is why
  `parse_jsonb()` was scattered across every persistence call site.
- #1171 — five hand-rolled `GenerationRecord` constructions with drifting field sets;
  every framing generation reached LangFuse at zero tokens on both engines while the
  handler 600 lines away populated them.
- #772 — the success-status rule had seven homes.
- #559 / #380 / #377 — task-type strings re-typed at 216 sites; enum-shadow literals;
  Prefect's state vocabulary leaked into domain presentation, with `QUEUED.upper()` a
  latent invalid Prefect state.
- #922 — three meanings of "capability", one of which would have frozen into a
  distribution format once packs published against it.
- #154 — domain modules importing `adapters.*` directly.

**Why it seemed reasonable.** Each addition worked, collided with nothing, and matched
adjacent code. "It doesn't collide" and "it's easy" were the stated justifications.

**How it failed.** Four conventions with no owner; a security hole on the one no-auth
lane; a vendor vocabulary that coincided with the domain's only for the terminal subset;
identity checks (`!= "qa.validate_repair"`) standing in for properties ("steps that emit
product artifacts") so the next such step was silently uncovered.

**How it was detected.** Independent health assessments (2026-06-11, 2026-07-04), the
bespoke-inventions sweep (2026-07-24), measurement over LangFuse (#1171), and — for
#218 — needing a rule while adding a surface and finding there was none.

**What emerged.** A written standard per surface with an enumerating guard: route lanes
(`docs/architecture/api-route-lanes.md`, no v2); task types as `StrEnum` with
"strings at the boundary, constants at the core, properties over identity, tables over
chains"; one pool factory; one record constructor; one status-rule seam; the retired
spellings guard; composition roots declared and two-sided.

**Where it is encoded.**
- Guards: `test_route_lanes.py` (#218), `test_task_type_literals_live_at_the_boundary.py`
  (#559), `test_no_enum_shadow_comparisons.py` (#380, #381),
  `test_run_status_is_the_only_status_vocabulary.py` (#377), `test_one_pool_factory.py`
  (#577), `test_generation_record_construction.py` (#1171),
  `test_retired_capability_spellings.py` (#922), `test_forbidden_imports.py` (#154, D26),
  the #772 structural test.
- Code: `squadops.tasks.task_types.TaskType` and its properties
  (`authors_qa_suite`, `fails_without_correction`, `emits_required_files`);
  `capabilities/success_status.py`; `adapters/persistence/pool.py`;
  `telemetry/models.py::build_generation_record`.
- CLAUDE.md: "Ownership before extension", "Task-type identifiers", "API Conventions".

**Where it does not apply.** An adapter translating an external vocabulary may compare
against that vocabulary's literals, with a justified allowlist entry (#380's boundary
rule).

**References.** #218, #219, #326, #448, #577, #1171, #772, #559, #558, #380, #381, #377,
#922, #154, #301.

---

### C3. Require rather than default at composition seams

**Rule.** Missing configuration is a startup error that names the setting. A seam that
needs a value takes it; it never invents one. Genuine defaults live in the schema where
they are declared and visible.

**What happened.**
- #333 — `entrypoint.py` fabricated an agent identity (`f"{role}-001"`) when
  `SQUADOPS__AGENT__ID` was unset, so a missing id surfaced as "no instance
  configuration for 'lead-001'" — the `_get_default_instances()` masking class the
  repo already had a rule against. #225 records joi running under a wrong id.
- #1157 (SIP-0106 Ruling 3) — the factory defaulted `provider="ollama"`, the agent
  entrypoint never passed one, `LLMConfig` had no field. The vLLM adapter was
  unreachable by any configuration from the day it landed.
- #327 — the prompt-manifest loader warned on hash mismatch and continued; "runtime
  warn-and-continue defeats the point of pinning".
- The 1.7.1 ruling on the same shape at the check seams, after #1253 stripped the
  planner's handoff regexes and exposed that they had been a builder task's only typed
  criteria (#1255): "require, don't default".

**Why it seemed reasonable.** A default keeps the container booting; a warning keeps the
fleet running; a fallback identity keeps the dev loop short.

**How it failed.** Each default converted a configuration error into a later, stranger
symptom, or into no symptom at all.

**How it was detected.** The 2026-07-04 health assessment (#333, #327); the SIP-0106
feasibility work finding an adapter nothing could select (#1157); the 1.7.1 shakeout
(#1255).

**What emerged.** `SQUADOPS__LLM__PROVIDER` required and never defaulted, written by
every deploy surface; agent identity required, with the reason in the code; the loader
hard-fails; reasoning levels have no default — an undeclared capability raises and a
test over the handler registry makes the gap a CI failure (#927); check governance
metadata is required, no-default fields (#730). CLAUDE.md's hard rule: no hardcoded
fallbacks that mask missing config.

**Where it is encoded.**
- Code: `src/squadops/agents/entrypoint.py` (raises on missing id, citing #333);
  `LLMConfig.provider` and `create_llm_provider(provider, …)` with no default;
  `adapters/prompts/filesystem.py` hard-fail; `capabilities/reasoning_policy.py`.
- SIP: SIP-0106 Ruling 3 / §5.
- CLAUDE.md: "No hardcoded fallbacks that mask missing config"; the mirror rule's
  "require, don't default".

**Where it does not apply.** Declared defaults in `config/schema.py` — visible, typed,
and documented as defaults rather than fallbacks.

**References.** #333, #225, #1157, #327, #391 (PR), #927, #730, #1253 (PR), #1255; SIP-0106.

---

### C4. Derive, don't author — a fact the system already holds is not restated by an agent

**Rule.** When the framework can derive a fact (a status, a section list, a check, a
table set, an error-envelope shape), the fact is derived and delivered to the agent that
needs it; the agent is never asked to restate it, and a restatement that reaches the
system is stripped with a named log line.

**What happened.**
- #1067 / #1070 — the success status was authored in the manifest, restated in plan
  prose, and re-authored in handler code while `scaffold_contract` already derived it.
  `cyc_79eebcb82205` was rejected twice for two documents disagreeing about an integer
  neither needed to decide.
- #1252 / #1253 — the planner authored `## .*(Backend|Server|API).*(Run|Start|…)` over
  handoff headings the build profile already checked by name; two of three correction
  rounds were spent on heading word order.
- #1254 — over 40 stored plans: 213 of 213 builder criteria were handoff regexes,
  `harness_boundary` doubled on 25 qa suites, `py_compile` beside the syntax gates. The
  authoring rules list is "a list of past guesses that each cost a roll".
- #911 / #912 / #902 — the error-envelope body shape was shown to no author; the qa
  author invented a field name in consecutive rolls ("the only move available"); a
  shared instruction taught stack #1's Python seam to a Next.js repair.
- #1087 — the frozen store exported a table handle for every declared entity, including
  shapes and projections no correct app writes; the 1.6.4 plan's ruling: "remove the
  ambiguity, do not document it … naming the tables in the brief is the weaker option —
  it leaves the handle present and relies on the author reading, which is the losing
  half of the #911/#912 lesson".
- #1427 / #1430 — the request itself named a framework document (`qa_handoff`) in
  seven places; the framing role faithfully lifted it into `required_artifacts[0]` and
  two stop conditions; the builder spent its emission on a retired file every roll.

**Why it seemed reasonable.** Prose was once the only channel to the implementer (the
Next.js skeleton carried the status only as a TODO inside the fill body), and telling
the author is cheaper than deriving.

**How it failed.** Two authored copies can contradict; an author told to restate will
restate wrongly; a documented handle is still a handle.

**How it was detected.** Framing rejections on identical PRDs, two rounds on heading
order, a 40-plan audit, and a live roll emitting `QA_HANDOFF.md` that would have failed
a case-sensitive basename match.

**What emerged.** The status derived and threaded (#1042, #1063); silence is the safe
default and a contradicting declaration must carry a `decisions[]` entry (#1067);
`sections_present` injected at plan time from the profile, never authored (#1255); the
handoff-regex gate plus dispatch strip with `handoff_regex_stripped` (#1253); root
tables derived by `root_persisted_entities()` (#1087); the planner's lane narrowed to
decomposition, prose intent and `criteria_refs` (#1254); the PRD carries product content
only, guarded (#1430).

**Where it is encoded.**
- Code: `scaffold_contract` derivation; `capabilities/success_status.py` (#772);
  `ImplementationPlan.validate_handoff_criteria`; `task_plan._applicable_acceptance`
  strips; `capabilities/handoff_sections`; `root_persisted_entities`;
  `assembly_notes` document constants.
- Guards: `test_request_fixtures_carry_product_content_only.py` (derived from the
  owning module, never a list); the #772 single-home test.
- Prompt assets: plan-authoring rules (`no-regex-on-the-handoff`,
  `do-not-restate-success-statuses`), rendered from the registry.

**References.** #1067, #1070, #1013, #1042, #1049, #1063, #1252, #1253 (PR), #1254,
#1255, #911, #912, #902, #1087, #1427, #1430 (PR), #772.

---

### C5. Generated artifacts and single-sourced facts have exactly one writer

**Rule.** A generated file is regenerated by its tool, never hand-edited; a
single-sourced fact is read from its source file, never from a copy; a pinned artifact
moves deliberately, once, with the owner's clearance and in its own commit.

**What happened.**
- #451 — `regen_fragment_manifest.py --write` updated stale hashes with an unanchored
  global `raw.replace(stored, computed)`. A placeholder entry with `sha256: '0'` replaced
  every `0` character in the manifest — version, timestamp, every other hash. Recovered
  via `git checkout` and hand-computed hashes using the script's own recipe.
- #1089 — `__version__` read installed metadata, which an editable install writes once.
  On a 1.6.3 tree it returned 1.4.0; `version_cli.py bump 1.6.3` announced "1.4.0 ->
  1.6.3" while correctly editing 1.6.2.
- #336 / #789 — version markers and the CHANGELOG drifted from `pyproject.toml`.
- #327 — a pinned prompt manifest that nothing verified at build time.
- The 1.6.4 cut moved `GENERATOR_VERSION` 7 → 8 and the reference contract v9 → v10
  "deliberately and once (owner-cleared 2026-08-25)"; #1246's plan-context goldens were
  regenerated in a second commit marked "owner approval needed".
- #1131's extraction was proven by every frozen fixture expanding byte-for-byte
  identically (3 manifests, 57 files).

**Why it seemed reasonable.** A global replace on a "globally unique" hash; the
package's own metadata as the version; regenerating a golden in the same commit as the
change that moved it.

**How it failed.** The unique value was not unique; the metadata was a stale copy; a
golden regenerated silently would have hidden a behaviour change.

**How it was detected.** Live corruption while registering a fragment (#451); the bump
tool's own output at the 1.6.3 cut (#1089); the cut-time marker checks.

**What emerged.** Anchored, single-occurrence replacement with an explicit new-entry
flow; the version read from `pyproject.toml` when a source tree is present; a guard that
the markers equal the file; `dist/` and generated metadata read-only; golden moves in
their own commit with the reason classified (`reference_defect`, `ambiguity_removal`).

**Where it is encoded.**
- Scripts: `scripts/dev/regen_fragment_manifest.py` (anchored replace);
  `scripts/maintainer/version_cli.py` (reads the file it edits).
- Guards: `test_version_resolution.py` (#1089), `test_docs_version_sync.py` (#336,
  #789); CI manifest-integrity guard (#327, PR #351).
- CLAUDE.md: "Read-Only Areas" (`dist/`, `manifest.json`, `agent_info.json`; bumps via
  `version_cli.py` only).

**References.** #451, #1089, #336, #789, #327, #1131, #1246 (PR); CHANGELOG 1.6.4
"Pinned fixtures moved, deliberately and once".

---

### C6. "Generic" is stack #1 — a stack-shaped fact lives behind the stack seam, and a check that cannot cover a stack refuses loudly

**Rule.** No live code under `capabilities/handlers/` or `cycles/` names a stack's file
shape or toolchain unless the module is a `stack_*` module or the line is allowlisted
with its reason. A per-stack fact (what invokes the app, the suite suffixes, the client
surface, the error seam) is declared on the `ScaffoldStack` and read through the seam.
A check that does not cover a stack is a declared gap, never a silent skip.

**What happened.**
- #1126 — `detect_self_mocking_tests` defined "invokes the application" as an
  `app/api/` import (the Next.js in-process model) inside a shared module, discarded a
  green FastAPI+React suite in the 1.6.5 set, and *passed* the more self-mocking
  alternative. Origin: commit `1b9b93a9`, written during Next.js work.
- #1131 — the FastAPI+React expander lived inline in `scaffold.py` for six weeks while
  stack #2 had its own module, so a check written on one stack was exercised only
  against that stack. The owner's question on 2026-08-27: "do I have to continually
  remind that we need to stay stack aware?"
- #1216 / #939 / #1229 — `undefined_names` covered `.py` only, so a `.ts` fill's
  undeclared identifier reached test execution and three patches across two rounds did
  not converge; on the other stack the same defect is caught at emission. Runtime-api
  has no node, so a Next.js dev repair could never earn a verdict. "Two stacks, the
  same defect class, opposite outcomes — and the difference was invisible before the
  run."
- #912 / #902 — one prompt asset teaching stack #1's seam to a stack #2 author.

**Why it seemed reasonable.** The first stack *was* the framework; a shared module with
a reasonable regex is the natural home for a check; a Python check that skips a `.ts`
file is doing nothing wrong.

**How it failed.** Every shared surface silently carried stack #1's shape, and the
acceptance layer treated an uncovered stack as a no-op where the two neighbouring layers
(#818, #838) refuse.

**How it was detected.** The 1.6.5 two-stack set's React rejections (`cyc_b9296c255dfc`
roll 1); the 1.7.0 shakeout `cyc_58d92ca2b407`; the 1.7.0 cut record's observation that
three of four rejection causes sat on the JS/TS side.

**What emerged.** `stack_fastapi_react.py` registered exactly as stack #2 is;
`AppInvocation` per stack; one suite-suffix vocabulary; `ScaffoldStack.client_surface_
lines`; per-check `required_tooling` and per-role `DECLARED_TOOLING_GAPS`; a missing
language declarable (#1216); rule B — a repair is verified where its checks can run.

**Where it is encoded.**
- Guard: `tests/unit/architecture/test_stack_shaped_literals_live_behind_the_seam.py`
  (fires on `1b9b93a9`); `test_typed_check_tooling_is_provisioned_where_checks_run.py`.
- Code: `capabilities/stack_fastapi_react.py`, `stack_nextjs_ts.py`, `ScaffoldStack`,
  `app_invocation_for`, `check_stack_for`, `JS_SUITE_SUFFIXES`.
- Plan: 1.7.1 "Stack Seams" (`docs/plans/1-7-1-plan.md`).

**References.** #1126, #1131, #1122, #1216, #939, #1229, #912, #902, #818, #838; 1.7.0
cut record §3.

---

## D. Correction and recovery

### D1. A repair describes the smallest reliable revision; a whole-file rewrite gives every unchanged line a fresh chance to be wrong

**Rule.** The repair brief names the failing cases and says to keep everything else
byte-for-byte; the router construction, decorators and handler names stay as they are;
a revision returns the prior artifact with the reviewer's notes ("revise, don't
re-roll"). The landed mechanism is prompt-side; anchored edits enforced by the framework
are the proposed next step.

**What happened.**
- #1213 — two of six rolls in the 1.6.5 FastAPI+React set died on whole-file rewrites of
  `backend/routes.py`: roll 5's dropped the router and every decorator (refused by
  `unresolved_imports`); roll 6's carried the *correct* fix inside a rewrite that
  switched to a prefixed router, refused by the literal `endpoint_defined` check. The
  React arm ran `3/1/2/1/2/2` correction rounds against Next.js's `0/0/0/0/0/0`.
- #667 — repairs stripped the `data-testid` anchors the first fill placed.
- #1014 — a dev repair stored a rewrite of a qa-owned file.
- #1123 — before it, the qa repair re-authored the whole file with no list (1.6.6 React
  roll 6: two failing cases of four).
- #1289 — and the REPAIR SCOPE block #1123 added never reached a model until 1.7.2.
- #994 — after an accepted repair, the rewind re-dispatched `develop` for the same
  subtask and the model had to out-compete its own accepted fix under a shrinking clock;
  the cycle held a working deliverable at 01:38 and spent an hour destroying its claim
  to it.
- #669 — framing re-rolls re-diced instead of revising (the "fay-6 new-dice lesson").
- #451 — the same shape in a maintainer script: an unanchored global replace.

**Why it seemed reasonable.** Re-emitting a file is the simplest output contract for a
model, and the frozen-file restore (SIP-0100) already contains the damage a rewrite can
do outside its slot.

**How it failed.** Inside the slot nothing contained it: the fix was right and the file
was wrong around it, and a wasted round is the scarce resource
(`max_correction_attempts: 3`).

**How it was detected.** The 1.6.5 record's per-roll round counts and stored patches;
#994 in the V7 window (roll 1 void); #1289 by measuring the render variables and the
stored prompt.

**What emerged.** The repair brief v6 (#1129: keep the router construction, decorators
and handler names — "a rewrite is refused before it is tested"); the REPAIR SCOPE block
with the runner's failing cases (#1123), rendered (#1289); anchors re-derived at
repair-input construction (#667); the emission-side ownership veto (#1014); a rewind
that keeps the accepted repair (#994); `framing_max_rerolls` as a revision budget
(#669). The framework-enforced form — the agent describes the revision, the framework
resolves it inside the producer's `WriteGrant`, preserves the rest byte-for-byte and
binds verification to one candidate revision identity — is the Scoped Code Revision
proposal (PR #1325, `sips/proposed/SIP-Scoped-Code-Revision.md`), which subsumes #1213.

**Where it is encoded.**
- Prompt assets: the repair brief and REPAIR SCOPE appendix; `already_supplied_lines`.
- Code: `_build_render_variables` (post-#1289); the rewind path (#994); SIP-0100
  frozen restore and `WriteGrant` in `cycles/write_authorization.py`.
- SIP: proposed — PR #1325 (design review is the 1.8 plan's opening step per the 1.7.5
  plan §1).

**References.** #1213, #1129, #667, #1014, #870, #1123, #1289, #994, #669, #451, #1325
(PR); `docs/plans/1-6-6-plan.md` ("#1129 is why a repairable defect ended two rolls").

---

### D2. A wasted round is not a round — the budget counts applied repairs, and a one-dispatch marker is one dispatch

**Rule.** An emission containing nothing is not an attempt; a refused patch is not a
correction round; a rewind after an accepted repair keeps the repair; a per-dispatch
marker is cleared at the attempt stamp. A retry of a contentless emission carries the
emission-shape fact.

**What happened.**
- #1053 — arm B spent two of three rounds on zero-byte `repair_output.md` files while
  holding a correct, stable diagnosis across all three rounds. `Max correction attempts
  (3) exhausted` read as "tried three times and could not converge" when it tried once.
- #1129 — a refused patch applied nothing and ran no retest, `qa.test` re-ran against
  the unrepaired tree, the signature repeated by construction, and the progress-aware
  terminal read "the repair did not help". Two rolls ended `plan_defect` after zero
  applied repairs, one holding the correct fix.
- #1347 — `emission_retry_feedback` was set on a RETRYABLE failure and never cleared;
  every later dispatch of the envelope read as an emission retry. The absent-suite fault
  re-applied to all three correction re-dispatches (`qa_suite_absent` APPLIED five times
  to one task) and the diagnostic's red was manufactured.
- #1273 — a prose-only repair was re-briefed from the empty emission with prose counted
  as content.
- #1372 — the retry re-rolled the same prompt blind; the builder had no retry path at all.

**Why it seemed reasonable.** Counting dispatches is the simplest budget; a marker set
once on an envelope is the simplest way to aim the next dispatch; "signature repeated"
is a sound terminal when a repair was applied.

**How it failed.** The budget was spent on non-events, and the terminal that protects
the budget could not tell "did not help" from "was never applied".

**How it was detected.** The vault (0-byte artifacts, #1053); the 1.6.5 record's rolls 5
and 6; the 1.7.3 instrument round's diagnostic (#1347).

**What emerged.** The refund with a bounded cap (#1053, #1273 — "the termination says
which absence"); a refused round clears chain adjacency the way an infra round does,
with one marker shared by the executor and the runner (#1129); the marker dropped at
the attempt stamp with a wiring test entered at `execute_run` (#1347); the retry with
its fact — chars, fences, the model's opening words — one path for every handler
(#1372); progress-aware termination (#435).

**Where it is encoded.**
- Code: `adapters/cycles/correction_runner.py` (refund, refused-round marker,
  progress-aware terminal); `dispatched_flow_executor._handle_task_outcome` (marker
  lifecycle, #1347); `handlers/cycle/base.py` emission seam (#1372).
- Instrument: `refunded_rounds`, `refused_rounds_not_counted`, `retried_with_fact` /
  `retried_blind` in the driver's texture (#1362 — L4 reads the refund, not the #1129
  exclusion).

**References.** #1053, #1129, #1347, #1273, #1372, #435, #998, #1362 (PR).

---

### D3. Table every seam that evaluates a task's criteria and the tree each one sees — a file the patch never carries is not evidence against the patch

**Rule.** Before binding a typed check onto a task's artifacts, table the seams that will
evaluate that task's criteria — emission (the role's container), agent-side repair
(the *repairing* role's container), the verifier (runtime-api), the file-owned gate, the
retest — and the tree each sees, and state the outcome on a tree that lacks the file. A
repair is verified where its checks can run, on the tree the verifier overlays, under
the repairing producer's grants.

**What happened.**
- #1229 — runtime-api has no node, so a Next.js dev repair could never earn a verdict;
  `cyc_05abfc7c1f00` spent three rounds on one route producing identical `unverifiable`
  verdicts (#1221 broke the deadlock; it did not make the verdict obtainable).
- #1240 / #1246 bound executing checks (`assertion_kinds_match`, `dom_anchor_queries`)
  onto qa suites. #1259 — a dev repair of a qa failure evaluated those checks on its own
  tree, which lacks the suite; `file_not_found` counted as an *executed failure* in both
  environments; a correct route fix was refused, the re-authored suite dropped the case
  that found the defect, and the cycle was accepted 17/17 shipping an app that drops a
  numeric `capacity`.
- #1264 — the repair evaluated the failed task's criteria on a tree without the failed
  emission; six rows were executed failures about a file the patch never touched.
- #1406 — a qa repair's verification re-asked the dev's three view-compile criteria at
  runtime-api, where npm is absent; the `missing_tooling` skip outranked the earlier
  executed-and-passed row, and three genuinely verified criteria left the credited set
  on an accepted, booting delivery.
- #1350 — #1323's patch-verification grants were derived from the *failed* task's
  envelope, so a dev repair of a dev-owned slot was refused as a QA write.

**Why it seemed reasonable.** One verifier, one environment, one set of grants is the
simplest design; a check bound to a file is naturally evaluated wherever the file's task
is judged; "an executed failure anywhere rejects" is the safe rule.

**How it failed.** The rule was applied to trees the check's subject was never in, by
producers who were not the one whose grants were checked, in environments without the
tool.

**How it was detected.** Shakeouts on the final 1.7.1 deploy (`cyc_9c379355b5e8`,
`cyc_4ec4ad5e2ca1`), the 1.7.4 checkpoint roll (`cyc_dd3068d22f2c`), the 1.7.3
own-frame diagnostic (`cyc_375bdea6e140`).

**What emerged.** Rule B (owner's ruling 2026-09-01): typed checks execute in the
producing role's container at emission and at repair; the rows ride the patch with
`executed_in`; runtime-api consumes them and cross-checks what it can. `file_not_found`
on a file the patch does not carry is `skipped / file_not_in_patch` in both
environments; on a file the patch *names* it keeps its rejection power. The repair
envelope carries `failed_task_artifacts` and materialises them beneath the accepted
workspace. Grants are the repairing step's. The seam table is a PR-template field.

**Where it is encoded.**
- CLAUDE.md: "Typed checks (adding or binding one)".
- PR template: "Evaluated at: emission <tree> · agent repair <tree> · verifier <tree>
  · gate · retest".
- Code: `_evaluate_typed_acceptance` in the agent; `cycles/patch_verification.py`
  (`REASON_FILE_NOT_IN_PATCH`, `executed_in`); `CorrectionProtocolResult.repair_typed_
  checks`; `DECLARED_TOOLING_GAPS`; `CheckSpec.required_tooling`.
- Guard: `test_typed_check_tooling_is_provisioned_where_checks_run.py`.
- Plan: `docs/plans/1-7-1-plan.md` (rule B); 1.7.5 plan §3.2 (#1406's framework half).

**References.** #1229, #1221, #1238, #1250 (PR), #1256, #1259, #1264, #1240 (PR),
#1246 (PR), #1406, #1407 (PR), #1323, #1350.

---

### D4. Framework rows are owed by contract, not by the failed attempt's history

**Rule.** The accepted-patch path derives every framework row the task's contract
declares from the patched set, through the same rule the producing handler uses, and
supersedes the failed attempt's rows — regardless of what the failed attempt carried.
An accepted patch's task is re-evaluated; it is never rejected on pre-patch rows.

**What happened.**
- #1318 (1.7.2 counted roll 1, void) — the builder's failed attempt carried a failing
  `required_files` row; the patch supplied the file; nothing re-emitted the row; a
  booting app was rejected on rows evaluated against the pre-patch workspace while the
  passing patch sat in the vault.
- #1364 (1.7.3 counted roll 1, void) — the builder's failed attempt was contentless and
  carried *no* row, so #1318's gate ("re-derive when the failed attempt carried it") did
  not fire; the required check had no executed row anywhere; a booting app was
  `blocked_unverified`.
- #1374 — two lines, two void counted rolls, one mechanism, patched gate by gate.

**Why it seemed reasonable.** "Never invent evidence for a task that never carried the
check" is the right rule for a task type that has no such check, and #1318 wrote it.

**How it failed.** The rule keyed on the attempt's history rather than the task's
contract, so the next shape — an attempt that never got far enough to write the row —
was uncovered.

**How it was detected.** Two counted rolls voided at the roll boundary, with the
delivered app passing its boot audit both times.

**What emerged.** Rows derived by contract (`TaskType.emits_required_files`), the
seam table applied to the re-store, and the roll-up's own premise (SIP-0096: a required
check is verified only by an executed-and-passed row) applied at the one seam that
composes a result from two attempts.

**Where it is encoded.**
- Code: `_try_accept_patch` (accepted-patch derivation); `TaskType` properties;
  `required_files_row`.
- SIP: SIP-0096 §6.2.
- Instrument: `framework_rows_rederived` in the driver's texture.

**References.** #1318, #1364, #1374, #1021, #291.

---

### D5. The repair targets the cause; routing runs on machine signals, and the failed task's own artifacts never narrow the target

**Rule.** Locus classification produces `OWN_ARTIFACT` only on explicit machine signals
(a stamped own-frame failure, a contradicted declared kind, an undeclared anchor), so a
qa repair can never "fix" an app defect by rewriting the tests. A failed task's own
artifacts ride the target and never narrow it. Type-keyed behaviour consults a property
on `TaskType`, never an identity check.

**What happened.**
- #1054 — the lead named dev task types; all three repairs dispatched to `qa.test_repair`;
  the suite was rewritten three times and the correctly diagnosed shadow store survived
  the entire correction arc. Arm B on the identical deploy repaired the app at round 0.
  The mechanism was the one `_resolve_repair_target`'s own docstring (#531) describes.
- #1120 — the analyzer honestly implicated the failed qa task's own suite; the narrowing
  treated it as a defect site and withheld the language-wide surface; the #884 veto then
  removed the qa file from the dev target; the target was empty and every round refunded
  until the cap terminated the run red. A 1.6.4 regression on the first stack #1 cycle
  since it shipped.
- #968 — three false analyzer claims in one roll, inherited verbatim; the subject
  oscillated app → tests → app on identical evidence.
- #1130 / #1123 / #1153 — a free-authored suite asserting something the contract never
  said rejected correct repairs with no route to the qa file.

**Why it seemed reasonable.** The failing check (`tests_pass`) belongs to the qa task, so
anchoring the repair there is the default; an analyzer's implicated file is the best
available pointer; conservative routing that refuses to touch tests is the safer error.

**How it failed.** Symptom-owner routing regenerates the symptom; an honest own-artifact
diagnosis became a narrowing site; a classifier with no machine signal fell back to
whichever chain it was built to prefer.

**How it was detected.** The 2026-08-23 paired validation (arm A vs arm B), the 1.6.5
stack #1 shakeout log (`cyc_3cde35fa5204`, twice in a row), the SIP-0104 P6 window
roll 6.

**What emerged.** Per-runner own-frame detection stamped by the stack (#1130, #1270);
the kind gate and the anchor rule as declaration-owned own-artifact signals (#1153,
#1240, #1246); own artifacts excluded from `analysis_files` (#1120); the analyzer's
claims verified against the workspace and the refutation handed to the decision
(#968); the locus classifier answering by task-type property (#1054, 1.7.4).

**Where it is encoded.**
- Code: `adapters/cycles/correction_runner.py` (`_resolve_repair_target`, the #884 veto,
  `_verified_implicated_files`); `capabilities/handlers/stub_detection.py`;
  `failed_tests_pass_row` stamping; `TaskType` properties.
- Guard: `test_task_type_literals_live_at_the_boundary.py` ("properties over identity").
- Records: `qa_owned_routed`, `absent_anchor_routed` log tokens read by the driver.

**References.** #1054, #531, #532, #688, #884, #1120, #1100, #968, #1130, #1123, #1153,
#1270, #559.

---

### D6. A gate whose premise has gone stale, or that is rubber-stamped, is retired — and it says so

**Rule.** A gate carries its premise in its rejection text; when a later change makes the
premise false, the gate is downgraded or retired rather than left dormant. A review gate
that stops for every design and is approved by reflex is replaced by a gate that stops
only when the design asks a question, with the machine pass-through recorded distinctly
from a human approval.

**What happened.**
- #1049 — `framing_consistency` rejected a plan for omitting a status restatement,
  stating "the implementer will default to 200". #1042 had made that false by deriving
  the status into the dev brief. Five byte-identical rejections across three cycles; two
  re-rolls consumed; a correct framing dead-ended. The gate's own comment recorded the
  now-stale reasoning.
- SIP-0103 §5d B1 (#807) — V4 roll 2's manifest went through `progress_plan_review`; a
  human approved it with a note about facts the deterministic gates had already proven,
  while the manifest carried one genuinely unresolved question (`expansion-gating`) and
  nothing surfaced it. "A gate that is rubber-stamped manufactures the appearance of
  review." §5d C then records that B1's justification was "half-funded when the
  control was removed" — two of the four diagnostics it cited were not yet built — and
  closes it the same day (`43754d6d`).
- #812 — `decided_by` was a hardcoded `"system"`, so all 140 human approvals in the
  project's history carried the word that means *no human was involved*.

**Why it seemed reasonable.** A gate that once prevented a real loss keeps looking
protective; a mandatory human review is the conservative default.

**How it failed.** The gate taxed every cycle for a harm that could no longer occur; the
review produced approvals a later reader could not distinguish from reflex.

**How it was detected.** Rejection tables across cycles (#1049); reading the V4 approval
note against the manifest's `unresolved` decision (§5d).

**What emerged.** #1049's downgrade (fires only where neither the skeleton nor the brief
carries the fact) and #1070's retirement of the completeness half; the question-gated
manifest review with `GATE_DECIDED_BY_NO_QUESTIONS = "system:no_open_questions"` kept
distinct on purpose; `decided_by` composed from the request identity, with `--as-agent`
for an agent that must declare itself.

**Where it is encoded.**
- Code: `cycles/manifest_authoring.py::open_questions`; the executor's gate branch;
  `framing_consistency.py` (conditional).
- SIP: SIP-0103 §5d B1 and C.
- Records: every set record names the decider per roll.

**References.** #1049, #1042, #1070, #807 (PR #808), #812, #802 (PR); SIP-0103 §5d.

---

## E. Measurement, CI and deployment

### E1. Pre-register, freeze, count from main, and say what the evidence does not cover

**Rule.** A measurement's parameters, predictions, readouts, gate constant and
prohibitions are fixed before roll 1 by the commit hash of the document; the deploy is
frozen and asserted by image id; counted rolls launch from `main`; a reading corrected
after the run is not a prediction; the cut record names every prediction no roll
exercised, every readout that was vacuous, and every difference between the tagged tree
and the validated deploy.

**What happened.**
- 1.6.3 was "the first time, a rate" — 1.6.2 had merged roughly twenty fixes and none
  had been measured. The set was pre-registered and unchanged throughout, and its
  interval was pre-registered as wide.
- 1.6.2's cut evidence ran on `98eb805e`; three changes merged after launch rode the tag
  untested, two of them authoring-facing. Stated in the CHANGELOG rather than implied.
- 1.7.4 skipped its step 10 (re-running the diagnostics on the pinned deploy) on the
  owner's ruling, and the record §4 names exactly which invariants rest on earlier
  deploys.
- 1.4.0's claim was narrowed at the cut: "a specified contract, not PRD-to-app" —
  seeded-manifest mode, with squad-authored mode moved to 1.6 as a headline.
- #1438 — the driver imports `squadops` modules to compute P0 and B1, resolving against
  its own tree; `frozen_deploy_commit` had been typed and read by nothing, so a
  framework change after the deploy would have had the instrument judge a roll against
  logic the system never ran.
- #1296 / #1297 — the record's deploy field was operator-typed and its fallback to the
  observed identity was dead code; a shakeout rendered `deploy ?`.
- #1004 / #1005 — an instrument defect on the V7 deciding roll; the disposition
  (score-as-measured, reset, or a labelled corrected-instrument re-measure) was the
  owner's ruling and both readings are always reported (3/6 pre-registered instrument,
  4/6 corrected).
- 1.7.4 pre-registration §3a — three expected readings were written against a tree that
  no longer existed; the flips were recorded *before* the diagnostics ran, because "a
  reading corrected after the run is not a prediction".
- 1.7.1 record §3.3 — React roll 5 was launched before roll 4's rounds had been read;
  the early stop should have fired. Recorded as a deviation; the chain's boundary
  release became a two-step (read, then release).

**Why it seemed reasonable.** A green roll on a recent deploy is persuasive; merging
"one more fix" before the cut is cheap; the driver's tree and the deploy's tree are
usually the same.

**How it failed.** Without a pin, a boundary moves without anyone deciding it should;
without disclosure, a tag inherits a validation it did not receive; without the
prediction fixed first, the readout is a story about the data.

**How it was detected.** At the cuts, by asking what the roll actually ran on; by the
owner's question about whether the deploy commit and the instrument commit may diverge
(#1438); by reading a shakeout record with `?` in it.

**What emerged.** The pre-registration as a document with a commit hash, the set config
as its §1 table in data, preflight refusing a dirty tree or a moved image id or HEAD,
counted rolls refused when `src/` or `adapters/` differ between the pinned deploy and
the driver's HEAD (#1438), the record naming the deploy it observed (#1297), the cut
record's "what the evidence does not cover" section, and the release-cut rule that
nothing else merges between opening the release PR and merging it (1.6.2).

**Where it is encoded.**
- Procedure: `docs/plans/verification-sets/README.md` ("What a set is", "What the record
  must say"); CLAUDE.md "Release cut" ("Say what the cut evidence does NOT cover",
  "Nothing else merges…").
- Instrument: `verification_set_driver.py` `preflight` (`--counting`), `.head_pin`,
  `frozen_image_ids`, `FRAMEWORK DRIFT` check (#1438), `rec["deploy"]` (#1297).
- Records: `docs/plans/*-cut-record.md`, `*-verification-set-record.md`.

**Where it does not apply.** Shakeouts run on a deploy unpinned by definition and
record its identity rather than asserting it; driver-only and docs-only changes do not
supersede a deploy.

**References.** #1438 (PR), #1296, #1297 (PR), #1004, #1005 (PR); CHANGELOG 1.6.2 "Not
exercised by the cut evidence, stated plainly", 1.6.3, 1.7.4; 1.7.4 pre-registration §3a;
1.7.1 record §3.3.

---

### E2. The shakeout is a loop with an exit rule; unexercised is not passed; a diagnostic runs the roll's own path

**Rule.** One shakeout per stack per deploy; a deploy on which either shakeout produced a
fix is superseded; the exit is a pair on one deploy with no new seam finding, stated
before the first launch with a budget; the cut record reports how many pairs it took. A
prediction no roll is likely to exercise gets a fault-injected diagnostic on the roll's
own path, non-counting by construction, read by the seam it reached.

**What happened.**
- 1.7.1 ran six shakeout deploys before the counted set; four of them each found the
  next seam defect (#1250, #1252, #1255/#1256, #1259/#1261), three latent in the pack's
  own PRs.
- 1.7.2's loop ran five rounds against a budget of three, all twelve findings in the
  instrument, none in the pack — reported as two numbers.
- #1251 — "three lines of plan text, never filed": three plans carried a fault-injection
  arm as an owner's decision; the 1.7.1 diagnostics became in-container replays instead;
  the Next.js shakeout found rule B's live gap only because a real emission happened to
  fail its build.
- #1310 — `qa_suite_absent` exercised the emission-retry path, not the repair-retest path
  it was registered against; the fault applies to every emission attempt so the loop
  reaches correction.
- #1352 — the Python own-frame fault was a `NameError` that `undefined_names` refused at
  emission; L7 had never been exercised on a pytest suite, invisibly, because the record
  read "the fault fired".
- #1300 — a fault that cannot bite logged APPLIED.
- 1.6.4 and 1.6.5 records: "P1, P3 and P5 were not exercised — the loss modes they were
  built against did not occur — and unexercised is not passed"; "Q1/Q2/Q4 … were not
  exercised, which is not passed".

**Why it seemed reasonable.** One shakeout pair before the counted set is the natural
plan; a green prediction on a green roll reads as held; a replay of the seam's function
with the fault's input is quicker than a hook in the deployed handlers.

**How it failed.** Each pair found the next defect; each replay proved the function and
not the path; each un-reached prediction was reported as if it had held.

**How it was detected.** By running the loop and counting; by the fault hook's own first
live run (#1300, "which is exactly what it was built to do").

**What emerged.** The loop and its exit rule in the procedure; `execution_overrides.
fault_injection` with a `FAULTS` registry naming the roll each fault came from and the
prediction it exercises; refusal at cycle create for an unknown or unwired fault;
`preflight --counting` refusing a set that declares one; `seam_reached` read per
diagnostic (#1310); a first-attempt-only fault read off the inputs.

**Where it is encoded.**
- Procedure: `docs/plans/verification-sets/README.md` ("The shakeout loop and its exit
  rule", "What a diagnostic is"); CLAUDE.md "The shakeout is a loop with an exit rule".
- Code: `squadops.capabilities.handlers.fault_injection.FAULTS`; cycle-create refusal.
- Instrument: `declared_fault_names`, `seam_reached`, the DIAGNOSTIC preflight log.

**References.** #1251, #1300, #1310, #1352, #1362 (PR), #1250, #1252, #1255, #1256,
#1259, #1261; CHANGELOG 1.7.1, 1.7.2; 1.6.4 and 1.6.5 records.

---

### E3. CI tests what ships: locks compiled against the constraints, every divergence documented, a bare install proven

**Rule.** The deployed dependency set is a subset of the tested set by construction; a
divergence that genuinely cannot follow CI is listed with its reason and fails when it
goes stale; `[project.dependencies]` mirrors the imports in both directions; a fresh-venv
install job proves the package installs and imports from its own metadata.

**What happened.**
- #1041 / #1203 — CI installed `tests/requirements.txt -c ci-constraints.txt`; the images
  installed `requirements/*.lock`, resolved independently. 42 packages disagreed — numpy
  1.26 vs 2.4, lancedb 0.8 vs 0.33, pyarrow 15 vs 24 — while the same `src/squadops/`
  ran under both; verified in the running agent container, not read off the files. The
  regression gate exercised a version set no image installed. Found on the way:
  `pip-compile` keeps an existing pin as a preference, so two locks carried different
  `langfuse` versions.
- #198 — `fastapi>=0.104.0` unbounded in the test requirements; CI drifted to 0.138,
  Starlette's router double-include check fired, 26 console tests failed; green locally,
  red in CI.
- #237 — production on 3.11, CI on 3.12, the locks compiled on 3.11 — "half of what
  #1041 was".
- #582 — `[project.dependencies]` was empty; `pip install squadops` raised
  `ModuleNotFoundError: pydantic` at first import; dependabot and pip-audit saw an empty
  tree; a wheel shipped none of its data files.

**Why it seemed reasonable.** Separate files for separate purposes — a reproducibility
lock for tests and narrower deployment pins per surface — is a sound split; the
requirements files were the truth and everything installed editable.

**How it failed.** "Nothing has broken because of this yet" (#1041) — the failure mode is
a library behaviour change CI cannot see, surfacing in a live cycle as a squad defect
the locus classifier cannot distinguish from one.

**How it was detected.** Diffing the lock files against the constraints; running the
comparison in the container; a fresh venv.

**What emerged.** `update_deps.sh` compiles the locks *with* `-c ci-constraints.txt`
(fixed by construction, not detection); `requirements/constraint-exceptions.txt` with a
reason per line; a drift test about documentation rather than a frozen count (an
undocumented divergence fails, a stale exception fails, an exception without a comment
fails); dependencies mirrored two-sided; the `fresh-venv install` job; Python 3.12
everywhere.

**Where it is encoded.**
- Guards: `test_dependency_drift.py` (#1041), `test_project_dependencies_mirror_imports.py`
  (#582).
- Scripts: `scripts/maintainer/update_deps.sh`; `requirements/constraint-exceptions.txt`.
- CI: `.github/workflows/ci.yml` fresh-venv install job; `deps-refresh.yml`.
- CLAUDE.md: "Python Requirement: 3.12 everywhere".

**References.** #1041, #1203 (PR), #198, #237, #217, #582, #637, #1204.

---

### E4. The box is a shared, finite instrument: one engine resident, host timers guarded, launches detached, cancellation through the CLI

**Rule.** Two model servers never coexist in the Spark's unified memory; a host reclaim
script never carries `-a` or `volume prune`; a driver launch outlives the session; a run
is cancelled through the CLI, never by hand in the database; a cycle's leases are
released on every cancellation path.

**What happened.**
- #1177 — Atlas idle at 90% GPU memory; a replay script called Ollama directly; Ollama
  measured the collision ("need to reduce device memory by 28802 MiB"), reported it, and
  loaded anyway. 95 minutes of swap thrash, `sshd` unable to fault its own pages in,
  ended by a power cycle. #1178 — no `systemd-oomd`, no `earlyoom`, no `MemoryMax`; the
  kernel OOM killer does not fire during thrash.
- #1465 — five months of deploys took the box to 65% of an 870G root: 1,795 dangling
  images, 164.7 GB of build cache. The pruning order is load-bearing (dangling images
  hold cache references; `docker image prune` alone reported 0 B reclaimed), and one
  flag away from the legitimate command is `docker system prune -a` (evicts every
  tagged image — the agents, runtime-api, the pinned sandbox env) or `volume prune`
  (the Postgres volume, on a box whose backups were installed the same day).
- #529 — cancelling a cycle or run left its focus leases held; the next cycle deadlocked
  on `focus_lease_conflict`; cleared by hand in `focus_leases`.
- `docs/plans/verification-sets/README.md` — a driver started as a session's background
  task was stopped from outside the session three times in one day; the cycle kept
  running and its gate went unwatched. A rebuild over a running cycle leaves its run
  `running` and every later preflight refuses.

**Why it seemed reasonable.** Each script did the one thing asked; the replay was a
control arm; the reclaim command is what the docs suggest; a background task is the
obvious way to launch.

**How it failed.** The host had no containment, the reclaim's dangerous variant is a
diff a reviewer would approve, and a session's lifetime is not a cycle's.

**How it was detected.** `sar` logs dating the cliff to the minute (#1177); `docker
system df` (#1465); the next cycle's pause (#529); the unwatched gate (README).

**What emerged.** `arm.sh` exclusivity honoured by every path; a weekly host timer on
the backup timer's pattern with a guard that reads what the script may remove and that
the unit template renders; lease release on every cancel path with an owner check
(#529, #712); the detached-launch recipe and the re-attach procedure; cancellation
through `squadops runs cancel`.

**Where it is encoded.**
- Guard: `tests/unit/architecture/test_host_timers_are_safe_and_renderable.py` (#1465).
- Procedure: `docs/plans/verification-sets/README.md` "Running it".
- Code: cancel routes, executor finalize and startup sweep releasing leases (#373,
  #529, #710, #712).

**References.** #1177, #1178, #1465, #529, #373, #710, #712.

---

## F. Rationale, amendments and corrections

### F1. Preserve the rationale: amend the SIP in the diverging PR, harvest before a move, state what a removal produced and for whom

**Rule.** When implementation contradicts or narrows an accepted SIP, the amendment goes
into the SIP as a new numbered section in the PR that diverges — never only in a release
plan, a code comment, or a closed issue's comments. A disposition deliberately not built
is an amendment too. Before extracting or moving a module, the load-bearing comment
rationale is harvested into a durable home and cited in the PR. Before removing
anything, say what evidence it produced and who consumed it. `updated_at` is never
hand-edited.

**What happened.**
- SIP-0103 §5d (2026-08-09) — three falsified premises and four unimplemented
  dispositions had been recorded only in `docs/plans/1-6-0-authorship-plan.md`, a
  document superseded at the cut, after which the SIP would have been the sole
  surviving description of a design it no longer matched. §5a's foundation inventory had
  claimed an authored manifest "propagates … with zero new plumbing"; authored mode was
  dead on arrival (#796).
- #1253 → #1255 — stripping the planner's handoff regexes was correct, and it exposed
  that they had been the builder task's only typed criteria; the verifier had been living
  on them, and the next builder repair was discarded unheard. The removal was right; what
  the removed thing had been producing was unknown.
- #1149 — the load-bearing rationale lived in comments (`model_registry.py:41-52`
  explains a magic number by a throughput measurement; `task_plan.py:243-249` explains
  routing by the false green it prevents), and 1.7 was about to extract exactly those
  files. 23 entries were harvested into SIP-0105 before #1131 moved the expander.
- #1229 — "a deferral recorded only in a closed issue's comments is a deferral that
  disappears"; option C was split into its own issue for that reason.
- #1251 — "three lines of plan text, never filed".
- #406 — the warmboot era's sixteen retros were distilled into
  `docs/book/WARMBOOT_ERA_LESSONS.md` before the operational leftovers were retired.
- SIP-0106 §1.2e/§1.2f (2026-08-30, 2026-09-08) — a parked arm and an unbuilt
  bootstrap recorded as amendments, because "silence reads as shipped".

**Why it seemed reasonable.** The plan is where the work is happening; the comment is
next to the code it explains; a deferral in a closed issue is written down.

**How it failed.** Plans are superseded at the cut; comments do not survive an
extraction unless the refactorer reads them; closed issues are not read.

**How it was detected.** Writing §5d and finding what had already been lost; the
builder repair discarded on the shakeout after #1253; the 1.7 plan's own sequencing
looking at the files it would move.

**What emerged.** Contributor workflow step 5a; the mirror rule on removal; the harvest
as a precondition of the Stack Seams pack and a PR-template line; the rule that an
issue, not plan text, carries a deferral; `update_sip_status.py` as the only writer of
`updated_at`.

**Where it is encoded.**
- CLAUDE.md: "5a. Amend" and the amendment rules; "The mirror rule on removal".
- PR template: "Removed: <thing> — produced <evidence> for <consumer>; replaced by
  <what>"; "Rationale: SIP-NNNN harvest entries N–M".
- SIPs: SIP-0103 §5d; SIP-0105 harvest; SIP-0106 §1.2a–§1.2f.
- Script: `scripts/maintainer/update_sip_status.py`; guard
  `test_sip_registry_audit.py`.

**References.** SIP-0103 §5d, #796, #1253 (PR), #1255, #1149, #1131, #1229, #1251,
#406 (PR), SIP-0106.

---

### F2. When the record is wrong, correct it in place, dated, beside the wrong reading

**Rule.** A corrected reading is written into the record that carried the wrong one,
with the date, the evidence, and how the error was made; the CHANGELOG, release package
and Release carry it; an issue whose premise was wrong is rewritten before it is built;
a fix that is falsified is reverted and the reversal recorded.

**What happened.**
- 1.6.3 record §6 — the cut-time reading ("two false rejections") was corrected the same
  day from the banked reports; the section says how the error was made (inferring from
  a boot audit that cannot see bodies). The 1.6.3 CHANGELOG section, release package and
  GitHub Release carry the correction.
- #691 — the original filing blamed an unauthorized dev write; provenance showed the
  artifacts were scaffold-seeded and hash-identical to the contract's frozen entries.
  "Rewritten 2026-08-03 … the real defect is larger than the one filed." Built after the
  rewrite (1.4.2: "Corrected premise, recorded").
- #1436 — #1431's first fix reverted within the hour; the readout now reports the
  artifacts it counts and says so.
- SIP-0106 §1.2f — first written as "a defect in the vendor's engine"; corrected the
  same day into what is established, what is observed but not established, and the two
  open confounds, with the original sentence quoted in the correction note.
- SIP-0103 §5b/§5d — "§5b Correction 1 is wrong in both halves", measured and stated.

**Why it seemed reasonable.** Silently editing the wrong sentence produces a cleaner
document.

**How it failed.** It does not arise here — the record shows the corrections made in
the open. The failure it prevents is the one SIP-0103 §5d names: a reader who cannot
tell a considered reading from a revised one.

**What emerged.** Corrections as dated sections; dual records where the instrument
changed (V7's 3/6 and 4/6 "both always reported"); the release surfaces updated with the
record.

**Where it is encoded.** The records and SIPs above; `build_release_package.py`
carrying the corrected section; the CHANGELOG entries.

**References.** 1.6.3 record §6, #1095 (PR), #691, #1436, SIP-0106 §1.2f, SIP-0103 §5d
A1, #1004/#1005.

---

## G. Release

### G1. The release cut is a guarded procedure — every step that has been missed is enforced, the package is previewed before it is written, and nothing merges in the window

**Rule.** Bump only via `version_cli.py`; markers, CHANGELOG rotation and the dated
section are guarded; the Release publishes itself from the tag; the SIP sweep is a
required line in the release PR; the release package is captured after the tag, previewed
without `--write` and read before it is written; every semver tag has a non-hollow
package; nothing else merges between opening the release PR and merging it.

**What happened.**
- #789 — five consecutive releases (v1.4.0–v1.5.0) tagged and never advertised; the
  CHANGELOG last rotated at 1.3.1, its `[Unreleased]` asserting things false since the
  1.4.0 cut. The 1.1.1 lesson recurring in a new form.
- #1061 — the Release step, written into the checklist on 10 Aug, missed at both
  subsequent cuts.
- #1076 — `build_release_package.py` printed `1 cycles` and wrote a roll-up of nulls:
  wrong route, no auth header, wrong field name, and a guard that caught only
  `JSONDecodeError`, so `{"detail": "Not Found"}` took the success path. "A hollow
  capture is worse than none: it looks like the evidence was taken, and the deploy it
  came from is gone by the time anyone looks."
- 1.6.2 — two PRs merged between opening the release PR and merging it; the CHANGELOG
  said they were excluded; the record was wrong until the branch was rebased.
- #1113 — six 1.6.4 fix PRs without `Closes` lines; five issues open at the cut, visible
  only in the package's Closes column.
- `test_site_sip_links.py` — a SIP renamed at promotion left a frozen release package
  linking the old name; `mkdocs build --strict` failed for five consecutive merges and
  v1.7.0 never reached the site.
- #1089 — the bump tool announcing the wrong "from" version.

**Why it seemed reasonable.** Pushing a tag reads as completion; a checklist held by a
careful person is usually enough; valid JSON is valid JSON.

**How it failed.** Every unguarded step was eventually missed by someone holding the
checklist, and the one instrument that would have shown the miss (the package) was
itself hollow.

**How it was detected.** `gh release list` at a later cut (#789); the site build
(#1061's header showing v1.5.0 for two releases); reading the preview (#1076).

**What emerged.** The seven-step procedure in CLAUDE.md with the guard named per step
and the unguarded step (ROADMAP entry) called out as such; `release.yml` on tag push;
`check_release_packages.py` on every push (main goes red the moment a tag is pushed
without its package); the `SIP sweep:` line enforced by `check_pr_closure.sh`; the
package gated on the roll-up actually being present, with absence recorded and its
reason; the site-link guard that drops a dangling link and keeps the text rather than
repointing it at a successor.

**Where it is encoded.**
- CLAUDE.md: "Release cut" (steps 1–7 with their guards and the reasons).
- Workflows: `.github/workflows/release.yml` (#1061), `pr-closure.yml` (#1113, #1151).
- Scripts: `scripts/maintainer/version_cli.py`, `build_release_package.py` (#1076),
  `scripts/dev/check_release_packages.py`, `check_pr_closure.sh`.
- Guards: `test_docs_version_sync.py` rules 1–4, `test_site_sip_links.py`,
  `test_version_resolution.py`.

**References.** #789, #1061, #1076, #1151, #1113, #133, #205, #1089, #336; CLAUDE.md
"Release cut"; CHANGELOG 1.6.2.

---

## Lessons Most Important for a Maintainer Agent

Ranked by how much each should change what an AI maintainer *does* on an ordinary PR or
measurement, and why. Where two lessons share a mechanism they are ranked together.

1. **Enter at the live caller (A1).** The three 1.7.1 defects were green in CI and
   found by live cycles because every test handed the seam its input. An agent writes
   tests fast and will default to this shape every time; the PR template's "Entry point
   exercised" line is the check. Without it, an agent's tests prove nothing about the
   cycle.

2. **Verify loaded, not built (A2).** A symbol present is not a feature reachable
   (#1289); a rebuild's exit code is not a deploy (#370); a probe that errored is not a
   probe that answered (#1425). An agent that reads the tree instead of the container
   will report "shipped" for things that never ran. Live call, paired control, output
   recorded.

3. **Three states, never two (B2).** Observed / asked-none / unaskable. Every readout
   an agent designs will collapse the last two unless told otherwise, and the collapsed
   reading always flatters the roll. Count non-execution beside failure; read by reason.

4. **Read the artifact, not the prose about it (B1).** The 1.6.3 reading was wrong
   because it trusted an oracle's verdict over the stored reports; the analyzer's claims
   were wrong three times in one roll. An agent produces and consumes prose fluently,
   which is exactly why it must cite the artifact id and the line.

5. **Guards over discipline (C1).** A rule written into CLAUDE.md and still missed is a
   guard, not a restatement. An agent has perfect recall of the rule and will still miss
   the step under delegation (#1061's natural experiment). When a lesson is learned, the
   deliverable is the test that fails, not the paragraph.

6. **Require, don't default (C3).** Every fallback an agent adds to keep a container
   booting converts a config error into a stranger symptom later (#333, #1157, #327).
   Missing config raises and names the setting.

7. **Table the seams before binding a check (D3).** #1259 refused a correct fix because a
   check bound for the qa tree was evaluated on the dev tree. An agent binding a check
   sees one evaluator; the cycle has five. The table goes in the PR.

8. **Controls before a gate; no hard gate on an unvalidated surface (A3, D6).** #552 was
   reverted whole; #1049 taxed every cycle for a harm that could no longer occur. A new
   gate ships reporting-only with its stored red and its stored greens, and is promoted
   on corpus evidence.

9. **The mirror rule and the amendment (F1).** Before removing, say what it produced and
   for whom (#1253 → #1255); when diverging from a SIP, amend it in the diverging PR;
   before moving a module, harvest its comments. An agent refactors quickly and will
   discard rationale it did not read.

10. **A wasted round is not a round; a marker is one dispatch (D2).** #1053, #1129 and
    #1347 each burned the correction budget on non-events. Any state an agent sets on an
    envelope needs a clearing rule stated in the same PR.

11. **Instrument before fixing; count the recurrence (B3).** #1268's fix followed a
    reading of the generations; #1067 was fixed four times before anyone counted. An
    agent's first plausible cause is a hypothesis, and a fix in an evidence instrument
    that rests on a heuristic (#1436) fails silently.

12. **Derive, don't author; one fact, one owner (C4, C2, C5).** A fact the framework can
    derive is delivered, never restated by an agent or by a prompt asset; a generated
    file has one writer; a cross-cutting surface has one seam. "The neighbouring code
    does it this way" is never justification.

13. **Pre-register and disclose (E1, E2).** Fix the prediction before the roll; freeze
    and assert the deploy; refuse to judge with code the deploy never ran (#1438); name
    what the evidence does not cover; treat "unexercised" as unexercised. The shakeout is
    a loop with an exit rule stated before the first launch.

14. **The cut is a guarded procedure (G1).** Preview the package before writing it
    (#1076); nothing merges in the window (1.6.2); every step with a miss on record has a
    guard, and the one without (ROADMAP) is named as unguarded.

15. **Stay stack-aware by structure (C6).** "Generic" was stack #1 for six weeks and a
    green React suite was discarded by a Next.js-shaped check. A stack fact lives on the
    `ScaffoldStack`; a check that cannot cover a stack declares the gap. The owner
    should not have to keep asking.
