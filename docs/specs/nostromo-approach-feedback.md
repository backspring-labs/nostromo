# Feedback: using Nostromo to build future SquadOps enhancements

**Date.** 2026-09-10.

**Basis.** The three companion documents in this directory — `maintainer-lessons-learned.md`,
`maintainer-work-archetypes.md`, `maintainer-interface-handoff-contracts.md` — and a read of the
Nostromo repository as it stood on 2026-09-10: `Platform Spec` (the platform spec),
`Bootstrap Plan` (the bootstrap plan), `instructions.md`, `crew/manifest.yaml`,
`crew/capabilities.yaml`, `crew/lifecycle.yaml`, `crew/budgets.yaml`, `docs/deviations.md`.

**Short version.** The approach is sound, its constitution already encodes most of what the
SquadOps record learned the hard way, and the one thing to change before commissioning is the
shape of the lifecycle, because it is fitted to the minority of the work.

---

## Where it fits the record well

Nostromo's principles map almost one-to-one onto the lessons the repository paid for:

| Nostromo principle | the SquadOps lesson it encodes |
|---|---|
| "GitHub artifact is the record; Buzz Canvas/thread is the workbench" | the amendment rule (SIP-0103 §5d) generalized — a decision recorded only in a superseded surface is lost |
| "Deterministic controls beat prompt promises" (§7.5) | #336's "what a test enforces stays true; what discipline enforces drifts" |
| "A claim without evidence is not a QA conclusion" | SIP-0096 §6.6 — narrative override is an evidence-integrity violation |
| fail closed on identity, budget and secrets (plan §3.2) | require, don't default (#333, #1157) |
| the deviation log (`docs/deviations.md`, plan §29) | the SIP amendment mechanism — record the divergence where the design lives, dated |
| probe-gated work packages with completion evidence | pre-registration and the per-roll record |
| the owner-authority list in `instructions.md` | nearly identical to the escalation list the record produced on its own (sudo, compose/init edits, pin moves, promotion, destructive box actions, anything that changes what a set compares to) |

That convergence is a good sign: the crew is being designed by someone who has the scars.

The single largest addition over how SquadOps has actually been built is **Dallas**. Review
today is a one-word "reviewed" stamp on 807 of 935 merged PRs, with 40 PRs carrying any comment.
An independent adversarial reviewer who separates blocking objections from non-blocking
concerns from unresolved questions, and tests claims against repository state, is the function
the record most visibly lacks.

---

## Where the record pushes back

### 1. The lifecycle is feature-shaped; the work is not

`IDEA_CREATED → EXPLORING → CONVERGING → SIP_DRAFTING → ARCHITECTURE_REVIEW → REVISION →
PROPOSED → ACCEPTANCE_REVIEW → ACCEPTED → PLANNING → IMPLEMENTING → VERIFYING → READY_TO_MERGE →
MERGED → OBSERVING → CLOSED` is the SIP ladder. That ladder is real, and it is where the
Ripley → Parker separation landed cleanly: the composition-roots standard and the recovery
extraction map (1.7.5) were exactly "architect writes the acceptance source, implementer builds
to it" and both were reviewed by the owner before the first constrained PR.

But the volume is elsewhere:

- `fix` is 381 of 935 merged PRs; `feat` is 173.
- 263 of 535 issue bodies cite a live cycle id; 115 a counted roll or set record; 61 a shakeout
  or diagnostic. The live cycle is the dominant source of work, ahead of CI and review combined.
- Every 1.7.x line was a measured pack driven by verification-set findings, run as a shakeout
  loop with an exit rule, on a frozen deploy, read at each roll boundary.

The record's most expensive single judgment is **reading a roll**: counted / void / reset;
whether a finding supersedes the deploy; whether a field reads "did not happen" or "could not
be asked" (#1425, #1431/#1436, #1445). That function has no home in the seven roles.
`OBSERVING` is one state-word for the most formal process in the repository — twelve
pre-registrations, twenty-nine set configs, a driver with a preflight that refuses on eight
conditions.

### 2. Brett is on the wrong side of the line the capabilities document drew

`Platform Spec` §11.6 gives Brett "failure classification" and "QA conclusions" on local
Qwen3.6 35B-A3B, deliberately not a coding variant. The capabilities document's allocation note
says: "Anything concluding 'clean', 'green', 'passing' or 'safe' is frontier — or returns raw
evidence for a frontier model to conclude from."

Brett as **collector** — run the gate, gather the rows, hand back raw output with its paired
control — is the L-tier work the record supports (capabilities 5.1, 5.2, 9.2, 9.8). Brett as
**the one who concludes** is the shape behind the record's delegation-era failures, and those
were *frontier* delegates: #1425 (three probes that never ran, read as data through a checkpoint
pair read as clean), #1357 (six merges read on three required checks while a non-required job
was red), 1.7.1 record §3.3 (a chain released on the headline before the rounds were read),
#1436 (a heuristic fix falsified within the hour). A bounded model is not proposed for those
classes because a stronger one already missed them.

### 3. "Ripley must not implement what Ripley designed" is right for features and wrong for the seam chain

Cross-layer defect tracing (archetype 2) is the shape where the trace *is* the fix's
specification and the next hop is found by whoever holds the code. #1250 → #1256 → #1259 →
#1264 was one engineer, one week; the PR bodies were the investigations ("The cause, read from
the executor"). Splitting investigation from implementation across two roles and a
Mother-routed handoff adds a boundary exactly where the record shows the work needs
continuity — and it is the archetype where every rework in the record clusters.

The separation is right for the SIP ladder. It should not be forced onto the fix line.

### 4. Cadence and budget

August merged 340 PRs; the first ten days of September merged 194 — from frontier sessions with
no per-session cap. Ripley and Parker share a $92/month hard envelope on GPT-5.6; Dallas has
$27 on Opus. A single `feat(checks)` PR in the record runs around 1,500 lines across 17 files
and rests on issue bodies of one to three kilobytes plus the vault.

The crew will run at a fraction of the recent cadence. That is fine if it is a stated target
and the archetype mix is chosen to fit it. The L+ archetypes — vocabulary sweeps against a
landed guard, extractions against a reviewed map, guards against a named shape, prompt changes
through the fragment system with a pin, dependency recompiles after the policy is set — are
where a bounded budget buys the most. Dallas's $27 should be scoped to the archetypes with
rework history (recovery-path changes, check and gate introduction, evidence instrumentation,
architecture standards) rather than spent on every PR.

### 5. The box

Mother and Brett are resident on the Spark's 121 GiB unified memory beside `qwen3.6:27b`,
which the `full` squad profile pins, and beside the verification-set driver, whose preflight
refuses any run in flight ("the GPU is not shareable"). #1177 is what two resident engines
cost: 95 minutes of swap thrash, `sshd` unable to page itself in, a power cycle. #1178 records
that the host had no memory containment at the time; the capabilities document §0 lists
`earlyoom` as installed since.

Spec §80 names the risk. The record quantifies it. Counted sets and crew operation should be
mutually exclusive on the box by schedule, and a counted set's deploy identity should record
whether any crew model was resident — otherwise the set's memory conditions differ from the
deploy's, silently.

### 6. What Nostromo's handoff contract carries, and what it does not

`Platform Spec` §15 defines a handoff as an envelope: work-item id, lifecycle state, canonical
GitHub references, Buzz thread or Canvas, capability requested, explicit request, acceptance
criteria or question, known unresolved issues, required return condition. That is the right
envelope and it is deliberately generic.

The SquadOps record supplies the **payloads** the envelope needs for the work to land without
rediscovering architecture — the seven candidate contracts in
`maintainer-interface-handoff-contracts.md`: the finding record, the bounded task card, the
change evidence, the ruling record, the deploy identity, the measurement pair, and the standing
delegation. Four of those (deploy identity, measurement pair, ruling record, standing
delegation) have no counterpart in the Nostromo documents yet; the task card exists in the
plan-row shape and nowhere as one artifact. The envelope should carry them rather than
restate them.

---

## What to do

Keep the roster open, as you said, and let two things derive it.

1. **Run WP-10's commissioning roll twice.** Once on the small, low-risk feature the plan
   describes (§17.1). Once on a fix-line item taken from a live verification-set finding —
   an issue whose body cites a cycle id and a stored artifact — because that is the shape
   roughly 70% of the work has and it is where the current lifecycle is least tested. The
   second roll will show whether the seam chain survives a Mother-routed split between
   investigation and implementation, or whether the fix line needs a single frontier holder
   from trace through wiring test through shakeout.

2. **Decide explicitly where the measurement function lives** — whoever pre-registers, runs
   preflight, reads records at the roll boundary, and rules on supersession — and put it on a
   frontier model. The capabilities document tiers every one of those judgments `F`
   (9.10–9.15), and the record's delegation failures are all in that class. Whether it is a
   new role, a Ripley responsibility, or the owner is the crew-shaping decision; the
   constraint from the record is only that it is not a local model concluding.

Everything else in the design can stay exactly as written. The constitution is good; the
budget boundaries are real; the record/workbench split is the right rule; Dallas is the
missing function. The two adjustments above are about fitting the machine to the work the
record shows, rather than to the work the SIP ladder describes.
