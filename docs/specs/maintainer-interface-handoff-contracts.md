# SquadOps Maintainer Interface and Handoff Contracts

**What this is.** The artifacts that pass between members of a maintainer crew building
SquadOps, derived from how the work has actually moved between people, sessions, terminals
and the owner to date — issues, PRs, plans, pre-registrations, records, SIP amendments,
runbooks and the operational log. For each recurring transition it names the producer, the
consumer, the artifact, what it must carry, what the consumer may assume and must re-check,
what is never allowed to live only in conversation, and when to stop and escalate.

> Handoffs should be artifacts, not conversation.

**What it does not assume.** SquadOps' own agent roster and its cycle/gate model are the
machinery being maintained, not a template for the crew. Nor does this document propose a
crew: the role words used below — Investigator, Implementer, Verifier, Integrator, Platform
operator, Measurement steward, Recorder, the owner, and an architect / primary engineer —
are labels for *functions the record shows someone performing*, taken from the capabilities
document's clusters, and nothing here depends on how many people or agents hold them or
what they are called. The interfaces are between functions; the artifacts are what cross
them. Where a function does not yet belong to anyone, the artifact still does.

**What the record says about how handoffs have actually worked.** Three facts shape
everything below:

1. **Review has been a stamp, not a diff read.** 807 of 935 merged PRs carry the owner's
   review object; every one sampled is a one-word `COMMENTED` review reading "reviewed";
   `reviewDecision` is empty on all 935; 40 PRs have any comment at all. Under delegation
   (September) the stamp appears on 78 of 194. Substantive review happened elsewhere: on
   plan revisions ("on the owner's written review of rev 2", 1.7.5 §10), on SIP drafts (ten
   points dispositioned, SIP-0103 §5c), and as in-session questions that produced a
   correction PR the same day (#1416). The required CI checks are the review of the code;
   the PR body is what a human reads. That is why the PR body's Evidence section carries the
   weight it does.
2. **The plan row and the issue body are the de facto task contract.** Every 1.7.x line was
   built from a table with the columns *item / what lands / how CI proves it* (1.7.3 §3.2;
   1.7.5 §3.2 adds *readout*, §3.6 adds *in the image?*), and every item pointed at an issue
   whose body carried *What happened / Why (read from the code) / Fix shape / Acceptance /
   Placement*. The two together are what a delegate worked from for whole lines (1.7.3: "do
   it all and merge once CI completes").
3. **Rulings are written where the decision lives, and dated.** In the plan (#1232 records
   rule B in §2.2, §6 and the revision history), in the pre-registration before the run
   (1.7.4 §3a, "a reading corrected after the run is not a prediction"), in the SIP as a
   numbered amendment (SIP-0106 §1.2e/f), on the PR (#1344: "Please reply with it here
   before this merges"), and in the plan's own "decisions taken under delegation" section
   (1.7.3 §9, "each is the owner's to overrule").

**Numbers behind the PR-body claims.** Of the 255 PRs merged since the template landed
(2026-08-26): 166 carry a `## Evidence` heading; 146 state a regression count; 133 carry
`Closes #`; 78 `No issue:`; 40 `Refs #N — remaining:`; 96 cite a cycle id; 44 cite a replay;
9 name the entry point exercised; 4 carry a `Removed:` line; 3 a `Rationale: SIP` line; 1
an `Evaluated at:` seam table. The template's newest fields are the least used, which is
the gap the Implementer → Reviewer section addresses.

---

## The transitions that actually recur

Thirteen, in the order a finding travels. The first eleven are the ones named in the
brief; two more (a decision escalated rather than taken; a whole line delegated) recur
often enough in the record to need their own artifact.

---

### T1. Problem observation → investigation

**Producer.** Whoever holds the observation: the Measurement steward (a roll record), the
Platform operator (a log window, a box reading), the Integrator (a red on main), the owner
(reading a roll: "the owner noticed the red before I did", #1357).

**Consumer.** Investigator.

**Trigger.** A verdict, readout, log line or box state that is wrong or cannot be right.

**Required artifact.** The observation *with its identifiers*: cycle and run id, deploy
identity (image ids, HEAD), the record section or log line quoted, the UTC window. For a
roll, the per-roll record is the artifact; for a box event, the `sar`/`docker` reading with
timestamps (#1177's table); for CI, the run URL and the failing job.

**Required fields.** What was observed; where (record §, log line, table); when (UTC);
what it was expected to be and by which prediction or rule; whether the deploy was pinned
or a shakeout.

**Evidence that must accompany it.** The quoted line, not a paraphrase; the record, not a
summary of it. The night runbook's standard applies from the first step: "a file, a line,
and the artifact or log entry that proves it".

**The consumer may assume.** The identifiers are correct and the record is the driver's
render of what it collected (README: "the readouts are read from the per-roll record, never
by hand from the log").

**The consumer must re-verify.** The four outcome states before diagnosing (runbook Step 1:
`unverified` is not `passed`); silent non-execution (Step 2); which stored version actually
ran (Step 4); and that the deploy carried the code the observation assumes (loaded checks,
#1425).

**Never only conversational.** The cycle/run ids and the deploy identity. An observation
without them cannot be re-read and is how #1296's `deploy ?` and #1425's unrun probes went
unnoticed through a checkpoint pair.

**Escalation.** A counted roll that may be void or a reset — stop the set for the owner
(1.6.5 §5) before investigating further; an unreachable box; evidence about to be
destroyed by a rebuild (capability 9.13).

**Examples.** The 1.7.4 record §5 findings rows; #1256 ("every `decided_by_agent` in the
line's records so far is 0"); #1425 (recorded identity re-read after the pair); #1177's
minute-by-minute table.

---

### T2. Investigation → implementation

**Producer.** Investigator.

**Consumer.** Implementer (often the same person, a different day — which is exactly why
the artifact matters).

**Trigger.** The mechanism is named to a file and a line, or the investigation has stopped
with what it ruled out.

**Required artifact.** An issue in the repository's established shape. From 535 issue
bodies the recurring sections are `Summary`/`What happened` (124), `Fix`/`Fix direction`/
`Fix shape` (143), `Evidence` (43), `Root cause`/`Why` (55), `Acceptance` (26),
`Placement` (18), `Related` (48).

**Required fields.**
- *What happened* — with cycle/run ids and the sequence (a timeline table where order
  matters: #1318, #1094).
- *Why — read from the code, not inferred* — file and line for each hop (#1256:
  `dispatched_flow_executor.py:3113`, `:3023`, `:2996`; `repair_handlers.py:324`;
  `correction_runner.py:844-855`, `:1474`).
- *Reproduced* — the offline replay that shows the mechanism (#1259's tree → verdict table;
  #1126 "Reproduced offline: `detect_self_mocking_tests([...])` → `MOCKS_THE_NETWORK`").
- *What it is NOT* — where a plausible cause was ruled out with evidence (#1312: not
  truncation, not extraction, not a missing contract, each with the number that rules it
  out).
- *Fix shape* — the layer, the seam, and the replay that will prove it, not the diff.
- *Placement* — which line or lane, and why (#1251, #1374).
- *Related / Not this* — sibling defects split out (#1229 "split out because a deferral
  recorded only in a closed issue's comments is a deferral that disappears").

**Evidence that must accompany it.** Artifact ids (`art_…`), log lines quoted with their
service and timestamp, the LangFuse generation id where a prompt is at issue (#1289's
`35f698cd`), the stored-artifact replay.

**The consumer may assume.** The mechanism, when it cites file:line and a reproduction.
Nothing else — a "fix direction" is a hypothesis about the remedy, not about the cause.

**The consumer must re-verify.** The premise against *current* main (#691 was filed on
artifact ids read without provenance and rewritten before it was built; #1149 §2 notes
"the executor grew from 4,349 to 4,933 lines since #1152 was filed"); the seam table when
the fix binds or re-weights a check (CLAUDE.md "Typed checks"); and, if the fix removes
something, what it produced and for whom (#1253 → #1255).

**Never only conversational.** The mechanism claim and its file:line; the replay that
reproduces it; what was ruled out. The runbook exists because two diagnoses in one night
were "explaining a symptom instead of tracing it" and were acted on.

**Escalation.** The investigation cannot reach a line ("say so and stop — an honest
'unresolved, here is what I ruled out' is worth more than a plausible story"); the fix
would change a verdict semantic or a pin (owner's ruling: rule B, #1269, GENERATOR_VERSION
moves); the fix's premise contradicts an accepted SIP (amend in the PR, step 5a).

**Examples.** #1256, #1259, #1250 (PR body as the investigation's record), #1312, #1120,
#1054 ("Read before fixing … this issue may be that guard misfiring rather than a missing
one").

---

### T3. Architecture decision → implementation

**Producer.** Architect / primary engineer, with the owner's review.

**Consumer.** Implementer(s) — often several, across PRs and days.

**Trigger.** A surface with no owning rule (#218), a structural debt named for a line
(#301, #1152), a SIP accepted, a ruling on an open seam decision.

**Required artifact.** A design artifact that is declared the *acceptance source*, distinct
from the plan that places and sequences it. The record has three shapes:
- **A standard** under `docs/architecture/` with its audit commit and its guard
  (`composition-roots.md`: "the audit of the four roots against it on main `5c686cbd`, and
  the decisions the audit forced … enforced by a composition-roots guard … landing in the
  same PR as the first root it constrains"; `api-route-lanes.md` with `test_route_lanes.py`).
- **A map** for an extraction (`1-7-5-recovery-extraction-map.md`: the invariant, the
  subject measured on a named commit, the steps in order, the core/tail split, the proof —
  "this map, not the plan, is the acceptance source").
- **A SIP** with its phase plan, and the harvest of any rationale the implementation will
  move (SIP-0105 §"Design decisions harvested", each entry *Rule / Evidence / Ruled by*).

**Required fields.** The principle in one sentence; the surface enumerated (every router,
every root, every method the map moves, with line numbers on a named commit); the rule's
boundary and its allowlisted exceptions with reasons; what the artifact deliberately does
not decide ("nothing here is derived from that standard"); the proof each implementing PR
must carry; the commit the guard must fire on.

**Evidence that must accompany it.** The audit or measurement on a named commit (four roots
audited; 4,668 lines with a 511-line method; 216 literals across 30 files); the owner's
review recorded in the artifact's own status line ("rev 2 on the owner's review the same
day").

**The consumer may assume.** The rule and the boundary. The plan row's *what lands* is
bounded by this artifact and the implementer does not re-derive it.

**The consumer must re-verify.** That the audited commit still describes main for the
paths the PR touches (`git diff --stat A B -- src/ adapters/`); that the guard fires on the
motivating commit before it is trusted to pass; that the harvest entries the PR preserves
still match the code being moved.

**Never only conversational.** The rule, the exceptions, the proof, and any narrowing —
SIP-0103 §5d exists because three falsified premises and four unbuilt dispositions had
been recorded only in a release plan, "a document superseded at the cut".

**Escalation.** The audit finds the standard cannot be applied without an exception the
artifact does not list; an implementing PR would change what "done" means (1.7.5 §3.5's
core/tail rule: "a core left incomplete stops the line, not the plan"); the design review
has not happened (the Scoped Code Revision review "never opened — the 1.8 plan's opening
step").

**Examples.** `docs/architecture/composition-roots.md`; `docs/plans/1-7-5-recovery-
extraction-map.md`; #218 → `test_route_lanes.py`; SIP-0105 §"harvested" → #1233; SIP-0103
§5d; #1232 (the ruling that unblocked rule B, recorded in the plan).

---

### T4. Primary engineer → supporting engineer

Covered in full in its own section below. In brief: the artifact is a **bounded task card**
— the plan row plus the issue it points at, with the bounding proof named — and the record
shows exactly which fields were present when delegated work landed clean and absent when it
did not.

---

### T5. Implementation → review

**Producer.** Implementer.

**Consumer.** Reviewer — historically the owner's stamp over the required CI checks;
structurally the Verifier (can the evidence fail?) and the Integrator (does it merge
cleanly and close what it says?).

**Trigger.** A PR opened with `--head`, CI green on every job including the non-required
ones (1.7.5 §3.10: "every job of main's run read after every merge").

**Required artifact.** The PR body in the template's shape (`.github/PULL_REQUEST_TEMPLATE.md`):
`## What`, `## Closes`, `## Evidence`, and where applicable `## Not in this PR` and a deploy
note. Detailed in the Implementer → Reviewer section below.

**Never only conversational.** Anything the closure check, the seam table or the mirror
rule asks for; the owner's OK on a do-not-modify file ("recorded on this PR", #1344).

**Escalation.** A regenerated pin or golden (its own commit, "owner approval needed",
#1246); a change on the do-not-modify list; a change that moves runtime behaviour while a
set is open ("no merges to main while a set is open").

---

### T6. Review → correction

**Producer.** Reviewer / owner.

**Consumer.** Implementer (or the plan's author).

**Trigger.** A review that finds a premise wrong, a count wrong, a scope wrong, or a claim
overstated.

**Required artifact.** A **dispositions list**: each point raised, numbered, with a
disposition and its consequence, written into the document under review so "the design
review inherits positions, not open threads" (SIP-0103 §5c — ten points, each `ACCEPT`,
`ACCEPT WITH SHAPE`, `ANSWERED`, …). For a plan: a `## Findings from the review` section and
a revision-history entry naming what changed and on whose ruling (1.7.5 §9, §10). For code:
a revert PR that says why (#553: "an unvalidated new rejection gate sitting in the path of a
measurement"; #1436: "reverted; the readout now reports the artifacts it actually counts
and says so"). For a record or SIP already published: a dated correction *beside* the wrong
reading, with how the error was made (1.6.3 record §6; SIP-0106 §1.2f "Corrected
2026-09-08, same day").

**Required fields.** The point as raised (quoted); the disposition; what it changes and
where; what it does not change ("No change to placement, sequencing, the set or the gates",
1.7.5 rev 5).

**Evidence that must accompany it.** For a reverted claim, the evidence that falsified it
(#1436's two-row table); for a corrected reading, the artifacts that were there all along
("the evidence that shows it was banked at the time: the seven per-round `test_report.md`
files").

**The consumer may assume.** The disposition is the ruling on that point.

**The consumer must re-verify.** That the correction propagated to every surface that
carried the claim (CHANGELOG, release package, Release, memory: #1095 corrected three).

**Never only conversational.** The disposition of each point. An in-session "are you SURE?"
became a PR the same day (#1416) precisely so the correction would outlive the session.

**Escalation.** A correction that would rewrite a pre-registered reading after the run
(forbidden; 1.7.4 §3a); a correction that changes a scoring instrument mid-window (#1005:
"Merge as part of the window ruling, not before").

**Examples.** SIP-0103 §5c; 1.7.5 §9–§10; #553; #1436; 1.6.3 record §6; #1416; #691
("Rewritten 2026-08-03").

---

### T7. Merge → deployment

**Producer.** Integrator (the merge) → Platform operator (the rebuild).

**Consumer.** Platform operator, then the Measurement steward.

**Trigger.** A tranche complete on main; the plan's sequencing step reached ("Deploy A;
one checkpoint pair").

**Required artifact.** Two: the **deploy note** in each PR that changes what the images
carry ("Executor-side only, so this needs a `runtime-api` rebuild … intended to ride the
roll-3 rebuild alongside #902", #908; "this changes the expanded tree, so it needs a
rebuild before the next window opens", #973), and the **deploy identity** after the
rebuild — the seven image ids, `head`, and every loaded-check probe's answer
(`deploy_identity()`, written to `shakeout-deploy.json` and into the pre-registration's
deploy table).

**Required fields.** Which services need rebuilding; whether the change moves the frozen
surface or a hash ("if it does, the contract must be re-emitted, re-ingested, and the
launcher refs updated before the next roll", runbook); the tranche this deploy is for and
what may *not* be on it (1.7.5 §7: "nothing that can move runtime behaviour rides beside
the closures").

**Evidence that must accompany it.** `rebuild_deploy.log` read (not stdout), the honest
exit code (#370), the identity with every probe `observed` rather than `ERROR:`, and
container `StartedAt` after the build (SIP-0104 P6 record).

**The consumer may assume.** Nothing about what the images carry until the identity says
so. "Loaded, not built" is the contract.

**The consumer must re-verify.** The probes (a rebuild has exited 0 with stale agents;
#1425's probes never ran); that no run was in flight when the rebuild happened (it leaves
`running` in the registry and every later preflight refuses); that the compose or init
edit, if any, carried the owner's recorded OK.

**Never only conversational.** The deploy note; the identity. "The operator hand-edited the
pin before each of its four shakeouts" (#1296) is what a conversational pin looks like.

**Escalation.** Any compose, init or Dockerfile change (owner's OK on the PR); a rebuild
needed while a set is open (the deploy freeze; "a deploy freeze is not a work freeze");
a rebuild that would destroy a record's perishable texture (container logs).

**Examples.** #908, #973 deploy notes; 1.7.4 pre-registration §2 deploy table; #1344;
`rebuild_and_deploy.sh` (#370); #1425.

---

### T8. Deployment → measurement

**Producer.** Platform operator (the pinned deploy) and the plan's author (the predictions).

**Consumer.** Measurement steward.

**Trigger.** The shakeout loop's exit rule met; the pins known.

**Required artifact.** The **pre-registration**, merged by commit hash before roll 1, and
its **set config** (the §1 table as data). Sections that recur across the twelve in the
record: §1 parameters and pins; §2 preconditions and the shakeout log (each deploy: built
from, images, purpose, found); §3 predictions with the readout each is read from — and §3a
rulings recorded *before* the diagnostics run; §4 texture; §5 delegation; §6 the gate
constant verbatim; §7 prohibitions; the "Loaded, not built" row.

**Required fields.** Project, squad and request profiles, overrides; the expected
config-hash and squad-snapshot prefixes; `frozen_deploy_commit` and the seven image ids;
`loaded_checks` per service with their paired controls; roll count and the early-stop rule;
every registered field's unaskable state as a schema property (#1445).

**Evidence that must accompany it.** The shakeout records that produced the pins; the
diagnostics' `seam_reached` per fault with the entry point each used; the preflight
output.

**The consumer may assume.** The predictions and their readouts as written. Not the pins —
those are asserted at every launch.

**The consumer must re-verify.** `preflight --set … --counting` every time: dirty tree,
unreleased leases, runs in flight, image ids, HEAD, probes, framework drift between the
pinned commit and the driver's tree (#1438), and that no declared fault is on a counting
set.

**Never only conversational.** A prediction's expected reading (§3a: "a reading corrected
after the run is not a prediction"); the gate constant ("copied verbatim onto every gate
approval — NO substitution of any kind").

**Escalation.** A prediction with no producer in the record (#1285's blocker — "every
texture field must have a producer before the set opens, checked against a real record"); a
seam not reached on the pinned deploy ("stops the line here, before the set opens", 1.7.5
§7 step 9).

**Examples.** `docs/plans/1-7-4-verification-set-preregistration.md` §2–§3a;
`docs/plans/verification-sets/1-7-4-*.yaml`; #1104/#1124/#1142/#1266 (the pre-registration
PRs); #1438.

---

### T9. Measurement → release decision

**Producer.** Measurement steward (the record) and the Recorder (the cut record).

**Consumer.** The owner (the decision) and the Recorder (the cut).

**Trigger.** The last counted roll read at its boundary; the live reads done.

**Required artifact.** The **record** (1.7.4's sections: headline; the bars; live
hypotheses; seam invariants and any gate amendment; findings; what the loop did when it
ran; the live readings; *what this set does not claim*; the rule for the next record) and
the **cut record** ("what the evidence does not cover: which predictions no roll exercised
and why, which readouts were vacuous on which stack, and where the tagged tree differs from
the validated deploy").

**Required fields.** The per-roll table (cycle, framing runs, gate decider, verdict, audit,
corrections, criteria, wall time); the counted/void/reset reading per roll with its reason
and the §-rule it was made under; the shakeout rounds taken against the budget and how
many were attributable to the pack; drift between the measured deploy and the tag; every
prediction's status including *unexercised*; the delegation under which it ran.

**Evidence that must accompany it.** Per-roll records rendered by the driver; the
pre-registration's hash; the image ids and StartedAt at close; the deploy A/B/C table with
what each found.

**The consumer may assume.** The facts in the record. The *meaning* is the
pre-registration's ("the per-roll record is facts; the pre-registration says what they
mean").

**The consumer must re-verify.** The close criteria against the plan's §3.9 one by one;
that the roll-boundary readings were made before the next launch (1.7.1 §3.3's deviation);
the release-package preview against the record before `--write` (#1076).

**Never only conversational.** A void or reset and its reason; a prediction left
unexercised; a difference between the deploy and the tag ("the 1.6.2 lesson").

**Escalation.** A falsified prediction or a reset (the set stops for the owner); an
instrument fix that would change the score of a counted roll (#1004 → the owner's ruling
with both readings kept: "3/6 pre-registered instrument / 4/6 corrected, both always
reported").

**Examples.** `docs/plans/1-7-4-verification-set-record.md`; `1-7-0-cut-record.md` §3
("what this line actually cost"); CHANGELOG 1.6.2 "Not exercised by the cut evidence,
stated plainly"; 1.6.3 record §6.

---

### T10. Finding → issue / follow-up work

**Producer.** Whoever holds the finding — most often the Measurement steward reading a
record, or an Implementer who found something "on the way" (22 issues say so).

**Consumer.** The Recorder (the tracker) and the next plan's author.

**Trigger.** A finding that is not the current PR's ("Not in this PR, stated"), a detection
during a set ("detections recorded, not fixed"), a deferral in a closed issue.

**Required artifact.** An issue (T2's shape) with a `Placement` section, or a line in the
plan's re-placement table with the count of plans that have carried it (1.7.5 §3.8), or a
`## Not in this PR` list naming each sibling's issue.

**Required fields.** The evidence it rests on (a stored artifact, a record §); its class
("the shape of #1261 and of the hollow release capture in #1076"); what it is *not* (a fix,
a decision — #1427: "the part that needs a decision, not a fix"); the lane it belongs in
and why an odd or even minor.

**Evidence that must accompany it.** The record row or artifact id; "filed on the owner's
go, each cited to the stored artifacts" (1.7.1 record §4).

**The consumer may assume.** The finding is real as cited. Not its placement, which is the
owner's.

**The consumer must re-verify.** That it is not already filed (the 2026-09-08 audit found
four closable and ten with drifted bodies); that a merged PR did not already close it
(#330, #372, #352 open with merged PRs, 1.7.5 §9).

**Never only conversational.** The deferral. #1251 ("three lines of plan text, never
filed") and #1229 ("a deferral recorded only in a closed issue's comments is a deferral that
disappears") are the two named failures; the 1.7.3 plan §8 rule followed: "filed as issues
before 1.7.4's plan is written, so neither is carried as plan text".

**Escalation.** A finding that bears on the counted set in flight (1.7.4 §3a.4 on #1406:
"any counted roll accepted with demoted criteria is named in the record"); a finding that
requires a design decision rather than a fix.

**Examples.** #1355/#1354's "Not in this PR" lists; 1.7.4 plan §6a (seven items re-placed
by name); #1229; #1251; #1427.

---

### T11. Owner ruling → resumed implementation

**Producer.** The owner.

**Consumer.** Whoever holds the line — Implementer, Measurement steward, Recorder.

**Trigger.** An open decision the crew raised rather than took; a review; a question asked
in session.

**Required artifact.** The ruling **written where the decision lives**, dated, in the words
the ruling used:
- in the plan — #1232 records "the owner's ruling of 2026-09-01 — B" in §2.2, §6 and the
  revision history, with a grep as its evidence;
- in the pre-registration before the run — 1.7.4 §3a "Five rulings recorded BEFORE the
  diagnostics run (2026-09-08, owner-approved)";
- in the SIP as a numbered amendment — SIP-0106 §1.2e "(owner ruling, 2026-08-30)";
- on the PR — #1344 "the 1.7.3 plan §3.2 step 10 requires the owner's explicit OK
  recorded on this PR"; #1246's pins "owner approval needed";
- in CLAUDE.md when it is a standing rule — "Owner's ruling of the same shape at the seams:
  require, don't default".

**Required fields.** The question as put; the ruling; the date; what it changes and what it
leaves unchanged; who may overrule it (a delegate's decision is "the owner's to overrule",
1.7.3 §9).

**Evidence that must accompany it.** The evidence the ruling was made on (V4 roll 2's
approval note versus the manifest's `unresolved` decision, SIP-0103 §5d B1; the decode
table behind SIP-0106 §1.2e).

**The consumer may assume.** The ruling settles the question for the line. "Raise a concern
once, then proceed on the ruling" (capability 13.5).

**The consumer must re-verify.** That the ruling reached every surface that stated the old
position (#1232 existed because #1230 merged with the decision still "pending"); that a
later finding has not falsified the ruling's premise (§5d C: B1's justification was
"half-funded when the control was removed").

**Never only conversational.** The ruling. Every example above is a ruling that was given
in conversation and then written down; the writing is the handoff.

**Escalation.** None — this is the terminal of escalation. The one obligation is to say
when a ruling's premise later fails (SIP-0103 §5d C, closed the same day).

---

### T12. Investigation → owner decision (a question, not a fix)

**Producer.** Investigator / Implementer.

**Consumer.** The owner.

**Trigger.** The correct next step is a decision the crew is not authorized to take: a
change that breaks comparability, moves a pin, touches compose or init, spends the box, or
narrows an accepted design.

**Required artifact.** The question with its options and a recommendation, and — where the
crew has already done everything that does not depend on the answer — the work waiting
behind it. The shape in the record:
- #1427 "The part that needs a decision, not a fix … Owner's call — raised rather than
  taken", with the trade stated both ways;
- #1004/#1005 "Window-protocol disposition is the owner's ruling … score-as-measured 3/6,
  §5.1 reset, or an explicitly-labeled corrected-instrument re-measure";
- 1.7.5 §8 "Decisions made by recommendation — the owner overrules, not fills in" (eleven
  numbered);
- #1177/#1178 parked with the evidence and the proposed fix, and #1412 with "nothing goes to
  Avarok from this issue without the owner's explicit go-ahead".

**Required fields.** What is being decided; what each option costs, with the number
("silently breaks comparability with three prior lines"); the recommendation; what has
been done already and what waits.

**Never only conversational.** The options and the recommendation — a decision made in
chat with no record is a T11 without its artifact.

**Escalation.** This *is* the escalation. The standing list of what needs the owner:
sudo, credentials, compose/init/Dockerfile edits, pin and hash moves, promotion of a SIP,
anything destructive on the box, anything that changes what a set compares to, anything
outward-facing.

---

### T13. Line → delegate (standing delegation) → line

**Producer.** The owner (the delegation) and the delegate (the return).

**Consumer.** The delegate, then the owner.

**Trigger.** Overnight operation of a set; a whole line ("do it all and merge once CI
completes", 1.7.3).

**Required artifact, outbound.** The **standing rules** and the plan. The rules exist in two
written forms and have run four overnight sets and one full line:
- the night runbook's "Unattended authority" — *do without asking*: read anything, query
  the database, replay stored artifacts, write code on a branch, open a PR, file an issue,
  run the regression and the contract gates; *never without an explicit rule*: deploy,
  rebuild, restart a service, merge, change frozen seeds mid-baseline; "a deploy freeze is
  not a work freeze";
- the pre-registration's §5 — "no pushes; triage per roll (trace artifact versions, read
  the code path before naming a mechanism); deploy frozen, work not frozen; detections
  recorded, not fixed; gates are the §6 constant. The morning report leads with the result.
  Every roll is launched only after the previous one's record is read."

**Required artifact, inbound.** The **morning report** ("plain English, deltas and
anomalies only, no optimism; lead with what happened and what it means; the identifier
second; never use an issue number as a noun; if a claim was later retracted, say so
plainly") and, for a delegated line, a **decisions-under-delegation** section in the plan
— 1.7.3 §9: eight decisions, "each recorded here so the plan and the tree do not disagree,
and each is the owner's to overrule".

**Required fields, inbound.** What was done against the plan; what diverged and why; what
was found and filed; what was *not* done and is waiting; every deviation from the standing
rules named as such (1.7.1 §3.3).

**The consumer may assume (owner).** The rules were kept unless the report says otherwise.
Every deviation in the record was self-reported (1.7.1 §3.3; #1425 "Introduced by me";
#1357 "I merged six PRs … reading only the three required ones").

**The consumer must re-verify (owner).** The decisions-under-delegation list against the
plan; the merges against the whole CI run; the pins against the identity.

**Never only conversational.** The rules; the deviations; the decisions taken.

**Escalation (delegate).** A reset or a falsified prediction stops the set; a seam not
reached stops the line; anything on the "never without an explicit rule" list.

**Examples.** `docs/ops/NIGHT_TRIAGE_RUNBOOK.md`; 1.6.4 §5, 1.6.5 §5, 1.6.6 §5; 1.7.3 §9;
1.7.1 record §3.3; the 1.6.4 record's opening ("Executed overnight under the owner's
delegation: every roll launched only after the previous record was read").

---

## Primary Engineer → Supporting Engineer

**The question.** What information most increases the chance that a bounded implementation
task is completed correctly without rediscovering architecture?

**The method.** Compare the delegated work that landed clean with the delegated work that
did not, and read off which fields were present in the first set and absent in the second.

### What was present when it worked

The 1.7.3 line — sixteen items, fully delegated, "nothing attributable to the sixteen
items" — was worked from a table whose every row carried:

| field | 1.7.3 §3.2 column | example |
|---|---|---|
| the objective, as a sentence about the tree | *what lands* | "`terminal_status` retired: `RunStatus` is the domain vocabulary everywhere, translated to Prefect's `State` at the `WorkflowTracker` adapter boundary only" |
| the proof, as a named guard or test | *how CI proves it* | "the leaked vocabulary anywhere outside the Prefect adapter fails CI" |
| the issue, as the mechanism and the files | the item link | #377's three-vocabulary table with file:line |
| the order and why | "in merge order … the widest rename first" | #922 then #559 |
| the one thing that needs the owner | inline | "#225 … the edit to `docker-compose.yml` needs the owner's explicit OK, recorded on the PR" |

The 1.7.5 plan added two columns because the line's attribution structure needed them:
*readout* (which record field will read the change) and *in the image?* (whether it can
ride beside a measured tranche). The extraction map and the composition-roots standard
supplied the rest for their items: the invariant, the subject measured on a named commit,
the steps, the proof per step, and "one connection to the standard, stated so it is not
mistaken for coupling".

The extractions that landed byte-identical (#1131, #663, #331, #186) each had a **bounding
artifact** — goldens captured first, an AST count, the frozen fixtures, the slice plan —
that made the proof a comparison rather than a judgement. #1149's harvest gave #1233 the
rationale to cite per entry.

### What was absent when it did not

| failure | the missing field |
|---|---|
| #1259 — two well-tested checks bound onto a suite; a correct dev repair refused | the **seam table**: which environments evaluate the task's criteria, on which tree, and the outcome on a tree without the file |
| #1255 — a strip that removed a builder task's only typed criteria | the **mirror-rule answer**: what the removed thing produced and who consumed it |
| #1425 — probe keys renamed; three probes never ran through a pair read as clean | the **paired control**: a probe must be shown to fail on a deploy lacking its target before it is trusted to pass (capability 9.7) |
| #1318 → #1364 — a gate keyed on the attempt's history | the **contract statement**: which rows a task type owes by contract, not by what an attempt wrote |
| #552 → #553 — a gate validated on synthetic fixtures | the **stored controls**: the live seeded contract it must pass, named |
| #1357 — a column drop on a table only `init.sql` creates | the **ownership fact** for the object being changed (which file creates it) |
| #1049 — a gate whose premise an earlier PR had made false | the **premise**, stated in the gate's own text so the next change can see it went stale |
| #1436 — a grouping key inferred from timestamps | the **prohibition** on inference in an evidence instrument, and the second case that falsifies the first |

None of these is "the architecture". Every one is a fact about the *evaluation surface* the
edit sits on — who else reads it, on what tree, with what already true — that the supporting
engineer could not have known from the objective alone and did not go looking for.

### The minimum useful contract

Derived as: the fields present in every clean delegation, plus the one field whose absence
explains each failure, minus fields the record shows were never needed.

**Always (five fields).**

1. **Objective as a statement about the tree** — the plan row's *what lands*. One sentence a
   reviewer can check against the diff.
2. **The bounding proof, named** — *how CI proves it*: the guard, golden, fixture hash, AST
   count, replay or record field that will fail if the work is wrong. If no such thing
   exists, the task is not yet bounded and goes back to the primary engineer.
3. **The mechanism and the files** — the issue in T2's shape, with file:line and the
   reproduction. The supporting engineer does not re-diagnose; they do re-verify the
   premise against main.
4. **Prohibited changes, by name** — the do-not-modify list (`dist/`, generated manifests,
   compose service names, version bumps outside the script); "not in this PR" siblings;
   whether the change may ride beside a measured tranche (*in the image?*); "no merges while
   a set is open"; no hand-edited pins, goldens or `updated_at`.
5. **Escalation conditions, by name** — what stops the work and goes to the owner: a pin or
   hash move, a compose/init edit, a change to a verdict semantic, a premise found false, a
   guard that will not fire on the motivating commit.

**When the seam has more than one reader (three more).** Required whenever the change
binds, removes or re-weights a check, touches the accepted-patch path, or changes what a
record reads — the archetypes where every rework in the record clusters.

6. **The seam table** — every evaluator of the affected criteria, the tree each sees, and
   the outcome on a tree lacking the file (CLAUDE.md "Typed checks"; PR template "Evaluated
   at:"). One line in the whole record since the template landed; #1259 is its cost.
7. **The mirror-rule answer** for anything removed — what it produced, for whom, replaced by
   what.
8. **The paired control** for anything that will report success — the stored red it must
   catch and the stored greens it must pass, or the deploy on which the probe must fail.

**When it earns its place (three more).** Present in the clean extractions and standards;
skip when the change is a leaf.

9. **Rationale and precedent** — the harvest entry (*Rule / Evidence / Ruled by*) or the
   "shape" citation the record uses constantly ("the #772 shape", "the shape #1149 had",
   "#846's applicability rule"). This is what stops the engineer from re-deriving a
   decision the tree already made, and it is cheap when the SIP or ADR entry exists.
10. **Known traps** — the specific ones for this surface, not a general list: "`gh pr edit`
    fails here", "`--wait` is not a flag", "run ruff check and format separately", "a symbol
    import proves nothing", "the config hash does not cover the PRD". The capabilities
    document §0 and the runbook are the current home.
11. **Verification commands** — the exact invocations, when they are not obvious from the
    proof: `run_regression_tests.sh`; the replay script over the stored artifact; the
    `docker exec … python -c` probe with its control.

**Deliberately not required.** *Expected scope* as a separate field — the record bounds
scope by the proof and the prohibitions, never by an estimate, and "sized as ONE coherent
PR" appears only in sweep-era issues (#577, #582). *Acceptance criteria* as prose beyond
the proof — where an issue carries an `Acceptance` section (26 of 535) it is a list of
replays and guard outcomes, i.e. field 2 written out.

**Where the contract already exists.** Fields 1–2 are the plan row; 3 is the issue; 4–5 are
scattered across CLAUDE.md, the plan's prohibitions and the standing night rules; 6–8 are
PR-template prompts with single-digit adoption; 9 is the harvest section; 10 is the
capabilities document. The Candidate Contracts section names the one artifact that would
gather them.

### The lane rule that sits underneath

Two engineers on one checkout is a handoff too. The record's rule is **file ownership,
coordinated explicitly**: "the executor god-file stays M-owned — M provides the sandbox's
integration seams … the shared acceptance-evaluation surface coordinates explicitly
(precedent: #421/#425)" (1.4 evidence-arc plan); "the widest rename first, so the Spark lane
and the remaining PRs rebase once" (1.7.3). A supporting engineer's task card names the
files it may touch and whose lane they are in.

---

## Implementer → Reviewer

**The question.** What evidence should accompany a PR so the reviewer validates fulfillment
of a contract rather than reconstructing the task?

**What the record shows the reviewer actually does.** Reads the body, trusts the required
checks, stamps "reviewed". Comments on 40 of 935. So the body must let a reader who will
not open the diff confirm that the contract (the task card's fields 1–8) was met — and let
a reader who *does* open the diff start from the claims rather than from zero.

**The evidence set, in the template's order.**

1. **`## What`** — the objective as landed, in the plan row's words, plus what the reader
   would otherwise infer wrongly: "Read from the code, not inferred" (#1250); "Two things
   this PR does not do, on purpose" (#1344); "What is deliberately NOT changed … stated so
   the fix is not credited with more than it does" (#1297).

2. **`## Closes`** — `Closes #N` to an open issue, `Refs #N — remaining: …`, or `No issue:
   …` with the reason. Enforced (`pr-closure.yml`, #1113); 133 / 40 / 78 of the last 255.

3. **`## Evidence`** — the contract's proof, item by item:
   - *the bounding proof ran*: "Regression: 8535 passed, 5 skipped" (146 of 255); the guard
     "fires on `1b9b93a9`"; "every frozen fixture byte-identical (3 manifests, 57 files)";
   - *the replay*: the stored red rejected and the stored greens passing, by artifact id
     (#1240: "1.6.6 React roll 3's first stored suite … rejected with exactly one
     contradiction … Controls: the accepted rolls 1 and 5's stored suites pass … two
     controls, stated"); 44 of 255;
   - *the entry point exercised* for any changed seam (9 of 255 — the field with the largest
     gap between the standard and practice);
   - *the seam table* for any bound or re-weighted check (1 of 255);
   - *the mirror rule* for any removal (4 of 255);
   - *the harvest entries* for any move (3 of 255);
   - *the live reading* when there is one: the shakeout cycle id and what it showed (96 of
     255 cite a cycle id);
   - *the instrument line* when the change adds observability: the log line's exact shape,
     so "the next such diagnosis is a log line rather than a reading of code paths".

4. **`## Not in this PR`** — every sibling finding with its issue number, and any deferral
   the reviewer might otherwise assume was done (#1355, #1354; #1246 "Not in this PR,
   stated").

5. **A deploy note** when the images change — which services, whether a hash or frozen
   surface moves, which deploy it rides (#908, #973). Zero of the last 255 use the heading;
   the fact now travels in the plan's *in the image?* column instead, which is fine for a
   planned line and absent for an unplanned fix.

6. **The owner's OK, on the PR**, when the change is on the do-not-modify list or moves a
   pin (#1344; #1246's separate commit).

**What the reviewer validates.** That each field of the task card has its line in the
Evidence; that the regression count is from the whole gate; that the replay's controls are
stored artifacts, not synthetic; that a changed seam names its live entry point; that a
removal states its mirror-rule answer; that "Not in this PR" matches the issues actually
filed; that every CI job — including `integration`, `fresh-venv install`, `dependency
audit` and `release packages captured` — is green, not only the required ones (#1357).

**What the reviewer does not do.** Re-derive the mechanism (that is T2's artifact); re-run
the replay (the Verifier's job if the evidence cannot be trusted as written, in which case
the PR is returned for the artifact, not the answer).

**What must not be only conversational.** Every item above. The two PRs that carried the
owner's OK in their body exist because a verbal OK is not on the PR.

---

## Candidate Maintainer Contracts

The smallest set of reusable formal contracts worth defining for the Nostromo maintainer
crew, each named for what it is, with where its shape already exists in the record and
what formalizing it adds.

| # | contract | between | already exists as | what formalizing adds |
|---|---|---|---|---|
| 1 | **Finding record** | observer → Investigator → tracker (T1, T2, T10) | the issue body's recurring sections; the runbook's standard ("a file, a line, and the artifact") | a fixed section order — *What happened (ids) / Why (file:line, reproduced) / What it is not / Fix shape / Placement / Related* — so an issue without a mechanism or without ids is visibly incomplete |
| 2 | **Bounded task card** | primary → supporting engineer (T4); also architecture → implementation (T3) | the plan row (*item / what lands / how CI proves it / readout / in the image?*) + the issue + scattered prohibitions | one artifact carrying the eleven fields above, with fields 1–5 mandatory and 6–8 mandatory when the seam has more than one reader; the file-ownership lane named |
| 3 | **Change evidence** | Implementer → Reviewer (T5) | the PR template's `What / Closes / Evidence / Not in this PR` | the Evidence section as a checklist against the task card's fields, so a missing entry point, seam table or mirror-rule line is a visible gap rather than a prompt in a comment; the deploy note restored as a field |
| 4 | **Ruling record** | owner → line (T6, T11, T12) | rulings written into plans, pre-registrations, SIP amendments, PR bodies; §5c-style dispositions; §9 decisions-under-delegation | one shape — *question as put / options and recommendation / ruling / date / what it changes / what it leaves unchanged / who may overrule* — used identically whether the ruling lands in a plan, a SIP, a PR or the pre-registration, and a rule that it is written before the work resumes |
| 5 | **Deploy identity** | Integrator/Platform operator → Measurement steward (T7) | `deploy_identity()` → `shakeout-deploy.json`; the pre-registration's deploy table; the deploy note | the identity as the *only* admissible statement of what a deploy carries — image ids, HEAD, StartedAt, every probe in the three-state vocabulary — with the deploy note in every image-changing PR |
| 6 | **Measurement pair** | plan author/Platform operator → Measurement steward → owner (T8, T9) | the pre-registration + set config; the record + cut record; the driver's `render` | already the most formal contract in the repository; formalizing adds only the §3a rule (rulings before diagnostics) and the three-state readout as schema, both landed in 1.7.5 |
| 7 | **Standing delegation** | owner → delegate → owner (T13) | the runbook's "Unattended authority"; the pre-registration's §5; 1.7.3 §9 | the two lists (*do without asking / never without an explicit rule*) as one referenced document, the morning-report shape, and the decisions-under-delegation section as a required return artifact for any delegated line |

**What is not on the list, and why.** A review-comment protocol (review is a stamp over CI
and the body; formalizing comments would formalize a thing that does not happen); a
separate architecture-decision record (the register SIP is `proposed`; until it lands,
the standard/map/harvest forms in T3 are the contract, and contract 2 points at them); a
merge-to-deploy handoff distinct from the deploy identity (the identity *is* the handoff).

**The one contract that does not exist yet in any form** is #2. Every other row names an
artifact the crew already produces; the task card is the artifact the record shows was
implicitly present when delegated work landed clean and absent, field by field, when it did
not.
