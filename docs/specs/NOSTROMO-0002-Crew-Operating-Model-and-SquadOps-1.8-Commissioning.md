# NOSTROMO-0002: Crew Operating Model and SquadOps 1.8 Commissioning Plan

**Status.** Proposed. Awaiting owner review.
**Date.** 2026-09-10.
**Supersedes.** Nothing. Amends NOSTROMO-0001 where §1.3 says so.
**Governs.** How the Nostromo crew works once it is live, and what must be true before it touches SquadOps 1.8 code.

---

## 1. What this document is

NOSTROMO-0001 says what Nostromo is. NOSTROMO-PLAN-0001 says how to stand it up. Neither says how the crew
*works* once the processes are running, because when they were written there was no evidence about how this
particular repository is actually maintained. That evidence now exists, in six documents derived from the
SquadOps record:

| Document | What it supplies |
|---|---|
| `maintainer-agent-capabilities.md` | every ability the work requires, each tiered `L` / `L+` / `F` |
| `maintainer-work-archetypes.md` | twenty-one shapes the work takes, each tiered, with its bounding proof |
| `maintainer-interface-handoff-contracts.md` | thirteen recurring handoffs and the seven contracts worth formalizing |
| `maintainer-lessons-learned.md` | what the repository learned by failing |
| `nostromo-maintainer-evaluation-framework.md` | how to tell whether the crew actually works |
| `nostromo-approach-feedback.md` | a read of the current Nostromo design against all of the above |

This document turns that evidence into an operating model and a commissioning plan.

### 1.1 The boundary, restated

> SquadOps' internal agent collaboration architecture is the system being maintained. It is not the template
> for the Nostromo maintainer crew.

SquadOps has a squad: agents it orchestrates inside a cycle, with its own gates, profiles and verdicts.
Nostromo has a **crew**: seven agents that develop the repository SquadOps lives in. The two designs share a
repository and nothing else. Where this document uses a word that exists in both — *gate*, *verification*,
*evidence* — it means the crew's, unless it names a SquadOps artifact explicitly.

The capabilities document states the same exclusion in its own terms, and it is the reason that document
tiers by *cost of being wrong* rather than by resemblance to any SquadOps role.

### 1.2 What this document is not

It is not a redesign of SquadOps. It proposes no change to SquadOps architecture, governance, cycles, gates
or agents. Every change it proposes is to Nostromo: its roles, contracts, lifecycles, harness bootstrap,
configuration files and commissioning gates. The only things it asks of the SquadOps repository are labels,
issue shape conventions, branch namespaces and rulesets — all of which the repository already uses in some
form, and none of which alter what SquadOps does.

### 1.3 Amendments to NOSTROMO-0001

Six changes. The first five are argued in §2; the sixth is scope definition rather than reversal and is argued in §10A.

| Spec section | Current text | Amendment | Reason |
|---|---|---|---|
| §11.6 Brett | Brett owns "failure classification" and "QA conclusions" | Brett owns bounded implementation, deterministic execution and evidence **collection**; Brett never concludes | every conclusion verb in §11.6 is tiered `F` by the capabilities document, and the record's four delegation failures were all frontier delegates concluding in the confirming direction |
| §11.3 Ripley | "Ripley MUST NOT be the primary implementation engineer for work Ripley designed" | unchanged for Lane A (design work); does not apply in Lane B (findings), where the investigator implements | cross-layer tracing is the archetype where the trace *is* the fix's specification, and where every rework in the record clusters |
| §11.2 Ash | Ash owns "exploratory discussion, idea expansion, external precedent research"; hosted on the Mac; "does not own production code"; no repository access | Ash is the **Science Officer**: owns proof infrastructure, corpus measurement and evaluation; hosted on the **Spark** with a worktree and a repository identity scoped to `tests/**` | Ash's marginal cost is zero and Parker's is scarce, so the free frontier-capable agent held the least work; and the capabilities document's Verifier cluster, "owns whether a check can fail", had no owner |
| §11.7 Lambert | Lambert "maintains sources used by NotebookLM" and instructional summaries, with no stated mechanism or access | scope defined: the source-manifest system (§10A.3), a read-only SquadOps checkout, write access to `education/` in the Nostromo repo, and a closed-over-living rule for what gets built | "maintain the instructional surface" is not implementable as written, and the naive implementation multiplies unguarded derived content, which drifts invisibly |
| §14 Lifecycle | one sixteen-state ladder | two lanes: Lane A (design) keeps the ladder; Lane B (finding) gets its own nine states | `fix` is 381 of 935 merged PRs against `feat` 173; 263 of 535 issue bodies cite a live cycle id |
| §10 Roster | seven agents, Brett capability `verification` | seven agents unchanged; Brett's capability becomes `bounded_implementation` plus `evidence_collection`; three new capabilities are routed | the verification capability splits at the `L`/`F` line and cannot be held by one role |

No other section of NOSTROMO-0001 changes. The architecture principles, the topology, the identity model,
the budget boundaries, the record-versus-workbench rule and the owner-authority list all survive the
evidence intact, and in several places the evidence is a direct vindication of them.

---

## 2. Where the evidence changed the design

Six disagreements between the current Nostromo design and the SquadOps record. Each states the record's
position, the current design's position, and the recommendation. The evidence documents are treated as
evidence, not authority: two of the six end with the current design substantially preserved.

### 2.1 Brett concludes — resolved against the current design

**Current design.** NOSTROMO-0001 §11.6 gives Brett "failure classification", "regression verification" and
"QA conclusions", on local Qwen3.6 35B-A3B, with production edit and commit denied
(NOSTROMO-PLAN-0001 §11.11).

**The record.** Every conclusion verb in that list is tiered `F`. Capability 5.4 (re-run the same invocation
before judging whether a red pre-existed) and 5.5 (distinguish a failure *caused* by the change from one
merely *revealed* by it) are frontier because a wrong answer is invisible and propagates. The allocation
note is explicit: *anything concluding "clean", "green", "passing" or "safe" is frontier — or returns raw
evidence for a frontier model to conclude from.* The four delegation-era failures in the tracker — probes
that never ran read as data, six merges read on three required checks while a non-required job was red, a
chain released before the rounds were read, a heuristic evidence instrument falsified within the hour —
were all committed by *frontier* delegates, in the confirming direction. A bounded model is not proposed
for those classes because a stronger one already missed them.

**Recommendation.** Invert Brett. He stops being the verification conclusion-maker and becomes a **local-model
supporting engineer**: bounded implementation against a written contract, the tests and guards that belong to
his own change, deterministic execution, evidence collection, and escalation the moment the task stops being
bounded. He runs checks and reports raw output with its paired control. He never says the word "clean".
His PRs are reviewed by Parker.

This is a larger change than it looks. It moves Brett from read-only to repository-writing, which means a
GitHub App identity, a branch namespace, rulesets, and a permission profile that permits edit, commit and
push. Those are listed in §45.

### 2.2 The lifecycle is feature-shaped — resolved against the current design

**Current design.** One sixteen-state ladder from `IDEA_CREATED` to `CLOSED`, which is the SIP ladder.

**The record.** `fix` is 381 of 935 merged PRs; `feat` is 173. Of 535 issue bodies, 263 cite a live cycle id,
115 a counted roll or set record, 61 a shakeout or diagnostic. The live cycle is the dominant source of work,
ahead of CI and review combined. The SIP ladder is real and is where the architect/implementer separation
landed cleanly — but it describes the minority of the work.

**Recommendation.** Two lanes, §23 and §24. Lane A keeps the ladder essentially as written. Lane B is nine
states with two legal loops. A defect does not climb the SIP ladder to get fixed, and a finding that turns
out to need a rule rather than a fix crosses into Lane A at a named transition.

### 2.3 Ripley never implements what Ripley designed — partially reversed

**Current design.** A flat prohibition in §11.3 and in `instructions.md`.

**The record.** Correct for the SIP ladder: the composition-roots standard and the 1.7.5 recovery extraction
map were both "architect writes the acceptance source, implementer builds to it", both owner-reviewed before
the first constrained PR, and both landed clean. Wrong for the seam chain: cross-layer tracing is the
archetype where "the fix's blast radius was unknown until the trace was complete", where the PR bodies *are*
the investigations, and where a six-hop chain ran as one engineer over one week. Splitting investigation from
implementation across a routed handoff adds a boundary exactly where the work needs continuity.

**Recommendation.** Keep the prohibition in Lane A. Suspend it in Lane B, where the rule becomes: **whoever
holds the trace holds the fix.** Normally that is Parker. Ripley may hold a Lane B chain end to end when the
trace is an architecture question — and if the fix would establish or change a rule, the item crosses into
Lane A and the prohibition returns with it (§24.4).

### 2.4 The measurement function has no home — resolved by assignment, not a new role

**Current design.** `OBSERVING` is one state-word. No role owns pre-registration, preflight, roll-boundary
reading, or supersession.

**The record.** This is the most formal process in the repository: twelve pre-registrations, twenty-nine set
configs, a driver whose preflight refuses on eight conditions. Capabilities 9.10 through 9.15 are all `F`.
The archetype document splits archetype 11 explicitly: preflight, detached launch, gate approval with the
pre-registered constant, collection and render are `L`/`L+` and *have already run four overnight
delegations*; every reading and every supersede call is `F`.

**Recommendation.** Do not create a role. Split the function along the line the record already ran it on:
Mother owns mechanics and collection, Ripley interprets, the owner rules on void, reset and supersession.
§37 states the split, and states the evidence that would justify promoting a dedicated Measurement Steward
later. Note that owner-reserved supersession is not an invented gate: a counted roll that may be void or a
reset already stops the set for the owner in the record.

### 2.5 Dallas is the missing function — confirmed, and extended upstream

**Current design.** Dallas reviews Ripley's design, and "MAY also perform a final independent review after
implementation/QA where warranted."

**The record.** Review has been a stamp: 807 of 935 merged PRs carry a one-word review, `reviewDecision` is
empty on all 935, and 40 PRs have any comment. Substantive review happened on plan revisions and SIP drafts,
before implementation, not on diffs after it. Rework clusters "where a change's evaluation surface had more
than one reader and only one was tested."

**Recommendation.** Confirm Dallas, and make the upstream half primary rather than optional. Dallas's most
valuable output is a seam table demanded before an implementation exists, not an objection to a finished
diff. §11 sets risk triggers; §13 sets what Dallas returns. The $27 cap forces this discipline anyway:
Dallas cannot review every PR, so he must review the ones where the record says rework lives.

### 2.6 The handoff envelope is right but empty — confirmed, and filled

**Current design.** NOSTROMO-0001 §15 defines a generic handoff envelope: work item, state, GitHub refs,
Buzz thread, capability requested, request, acceptance criteria, unresolved issues, return condition.

**The record.** The envelope is correct and deliberately generic. What it lacks is payloads. Four of the
seven contracts the record names — deploy identity, measurement pair, ruling record, standing delegation —
have no counterpart anywhere in the Nostromo documents, and the task card exists only as a plan-row shape.

**Recommendation.** Keep the envelope exactly as it is, as the transport. Add seven payload contracts that
travel inside it (§15 to §22). The envelope says *who is being asked for what*; the payload says *what they
need in order to answer without rediscovering architecture*.

### 2.7 Ash was read-only for no derived reason — resolved against the current design

**Current design.** Ash is a research and ideation role on the Mac, with no repository access, no GitHub
identity, and no place in either lifecycle lane after the exploration phase.

**The arithmetic.** Ash's marginal cost is zero: the $20 subscription is spent whether Ash works or not.
Parker's $65 is metered, scarce, and already carrying two jobs — implementing what has no table, and
producing tables for Brett — which §55's OD-3 flags as an open capacity question. The crew gave its one
free frontier-capable agent the least work and its scarcest agent the most.

**The constraints turned out not to be real.** Ash runs a cloud model, so an Ash process on the Spark is a
thin client costing tens of megabytes rather than the gigabytes the interlock exists to manage. The required
regression check runs the unit suite, which does not need the live stack, so a repo-facing Ash can produce
the evidence a PR body requires. A GitHub App for Ash is the same shape as Parker's. The read-only rule was
inherited from the specification's framing of Ash as a conversational thinking partner and was never
re-derived against the work.

**The one real constraint** is that a consumer subscription is rate-limited per window, so Ash is
interruptible in a way a metered agent is not. That is an argument about *which* work Ash holds, not about
whether Ash holds any: Ash takes work that tolerates pausing and never sits on the critical path of a merge.

**The function that had no owner.** The capabilities document proposes seven role clusters, one of which is
a **Verifier** who "owns whether a check can fail". This operating model dissolved it: execution went to
Brett and authoring was scattered between Parker and Brett. Seven of the nine capabilities in that domain
are tiered `F` — naming the bug a test catches before writing it, entering at the live caller rather than
the seam, pairing every assertion with a control, proving a new test fails against the pre-fix tree,
deriving a guard from the owning module rather than a hand-listed set, tabling every seam before binding a
check.

**Recommendation.** Ash becomes the Science Officer and owns proof, constructively (§9). Ash moves to the
Spark with a worktree and an identity path-scoped to `tests/**`, which yields a structural property worth
having on its own: **the author of a proof cannot modify the thing being proved.**

---

## 3. The organizing principle

One sentence from the archetype document does more work than any other in this design:

> The frontier's job is to produce that table, and the bounded engineer's job begins when it exists.

"That table" is whatever makes a change's evaluation surface legible: a seam table, a reviewed extraction
map, an AST census, a stated rule with its allowlist and the commit its guard must fire on, a stated producer
with its unaskable state. Every archetype in the record carries a split tier keyed on whether that artifact
exists yet. Nothing in the record arrived pre-bounded: *every* mechanical change was bounded by a map, a
guard, a census or a plan row first.

That gives the crew its shape:

```text
Ripley and Dallas      produce and stress the table
Parker                 produces the table for the work he delegates, and does the work that has none
Brett                  begins when the table exists, and stops when it turns out not to
Mother                 checks that the table is present before routing, and never reads it
The owner              rules where the table itself is in question
```

The Bounded Task Card (§16) is that table, written down. It is the central mechanism of this operating model,
and the one contract the record says does not yet exist in any form.

A corollary the record states twice, and which this design treats as inviolable:

> Every delegation needs a paired control. A subordinate reporting success on a task it could not have failed
> is the same defect as a test that can only pass.

---

# Part I — The Crew

## 4. Ripley — Architect and technical lead

**The question Ripley answers.** How should this fit into SquadOps, and is the rule we are about to
establish the right one?

Ripley owns high-cost technical judgment. Frontier reasoning is spent here on removing ambiguity before it
becomes an expensive edit.

**Owns.**

- Architecture and technical direction for SquadOps changes the crew makes.
- Feature framing: turning an owner objective or an Ash-converged idea into a bounded technical problem.
- Interpreting existing SquadOps SIPs, plans and architecture standards, and reading accepted SIP text as
  specification rather than as background.
- Deciding whether work requires a new design artifact — a standard, a map, or a SIP — and authoring it.
  The design artifact is declared the **acceptance source**, distinct from the plan that sequences it.
- Producing the *table* that bounds delegable work at the architecture level: the enumerated surface, the
  rule's boundary, its allowlisted exceptions, what it deliberately does not decide, and the proof each
  implementing PR must carry.
- Resolving architectural ambiguity before implementation begins.
- Measurement interpretation where the conclusion is high-cost (§37).
- Resolving escalations from Parker, Dallas or Mother that are architectural rather than owner-reserved.
- Deciding whether historical evidence supports changing an established rule, and recording that decision
  where the rule lives.

**Does not own.**

- Being the implementer of record for work Ripley designed, in Lane A. The separation landed cleanly twice
  in the record and is kept.
- Rewriting Dallas's objections into agreement. Dallas is independent input, not a subordinate approval step.
- Product acceptance. SquadOps governance and the owner accept; Ripley proposes.
- Routine implementation volume. Ripley's cap is $27 against Parker's $65 for exactly this reason.

**When Ripley may stay through a fix chain.** The Lane A prohibition does not apply in Lane B. Ripley may
hold a finding from investigation through implementation when **all** of the following hold:

1. the trace is an architecture question — the defect is that a rule is missing, contradicted, or applied at
   the wrong layer, rather than that code is wrong at a known layer;
2. the fix is bounded by an existing accepted artifact, so Ripley is building to a rule that already exists
   rather than to one Ripley is inventing in the same turn;
3. Dallas reviews the resulting PR, because the usual independence provided by the Ripley/Parker split is
   absent and has to come from somewhere.

If the fix would *establish or change* a rule, the item crosses to Lane A (§24.4), Ripley writes the design
artifact, and Parker implements it. Ripley never both writes a new rule and lands the first change
constrained by it.

**Escalates to.** The owner, for anything on the owner-reserved list (§12). Nothing else — Ripley is the
terminal technical authority inside the crew.

---

## 5. Dallas — Independent adversarial assurance

**The question Dallas answers.** What is wrong with this, what would make the proof falsely reassuring, and
what has not been looked at?

Dallas is the function the SquadOps record most visibly lacks, and the record says where the value is. Rework
clusters where a change's evaluation surface had more than one reader and only one was tested. That surface
is cheapest to table *before* implementation. So Dallas runs upstream by default and downstream by risk.

### 5.1 Upstream Dallas

For work that trips a risk trigger (§11), Dallas challenges the technical direction **before implementation
begins**. The pattern:

```text
Ripley proposes
      ↕
Dallas challenges
      ↓
Ripley resolves and records the disposition in the canonical artifact
      ↓
implementation begins
```

Dallas challenges:

- problem framing, and whether the problem as stated is the problem;
- assumptions, and which of them are load-bearing;
- causal claims — "read from the code" versus inferred;
- evidence quality, and whether a cited artifact says what it is claimed to say;
- missing seams and missing consumers: who else evaluates this criterion, on what tree, with what already
  true;
- proposed acceptance criteria, and whether the proof can actually fail;
- likely silent-failure modes, and what a falsely reassuring green would look like here;
- whether the design is unnecessarily broad, and what the smallest version that still holds the invariant is;
- whether an existing architecture rule is being contradicted without amendment;
- whether the proposed task is bounded enough to delegate — that is, whether the table exists.

Dallas does **not** rewrite the proposal into Dallas's preferred design. A review that redesigns scores zero
on proportionality in the evaluation framework even when the detection is correct.

### 5.2 Downstream Dallas

Dallas independently reviews Parker-authored work where risk warrants, and is the default independent
approver for significant Parker work. Dallas reviews against repository state, not against the implementation
narrative: the claim in the PR body is a hypothesis about the tree until an artifact says otherwise.

Dallas evaluates:

- whether the implementation actually satisfies the accepted invariant, not a neighbouring one;
- what evidence in the body could be falsely reassuring — a regression count from a subset presented as the
  whole gate, a symbol import presented as a live call, a seam test presented as a wiring test;
- whether neighbouring seams and callers are accounted for;
- whether the proof is broader than the implementation, or narrower;
- whether there is hidden behaviour change inside a nominal move;
- whether the PR preserves rationale and scope, and whether a removal answers the mirror rule.

### 5.3 What Dallas does not do

Routine implementation. Dallas may write a throwaway probe or a failing test to demonstrate an objection, in
Dallas's own worktree, at a detached commit, and attaches it as evidence. Dallas does not push it to the
branch under review and does not fix the defect.

### 5.4 Review outcome vocabulary

Every Dallas return, upstream or downstream, classifies each point into exactly one of:

| Outcome | Meaning | Consequence |
|---|---|---|
| **Blocking objection** | the work as proposed or landed is wrong, unprovable, or contradicts an accepted rule | must be dispositioned in the canonical artifact before the work proceeds or merges |
| **Non-blocking concern** | a real weakness that does not justify stopping | recorded; may be accepted as-is with a reason |
| **Unresolved question** | Dallas cannot determine the answer from available evidence | must be answered or explicitly deferred with a named owner |
| **Approved** | no blocking objections remain | the work may proceed |
| **Returned for artifact** | the claim may be true but the evidence does not establish it | the PR comes back with the artifact, not with a re-assertion |

*Returned for artifact* is a deliberate addition to the vocabulary in `instructions.md`. The contracts
document is explicit that a reviewer who cannot trust the evidence as written returns the PR "for the
artifact, not the answer", and without a named outcome for that the reviewer either re-runs the work or
waves it through.

---

## 6. Parker — Primary engineer

**The question Parker answers.** How do we build this correctly, and what part of it can be safely handed to
Brett?

Parker is the main engineering owner and the largest metered consumer. Parker holds two jobs the record
treats as inseparable from each other: doing the work that has no table, and producing the table for the work
that can be delegated.

**Owns.**

- Investigating defects, including cross-layer traces where a fact is computed at one seam and never
  delivered at another.
- Tracing behaviour across layers to every consumer, and to the next hop.
- Implementing difficult changes.
- **Continuity**: holding diagnosis and implementation together where they are inseparable.
- Decomposing approved feature work into implementable slices.
- Determining whether a slice is suitable for Brett — that is, whether its bounding proof exists.
- Constructing Bounded Task Cards (§16).
- Reviewing Brett's pull requests against the card.
- **Reclaiming** work when a delegated task turns out not to be bounded.
- Producing change evidence (§17) for Parker's own work.

**Does not own.**

- Redefining accepted architecture during implementation. A material deviation returns to Ripley, and where
  required to the owner.
- Approving Parker's own work. Independence comes from Dallas or the owner.
- Concluding measurement readings (§37).

### 6.1 Feature work

```text
Ripley and Dallas establish the accepted technical direction
        ↓
Parker implements, or decomposes into cards and implements the remainder
```

Parker does not re-derive the rule. Parker does re-verify the premise against current `main`, because the
record shows design artifacts go stale against a moving tree and one issue was filed on a premise that had
already changed.

### 6.2 Defect work

```text
Parker investigates
    ↓
Parker identifies the causal seam, to file and line
    ↓
Parker implements at the layer that owns the defect
    ↓
Parker proves it at the wiring, not only at the seam
```

No artificial handoff is inserted between investigation and implementation. This is the single most
important departure from the current lifecycle, and it is what the record's six-hop chains and clustered
rework argue for. Mother tracks the item's state through all four steps without changing its owner.

### 6.3 Reclaiming delegated work

Parker reclaims a card when Brett escalates, and also unprompted when review shows the card was wrong.
Reclaiming is a normal outcome, not a failure of either agent: a card that turns out not to be bounded is a
framing defect, and the evaluation framework classifies it as such precisely so that it is never read as
evidence about Brett's capability.

---

## 7. Brett — Supporting engineer, local model

**The question Brett answers.** Does the tree now match what the card said it should, and here is the raw
output that shows it.

This is a redefinition. Brett was the QA conclusion-maker; Brett becomes a bounded implementer and collector.
The reason is in §2.1 and it is not about model strength: the conclusions previously assigned to Brett are the
exact class of judgment that frontier delegates got wrong in the record, in the confirming direction.

**Owns.**

- Bounded implementation against a Bounded Task Card, inside Brett's own worktree and branch namespace.
- Tests and guards that belong to Brett's own change.
- Deterministic verification execution: the regression gate, targeted suites, architecture guards, named
  replays, lint and format as separate invocations.
- Evidence collection: running the thing, gathering the rows, extracting the fields, returning raw output
  with its paired control.
- Mechanical changes against an existing pattern where the pattern is named and a guard enforces it.
- Escalation the moment the task stops being bounded.

**Does not own — and must never state.**

Brett must not make any of the following claims. Each is `F` in the capabilities document, and each is the
shape of a recorded failure:

- "the system is safe", "the build is clean", "the release is green";
- "this regression is pre-existing" — re-running the same invocation and judging causation is capability 5.4
  and 5.5, both frontier;
- "the counted verification set should be accepted";
- "this measurement finding does not supersede the deploy";
- "the probes passed" where the probes' own execution was not independently demonstrated.

Brett returns the output and says what was run. Somebody else concludes. This is not a statement about
Qwen's ability; it is a statement about which errors are invisible.

**Brett's reporting shape.** Every Brett return carries the command, the raw output or its artifact path, the
paired control and what it did, and one of: *the card's proof ran and passed*, *the card's proof ran and
failed*, or *I could not run the card's proof, for this reason*. The third is an escalation, not a result.

**Review.** Brett's pull requests are reviewed and approved by Parker. Dallas reviews Brett's work only when
the change lands on a seam that trips a risk trigger, which should be rare by construction: if it trips a
trigger, it probably should not have been delegated.

---

## 8. Mother — Coordination and control plane

**The question Mother answers.** What happens next, who holds it, and is the artifact it needs actually
present?

Mother owns deterministic coordination. Mother does not own technical judgment, and the design deliberately
moves as much of Mother's behaviour as possible out of model inference and into configuration, checks and
scripts.

**Owns.**

- Routing work items by capability, resolved from `crew/capabilities.yaml`, never from prompt assumption.
- Maintaining crew state: the lane, the state, the active owner, the links.
- **Checking that required handoff artifacts exist** — presence and shape, never content quality.
- Initiating the right crew participant with the right context.
- Tracking lifecycle transitions and recording them durably.
- Watching GitHub and Buzz events: PR opened, checks completed, review submitted, merged, issue closed.
- Launching predefined verification mechanics: the preflight, the detached launch, the collection, the render.
- Collecting artifacts and attaching them to the work item.
- Enforcing scheduling and interlock rules, including the Spark mode interlock (§36).
- Preserving resumable state across process restarts.
- Surfacing blocked and escalated work to the owner.

**Does not own.**

- Substituting Mother's judgment for Ripley's, Parker's or Dallas's. If Mother has an opinion about a
  technical question, Mother routes it.
- Reading a measurement. Mother gathers the record; Mother does not say what it means.
- Deciding that a card is good. Mother checks that the card's mandatory fields are *present*; Parker and
  Dallas judge whether they are *right*.
- Breaking diagnostic continuity. When Parker holds a Lane B trace, Mother updates state and does not
  reassign, does not inject a handoff, and does not request a status narrative mid-trace.

**The distinction that matters most.**

```text
Mother can gather measurement evidence.
Mother does not decide what the measurement means when that decision is frontier-tier.
```

**Mother's presence check.** Before routing a handoff, Mother verifies that the payload contract required by
that transition has its mandatory fields present. A handoff missing a mandatory field is returned to its
producer with the field named. This is a deterministic string-and-structure check, implementable as a script,
and is the single highest-value mechanical thing Mother does: the record's delegation failures are each
explained by exactly one absent field.

---

## 9. Ash — Science Officer: proof, evidence and evaluation

**The question Ash answers.** Can this claim be trusted, and what would it take to prove it false?

Ash owns **proof, constructively**. Where Dallas asks whether a proof can fail, Ash builds the proof that
can. Where Ripley decides what a rule should be, Ash measures what that rule would do to the code that
already exists. Where the crew claims a capability, Ash builds the benchmark that tests the claim.

Ash is resident on the Spark with a worktree, a GitHub identity, and a repository path scope of `tests/**`.
The scope is the point: **Ash cannot make a test pass by changing the code it tests.** That is the mirror of
Brett's bounded scope and it makes Ash's proofs structurally independent of the implementation.

### 9.1 What Ash owns

**Proof infrastructure.** The reusable machinery every change is proven against: architecture guards and
ratchets under the repository's guard directory; replay harnesses over stored artifacts; fixtures and golden
corpora; the paired controls a guard needs before it may gate anything. A guard Ash writes carries the commit
it must fire on, and Ash demonstrates it firing there before it is trusted to pass.

**Corpus measurement before a rule lands.** When Ripley is about to write a rule, Ash measures what it would
do to the tree as it stands, and reports the count. The record settles the value of this. A check measured
against nine already-accepted suites first showed that the obvious form would have wrongly flagged seven of
them, so the rule was written differently and held. Two checks that were not measured first were reverted,
one of them as an unvalidated rejection gate sitting in the path of a measurement.

This is also what makes Dallas's upstream challenge evidential rather than rhetorical. Dallas asks whether a
proof can fail; Ash can answer with a number across the existing corpus.

**Evaluation.** The benchmark and everything that makes it honest: case construction; the admission proof
that every oracle fails on the broken tree and passes on the clean one; blinded scoring of the quality
dimensions; classification of every non-passing run; and the graduation ladder's arithmetic (§44.3). Ash is
the independent evaluator the evaluation design requires, because Ripley interprets measurement and holds
architecture, Parker and Dallas are the subjects being scored, and Mother may not conclude.

**Precedent and decision archaeology.** Reconstructing a prior decision and its reason before anyone
contradicts it. This is archival work across the proposal corpus, plans and records, and it is a different
skill from reading current code. Ripley reads the tree as it is; Ash reads how it came to be that way. The
failure this prevents is on record: three falsified premises and four unbuilt dispositions survived only in
a plan superseded at a release cut, after which the proposal would have been the sole surviving description
of a design it no longer matched.

**External evidence.** Standards, protocols, library and vendor investigation, ecosystem facts that postdate
training, and comparisons where SquadOps is choosing between external options. Findings carry their sources
with the date read, because external facts expire.

### 9.2 What Ash does not own

- **Review of work in flight.** That is Dallas. Ash builds proofs; Ash does not adjudicate pull requests.
- **The test for someone else's specific fix.** A fix and its proof are coupled, and splitting them would
  insert a handoff into exactly the chain §24.2 protects. The implementer writes the test for their own
  change, using the infrastructure Ash builds.
- **Production code.** Ash's path scope is `tests/**`. A proof that requires a source change goes to Parker.
- **Anything on the critical path of a merge.** Ash is rate-limited by subscription and must never be the
  thing a merge waits on.
- **Deciding whether an oracle was right.** When a benchmark result turns on whether the oracle itself was
  wrong, that is Ripley's or the owner's call, not the evaluator's.

### 9.3 Why this role and not a second implementer

A second implementer would add another queue for Parker to review and would sit on the merge path, which the
rate limit makes a poor fit. Proof work compounds instead. **The bounding proof is the single field that
decides whether work can be delegated to Brett at all**, so an agent that manufactures proofs is
manufacturing delegability, converting free subscription capacity into local-model throughput.

### 9.4 The dependency this creates, and its release valve

If Parker needs a replay harness that does not exist, Parker now has someone to ask — and something to wait
for. Ash owns the *standard* for proof infrastructure, not a monopoly on writing it. A blocked implementer
builds what they need and Ash reviews the shape afterward. Ash being unavailable must never stop work.

### 9.5 What is retained

Ash remains the owner's exploratory thinking partner in conversation. Nothing about the ideation character
is lost; what changed is what Mother *routes* to Ash. Ash still returns durable artifacts rather than
conclusions that live only in a Buzz thread.

Ash's subscription-backed configuration must never fall back to metered API usage, which is enforced by the
absence of any API key in Ash's environment.

---

## 10. Kane — an experiment slot, not a crew member

Kane is **not** added to the roster, does not appear in `crew/manifest.yaml` as an agent, and holds no
capability in `crew/capabilities.yaml`.

Kane is a name reserved for a harness experiment: a second harness bound to the *same* local model Brett
uses, so that a comparison isolates harness behaviour rather than confounding harness with model. The
evaluation framework requires exactly this design — a 2×2 of two harnesses by two models on one case set, so
that a harness effect and a model effect separate by the interaction term rather than being inferred from a
single pair.

When that experiment runs, Kane is a launcher profile and a benchmark configuration. If a harness proves
better on the outcome-class distribution, the result is that **Brett's harness changes**. It does not create
an eighth crew member.

The record gives no evidence for a Kane-shaped role, and the design principle stands: do not create a
permanent role to justify a persona.

---

## 10A. Lambert — Knowledge projection, and the source-manifest system

Lambert keeps the character NOSTROMO-0001 §11.7 defines: the Google knowledge projection, $0 incremental,
off the critical engineering path, and explicitly unable to block SquadOps development by being unavailable.
With Ash moved to the Spark (§9), Lambert is the crew's only Mac-resident agent, which suits a role whose
unavailability is designed to cost nothing.

What this section adds is scope and a mechanism, because "maintain the instructional surface" is not
implementable as written and the naive implementation is actively harmful.

### 10A.1 The problem with educational material

Derived material is unguarded content. A guide is never run, so when it drifts nothing fails — it simply
becomes a confident description of a system that no longer exists. The record names this failure three ways:
version and documentation drift recurred three separate times despite a written rule; falsified premises
survived only in a plan that was superseded at a cut; and the governing lesson, *what a test enforces stays
true, what discipline enforces drifts.*

Producing many forms of material multiplies that surface. Ten guides is ten things that rot invisibly.

### 10A.2 The rule that makes it safe

**Prefer material about things that are closed.** A closed release line's plan, record, cut record and
changelog entry are final. Material built from them cannot go stale, needs no refresh, and needs no
automation. This matters practically as well as theoretically: the programmatic notebook API is a Google
Cloud Enterprise product, not the consumer surface the existing subscription carries, so any design that
depends on continuous sync depends on a recurring manual step — and the record's natural experiment on
recurring manual steps is that the one unguarded step was missed twice by someone holding the checklist.

Where material must cover something living, it carries its pin and its date visibly, so staleness is legible
rather than invisible. That is the three-state readout lesson applied to documentation: a reader can tell
current from stale from unknown.

### 10A.3 The source-manifest system

One manifest per topic, in the **Nostromo** repository under `education/manifests/`. It lists the canonical
sources and the commit they were taken at. Everything generated from it carries the manifest's id and date.
Generated formats are **regenerated, never hand-edited**, which turns drift from a discipline problem into a
build problem.

```yaml
id: maintainer-lessons
title: What this repository learned by failing
audience: owner
status: living            # living | frozen
source_repo: squad-ops
source_commit: <40-hex>   # the pin; the whole point of the manifest
captured: 2026-09-11
sources:
  - path: docs/...        # canonical, in-repo
  - url: https://...      # external, with the date read
    read: 2026-09-11
formats: [audio-overview, study-guide, timeline, briefing]
regenerate_when: the source commit moves, or a listed source is amended
```

- **`frozen`** means the sources are final and the manifest is never refreshed. A closed release line.
- **`living`** means it tracks a moving corpus and is refreshed on a schedule (§10A.5).

This obeys the rule the record paid for twice: **derive, do not author.** A guide that restates a fact the
system already holds is a second copy that will eventually disagree with the first. The manifest points at
the fact; it does not repeat it.

### 10A.4 What gets made, and what does not

| Build | Why it is safe |
|---|---|
| The maintainer lessons corpus | twenty-seven lessons already structured as rule, what happened, how it failed, where it is encoded; it is about principles, so it barely drifts. The highest-value first artifact |
| One frozen manifest per closed release line | final by the time it is built; zero maintenance forever |
| Architecture standards, each paired with its motivating failure | standards carry their audit commit already, so the manifest is nearly free |
| The roadmap's ordering and what gates what | slow-moving and genuinely hard to reconstruct |

**Never:** current code structure, open issues, in-flight pull requests, operational procedure a reader
might act on. Those live in the repository where they are guarded, and a stale copy of them is worse than
no copy.

### 10A.5 Lifecycle and the refresh step

A release cut is already a guarded procedure. Nostromo hangs one step off it, on the Nostromo side rather
than in SquadOps' own checklist: when a line cuts, **freeze that line's manifest** and **re-pin every
`living` manifest, then regenerate its formats.** Living manifests are refreshed nowhere else, so there is
exactly one moment to remember and it is attached to a procedure that already has a checklist.

### 10A.6 Access, and the boundary

Lambert needs a **read-only** SquadOps checkout to curate manifests, and write access to the Nostromo
repository for `education/`. Lambert gets **no SquadOps write access of any kind**, because the role is a
projection and a projection does not modify its source.

**Lambert's artifacts are never a source.** If a decision ever rests on what a guide or a notebook said,
there is a stale unguarded surface competing with GitHub. The division against Ash (§9) is clean and
deliberate: Ash answers questions about open work and live precedent, grounded in the current tree with
citations; Lambert projects closed work into a durable reading surface. Two oracles answering the same
question with different freshness is exactly the shape to avoid.

### 10A.7 Not on the 1.8 path

Lambert has no place in either lifecycle lane, is not part of the commissioning gate (§43), and is not a
dependency of any 1.8 work. Gemini's ACP mode is also the least proven runtime in the crew, which is
tolerable precisely because nothing depends on it. This work is worth doing and must not consume
commissioning attention.

**Scope note.** Start with SquadOps material only. SquadOps is public, so its corpus carries no exposure
question. The Nostromo repository is private and holds the operating model and the maintainer analysis;
putting those into a third-party product is a decision to take deliberately rather than by default, and
little is lost by deferring it, because the corpus that is genuinely hard to hold is SquadOps'.

---

# Part II — Authority and Review

## 11. Risk triggers: when Dallas enters before implementation

Dallas does not review every design. Reviewing everything would exhaust a $27 cap on work with no rework
history and would turn adversarial review into the stamp it is supposed to replace.

Dallas enters **upstream** when the work has any of the following properties. Each trigger is drawn from
where rework actually clusters in the record, and each names the archetype it corresponds to.

| # | Trigger | Why | Archetype |
|---|---|---|---|
| T1 | Introduces or changes an **architecture rule or standard**, or the guard that enforces one | the rule's boundary and its allowlisted exceptions are the expensive part; standards were owner-reviewed before the first constrained PR | 8 |
| T2 | **Binds, removes, or re-weights a check or gate**, or promotes one from reporting-only to blocking | a false positive in a blocking check recreates the unwinnable loop the check exists to end; two well-tested checks bound without a seam table is the record's canonical failure | 4 |
| T3 | Changes **correction or recovery semantics**: what the loop counts, routes, refunds, retries, verifies or carries forward | every one changed a semantic the next roll would be judged by; five were owner rulings | 3 |
| T4 | Changes **evidence or observability semantics**: what a record field means, what a readout reads, what a probe asserts | an instrument that encodes an inference is the class this line keeps finding | 10 |
| T5 | **Cross-layer** change where a value crosses a seam and silence is a possible failure mode | latent for weeks with green CI; found by a live cycle, not by tests | 2 |
| T6 | **Migration or persistence semantics**: schema, a hash, a pin, a frozen surface, anything that changes what a measurement compares against | dropping one column on a table that `init.sql` creates was red in CI's integration job for six merges | 18, 5 |
| T7 | **Security or identity**: authentication, credentials, realm configuration, database role isolation | test isolation broken against the deployment database is faster and greener, and catastrophic | 8.5 |
| T8 | **Broad refactor or extraction** across more than one module, before the map is accepted | the failures are upstream, in framing: an extraction started without a map | 6 |
| T9 | A **finding whose initial diagnosis carries high uncertainty** — the mechanism is inferred rather than read, or a plausible cause has not been ruled out with evidence | a wrong mechanism claim in an issue propagates into a wrong fix | 13 |
| T10 | The work would **contradict an accepted SIP or standard** without amending it | three falsified premises recorded only in a superseded document | 15 |

**Nothing else requires upstream Dallas.** A localized repair at a known layer, a vocabulary sweep against a
landed guard, a dependency recompile after the policy is set, a prompt wording change through the fragment
system — these go straight to implementation. Ripley or Parker may request Dallas voluntarily, and the owner
may require Dallas on anything.

**Who decides a trigger fired.** Ripley for Lane A, Parker for Lane B, at the point the work is framed. The
decision is recorded in the work item as one line: the trigger number, or "no trigger". Mother checks the
line is present, not whether it is right. Dallas may assert a trigger was missed, which is itself a blocking
objection.

**Downstream Dallas** reviews a Parker-authored PR when the same triggers apply, and is the default
independent approver for significant Parker work, where *significant* means: it lands on a seam with more
than one reader, it changes a semantic anything else is judged by, or it is more than a single-file localized
repair. Brett-authored PRs go to Parker, not Dallas, unless a trigger fired — in which case the prior
question is why it was delegated.

---

## 12. The authority graph

```text
Feature / architecture (Lane A)

  Ripley frames
     ↕
  Dallas adversarial challenge          (risk-triggered; §11)
     ↓
  accepted direction, dispositions recorded in the canonical artifact
     ↓
  Parker implements, or decomposes into Bounded Task Cards
     ↓
  Brett implements bounded subwork where a proof exists
     ↓
  Parker reviews Brett; Dallas reviews Parker where risk warrants
     ↓
  owner accepts; merge


Finding / defect (Lane B)

  Finding Record opened (by Mother from an event, or by any crew member)
     ↓
  Parker investigates → diagnoses → implements → proves     (continuity, §6.2)
     ↓
  Dallas challenges the diagnosis where T9 fired, before the fix is built
     ↓
  Parker reviews Brett where slices were delegated
     ↓
  Dallas reviews Parker where risk warrants
     ↓
  owner accepts; merge
```

### 12.1 Pull-request authority

| PR author | Reviewer | Approver | Notes |
|---|---|---|---|
| Brett | Parker | Parker | Dallas only if a risk trigger fired |
| Parker | Dallas where risk warrants, else owner | Dallas is the default independent approver for significant Parker work | Parker never approves Parker |
| Ripley (Lane B continuity, §4) | Dallas | Dallas | mandatory, because the usual Ripley/Parker independence is absent |
| Ripley (design artifact, Lane A) | Dallas, then owner | owner | the artifact is the acceptance source |
| Ash (guard or rule-bearing proof) | Dallas | Dallas | "can this check fail" is Dallas's question and Ash's product |
| Ash (fixtures, replays, benchmark) | Parker | Parker | no rule content; routine proof infrastructure |

**Nobody approves their own work.** This is enforced three ways, in descending order of reliability: a
GitHub ruleset requiring a review from someone other than the author; the launcher refusing to mint a token
for an approval on a PR whose author identity matches; and the constitution. The first is the one that
matters — what a test enforces stays true, what discipline enforces drifts.

**Mechanical merge** is separate from approval. Merge into `main` is owner-reserved by default (§13), and may
be delegated to Mother for a defined class of work under a Standing Delegation (§22). Mother merging is a
mechanical act on a recorded approval, never a judgment: Mother verifies the approval exists, every CI job is
green including the non-required ones, and the closure reference resolves — then squashes.

---

## 13. Owner-reserved authority

Derived from the record, not invented. Each item below appears in `instructions.md`, in NOSTROMO-0001 §16, or
in the SquadOps record's own standing escalation list, and most appear in all three.

The owner exclusively decides:

1. **Credentials and secrets** — provisioning, rotation, placement.
2. **`sudo` and anything requiring it** on any host.
3. **Destructive host actions** — image or volume pruning, database drops, anything one flag from data loss.
4. **Docker Compose, `init.sql` and Dockerfile edits.** Every such edit in the record carried the owner's
   recorded OK, on the PR.
5. **Model and deployment pin moves** — `GENERATOR_VERSION`, contract versions, frozen surfaces, expanded-tree
   hashes, regenerated goldens and fixtures. Each is a deliberate, classified, owner-cleared act.
6. **Release and promotion decisions** — the cut, the tag, SIP promotion, the package capture.
7. **Anything that changes what a measurement compares against** — a reset, a void ruling, a supersession
   call, an instrument correction during an open set, a scoring change mid-window.
8. **Material architectural acceptance**, and unresolved Ripley/Dallas disagreement.
9. **Budget reallocation**, and provider or model changes that materially alter cost or capability.
10. **Anything outward-facing** — anything that leaves the tailnet or the two repositories.
11. **Merge into SquadOps `main`**, unless delegated for a named class under a Standing Delegation.

Two things are deliberately **not** on this list, because the record does not support them: routine branch
creation and PR opening (the night rules permit both without asking), and filing issues (permitted, and the
record shows unfiled findings are the failure mode, not filed ones).

**Escalate decisions, not chores.** A run that stops on a routine item is classified `WRONG_ESCALATION` in
the evaluation framework and scores zero on escalation judgment. Stopping is not free.

---

## 14. Preventing the failures review is supposed to catch

Three mechanisms, in order of reliability.

**Deterministic.** GitHub rulesets on `squad-ops`: per-identity branch namespaces, path restrictions per
namespace, required reviews from a non-author, required status checks including the non-required jobs the
record shows being missed, and a bypass list that does not contain the crew. Exported as JSON to
`infrastructure/github/rulesets/` so the boundary is reconstructable.

**Launcher-enforced.** Preflight refuses to start an agent whose credentials, identity, worktree, allowlist or
budget boundary is wrong. The existing launcher contract already does most of this; §45 adds the checks the
new roles need.

**Constitutional.** `instructions.md`, which is the weakest of the three and is treated as the fallback, not
the mechanism. The record's own verdict applies: what a test enforces stays true; what discipline enforces
drifts.

---

# Part III — Contracts

## 15. The contract model

NOSTROMO-0001 §15 defines a handoff **envelope**: work item, lifecycle state, canonical GitHub references,
Buzz thread, capability requested, explicit request, acceptance criteria, unresolved issues, return condition.
That envelope stays exactly as written. It is the transport.

This part defines seven **payloads** that travel inside it. The envelope says who is being asked for what;
the payload is what they need in order to answer without rediscovering architecture.

Three rules govern every contract below.

**The record rule.** GitHub holds the canonical content. Buzz holds a reference and the conversation around
it. Nothing accepted lives only in Buzz history. This is NOSTROMO-0001's rule and the SquadOps record's
independently — a decision recorded only in a surface that is later superseded is a decision that disappears.

**The presence rule.** Mother checks that a contract's mandatory fields are *present* before routing. Mother
never judges whether they are *right*. Presence is a deterministic check; correctness is frontier judgment.

**The smallest-mechanism rule.** No new database, no new schema registry, no new workflow engine. Every
contract below is either a GitHub issue, a GitHub pull request body, a file in a repository, or a labelled
tracking issue. Where a structured GitHub artifact suffices for commissioning, a machine-readable schema is
not introduced.

### 15.1 Contract summary

| # | Contract | Producer | Consumer | Canonical storage | Buzz | Mother validates | Loaded into agent context |
|---|---|---|---|---|---|---|---|
| 1 | **Finding Record** | any crew member; Mother from an event | Parker (or Ripley) | `squad-ops` issue | link + summary line | yes, presence | yes, in full |
| 2 | **Bounded Task Card** | Parker (or Ripley for Lane A slices) | Brett | `squad-ops` issue | link + assignment message | yes, mandatory fields | yes, in full — it is Brett's primary context |
| 3 | **Change Evidence** | implementer (Brett, Parker, Ripley, Ash) | reviewer (Parker, Dallas, owner) | `squad-ops` PR body | link + status events | yes, section presence | yes, for the reviewer |
| 4 | **Ruling Record** | owner | whoever holds the line | where the decision lives: plan, SIP amendment, PR comment, pre-registration, or `instructions.md` | link + the ruling text | yes, presence before work resumes | yes, the applicable rulings |
| 5 | **Deploy Identity** | Mother (mechanics), owner (the rebuild decision) | Ripley, Parker, the owner | `squad-ops` generated artifact (`shakeout-deploy.json`) + the pre-registration's deploy table | link + the probe summary | yes, that every probe is `observed` | on demand |
| 6 | **Measurement Pair** | Ripley (pre-registration), Mother (record mechanics) | Ripley (interpretation), owner (rulings) | `squad-ops` `docs/plans/` pre-registration and record | link | yes, that pre-registration precedes roll 1 | on demand |
| 7 | **Standing Delegation** | owner | the delegate, usually Mother or Parker | `nostromo` repo, `docs/ops/standing-delegation.md` | referenced by name | yes, that one is in force | yes, always, for the delegate |

Contract 2 is the only one with no existing shape anywhere in the record. The other six formalize artifacts
the work already produces.

---

## 16. Contract 2 — the Bounded Task Card

The central mechanism. This is the table that turns `F` work into `L+` work, written down.

### 16.1 What it is, concretely

**A Bounded Task Card is a GitHub issue in `squad-ops`, authored by Parker, with a fixed section order.**

Not a YAML file, not a row in a database, not a Buzz message. The choice is forced, not stylistic: the
SquadOps repository enforces a closure check requiring every PR to carry `Closes #N` against an **open
issue**, `Refs #N — remaining:`, or `No issue:`. Brett's work produces a PR. That PR needs an issue to close.
Therefore the card is an issue.

Three consequences follow, all of them good. The card inherits issue permanence, so a delegated task cannot
vanish into a thread. It inherits the tracker, so an abandoned card is visible. And it inherits the shape
the repository's 535 issue bodies already use, so Brett is reading a familiar artifact rather than a
Nostromo invention.

**Labels.** `nostromo:card` identifies it. `nostromo:lane-a` or `nostromo:lane-b` records which lifecycle
produced it. These are the only labels Nostromo adds to `squad-ops`, and they follow the repository's
existing `track:` label precedent.

### 16.2 The fields

Eleven fields in three groups, derived from the contracts document's comparison of delegated work that
landed clean against delegated work that did not.

#### Always mandatory — five fields

**1. Objective as a statement about the tree.** One sentence a reviewer can check against the diff. Not a
task description; a description of the repository's state afterwards. The plan-row form: *"`terminal_status`
retired: `RunStatus` is the domain vocabulary everywhere, translated to Prefect's `State` at the
`WorkflowTracker` adapter boundary only."*

**2. The bounding proof, named.** The guard, golden, fixture hash, AST count, replay, or record field that
will fail if the work is wrong. Named specifically enough to run.

> **If no such proof exists, the task is not bounded and the card must not be written.** Parker does the work
> instead, or produces the proof first as a separate piece of work. This is the single most important rule
> in the operating model.

**3. The mechanism and the files.** The defect or change traced to file and line, with the reproduction.
Brett does not re-diagnose. Brett *does* re-verify the premise against current `main`, because design
artifacts go stale against a moving tree.

**4. Prohibited changes, by name.** The explicit list: read-only areas (`dist/`, generated manifests,
`docker-compose.yml` service names, `pyproject.toml` version, goldens, pins, `updated_at`); files outside the
allowed scope; sibling findings that are "not in this PR"; whether the change may ride beside a measured
tranche; whether merges are frozen because a set is open.

**5. Escalation conditions, by name.** What stops the work and goes back to Parker or to the owner: a pin or
hash move, a compose or `init.sql` edit, a change to a verdict semantic, the premise found false, the named
guard failing to fire on the motivating commit, the work exceeding the allowed scope.

#### Mandatory when the seam has more than one reader — three fields

Required whenever the change binds, removes or re-weights a check, touches the accepted-patch path, or
changes what a record reads. These are the archetypes where every rework in the record clusters.

**6. The seam table.** Every evaluator of the affected criteria, the tree each one sees, and the outcome on a
tree that lacks the file. The SquadOps cycle has five such seams — emission, agent-side repair, the verifier,
the file-owned gate, the retest — and an agent binding a check sees one.

**7. The mirror-rule answer** for anything removed: what it produced, for whom, and what replaces it.

**8. The paired control** for anything that will report success: the stored red it must catch and the stored
greens it must pass, or the deploy on which a probe must fail. *"Two controls, stated" is acceptable; zero
controls is not.*

#### When they earn their place — three fields

**9. Rationale and precedent.** The harvest entry or the shape citation, so Brett does not re-derive a
decision the tree already made.

**10. Known traps, specific to this surface.** Not a general list. The ones that bite here: `gh pr edit`
fails in this repository; `--wait` is not a flag; run `ruff check` and `ruff format` as separate invocations
because chaining hides the format step; a symbol import proves nothing about a container.

**11. Exact verification commands,** when they are not obvious from the proof.

#### Deliberately not required

*Expected scope as an estimate.* The record bounds scope by the proof and the prohibitions, never by a size
estimate, and there is no case where an estimate helped.

*Acceptance criteria as prose beyond the proof.* Where issues carry an acceptance section it is a list of
replays and guard outcomes, which is field 2 written out longhand.

### 16.3 The card template

```markdown
## Objective
<one sentence about the state of the tree afterwards>

## Bounding proof
<the named guard / golden / replay / AST count / record field, and how to run it>

## Mechanism
<file:line, the reproduction, what was ruled out>

## Allowed scope
<paths this work may touch>

## Prohibited
<read-only areas, siblings not in this PR, ride-along restrictions>

## Escalate and stop if
<named conditions>

## Seam table            <!-- when the seam has more than one reader -->
| evaluator | tree it sees | outcome on a tree lacking the file |

## Removed               <!-- when anything is removed -->
<thing> — produced <evidence> for <consumer>; replaced by <what>

## Paired control        <!-- when anything reports success -->
<the stored red it must catch; the stored greens it must pass>

## Rationale             <!-- when precedent exists -->
## Traps                 <!-- when this surface has specific ones -->
## Commands              <!-- when not obvious -->
```

### 16.4 Lifecycle

1. **Parker writes the card** after establishing that the bounding proof exists. Parker opens it as a
   `squad-ops` issue under Parker's GitHub App identity, labelled `nostromo:card`.
2. **Mother checks presence** of fields 1–5, and of 6–8 when Parker's own risk line says a trigger fired.
   A card missing a mandatory field is returned to Parker with the field named. Mother does not judge quality.
3. **Mother assigns it to Brett** through Buzz: an @mention carrying the envelope, with the issue URL.
4. **Brett's harness loads the card** as the work-bootstrap layer (§32). The card is the primary context;
   Brett does not receive the surrounding thread.
5. **Brett works** in Brett's worktree, on a branch under `nostromo/brett/`.
6. **Brett returns** either a PR whose body is the Change Evidence contract, or an escalation naming which
   condition from field 5 fired.
7. **Parker reviews** against the card (§19.1), and approves, requests changes, or reclaims.
8. **Merge** per §12.1.

### 16.5 When a card must be returned as insufficient rather than executed

Brett stops and returns the card, without writing code, when:

- **field 2's proof does not exist, cannot be run, or does not fail on the current tree.** A proof that
  cannot fail is not a proof, and a delegation whose report cannot be checked is the defect the paired-control
  rule exists to prevent;
- **the mechanism in field 3 does not reproduce** against current `main`;
- **the work cannot be done inside the allowed scope** in field 4;
- **a seam is discovered that the seam table does not list**, when a seam table was required;
- **any escalation condition in field 5 fires.**

Returning a card is a correct outcome, classified `ESCALATED_CORRECTLY`, and it ranks above every outcome
except a clean pass. The evaluation framework is explicit that an honest stop is worth more than a plausible
story. Stopping on a *complete and executable* card is the opposite error, `WRONG_ESCALATION`, and is also
recorded.

---

## 17. Contract 1 — the Finding Record

**Producer.** Whoever holds the observation: Mother reading a CI or cycle event, Parker finding something on
the way, the owner noticing a red, Brett's collected output showing something unexpected.
**Consumer.** Parker, or Ripley when the finding is architectural.
**Canonical storage.** A `squad-ops` issue, labelled `nostromo:lane-b`.

**Required fields, in fixed order** — the shape 535 issue bodies already converge on, made mandatory so that
an issue without a mechanism or without identifiers is visibly incomplete:

1. **What happened**, with identifiers: cycle and run ids, the deploy identity, the record section or log line
   **quoted rather than paraphrased**, the UTC window. An observation without identifiers cannot be re-read.
2. **Why — read from the code, not inferred.** File and line for each hop. The distinction is load-bearing:
   an agent's first plausible cause is a hypothesis, and one issue in the record was filed on an inferred
   premise and had to be rewritten before it could be built.
3. **Reproduced.** The offline replay that shows the mechanism, by artifact id.
4. **What it is not.** Each plausible cause ruled out, with the evidence that rules it out.
5. **Fix shape.** The layer, the seam, and the proof that will demonstrate it. Not the diff.
6. **Placement.** Which line or lane, and why.
7. **Related / not this.** Sibling defects split out as their own issues, because a deferral recorded only in
   a closed issue's comments is a deferral that disappears.

**Lifecycle.** Opened → investigated → diagnosed (fields 2–4 complete) → becomes the anchor for the fix PR →
closed by that PR's `Closes` line.

**An honest stop is a valid terminal state.** "Unresolved, here is what I ruled out" with fields 1, 3 and 4
complete is worth more than a plausible story, and the issue stays open with that content.

**Mother validates** that fields 1 and 2 are present before routing for implementation. Mother does not
judge the mechanism.

---

## 18. Contract 3 — Change Evidence

**Producer.** The implementer. **Consumer.** The reviewer.
**Canonical storage.** The `squad-ops` pull request body, in the repository's existing template shape.

The reviewer must be able to confirm the contract was met **without reconstructing the task**. Every field
below maps to a field of the card or the finding it implements, so a missing entry is a visible gap rather
than a prompt in a comment.

| Section | Content | Maps to |
|---|---|---|
| `## What` | the objective as landed, in the card's words, plus what a reader would otherwise infer wrongly — including what is deliberately *not* changed | card field 1 |
| `## Closes` | `Closes #N` to an open issue, `Refs #N — remaining:`, or `No issue:` with the reason | enforced by the repository's closure check |
| `## Evidence` | the bounding proof, run, with its output; the replay by artifact id with its controls named; the **entry point exercised** for any changed seam; the seam table for any bound check; the mirror-rule line for any removal; the regression count **from the whole gate**; the live cycle id where there is one | card fields 2, 6, 7, 8 |
| `## Not in this PR` | every sibling finding with its issue number | card field 4 |
| deploy note | which services need rebuilding, whether a hash or frozen surface moves, which deploy it rides | card field 4 |
| owner's OK | quoted on the PR, when the change is on the read-only list or moves a pin | §13 |

**Three claims in an Evidence section are presumed false until an artifact says otherwise**, because each is
a recorded failure mode: a regression count that is not from the whole gate; a "verified in the container"
claim backed by a symbol import rather than a live call with its control; and a "wiring test" that is a seam
test handed its own input.

**Mother validates** that the sections exist and that the closure line resolves. Mother does not read the
evidence.

---

## 19. Review contracts

### 19.1 Parker's review of Brett

Parker evaluates exactly five things, and nothing else:

1. **Did Brett satisfy the card's objective?** Check field 1 against the diff.
2. **Did scope stay bounded?** Nothing outside the allowed paths; nothing on the prohibited list.
3. **Did the named proof run, and could it have failed?** Field 2's proof, with its output in the Evidence.
4. **Did Brett hit an escalation condition and continue anyway?** The worst outcome, and the one to look for
   hardest.
5. **Are the tests and evidence adequate for the change Brett actually made** — including a control that must
   not fire, for any assertion that reports success.

If the card was wrong, Parker fixes the card and re-issues or reclaims the work. Parker does not silently
absorb a framing defect as a Brett failure: the evaluation framework classifies framing failures separately
precisely so that a class's tier is never decided from Brett's raw pass rate.

### 19.2 Dallas's review of Parker

Dallas returns the §5.4 vocabulary against these questions:

1. Does the implementation satisfy the **accepted invariant**, or a neighbouring one?
2. What evidence here could be **falsely reassuring**?
3. Are **neighbouring seams and callers** accounted for?
4. Is the **proof broader than the implementation**, and does it enter where the live system enters?
5. Is there **hidden behaviour change** inside a nominal move?
6. Does the PR **preserve rationale and scope** — the mirror rule for removals, the amendment for
   divergences?

Dallas cites file, line, and the artifact for every blocking objection. A blocking objection without an
artifact is an unresolved question.

### 19.3 The upstream Dallas return

```text
Claim challenged      <the specific claim, quoted>
Evidence inspected    <what Dallas actually read: files, artifacts, records>
Blocking objections   <each with the invariant it violates and the evidence>
Non-blocking concerns
Unresolved questions
Suggested falsification  <what would disprove the proposal; what proof would actually fail>
Recommendation        <proceed / proceed with named narrowing / do not proceed>
```

Ripley or Parker must **disposition every blocking objection before implementation proceeds**, and the
disposition is recorded in the canonical artifact — not in the Buzz thread. The disposition form the record
uses: each point numbered, with `ACCEPT`, `ACCEPT WITH SHAPE`, `ANSWERED` or `REJECTED`, what it changes,
and what it explicitly does not change. The purpose is that the next reader inherits positions, not open
threads.

---

## 20. Contract 4 — the Ruling Record

**Producer.** The owner. **Consumer.** Whoever holds the line.
**Canonical storage.** Where the decision lives, dated: the plan, the SIP as a numbered amendment, the PR
body, the pre-registration before the run, or `instructions.md` when it is a standing rule.

**Required fields.** The question as put; the options with what each costs; the ruling, in the words used;
the date; what it changes and what it leaves unchanged; who may overrule it.

**The rule that makes it a contract:** the ruling is **written before the work resumes**. Every ruling in the
record was given in conversation and then written down; the writing is the handoff. A ruling that exists only
in a Buzz thread is not a ruling, and the crew does not act on it.

**Escalation to the owner carries its own shape** — the question, the options with their costs, a
recommendation, and what has already been done that does not depend on the answer. The crew raises the
decision rather than taking it, and does everything that does not turn on it first.

**Mother validates** that a ruling record exists and is linked before moving a blocked item back to active.

---

## 21. Contracts 5 and 6 — Deploy Identity and Measurement Pair

Both already exist in the SquadOps repository as generated artifacts and plan documents. Nostromo does not
reimplement them; it names who holds each part and what the crew may assume.

### 21.1 Deploy Identity

**The only admissible statement of what a deploy carries.** Image ids, HEAD, container start times, and
every loaded-check probe's answer in the three-state vocabulary.

- The crew may assume **nothing** about what the images carry until the identity says so. *Loaded, not built.*
- A probe that errors **stops the launch**. A probe recorded as `No such container` is an unasked question,
  not a passing probe.
- Container start times are part of the identity, not decoration: an identical image id on a container
  restarted mid-window is still a moved boundary.
- **Nostromo addition.** The identity must record whether any crew inference model was resident on the Spark
  during the window (§36). Otherwise a counted set's memory conditions differ from the deploy's, silently.

### 21.2 Measurement Pair

The pre-registration and the record, together.

- The pre-registration is fixed **before roll 1, by the commit hash of the document**. A reading corrected
  after the run is not a prediction.
- The per-roll record is facts; the pre-registration says what they mean.
- **Unexercised is not passed.** A prediction no roll exercised is named as unexercised in the record.
- The record says what the evidence does **not** cover.
- Who does what is §37.

---

## 22. Contract 7 — the Standing Delegation

**Producer.** The owner. **Consumer.** The delegate, then the owner again.
**Canonical storage.** `docs/ops/standing-delegation.md` in the **Nostromo** repository, referenced by name
and date from any work it governs.

Two lists, taken from the shape that has already run four overnight sets and one full delegated line:

**Do without asking.** Read anything; query the database read-only; replay stored artifacts; write code on a
branch; open a PR; file an issue; run the regression gate and the contract gates.

**Never without an explicit rule.** Deploy; rebuild; restart a service; merge; change frozen seeds or pins
mid-baseline; anything on the owner-reserved list (§13).

**The standing note that prevents the most common misreading:** *a deploy freeze is not a work freeze.*

**The return artifact.** A report that leads with what happened and what it means, identifiers second;
deltas and anomalies only; no optimism; every deviation from the standing rules named as a deviation; and for
a delegated line, a **decisions-taken-under-delegation** section listing each decision, each of which is the
owner's to overrule.

**Mother validates** that a standing delegation is in force and names the class of work before executing
anything on the "never without an explicit rule" list, and refuses otherwise.

---

# Part IV — Two Work Lifecycles

## 23. Lane A — design and architecture

Used when the work establishes or changes a rule, adds a capability, or requires a design artifact. The
existing sixteen-state ladder is retained with two changes: the Dallas challenge becomes an explicit state
rather than an implicit review, and the states are grouped so that the four things that must stay distinct
stay distinct.

```text
IDEA_CREATED
   ↓
EXPLORING          ── Ash, where external evidence is needed
   ↓
CONVERGING
   ↓
DESIGN_DRAFTING    ── Ripley authors the acceptance source: a standard, a map, or a SIP
   ↓
DALLAS_CHALLENGE   ── risk-triggered (§11); skipped explicitly, with the "no trigger" line recorded
                   ── Ash measures the corpus first where the work establishes a rule (§9)
   ↓
REVISION           ── Ripley dispositions every blocking objection in the artifact
   ↓
PROPOSED
   ↓
OWNER_ACCEPTANCE   ── material architectural acceptance is owner-reserved
   ↓
ACCEPTED           ── the artifact is now the acceptance source
   ↓
PLANNING           ── Parker decomposes; cards written where proofs exist
   ↓
IMPLEMENTING       ── Parker and Brett
   ↓
VERIFYING          ── the bounding proofs run; evidence assembled
   ↓
REVIEW             ── Parker reviews Brett; Dallas reviews Parker where risk warrants
   ↓
READY_TO_MERGE
   ↓
MERGED
   ↓
OBSERVING          ── §37; the change is watched on a live deploy where it is observable
   ↓
CLOSED
```

`BLOCKED` is orthogonal and may be entered from any state, carrying the reason and what it waits on.

**What must stay distinct, and why.** The architecture decision, the implementation, the independent
challenge, the evidence, and the observation are five different things, and collapsing any two of them is a
recorded failure. Specifically: an accepted design that is silently narrowed during implementation is the
amendment failure; evidence produced by the same party that concluded from it is the independence failure;
and a change merged without observation is how three defects stayed latent from merge day with green CI and
were found by a live cycle rather than by tests.

**Ripley does not implement in Lane A.** The prohibition holds here, unchanged.

---

## 24. Lane B — findings and defects

Used when something is wrong: a verification-set finding, a red on `main`, a live cycle producing a wrong
verdict, an owner observation. This is roughly seventy percent of the work by the record's own count, and it
does not climb the SIP ladder.

```text
FINDING            ── Finding Record opened (§17) with identifiers and the quoted line
   ↓
INVESTIGATING      ── Parker traces; continuity is protected (§24.2)
   ↓
DIAGNOSED          ── mechanism read from the code to file and line; ruled-out causes recorded
   ↓
FIX_FRAMED         ── the layer, the seam, and the proof named; Dallas challenges if T9 fired
   ↓
IMPLEMENTING       ── Parker, or Brett against a card where a proof exists
   ↓
VERIFYING          ── the replay, the wiring test, the affected suites
   ↓
REVIEW
   ↓
MERGED
   ↓
OBSERVING          ── the shakeout or the next live cycle
   ↓
CLOSED
```

### 24.1 The two legal loops

```text
VERIFYING ──(a new seam discovered)──> INVESTIGATING
```

The fix was right and incomplete: the value crosses another boundary that was not traced. This is the normal
shape of a cross-layer defect, and the record's canonical example ran six hops across five issues over a
week. Looping is not failure; it is the archetype working correctly. Mother records the loop and does not
reassign.

```text
IMPLEMENTING ──(premise falsified)──> ESCALATED
```

The mechanism turned out to be wrong. The work stops, the Finding Record is corrected in place with the
evidence that falsified it, and the item returns to `INVESTIGATING` or to the owner. An issue whose premise
was wrong is rewritten before it is built, not built around.

### 24.2 Diagnostic continuity

**The rule.** Between `INVESTIGATING` and `VERIFYING`, the item has one holder, and Mother does not change it.

Mother updates state, records links, and surfaces the item. Mother does not insert a handoff between
investigation and implementation, does not reassign at a state boundary, and does not request a status
narrative mid-trace. The record is unambiguous on the cost of routing interrupting reasoning: a correctly
diagnosed cause survived an entire three-round correction arc while routing sent every repair to the wrong
target, and a control arm on the identical deploy fixed it at round zero.

The holder is normally Parker. It may be Ripley under §4's three conditions. It is never Brett, because
diagnosis is `F`.

### 24.3 Delegation inside Lane B

Parker may cut a card from a Lane B item once the diagnosis is complete and a proof exists — typically the
replay of the stored red with its controls. The mechanism field of the card is then the Finding Record's
fields 2 and 3, cited rather than restated.

### 24.4 When a finding becomes architecture work

A Lane B item crosses to Lane A, entering at `DESIGN_DRAFTING`, when any of these is true:

- the correct fix requires a **rule that does not exist** — the defect is that no seam owns the concern;
- the fix would **contradict an accepted SIP or standard**, which means the artifact needs amending, and an
  amendment is a design act;
- the mechanism is the **fourth or later recurrence** of the same fact. When something has been fixed more
  than twice, the count is the finding, and the remedy removes the class rather than the instance;
- the fix would **change a verdict semantic, a pin, or what a measurement compares against** — which is also
  owner-reserved.

The crossing is recorded on the item, and the Lane A prohibition on Ripley implementing returns with it.

---

## 25. Where lifecycle state lives

This resolves the open decision in the repository README.

**The work artifact is a `squad-ops` issue or pull request. The crew's lifecycle state is a tracking issue in
the `nostromo` repository, one per work item.**

The tracking issue's body carries only: the lane, the current state, the active holder, the risk-trigger line,
and links to every canonical artifact. It carries **no content of its own** — no restated mechanism, no
duplicated design — because duplicated canonical content is how two surfaces come to disagree. Labels carry
lane and state so the board is queryable without parsing bodies.

**Why not labels on `squad-ops` issues.** It is a public repository, and crew coordination vocabulary does not
belong in it. The crew/squad separation is deliberate and mixing the two words on one issue is exactly the
confusion the vocabulary rule exists to prevent. Nostromo adds only `nostromo:card`, `nostromo:lane-a` and
`nostromo:lane-b` to `squad-ops`, which mark provenance rather than crew state.

**Why not a GitHub Project.** It is the better tool at volume, needs organization-level permissions the crew
apps deliberately do not have, and is GraphQL-only. Graduate to it when more than roughly twenty items are
open at once; the tracking issues convert cleanly because they are already one item per work item.

**Why not a database.** Rule three of §15.

**Mother writes the tracking issue** under a `nostromo-mother` GitHub App installed on the `nostromo`
repository only, with Issues write and nothing else. Mother therefore has **no write access to `squad-ops`
at all**, which is a property worth having: the coordinator cannot modify the product.

**Restart recovery.** After a process restart, Mother reconstructs state by listing open tracking issues.
That is the whole recovery procedure, and it satisfies the spec's requirement that a restart must not erase
the authoritative status of work.

---

# Part V — Buzz Collaboration

## 26. What Buzz is, and what it is not

Buzz is the shared collaboration substrate. It is **not** the agent harness, and it is **not** the source of
truth for any engineering fact.

```text
Buzz owns          identity, addressing, presence, the conversation, the routing signal
Buzz does not own  the work artifact, the design, the evidence, the decision, the lifecycle truth
```

Buzz carries a **reference and a summary**; GitHub carries the content. When a crew member needs a fact, they
read it from GitHub through their harness, not from a Buzz message. The reason is not purity: an agent
process restarts, a channel scrolls, a thread is archived, and a fact that lives only in a message is a fact
the next session cannot recover.

**The fourth wall stays up.** Buzz does not know what a SquadOps cycle is, what a roll is, or what a gate
decision means. Buzz knows that a work item exists, what state it is in, who holds it, and which URLs matter.
Nothing about SquadOps' internals is modelled in Buzz, and SquadOps has no dependency on Buzz whatsoever.

---

## 27. What Buzz knows

| Buzz knows | Buzz does not know |
|---|---|
| the work item and its Nostromo identifier | the content of the design |
| the lane and current state | why the state changed, beyond one line |
| the active holder | how the holder is reasoning |
| links to canonical GitHub artifacts | the artifacts themselves |
| the capability requested in a handoff | whether the handoff was any good |
| that an escalation was raised, and to whom | the ruling, except as a link and a quote |
| that a PR opened, that checks completed, that a review landed, that it merged | the diff, the evidence, the objections |
| the terminal state | anything SquadOps-internal |

Every one of the left-hand column is a routing signal or an addressing fact. Nothing in it is load-bearing
engineering content.

**The load-bearing-facts rule for agents.** An agent must never treat a Buzz message as the source of a fact
it will act on. Cite the artifact; read the artifact. If a crew member states a number, a file path, or a
verdict in Buzz, it is a pointer to where that fact is recorded, and the receiving agent reads it there.
Agents produce and consume prose fluently, which is exactly why every load-bearing claim carries the artifact
id and the line.

---

## 28. Channel and thread conventions

```text
#nostromo-control        crew presence, status, blocked work, budget, escalations, the daily sweep
#nostromo-<work-item>    one channel per substantial work item
   └── threads           one per contract exchange: a challenge, a card, a review
```

- **One channel per substantial work item**, created by Mother when the item opens and archived when it
  closes. Buzz's ACP conversation context is channel-scoped, so the channel boundary is also the context
  boundary — this is the mechanism that keeps one item's context out of another's.
- **Threads for contract exchanges.** A Dallas challenge is a thread. A card assignment is a thread. A review
  is a thread. This gives each contract a stable address.
- **Small items do not get a channel.** A localized Lane B repair runs in `#nostromo-control` with a thread.
  Creating the whole roadmap's channel structure before the pattern is proven is explicitly not done.
- **@mentions are the handoff event.** A handoff is an explicit @mention carrying the envelope. Handoffs are
  never inferred from silence, and an agent never begins work because a message merely mentioned its area.
- **Every agent runs `respond_to: allowlist`.** No agent responds to `anyone`, ever.

**How Mother knows to activate a role.** Three sources, in order of reliability: a GitHub webhook or poll
result (PR opened, checks completed, review submitted, merged); a crew member's explicit handoff @mention;
and the tracking issue's state, which Mother owns. Mother never activates a role because a conversation
seemed to imply it.

---

## 29. What actually happens in Buzz

### 29.1 A new feature (Lane A)

```text
 1. Owner states the objective in #nostromo-control, or Mother reads it from a milestone.
 2. Mother opens the Nostromo tracking issue (lane A, state IDEA_CREATED), creates
    #nostromo-<item>, and posts the item header: identifier, lane, state, links.
 3. Mother @Ash if external evidence is needed. Ash researches and returns a durable artifact,
    linked. Ash's sources carry the date read.            [state → EXPLORING → CONVERGING]
 4. Mother @Ripley with the envelope. Ripley reads canonical GitHub and design context in
    Ripley's worktree — not from the Buzz thread.          [state → DESIGN_DRAFTING]
 5. Ripley authors the acceptance source, commits it, and posts the framing plus the link and
    the risk-trigger line: "T2, T4 fired" or "no trigger".
 6. If the work establishes or changes a rule, Mother @Ash to measure the corpus that rule
    will apply to. Ash reports the count, not an opinion: what the rule would flag across the
    tree as it stands. The count goes in the artifact.
 7. If a trigger fired, Mother @Dallas. Dallas reads the artifact and the repository, and
    returns the §19.3 shape in a thread, with Ash's count in hand. [state → DALLAS_CHALLENGE]
 8. Ripley dispositions every blocking objection *in the artifact*, commits, and posts the
    disposition summary with the commit link.               [state → REVISION → PROPOSED]
 9. Mother surfaces the item to the owner for acceptance.   [state → OWNER_ACCEPTANCE]
    The owner's ruling is recorded in the artifact, dated.  [state → ACCEPTED]
10. Mother @Parker with the envelope and the accepted artifact.  [state → PLANNING]
11. Parker either implements directly, or writes Bounded Task Cards as squad-ops issues and
    posts each card's link. Mother checks each card's mandatory fields are present.
12. For each card, Mother @Brett in a thread with the envelope and the card URL. Brett
    acknowledges, works in Brett's own worktree through Brett's harness, and reports through
    Buzz. Brett never modifies the repository through Buzz.  [state → IMPLEMENTING]
13. PR opened. Mother surfaces it: author, branch, card, checks pending.
14. Checks complete. Mother posts every job's status, including the non-required ones.
15. Mother routes the review per §12.1: @Parker for a Brett PR, @Dallas for significant
    Parker work.                                            [state → VERIFYING → REVIEW]
16. Approval recorded. Merge per §12.1.                     [state → MERGED]
17. Mother opens the observation window and records what will be watched. [state → OBSERVING]
18. Observation read by Ripley (§37). Item closed; channel archived.      [state → CLOSED]
```

**Which events become Buzz messages.** Handoffs, escalations, state transitions, PR lifecycle events, check
results, review outcomes, and blocked notices. That is all. Intermediate reasoning does not go to Buzz;
it goes into the artifact or stays in the agent's session.

**Which artifacts are linked, never pasted.** The design artifact, the card, the PR, the evidence, the
ruling, the record. A Buzz message may quote one line for context and must link the source.

### 29.2 A defect (Lane B)

```text
 1. The finding arrives: Mother detects a red on main or a cycle event; or the owner posts an
    observation; or a crew member reports something found on the way.
 2. Mother opens the Finding Record as a squad-ops issue with the identifiers and the quoted
    line, opens the Nostromo tracking issue (lane B, FINDING), and posts the header.
 3. Mother @Parker with the envelope.                        [state → INVESTIGATING]
 4. **Parker holds the item from here to VERIFYING.** Parker traces in Parker's worktree,
    updates the Finding Record's fields 2 through 4 as they are established, and posts a
    one-line progress note at each state change — not a narrative, and not on request.
    Mother does not reassign, does not inject a handoff, and does not ask for a status
    report mid-trace.                                       [state → DIAGNOSED]
 5. Parker posts the fix shape and the risk-trigger line.    [state → FIX_FRAMED]
    If T9 fired — the diagnosis carries high uncertainty — Mother @Dallas to challenge the
    diagnosis *before* the fix is built. This is the cheapest possible moment to catch a
    wrong mechanism claim, which otherwise propagates into a wrong fix.
 6. Parker implements, or cuts a card for a bounded slice.   [state → IMPLEMENTING]
 7. The replay, the wiring test and the affected suites run. [state → VERIFYING]
    If a new seam appears, the item loops to INVESTIGATING with the same holder.
 8. PR, checks, review, merge as in Lane A steps 12–15.
 9. Observation: the next shakeout or live cycle.            [state → OBSERVING → CLOSED]
```

**The thing Mother must not do.** Between steps 3 and 7 the item has one holder. The coordination layer's
job there is to record and to surface, not to route. This is the single most important behavioural
constraint on Mother, and it is the one the current lifecycle design gets wrong by implying a handoff at
every state boundary.

### 29.3 Escalation

Any crew member may escalate. The escalation is an @mention to the owner in `#nostromo-control` carrying:
the question as put, the options with what each costs, a recommendation, and what has already been done that
does not depend on the answer. Mother marks the item `BLOCKED` with the reason.

The owner's ruling is written where the decision lives (§20) and linked. Mother verifies the ruling record
exists before moving the item back to active. Raise a concern once, then proceed on the ruling.

---

# Part VI — Harness Bootstrap

## 30. The four layers

Every crew session is assembled from four layers, in this order. The launcher owns all four and no agent
assembles its own.

```text
1. Identity      who you are, what you may do, what you must never do      always loaded
2. Repository    where the code is, what the rules are, how to work here   always loaded, role-varied
3. Work          this item, this contract, this question                   task-specific, replaced per item
4. Session       harness, model, endpoint, worktree, tools, budget         process configuration
```

Layers 1 and 2 are stable and small. Layer 3 changes per work item and is the only layer that should be
large. Layer 4 is environment rather than prompt.

The prompt layering the launcher contract already specifies is preserved: Buzz base instructions, then
Nostromo crew instructions, then the role persona, then channel context, then conversation, then the current
event. Layers 1 and 2 here are that stack's first three elements made explicit.

---

## 31. Identity bootstrap

Always loaded, identical structure for every role, contents from `crew/manifest.yaml` and the persona file.

| Element | Source | Notes |
|---|---|---|
| Persona: identity, mission, owns, does not own | `agents/<role>.persona.md` | the "does not own" list is as load-bearing as the "owns" list |
| Authority: what this role decides alone | this document, Part II | |
| Prohibitions: what this role must never state or do | persona + §7 for Brett | Brett's forbidden-conclusions list is verbatim |
| Escalation rules: what stops the work, and to whom | §13 and the role's escalation conditions | |
| Review obligations: what this role reviews and against what | §19 | |
| Budget profile and what happens at exhaustion | `crew/budgets.yaml` | stop metered use, report BLOCKED, wait |
| Stable Buzz identity and the allowlist | `crew/manifest.yaml`, derived pubkeys | `respond_to: allowlist`, never `anyone` |

**Size target: under 2,000 tokens.** If a persona needs more than that, the excess belongs in the repository
layer or in a skill, not in every turn of every session.

---

## 32. Repository and work bootstrap, and the context strategy

This is where the temptation to over-load is strongest, and where the cost is paid on every single turn.

### 32.1 The strategy

```text
universal maintainer doctrine   →  a small, stable instruction set, always loaded
role-specific lessons           →  the role's persona, always loaded for that role
task-specific precedent         →  linked from the Bounded Task Card or Finding Record, read on demand
long-form history               →  retrieved when a question requires it, never preloaded
```

**Do not inject the maintainer lessons document, the capabilities document, the archetype document, or
repository history into any session.** They are 5,274 lines. What goes into context is their distillate.

### 32.2 The universal doctrine

Ten rules, derived from the lessons document's own ranking of what should change what a maintainer *does* on
an ordinary change. This is the whole of the always-loaded engineering doctrine, for every repo-facing role.
It lives in `instructions.md`.

1. **Enter at the live caller.** A seam test proves the seam; only a test entering where the cycle enters
   proves the cycle reaches it. Name the entry point in the PR.
2. **Loaded, not built.** Verify code is reachable in the running container with a live call and its paired
   control. Never a symbol import, never a rebuild's exit code.
3. **Three states, never two.** `observed(value)`, `asked_none`, `unaskable(reason)`. Never fold an
   unanswerable question into a zero. The collapsed reading always flatters the result.
4. **Read the artifact, not the prose about it.** Cite the artifact id and the line for every load-bearing
   claim. Narrative never overrides a structured verdict.
5. **Guards over discipline.** When a lesson is learned, the deliverable is the test that fails, not the
   paragraph. A rule written down and still missed gets a guard.
6. **Require, don't default.** A seam that needs a value takes it; it never invents one. Missing
   configuration is a startup error that names the setting.
7. **Table the seams before binding a check.** You see one evaluator; the cycle has five. The table goes in
   the PR.
8. **Controls before a gate.** The stored red it catches and the stored greens it passes, both named. Two
   controls stated is acceptable; zero is not. No hard gate on an unvalidated surface.
9. **The mirror rule and the amendment.** Before removing anything, say what it produced and for whom. A
   divergence from an accepted design is amended in the PR that diverges.
10. **Your first plausible cause is a hypothesis.** Read it from the code. A heuristic in an evidence
    instrument fails silently the first time the data's shape changes.

Two more apply to specific roles and live in their personas rather than the common set: *a wasted round is
not a round* (anything touching correction budgets), and *derive, don't author* (anything touching prompts or
authored content).

### 32.3 Repository bootstrap, per role

| Element | Ripley | Dallas | Parker | Brett | Mother | Ash |
|---|---|---|---|---|---|---|
| SquadOps worktree path | yes | yes, detached | yes | yes | read-only checkout | yes |
| Branch / worktree policy | `nostromo/ripley/**` | detached commit, never a branch | `nostromo/parker/**` | `nostromo/brett/**` | none | `nostromo/ash/**`, path-scoped to `tests/**` |
| `CLAUDE.md` and contributor workflow | yes | yes | yes | yes | no | yes |
| Architecture standards under `docs/architecture/` | yes | yes | on demand | on demand | no | yes |
| The ten doctrine rules | yes | yes | yes | yes | abbreviated | yes |
| Role-specific lessons | design, precedent, amendment | falsely-reassuring proofs, seam tables, controls | continuity, tracing, delegation, budgets | bounded execution, collection, forbidden conclusions | routing, presence checks, interlock | controls, guards that fire, corpus measurement, blinded scoring |
| GitHub tooling | `gh`, Issues + PR write | `gh` read | `gh`, Issues + PR write | `gh`, Issues read + PR write | `gh` on `nostromo` only | `gh`, Issues + PR write on both repos |
| Shell / tool capabilities | read, grep, edit own artifacts, git | read, grep, run tests, git read | full dev loop | edit, test, lint, git, push to own namespace | read, scripts, `gh` | edit under `tests/**`, run tests, git, push to own namespace, web research |

**Skills, not context.** Procedural knowledge — how to run the regression gate, how to author a verification
set config, how to read a roll record, the surface-specific traps — belongs in `skills/*/SKILL.md`, loaded by
the harness when the task calls for it, not in the always-on prompt. The Persona Pack already reserves this
path.

### 32.4 Work bootstrap

Assembled by the launcher per work item, from the tracking issue and the canonical artifacts.

| Element | Source |
|---|---|
| Work item identifier and lane | Nostromo tracking issue |
| Current lifecycle state | Nostromo tracking issue |
| The canonical `squad-ops` issue or PR | linked |
| The contract payload — card, finding, or challenge | fetched full text |
| Design / SIP / plan references | linked, fetched on demand |
| Unresolved questions | the tracking issue and the artifact |
| Required return condition | the handoff envelope |

**For Brett, the card is the work bootstrap and very nearly the whole context.** Brett receives the card's
full text, the allowed paths, and nothing else from the conversation. Brett does not receive the Buzz thread
that produced the card, the design discussion behind it, or the other cards in the same batch. That is
deliberate on two grounds: it is the condition the evaluation measures, and surrounding context is where
scope creep comes from.

### 32.5 What must never be permanently loaded

- The maintainer lessons, capabilities, archetype, contracts and evaluation documents in full.
- Repository or git history.
- Other work items' threads.
- The whole issue tracker, or an issue's full comment history where the card cites what matters.
- Prior conversation from a previous work item. Channel-scoped context is the boundary.
- Any secret, ever, in any layer.

---

## 33. Session bootstrap

Owned by the launcher, verified by preflight, never assembled by the agent.

| Element | Where it comes from |
|---|---|
| Harness binary and ACP arguments | `crew/manifest.yaml` + runtime manifest |
| Model endpoint | Ollama on the Spark, or the provider boundary |
| Reasoning profile and temperature | runtime manifest, per role |
| Context limits | harness configuration; Ollama `num_ctx` raised for tool-calling reliability |
| Persistence and session affinity | Herdr pane per role on the Spark |
| Worktree assignment | `crew/manifest.yaml` workspace profile |
| Buzz bridge identity | host-local private key; derived pubkey checked against the manifest |
| Secrets and tool permissions | host-local secret file, mode 0600; harness permission profile |

**Preflight refuses to start** when any of these is wrong. The existing launcher contract already checks
identity, worktree, credential isolation, GitHub attribution and allowlist; §45 adds the checks the
redefined roles need. An identity that cannot be established is refused, not passed.

**Reasoning profile is a first-class setting, not a default.** The record contains a measurement where the
same model on the same task produced one usable emission in six with reasoning off and six in six with it on.
Every role's reasoning declaration is explicit in the runtime manifest, and the benchmark records it per
call. The corollary is that a task's *shape* — a transcription versus an argument — may need opposite
settings, so the manifest allows a per-task override which the card may request.

---

## 34. Context budget

| Layer | Target | Loaded |
|---|---|---|
| Identity | < 2,000 tokens | every turn |
| Universal doctrine | < 1,500 tokens | every turn, repo-facing roles |
| Role lessons | < 1,500 tokens | every turn, that role |
| Repository rules | < 2,000 tokens | every turn, repo-facing roles |
| Work item and contract | 2,000–8,000 tokens | per item |
| Skills | variable | when the task calls for it |
| Retrieved history | variable | on demand only |

A repo-facing session starts around 7,000 tokens of fixed context before the work item. That is the number to
watch: if it grows past roughly 10,000, something that belongs in a skill or a retrieval has been promoted
into the always-on layer, and the correct fix is to demote it rather than to raise the budget.

---

# Part VII — Harness and Model Strategy

## 35. Assignments, reconciled against the current repository

The table below states what `crew/manifest.yaml` configures **today**, what this model proposes, and whether
the change is proven or an experiment. Nothing here is presented as settled that has not been measured.

| Role | Configured today | Proposed | Change | Status |
|---|---|---|---|---|
| **Parker** | `codex-acp`, OpenAI `gpt-5.6-sol`, project `nostromo-parker`, $65 | unchanged; add persistent session affinity and a long-lived worktree | none to model or harness | **settled** — the largest cap belongs to the largest consumer |
| **Ripley** | `codex-acp`, OpenAI `gpt-5.6-sol`, project `nostromo-ripley`, $27 | unchanged | none | **settled** |
| **Dallas** | `claude-agent-acp`, Anthropic Opus, workspace `nostromo-dallas`, $27 | unchanged; add the requirement that Dallas's worktree is detached and never shares Parker's tree or session | none to model or harness | **settled** — a different provider family is what makes the review independent |
| **Brett** | `opencode-acp`, Ollama `qwen3.6-35b-a3b`, general variant, read-only permissions | **coding-capable local model**, write permissions inside his own worktree, a GitHub App identity, a branch namespace | **material** | **experiment** — see §35.1 |
| **Mother** | `opencode-acp`, Ollama `qwen3.6-35b-a3b`, control workspace | unchanged model and harness; move coordination logic from prompt into scripts | none to model | **settled**, with the caveat in §35.2 |
| **Ash** | `codex-acp`, ChatGPT Plus subscription, **Mac**, no repository access | **Spark**, worktree, GitHub identity path-scoped to `tests/**`; same harness and model | **material — host and access** | **settled on reasoning, unproven in practice** — the arithmetic in §2.7 is not in doubt; what is unmeasured is whether subscription rate limits leave Ash enough throughput to be depended on |
| **Lambert** | `gemini-acp`, Gemini subscription, Mac | unchanged host, harness and model; gains a read-only checkout and `education/` write in the Nostromo repo | **scope only** | **settled**, with the caveat that Gemini's ACP mode is the least proven runtime in the crew — tolerable because nothing depends on it |
| **Kane** | not configured | not added; an experiment slot only (§10) | none | **not a role** |

### 35.1 Brett's model and harness are two open experiments, not decisions

Two variables change together, which is exactly the confound the evaluation design forbids. They must be
separated.

**The model.** NOSTROMO-0001 §11.6 chose the *general* Qwen3.6 35B-A3B deliberately, "not a
coding-specialized variant", because the role was verification and evidence reasoning. Under this operating
model the role is bounded implementation, and the reasoning is that a coding-tuned variant should be better
at it. **That reasoning is a hypothesis and is not evidence.** It is tested by holding harness, task packet,
commit and oracle constant and varying only the model.

**The harness.** The working direction is a coding-focused harness, with the `pi` agent as the leading
candidate. What is in its favour, on the merits of Brett's role:

- `.pi/SYSTEM.md` **replaces** the system prompt rather than appending to it, which suits a role whose design
  is that the Bounded Task Card is nearly the whole context;
- `--tools` / `--exclude-tools` / `--no-builtin-tools` give a bounded tool surface by construction;
- an extension hook on `tool_call` can **block a call and terminate the turn**, which moves Brett's
  prohibitions from the constitutional tier of §14 to the deterministic tier — a path boundary enforced in
  code rather than by instruction.

What must be recorded plainly, because it is why this is still an experiment:

- `pi` has **no built-in permission system**; isolation is expected from a container or sandbox, and the
  extension hook above is the substitute that Nostromo would have to write.
- `pi` has **no first-party ACP support**. As of 2026-09-11 there is one actively maintained independent
  adapter, `regadas/pi-acp` (MIT, TypeScript, a fork of `svkozak/pi-acp`), targeting stable ACP v1 on the
  current SDK, mapping pi tool execution to ACP tool calls and pi's extension permission UI to ACP
  permissions. It is **not published to npm** and is built from source, so Nostromo would pin a commit and
  carry it in the source baseline. Its development is centred on Zed, so compatibility with `buzz-acp` is
  unverified and is an empirical question, not a documentation question.
- `pi` has **no MCP support**, and the adapter therefore *rejects* any `session/new` carrying a non-empty
  `mcpServers` list. This does **not** block Brett: `buzz-acp` sends an empty list when
  `BUZZ_ACP_MCP_COMMAND` is unset, and Brett's loop is receive-card, work, report, which the base
  prompt/response path already carries. It does mean Brett can never use the Buzz MCP bridge.
- `pi` sessions do not coordinate concurrent writers, so Brett must run as a single agent instance, never a
  `buzz-acp` pool.

**Therefore: the harness is decided by the benchmark, not in advance, and the benchmark does not need ACP.**
The evaluation runner invokes a harness directly, so `pi` and OpenCode can be compared on the same local
model, the same cases and the same oracles with zero ACP integration work. Only the winner pays the
integration cost. Until that comparison runs, `crew/manifest.yaml` keeps OpenCode ACP, which is already
configured, already ACP-native, and already has a permission profile in the plan.

**The design constraint that makes the comparison mean anything.** The same underlying local model is
retained across harnesses, so the experiment isolates harness behaviour. A harness effect is one that appears
across both models on the same case; a model effect is one that appears across both harnesses; anything
appearing in one cell only is an interaction and is reported as such rather than attributed.

### 35.2 Mother's model is adequate because Mother should barely use it

Mother's work is routing, presence checks, state writes and event watching. Nearly all of it is deterministic
and belongs in scripts that Mother invokes, not in model inference. The design target is that Mother's model
handles natural-language framing of messages and nothing load-bearing.

The risk the spec already names is that Mother becomes a second orchestration framework inside a prompt. The
mitigation is mechanical: `crew/capabilities.yaml` for routing, a presence-check script for contract
validation, the tracking issue for state, and the interlock guard for scheduling. If Mother's prompt starts
growing rules, that is the signal that logic has leaked into inference and should be extracted.

### 35.3 Budget reconciliation

The envelope is unchanged: $20 + $65 + $27 + $27 = $139 against a $150 ceiling.

What changes is where Dallas's $27 goes. Reviewing every PR would exhaust it on work with no rework history.
Scoped to the risk triggers in §11 — architecture rules, check and gate introduction, recovery semantics,
evidence instrumentation — it covers the archetypes where the record says rework actually lives.

Brett's work is unmetered and Ash's is fixed, which is the point. The operating model converts frontier
tokens into local tokens wherever a bounding proof exists, and Ash is where those proofs come from — so the
one agent whose marginal cost is zero is also the one manufacturing the delegability that keeps Parker's
cap intact. The measure of success is **paid tokens per passing change, at equal or better silent-failure
count**. A reduction in paid tokens bought with one additional silent failure is a worse result, not a
cheaper one.

---

# Part VIII — The Spark Interlock

## 36. Crew development mode and counted SquadOps mode

The Spark is both the crew's local inference host and the machine that runs SquadOps verification. The
record quantifies what happens when that is not managed: two model servers in unified memory produced
ninety-five minutes of swap thrash, `sshd` could not fault its own pages in, and the box ended in a power
cycle. The host had no memory containment at the time. The verification-set driver's own preflight already
refuses to run while another run is in flight.

NOSTROMO-0001 §80 names this risk and assumes phase separation. This section makes it deterministic.

### 36.1 The two modes

```text
CREW_DEVELOPMENT
    local crew inference permitted (Mother, Brett)
    crew repository work permitted
    no counted SquadOps execution

COUNTED_SQUADOPS
    crew local inference stopped and models unloaded
    no crew repository mutation on squad-ops
    cloud-backed crew roles may read and may work on the Nostromo repo
    Mother remains alive to collect, and runs no local inference
```

### 36.2 Rules

1. **Never concurrent.** A counted set and crew local inference never overlap on the Spark. One engine
   resident at a time.
2. **No repository mutation during a counted run.** No merges to `squad-ops` `main` while a set is open, and
   no rebuild over a running cycle: a rebuild leaves the run `running` in the registry and every later
   preflight refuses.
3. **Mode is explicit and recorded**, not inferred from whether anything appears to be running.
4. **Deploy identity records residency.** Whether any crew model was resident during the window becomes part
   of the identity (§21.1), so a set's memory conditions are never silently different from the deploy's.
5. **Mother enforces the transition** where it is mechanical and refuses where it is not.

### 36.3 The mechanism

A mode file on the Spark, a guard script, and a preflight check — in that order of authority, with the
prompt last.

```text
~/.config/nostromo/spark-mode        CREW_DEVELOPMENT | COUNTED_SQUADOPS
nostromo-spark-mode <mode>           transitions, refuses on a dirty transition
nostromo-spark-mode check            exits nonzero if the current mode forbids the caller's action
```

Entering `COUNTED_SQUADOPS` requires: no crew work item in a mutating state; Mother and Brett's local
inference stopped and the Ollama model unloaded; and the resulting free memory recorded. Entering
`CREW_DEVELOPMENT` requires no SquadOps run in flight, read through the CLI rather than assumed.

Each local-inference launcher calls `check` at startup and refuses to start in the wrong mode. Mother calls
it before routing any repository-mutating work. This is a deterministic guard, not a convention, which is the
whole point: what a test enforces stays true.

### 36.4 What this does not solve

Memory containment on the host is a prerequisite, not a consequence — `earlyoom` is installed and its
thresholds should be read from the running process rather than the declared unit, because the kernel OOM
killer does not fire during thrash. Disk headroom is a separate standing risk: five months of deploys once
took the box to sixty-five percent of an 870 GB root, and the reclaim command that fixes it sits one flag
away from a command that destroys the Postgres volume. Both are owner-reserved operations (§13).

---

# Part IX — Measurement

## 37. Who owns which part of measurement

The most expensive single judgment in the SquadOps record is reading a roll: counted, void or reset; whether
a finding supersedes the deploy; whether a field reads "did not happen" or "could not be asked". That
function currently has no home in the seven roles. This section gives it one without creating a role.

The split follows the line the work has already been run on: four overnight verification sets ran under
delegation where the launching, gating with the pre-registered constant, and collecting were delegated, and
the counted/void/reset reading was made per roll by the owner's line, with a falsified prediction stopping
the set.

| Function | Holder | Why |
|---|---|---|
| **Pre-registration authoring** | Ripley, owner-reviewed | it is a design act: predictions, readouts, prohibitions and the gate constant |
| **Pre-registration freezing** | Mother | mechanical: merge by commit hash before roll 1 |
| **Preflight** | Mother | mechanical: run it, report every refusal verbatim, never interpret one away |
| **Launch** | Mother | mechanical, detached, so the work outlives its supervisor |
| **Gate approval with the pre-registered constant** | Mother | mechanical: copy the constant verbatim, no substitution of any kind |
| **Collection and render** | Mother | mechanical: the driver renders the per-roll record; never assembled by hand from logs |
| **Reading a roll: counted / void / reset** | **Ripley proposes, owner rules** | `F`; a void or reset already stops the set for the owner in the record |
| **Supersession: does this finding supersede the deploy** | **Ripley proposes, owner rules** | `F`; changes what the next measurement compares against |
| **Interpreting `observed` / `asked_none` / `unaskable`** | **Ripley** | `F`; the collapsed reading always flatters the result |
| **Preservation of perishable evidence** | Mother executes, Ripley decides what is perishable | a record's texture derives from container logs; a rebuild destroys it permanently |
| **Instrument correction during an open set** | **owner** | an instrument fix that changes a counted roll's score is a ruling, and both readings are reported |

### 37.0 Two measurements, deliberately kept apart

This section is about **SquadOps measurement**: verification sets, counted rolls, deploy identity,
supersession. Ripley interprets it and the owner rules on it.

The **crew's own benchmark** — case construction, oracle admission, blinded scoring, failure classification
— is a different instrument measuring a different subject, and it belongs to Ash (§9, §42.3a). Keeping them
apart is deliberate: the party whose architecture is being measured should not also score the crew's
performance, and the party scoring the crew should not rule on what a SquadOps roll means.

Mother runs the mechanics for both, and concludes from neither.

### 37.1 The line Mother must not cross

```text
Mother can gather measurement evidence.
Mother does not decide what the measurement means when that decision is frontier-tier.
```

Concretely, Mother may report "preflight refused: image id drift on `runtime-api`" and may not report "the
drift is harmless". Mother may report "three probes recorded `No such container`" and may not report "the
probes passed". Mother may report "roll 3 completed in 54 minutes with verdict X" and may not report that
roll 3 was counted.

### 37.2 Whether Ripley can carry this

Ripley's $27 cap is the constraint. Reading a roll boundary is a small number of high-value tokens — the
record is rendered, and the judgment is against pre-registered predictions — so the cost is compatible with
the cap. What is *not* compatible is Ripley also authoring every pre-registration, running every diagnostic
interpretation, and holding architecture for the 1.8 line simultaneously.

The initial answer is therefore: Ripley carries it for 1.8, and the load is watched.

### 37.3 What would justify a dedicated Measurement Steward

Add the role only on evidence. Any two of these, observed over one release line:

1. **Ripley's cap becomes the binding constraint on measurement**, rather than on architecture — that is,
   roll readings are delayed or batched because tokens ran out.
2. **Roll-boundary readings are consistently late**, such that the next roll launches before the previous
   one's record is read. That exact deviation is on record and it is what the early-stop rule exists to
   prevent.
3. **Measurement interpretation and architecture judgment conflict inside one session** — Ripley reading a
   roll against predictions Ripley authored, without an independent challenge, is the same independence
   defect the Ripley/Parker split exists to avoid elsewhere.
4. **More than one measured line runs concurrently**, which makes the function continuous rather than
   episodic.

If added, the role is frontier-tier by construction, receives its own provider boundary, and takes the
`F` rows of the table above from Ripley — leaving the owner's rulings untouched, since those are
owner-reserved for reasons independent of who proposes.

---

# Part X — Concurrency

## 38. What may run at once

Four independent constraints. The binding one at any moment is whichever is tightest.

### 38.1 The worktree constraint

Git permits a branch to be checked out in one worktree at a time. Long-lived role worktrees with branches
swapped are acceptable for v1 if cleanup is disciplined.

- **One active branch per role worktree.** A role works one item at a time in its tree.
- **Dallas and Brett-as-reviewer check out a detached commit, never a branch.** This resolves the second open
  decision in the repository README, and it protects review independence: Dallas must not review inside
  Parker's mutable tree.
- A second concurrent item for the same role needs a second worktree, which is permitted and named
  `<role>-2`, with the same rulesets.
- **Ash has a worktree on the Spark** and adds no meaningful memory pressure, because Ash's model runs
  remotely and the local process is a thin client. Ash's *test execution* is local CPU, so it stops during
  `COUNTED_SQUADOPS` along with everything else that could perturb a measured run (§36).

### 38.2 The independence constraint

- Dallas's session and context are separate from Parker's. A reviewer who inherits the implementer's session
  is not independent.
- No agent reviews or approves its own work, enforced by ruleset (§14).
- Brett's context is the card, not the discussion that produced it (§32.4).

### 38.3 The budget constraint

Concurrent metered sessions burn caps in parallel and the caps are monthly. At $65, $27 and $27 with hard
provider limits, the practical ceiling is roughly two concurrent metered work items, and one is the
commissioning default. Local roles are unmetered and unconstrained by this.

When a provider boundary is exhausted, the agent stops metered use, reports `BLOCKED` with the reason, and
waits. No agent borrows another's credential, and no agent routes around a spend limit — which is enforced by
the credential isolation the launcher checks, not by the instruction.

### 38.4 The Spark constraint

§36. Crew local inference and counted SquadOps execution never overlap. During `COUNTED_SQUADOPS`, Mother
and Brett are down, and the metered roles may read and may work on the Nostromo repository but must not
mutate `squad-ops`.

### 38.5 Recommended concurrency for commissioning and early 1.8

| Phase | Concurrent work items | Notes |
|---|---|---|
| Commissioning A and B | 1 | one at a time, so a failure is attributable |
| The Brett delegation experiment | 1 | the box is otherwise idle; runs need identical conditions |
| Early 1.8 | 1–2 | a second only when the first is in review or observing |
| Steady state | 2–3 | revisit when the budget and the interlock have been observed together |

Mother serializes. When more work is ready than the constraints permit, it queues on the tracking board and
Mother surfaces the queue rather than starting it.

---

# Part XI — Commissioning

## 39. What commissioning is for

Bootstrapping is not evidence that the crew works. Seven processes that start, authenticate and answer
@mentions demonstrate infrastructure and nothing about engineering. Commissioning is the evidence.

Three things are measured, and they are different questions:

| Question | Measured by |
|---|---|
| Does the machinery work end to end? | Commissioning A and B |
| Does crew collaboration increase what a local model can safely do? | the delegation experiment (§42) |
| Does review catch what review is supposed to catch? | the reviewer challenge (§42.3) |

The outcome vocabulary is shared across all three, and it is the evaluation framework's, unchanged.

### 39.1 Outcome classes

Ordered best to worst. Every run ends in exactly one.

| Class | Meaning |
|---|---|
| `PASS` | all gates pass, the hidden oracle passes, and the claim matches the oracle |
| `ESCALATED_CORRECTLY` | the run stopped and returned a decision or a missing field, and the contract says it should have |
| `HONEST_FAIL` | the run reported failure, or "unresolved, here is what I ruled out", and did not claim completion |
| `LOUD_FAIL` | gates red |
| `WRONG_ESCALATION` | the run stopped on a case whose contract was complete and executable |
| `SILENT_FAIL` | visible gates green, the run claimed completion, the hidden oracle red |

**`SILENT_FAIL` is worse than every other outcome, including a wrong escalation, because it is the only class
that reaches `main`.** An honest stop is worth more than a plausible story, and the ordering is the most
important design decision in the evaluation model.

---

## 40. Commissioning A — a bounded feature

**Shape.** Small, low-risk, non-destructive, one branch, a real but minor SquadOps improvement with a small
design decision in it. Explicitly not the hardest open SIP.

**Proves.** Identities bootstrap. Buzz collaboration works without the owner relaying messages. The handoff
envelope survives a role boundary. Worktrees are isolated. The PR and review chain runs. Evidence is captured
in the contract's shape. Lane A's states advance and are recoverable after a restart.

**Runs the full Lane A path**: Ash where research is needed, Ripley framing, a deliberate Dallas challenge
even if no risk trigger fires, owner acceptance, Parker implementation with at least one Bounded Task Card to
Brett, Parker's review of Brett, Dallas's review of Parker, merge, observation.

**Recorded.** Handoffs that needed human relay (target: zero); broken @mentions; identity confusion; persona
drift; agent process restarts and whether state recovered; spend per role; whether channel-scoped context was
sufficient; whether GitHub artifacts allowed session recovery.

---

## 41. Commissioning B — a real finding

**Shape.** A defect taken from a real SquadOps verification-set or live-cycle finding: an issue whose body
cites a cycle id and a stored artifact. This is the shape roughly seventy percent of the work has, and it is
where the current design is least tested.

**Proves.** Investigation-to-implementation continuity survives contact with Mother. The Finding Record
carries what the implementer needs. Dallas's upstream challenge of a diagnosis works. A legal loop back to
`INVESTIGATING` is handled without losing the holder. The replay, the wiring test and the observation land.

**Specifically tests whether Mother's routing interferes with diagnosis.** This is the open question that
Lane B exists to answer. The failure mode to watch for is Mother inserting a handoff at a state boundary, or
requesting a narrative mid-trace, and the item's owner changing hands while the trace is live.

**Recorded.** Everything from §40, plus: whether the holder changed between `INVESTIGATING` and `VERIFYING`;
how many loops occurred and whether each was legal; whether Dallas's challenge changed the diagnosis; whether
the fix entered at the live caller.

---

## 42. The delegation experiment

The question: **does crew collaboration increase effective local-model capability?** Or, precisely: does a
Parker-framed Bounded Task Card change a local Brett's outcome, holding everything else fixed?

### 42.1 The arms

```text
Arm B    Parker-framed Bounded Task Card  →  Brett implements locally  →  Parker reviews
Arm C    the raw issue, no card           →  Brett implements locally  →  same oracle
```

**B minus C on outcome class and silent-failure count is the value of framing.** That is the whole
experiment.

An optional third arm, run only if the first two are clean:

```text
Arm D    Arm B without Parker's review    →  straight to the oracle
```

**B minus D on silent failures is the value of review.**

### 42.2 What is held constant

Everything except the packet:

| Held constant | Detail |
|---|---|
| Starting tree | the same commit, a worktree detached at it, history truncated so the run cannot read the future |
| Model | one Qwen tag, one quantization, one context window, one engine version |
| Harness | one, the one Brett is commissioned on |
| Hidden oracle | held by the runner, never given to the run, applied after |
| Verification | the same gates in the same order |
| Budget | the same token and wall-clock cap; a run stopped by budget is a loud failure with reason `budget` |
| Reasoning profile and temperature | fixed per case and recorded per call |
| Context | the packet only; no prior conversation; the worktree scrubbed between runs |

**Every case runs at least three times per arm, and the distribution of outcome classes is reported, never a
single run.** Local models at nonzero temperature vary run to run.

**The oracle is behaviour against the contract, not similarity to a historical patch.** Any implementation
producing the required readings passes.

### 42.3 The reviewer challenge

Separately, Parker and Dallas are each given a set of pull requests presented as Brett's work, with plausible
evidence sections. Half carry a planted defect; half are correct, some with misleading evidence. The
planted defects are drawn from the record's own failure shapes:

- a change that passes narrow tests and violates an architecture rule;
- a removal that takes away something's only evidence producer, with a green test;
- an assertion with no control that must not fire;
- scope expansion beyond the allowed paths;
- a behaviour change inside a nominal pure move, with "byte-identical" claimed in the body;
- a false reassuring claim: a regression count from a subset presented as the whole gate;
- evidence from the wrong deploy or the wrong tree;
- a correct implementation whose body claims a wiring test that is actually a seam test;
- **a control: a correct implementation with complete evidence.**

**Every planted case must be admitted the same way a gate is:** the oracle is shown to fail on the mutated
tree and pass on the clean tree before the case is used. A trap that cannot catch its own defect measures
nothing.

**Scored.** Detection rate on planted defects. False-positive rate on the controls. Finding quality: names
the symptom, names the violated invariant, or names the invariant and the evidence that shows it. And
**proportionality** — a review that redesigns rather than requesting the smallest correction that restores
the invariant scores zero here even when the detection is right.

### 42.3a Who runs and scores the evaluation

**Ash** (§9). Ash constructs the cases, proves each oracle fails on the broken tree and passes on the clean
one, scores the quality dimensions **blind to which arm produced the run**, and classifies every non-passing
run. Mother runs the mechanics on the Spark; Ash never executes a benchmark run against work Ash will score.

This assignment is forced rather than chosen. The evaluation design requires a scorer who has not seen the
arm's identity. Ripley interprets measurement and holds architecture. Parker and Dallas are the subjects
being scored. Mother may not conclude. Ash is the only frontier-capable role with no stake in the work.

**The conflict this creates, and its limit.** Ash authors cases and then scores runs against them, which is
the same shape as an instrument whose author's assumptions decided a headline. Two things bound it: the
oracle is mechanical and its admission is proven, so Ash never decides pass or fail; and whether an oracle
itself was wrong is classified as a verification failure and goes to Ripley or the owner, never to Ash.

### 42.4 What the experiment costs

All Brett runs are local and unmetered. Parker's framing and review are the only paid calls: a handful of
cards and a bounded number of reviews. The whole thing fits in one idle-box window and a small fraction of
one month's cap.

### 42.5 What continues the experiment, and what ends it

**Continue** when: arm B records zero silent failures; most runs pass or escalate correctly; the escalation
case stops every time; and arm B beats arm C on passes, or arm C shows a silent failure where arm B shows
none. Either of the last two is the framing effect.

**Stop, for this model and harness,** when: arm B records any silent failure; or arm B does not beat arm C
and shows no difference in silent failures, which means the card is not what the local model lacks; or
repeated failures classify as harness or tooling problems, in which case the harness was measured rather
than the model, and it is fixed and re-run.

### 42.6 Why failures are classified before they are counted

Every non-passing run is classified as one of: implementation capability, task framing, missing context,
architecture judgment, harness or tooling, verification or oracle, reviewer, or environment. A failure caused
by a missing card field is a framing result and says nothing about Brett. A failure caused by a tool that
does not work in this repository says nothing about either.

**A class's tier is never decided from a raw pass rate.** This is the rule that keeps the experiment
honest, and it is the reason the classification exists at all.

---

# Part XII — The 1.8 Adoption Gate

## 43. What must be true before Nostromo touches real 1.8 code

Three tiers. Perfection is not the bar; a minimum is.

### 43.1 Required — the crew does not touch 1.8 until all of these hold

| # | Criterion | Evidence |
|---|---|---|
| 1 | All seven crew identities bootstrap, authenticate, and hold stable Buzz pubkeys | WP-5 through WP-8 probes |
| 2 | Buzz routing works: every allowlisted peer @mention reaches its harness; unauthorized identities do not | the allowlist matrix |
| 3 | Persistent sessions recover: a killed agent restarts and resumes from GitHub and the tracking issue | restart test per role |
| 4 | Worktree isolation is proven: no role can mutate another's tree; Dallas reviews detached | filesystem and ruleset evidence |
| 5 | Task contracts survive the handoff: a Bounded Task Card reaches Brett with every mandatory field, through Buzz, without owner relay | commissioning A |
| 6 | Brett stays in scope on commissioning work: no change outside the card's allowed paths | the diff |
| 7 | **Parker catches a deliberately incomplete or incorrect Brett change** | the reviewer challenge, Parker's set |
| 8 | **Dallas catches at least one planted high-risk trap** | the reviewer challenge, Dallas's set |
| 9 | Escalation reaches the correct authority, and a routine item does not produce a wrong escalation | commissioning A and B |
| 10 | No agent self-approves where independence is required | ruleset rejection evidence |
| 11 | The Spark interlock works deterministically: a local launcher refuses in `COUNTED_SQUADOPS` | the guard's exit code |
| 12 | Benchmark records distinguish `PASS`, `ESCALATED_CORRECTLY`, `HONEST_FAIL` and `SILENT_FAIL` | the runner's outputs |
| 13 | **One feature flow and one defect flow complete end to end** | commissioning A and B |
| 14 | **Zero silent failures across all commissioning work** | the classification record |

Criterion 14 is absolute. Every other criterion admits a judgment call about whether the evidence is good
enough; this one does not. A silent failure is the only outcome that reaches `main`, the record's
delegation-era failures were all of this kind, and there is no threshold at which one is acceptable.

### 43.2 Desirable — wanted before 1.8, not blocking

- The delegation experiment showing a measurable framing effect. If the effect is absent, the finding is
  that Brett takes raw issues on that class, which is also useful.
- All seven contracts exercised at least once.
- Budget observed over a full month against the configured envelope.
- The `pi`-versus-OpenCode harness comparison run.
- A dependency baseline pinned for every crew component.

### 43.3 Later — explicitly deferred

- Qualifying Brett on additional archetypes beyond the first two or three.
- A dedicated Measurement Steward (§37.3).
- A GitHub Project as the lifecycle board.
- Machine-readable contract schemas.
- Lambert's instructional projection of 1.8 work. The source-manifest system (§10A.3) may be built at any time, because it is off the critical path and depends on nothing in the gate.

---

# Part XIII — Initial 1.8 Operating Policy

## 44. What the crew takes first

SquadOps 1.8 is the Automation and Learning release: the Cycle Evaluation Scorecard and the Campaign
mechanic as dual-lane co-headliners, with Cross-Cycle Memory as a decision point and the rails shipping
either way. Grade definitions land before continuation policy.

That headline work is frontier work by every criterion in the archetype tiering: new seams, new semantics,
and a scorecard whose whole purpose is to decide what a cycle's outcome means. **The crew does not start
there.**

### 44.1 Safe first, by archetype

Routed to Brett against a Parker card, because a bounding proof exists or can cheaply be made:

| Archetype | Why it is safe | The proof |
|---|---|---|
| **7. Vocabulary and identifier sweeps** against a landed guard | wide and semantically flat; the guard frames the edit; a sixteen-item delegated line found nothing attributable | the guard has nothing left to flag, and fails a return |
| **9. Guard authoring** against a named shape | the revert-and-run proof is mechanical | the guard fires on the motivating commit and passes `main` |
| **6. Behaviour-preserving extraction** against a reviewed map | reliably mechanical once the map exists | goldens captured first, byte-identical after; AST name counts |
| **5. Scaffold emitter fixes** with no pin movement | the proof is a comparison, not a judgment | every frozen fixture byte-identical |
| **10. Evidence instrument fields** with a stated producer | bounded when the three states and the line shape are specified | a test with the real line shape; the field's three states demonstrated |
| **16. Dependency recompiles and workflow edits** after the policy is set | the policy is the frontier part; the recompile is not | the drift guard; the fresh-venv install job |
| **21. Dead-code removal** once the census and mirror-rule answer exist | the census is the judgment, and it is done by then | the AST or grep census in the PR |

Held with Ripley, Parker and Dallas:

| Archetype | Why |
|---|---|
| **2. Cross-layer tracing** | blast radius unknown until the trace is complete |
| **3. Recovery-path semantics** | every change alters what the next roll is judged by |
| **4. Typed-check and gate introduction** | the seam table and the blocking decision are the expensive parts |
| **8. Architecture rules and standards** | the rule's boundary and its exceptions |
| **11. Roll readings and supersession** | §37 |
| **12, 13, 15. Plans, issue triage, SIP work** | every revision in the record was on the owner's review or ruling |
| **17, 18. Host and compose operations** | one flag from data loss; owner-gated |

### 44.2 The first three work items

1. **A Lane B bounded defect** whose causal layer is already established — a finding with the mechanism
   already read to file and line. Proves the fix line end to end at low risk.
2. **An architecture guard against an already-decided rule.** The rule exists; the guard does not. The
   frontier part is already done, so this is a clean `L+` delegation with an unambiguous proof.
3. **A bounded extraction against an accepted map**, if one is live in the 1.7.5 closure work. This is the
   archetype with the best clean-landing record once framed.

None of these touch the 1.8 headline features. All of them are real work the release line needs.

**Ash's first work runs alongside them, not after.** Item 2 needs a guard, and a guard is Ash's product: Ash
measures what the rule would flag across the existing corpus, reports the count, and builds the guard with
the commit it must fire on demonstrated. That is the cheapest possible proof that the Science Officer role
works, because the corpus measurement either changes the rule's shape or confirms it, and both outcomes are
informative.

### 44.3 How archetypes graduate to Brett

Evidence only, per archetype, and the tier is a hypothesis about this configuration rather than a permanent
ceiling.

**Graduate an archetype** when, on that archetype: at least a dozen runs across at least four distinct
tasks; nearly all passing or escalating correctly; **zero silent failures, ever, for that configuration on
that archetype**; and no repeated failure classified as implementation capability.

**Do not graduate** when a silent failure has occurred, when failures repeatedly classify as architecture
judgment, or when fewer than four distinct tasks have been seen — in the last case the evidence is
insufficient rather than negative.

**Qualification is scoped and expires.** It is per archetype, per harness, per model configuration. A new
model tag, a new quantization, or a new harness version resets that archetype to insufficient evidence. The
reason is in the record: the reasoning declaration alone moved one task's usable-emission rate from one in
six to six in six.

**If a qualified archetype later produces a silent failure on real work, the qualification was wrong.** The
correction is written in place, dated, beside the reading it replaces, with the evidence that falsified it —
and the archetype returns to frontier.

### 44.4 The standing rule underneath all of it

> The frontier's job is to produce the table; the bounded engineer's job begins when it exists.

Work is never delegated because it looks small. It is delegated because its evaluation surface has been
tabled and turned into a guard, a golden, a census or a probe. Delegating before the table is written is how
the record's worst delegation failures happened, and the model doing the work did not change that.

---

# Part XIV — Repository Change Plan

## 45. What must change in this repository

Every row names the actual current file. `R` = required before commissioning. `F` = may follow.

### 45.1 Configuration

| File | Change | Reason | Verification | When |
|---|---|---|---|---|
| `crew/manifest.yaml` | Brett: `capability: verification` → `bounded_implementation`; add `github_identity: nostromo-brett`, `branch_namespace: nostromo/brett`; change harness/model only after §35.1's experiment | Brett writes to the repository now | `tests/test_crew_config.py` extended | **R** |
| `crew/manifest.yaml` | Mother: add `github_identity: nostromo-mother` scoped to the `nostromo` repo | Mother owns the tracking issues | test | **R** |
| `crew/manifest.yaml` | Ash: `host: mac` → `spark`, `supervisor: launchd` → `herdr`, `workspace_profile: research` → `proof`; add `github_identity: nostromo-ash`, `branch_namespace: nostromo/ash`, `path_scope: tests/**` | §2.7, §9 | `tests/test_crew_config.py` extended: Ash is on Spark, carries a path scope, and holds no `*_API_KEY` | **R** |
| `crew/manifest.yaml` | add `reasoning_profile` per agent | it is a first-class setting, not a default | test asserts presence | **R** |
| `crew/capabilities.yaml` | replace `verification: brett` with `bounded_implementation: brett`, `evidence_collection: brett`; add `measurement_mechanics: mother`, `measurement_interpretation: ripley`; replace `ideation_research: ash` with `proof_infrastructure: ash`, `corpus_measurement: ash`, `evaluation: ash`, `precedent_research: ash`, `external_research: ash`; replace `google_knowledge: lambert` with `knowledge_projection: lambert`, `source_curation: lambert` | the verification capability splits at the `L`/`F` line; Ash gains the Verifier cluster; Lambert's scope is named | test asserts every capability resolves to a manifest agent | **R** |
| `crew/manifest.yaml` | Lambert: add `workspace_profile: projection`, a read-only SquadOps checkout path, and `github_identity: nostromo-lambert` scoped to the `nostromo` repo | §10A.6 | test asserts Lambert holds no `squad-ops` write identity | F |
| `crew/lifecycle.yaml` | restructure into two lanes with their states, the legal loops, and the Lane B → Lane A crossing conditions | §23, §24 | test asserts both lanes parse, initial and terminal states exist, and every loop target is a declared state | **R** |
| `crew/budgets.yaml` | unchanged; add a comment recording that Dallas's cap is scoped to risk-triggered review | §35.3 | none | F |
| `.plugin/plugin.json` | unchanged roster; add `skills/` if the Persona Pack supports it at the pinned version | procedural knowledge is not prompt context | verify against the pinned spec | F |

### 45.2 Instructions and personas

| File | Change | Reason | When |
|---|---|---|---|
| `instructions.md` | add the ten doctrine rules (§32.2) | universal maintainer doctrine, always loaded | **R** |
| `instructions.md` | amend role integrity: Brett's new line; the Lane B exception to Ripley's prohibition; Mother's continuity constraint | §2.1, §2.3, §24.2 | **R** |
| `instructions.md` | add the review outcome vocabulary including *returned for artifact* | §5.4 | **R** |
| `instructions.md` | add the load-bearing-facts rule for Buzz | §27 | **R** |
| `agents/*.persona.md` (7, not yet authored) | author per §31, with role-specific lessons | WP-9 deliverable, now with content to put in them | **R** |
| `agents/brett.persona.md` | the forbidden-conclusions list verbatim | §7 | **R** |

### 45.3 New directories

| Path | Contents | When |
|---|---|---|
| `contracts/` | one file per contract: the card template, the finding template, the change-evidence checklist, the ruling shape, the standing-delegation lists | **R** |
| `docs/ops/standing-delegation.md` | the two authority lists and the return-report shape | **R** |
| `skills/` | `squadops-repo`, `bounded-task-card`, `finding-record`, `verification-mechanics`, `release-cadence` | F, except the first two |
| `bench/` | cases, packets, oracles, the runner, records | **R** for the delegation experiment |
| `commissioning/` | the two work-package definitions and their evidence | **R** |
| `education/manifests/` | one source manifest per topic (§10A.3), plus an index recording where each manifest's generated formats live | F |
| `infrastructure/github/rulesets/` | exported ruleset JSON | **R** |
| `infrastructure/spark/` | the mode file, the guard, the launcher hook | **R** |

### 45.4 Infrastructure

| Item | Change | Reason | When |
|---|---|---|---|
| GitHub App `nostromo-brett` | register, install on `squad-ops`, Contents + PR + Issues read | Brett opens PRs now | **R** |
| GitHub App `nostromo-mother` | register, install on **`nostromo` only**, Issues write | the tracking board | **R** |
| GitHub App `nostromo-ash` | register; install on **both** repos — `squad-ops` with Contents + PR + Issues write, `nostromo` for `bench/` | Ash authors guards, fixtures and benchmark cases | **R** |
| Ash's Spark worktree | create `~/worktrees/squadops/ash`; validate the repository bootstrap and the unit suite in it | §9, plan §11.6–11.7 | **R** |
| GitHub App `nostromo-lambert` | register, install on **`nostromo` only**, Contents write for `education/` | Lambert curates manifests and never writes to SquadOps | F |
| Lambert's SquadOps checkout | read-only clone on the Mac; no worktree, no branch, no push remote | §10A.6 | F |
| Ash's Codex auth on the Spark | ChatGPT login flow completed on the Spark rather than the Mac; confirm the adapter reports ChatGPT-authenticated and that no `OPENAI_API_KEY` or `CODEX_API_KEY` is present | §2.7 host move; plan §8.5 | **R** |
| Apps `nostromo-parker`, `nostromo-ripley` | **add Issues read/write** — WP-1 §8.7 currently grants only Contents, Pull requests and Metadata | they must file Finding Records and Bounded Task Cards | **R** |
| `squad-ops` rulesets | add `nostromo-brett-branches` and `nostromo-brett-paths`; add `nostromo-ash-branches` and `nostromo-ash-paths` restricting Ash to `tests/**`; add a require-review-from-non-author rule to each identity ruleset | §12.1, §14; **the author of a proof must not be able to modify the thing proved** | **R** |
| `squad-ops` labels | add `nostromo:card`, `nostromo:lane-a`, `nostromo:lane-b` | provenance only | **R** |
| `nostromo` labels | lane and state labels for tracking issues | §25 | **R** |
| Brett's OpenCode permission profile | plan §11.11 denies production edit and commit/push; both must be allowed inside Brett's worktree and namespace, with merge still denied | Brett's role changed | **R** |
| Launcher preflight | add: Brett's App key present and resolving; Brett's branch namespace matches; Mother has no `squad-ops` write credential; the Spark mode permits this role; the reasoning profile resolves | §33 | **R** |
| Spark mode guard | `nostromo-spark-mode` and the launcher hook | §36.3 | **R** |

### 45.5 Tests

| File | Change | When |
|---|---|---|
| `tests/test_crew_config.py` | extend for the new capabilities, the two-lane lifecycle, Brett's identity and namespace, reasoning profiles, and Mother's absence from `squad-ops` write | **R** |
| `tests/test_contracts.py` (new) | every contract template exists and carries its mandatory field headings; the card template's five always-fields are present | **R** |
| `tests/test_spark_interlock.py` (new) | the guard's modes and exit codes | **R** |
| `tests/test_education_manifests.py` (new) | every manifest parses and carries `id`, `status`, `source_commit` (40 hex) and `captured`; `status` is `living` or `frozen`; a frozen manifest names its release tag; no manifest lists a source under `src/`, `adapters/`, or an issue or pull-request URL | F |

### 45.6 Specification and plan amendments

| File | Change | When |
|---|---|---|
| `docs/specs/NOSTROMO-0001-*.md` | the four amendments in §1.3, each as a dated amendment section rather than a silent edit | **R** |
| `docs/specs/NOSTROMO-PLAN-0001-*.md` | WP-1 §8.7 App permissions; WP-4 §11.11 Brett's permission profile; WP-9 persona content; WP-10 commissioning replaced by §40–§42 | **R** |
| `README.md` | resolve both open decisions: lifecycle store (§25) and reviewer checkout (§38.1) | **R** |
| `docs/source-baseline.md` | pin Brett's model and harness once §35.1 resolves | F |

### 45.7 On the envelope question

**Keep the generic handoff envelope as the transport, and add the concrete payload contracts separately.**
The envelope is correct, deliberately generic, and is what makes Mother's routing uniform across every
transition. Replacing it with per-transition shapes would put contract knowledge into the router, which is
exactly where it must not be. The payload rides inside it as a link plus a type.

---

# Part XV — Implementation Sequencing

## 46. Where this work sits against NOSTROMO-PLAN-0001

The existing plan's dependency graph is sound and is not replaced. WP-0 is done; WP-2 completed on
2026-09-08 with the Buzz relay live, closed and reboot-proven. This document's work attaches to the existing
packages rather than renumbering them.

```text
WP-0  repository scaffold                          DONE
WP-1  provider boundaries, GitHub identities        owner-blocked · amended by §45.4
WP-2  Jetson Buzz server                            DONE
WP-3  Mac cockpit and owner identity                gated on the owner's Buzz identity
WP-4  Spark base: Herdr, worktrees, Ollama          amended by §45.4 (Brett's profile, mode guard)
WP-5  mint seven Buzz identities                    gated on the relay hostname switch
WP-6  Spark local agents: Mother and Brett          amended: Brett writes now
WP-7  Spark cloud agents                            unchanged
WP-8  Mac agents                                    unchanged
WP-9  personas, instructions, channels              ← Phase 0 and 2 land here
WP-10 commissioning roll                            ← replaced by §40 and §41
WP-11 stabilization and baseline freeze             unchanged
WP-12 delegation experiment and evaluation          NEW (§42)
WP-13 1.8 activation                                NEW (§44)
```

### 46.1 The phases

**Phase 0 — Reconcile the design.** No infrastructure. Amend NOSTROMO-0001 with §1.3's four changes. Update
`crew/lifecycle.yaml` to two lanes, `crew/capabilities.yaml` to the new routing, `crew/manifest.yaml` for
Brett and Mother. Write the contract templates into `contracts/`. Extend the test suite. Owner reviews and
approves the shapes.
*Depends on:* nothing. *Blocks:* everything. *Verified by:* `uv run pytest` and owner acceptance.

**Phase 1 — Identity and infrastructure amendments.** Fold §45.4 into WP-1 and WP-4: the two new GitHub
Apps, the Issues permission on the existing two, Brett's rulesets and branch namespace, Brett's revised
OpenCode permission profile, the Spark mode guard and its launcher hook, the extended preflight.
*Depends on:* Phase 0, WP-1's owner console work. *Verified by:* an attribution probe per identity, a
ruleset rejection probe, and the interlock's exit codes.

**Phase 2 — Personas, doctrine and channels.** WP-9 as written, with this document's content: seven persona
files, the ten doctrine rules in `instructions.md`, the persona regression prompts, the channel conventions,
the allowlist matrix, and the synthetic handoff tests.
*Depends on:* Phases 0 and 1, and WP-5 through WP-8. *Verified by:* WP-9's existing gate plus a role-integrity
prompt per agent.

**Phase 3 — Contracts in practice.** Exercise each contract once on synthetic work before real work: a
Finding Record, a Bounded Task Card through to a Brett PR, a Change Evidence body, a Ruling Record, a
Standing Delegation. Mother's presence-check script lands here.
*Depends on:* Phase 2. *Verified by:* one artifact of each type, and the presence-check script rejecting a
card with a field removed.

**Phase 4 — Guardrails.** Merge authority rules, self-approval rejection, the interlock under a real
transition, budget exhaustion behaviour, and the deterministic checks proven by making each one fail.
*Depends on:* Phase 3. *Verified by:* each guard demonstrated failing, not merely passing. A guard proven
only by passing is a guard that has not been proven.

**Phase 5 — Commissioning.** §40 then §41, in that order, one at a time.
*Depends on:* Phase 4. *Verified by:* §43.1 criteria 1 through 6, 9, 10, 13.

**Phase 6 — Evaluation.** The delegation experiment (§42.1–42.2) and the reviewer challenge (§42.3). The
`pi`-versus-OpenCode comparison if the schedule allows, on the same model.
*Depends on:* Phase 5, and an idle box. *Verified by:* §43.1 criteria 7, 8, 12, 14.

**Phase 7 — 1.8 activation.** Declare the permitted archetypes (§44.1), take the first three work items
(§44.2), measure outcomes against the same vocabulary, and expand only on the graduation evidence in §44.3.
*Depends on:* the full §43.1 gate. *Verified by:* work landing in `squad-ops` 1.8 with zero silent failures.

### 46.2 Ordering constraints worth naming

- **Phase 0 has no dependency and blocks everything.** It is document and configuration work, doable now,
  in parallel with the owner's WP-1 console work.
- **The relay hostname switch must precede WP-5**, which is already a committed gate and is unaffected by
  this document.
- **Phase 6 needs an idle Spark.** It is the natural thing to run in a window where no counted set is live.
- **Commissioning B must use a real finding**, so it depends on there being one — which the tracker reliably
  supplies.

---

# Part XVI — The Twenty Design Questions

## 47. Recommendations

**1. Should Dallas adversarially review every Ripley design, or only risk-triggered ones?**
Only risk-triggered. Reviewing everything exhausts a $27 cap on work with no rework history and converts
adversarial review into the stamp it replaces. Ripley or Parker records the trigger line on every item, and
"no trigger" is an explicit, auditable statement rather than an omission.

**2. What exact risk criteria invoke Dallas upstream?**
The ten triggers in §11: architecture rules and guards; binding, removing or re-weighting a check; recovery
and correction semantics; evidence and observability semantics; cross-layer changes with silent-failure risk;
migration, pin and hash semantics; security and identity; broad refactors before the map is accepted; a
diagnosis with high uncertainty; and contradicting an accepted design without amending it.

**3. Does Parker own cross-layer defect diagnosis through implementation?**
Yes. Parker holds a Lane B item from `INVESTIGATING` to `VERIFYING` without a change of holder. The trace is
the fix's specification, and the record's worst outcomes came from routing interrupting reasoning, not from
insufficient separation.

**4. What kinds of work may Parker delegate to Brett?**
Work whose evaluation surface has been tabled and whose bounding proof exists and can fail: vocabulary sweeps
against a landed guard, guard authoring against a named shape, extraction against a reviewed map, scaffold
emitter fixes with no pin movement, instrument fields with a stated producer, dependency recompiles after the
policy is set, dead-code removal once the census exists. Never anything that concludes.

**5. What exact artifact constitutes the Bounded Task Card?**
A GitHub issue in `squad-ops`, labelled `nostromo:card`, with the eleven-field section order in §16.3. Five
fields always; three more when the seam has more than one reader; three when they earn their place.

**6. Where does that artifact live?**
`squad-ops`, because the repository's closure check requires every PR to close an open issue and Brett's work
produces a PR. That constraint decides it.

**7. How does Brett's harness load it?**
The launcher fetches the issue body by URL at session start and places it in the work-bootstrap layer. It is
the primary context. Brett does not receive the Buzz thread that produced it.

**8. What must be present in Brett's startup context?**
Identity and prohibitions including the forbidden-conclusions list; the ten doctrine rules; the repository
rules and the allowed tool set; the worktree and branch namespace; and the card in full. Roughly seven
thousand tokens plus the card.

**9. What must NOT be permanently loaded because of context cost?**
The five maintainer analysis documents in full; repository or git history; other work items' threads; full
issue comment histories; prior conversation across work items. Procedural knowledge goes to skills; precedent
goes behind links in the card.

**10. What exactly does Buzz persist?**
The work item and its identifier, the lane and state, the active holder, links to canonical artifacts, the
capability requested, escalations, PR and review and merge events, and the terminal state. Every one is a
routing or addressing fact. No engineering content.

**11. What stays canonical in GitHub?**
Everything else: designs, findings, cards, code, tests, evidence, rulings, records, and the crew's own
lifecycle state as tracking issues in the `nostromo` repository.

**12. How does Mother route work without fragmenting diagnostic continuity?**
By recording rather than reassigning between `INVESTIGATING` and `VERIFYING`. Mother updates state, surfaces
progress and checks artifacts. Mother does not insert a handoff at a state boundary, does not request a
narrative mid-trace, and does not change the holder when the item loops back to `INVESTIGATING`.

**13. Who interprets verification-set results?**
Ripley proposes; the owner rules on counted, void, reset and supersession. Mother runs the mechanics and
never concludes.

**14. What is Mother's role in measurement?**
Freezing the pre-registration by commit hash, preflight, detached launch, gate approval with the constant
copied verbatim, collection, render, and preserving perishable evidence. Reporting refusals verbatim without
interpreting any of them away.

**15. When does Dallas review Brett's work, versus Parker only?**
Parker only, by default. Dallas reviews a Brett PR only when the change lands on a seam that trips a risk
trigger — which should be rare, because if a trigger fired the prior question is why it was delegated.

**16. Who has mechanical merge rights versus approval authority?**
Approval: Parker for Brett's work; Dallas for significant Parker work; the owner for architecture and
anything owner-reserved. Merge into `main`: owner-reserved by default, delegable to Mother for a named class
under a Standing Delegation, where Mother's act is mechanical — approval present, every job green including
the non-required ones, closure reference resolving.

**17. What prevents self-approval?**
A GitHub ruleset requiring review from a non-author; the launcher refusing to mint a token for an approval on
an agent's own PR; and the constitution, in that order. The first is the one that holds.

**18. What prevents concurrent counted SquadOps execution and conflicting Nostromo activity on the Spark?**
The two-mode interlock in §36: a mode file, a guard script that every local launcher calls at startup, no
repository mutation during a counted run, and the crew's model residency recorded in the deploy identity.

**19. What first 1.8 archetypes are safe for the crew?**
A bounded Lane B defect whose causal layer is established; an architecture guard against an already-decided
rule; a bounded extraction against an accepted map. None of the 1.8 headline features.

**20. What evidence graduates Brett to more difficult task classes?**
Per archetype, per harness, per model configuration: at least a dozen runs across at least four distinct
tasks, nearly all passing or escalating correctly, **zero silent failures ever**, and no repeated failure
classified as implementation capability. Qualification expires on any model tag, quantization or harness
change.

---

# Part XVII — Reference

## 48. Recommended crew roster

| Identity | Role | Model | Harness | Machine | Authority | Primary inputs | Primary outputs | Reviewer / escalates to |
|---|---|---|---|---|---|---|---|---|
| **Mother** | Coordination and control plane | Qwen3.6 35B-A3B, local | OpenCode ACP | Spark | routes, records state, checks artifact presence, runs measurement mechanics, enforces the interlock; **no technical judgment** | GitHub and Buzz events, tracking issues, capability table | routed handoffs, state transitions, collected artifacts, surfaced escalations | owner |
| **Ash** | Science Officer: proof, evidence and evaluation | ChatGPT Plus subscription, $20 fixed | Codex ACP | **Spark** | owns proof infrastructure and the crew's benchmark; path-scoped to `tests/**`; **no review of work in flight** | rules about to land, findings needing precedent, benchmark cases | guards that fire on their motivating commit, replays and fixtures, corpus counts, blinded scores, research artifacts | Dallas for guards, Parker for fixtures |
| **Ripley** | Architect and technical lead | GPT-5.6 Sol, `nostromo-ripley`, $27 | Codex ACP | Spark | architecture direction, design artifacts, measurement interpretation, resolves escalations from the crew | objectives, SIPs, plans, standards, records | acceptance sources, dispositions, roll readings | Dallas challenges; escalates to owner |
| **Dallas** | Independent adversarial assurance | Claude Opus, `nostromo-dallas`, $27 | Claude ACP | Spark | blocking objections that must be dispositioned; default independent approver for significant Parker work | designs, PRs, repository state | the §19.3 return; review outcomes | owner, on unresolved disagreement |
| **Parker** | Primary engineer | GPT-5.6 Sol, `nostromo-parker`, $65 | Codex ACP | Spark | implements, traces, decomposes, writes cards, reviews Brett, reclaims work | accepted designs, Finding Records | implementations, Bounded Task Cards, change evidence | Dallas reviews; escalates to Ripley or owner |
| **Brett** | Supporting engineer | Qwen local, coding-capable *(experiment, §35.1)* | OpenCode ACP *(comparison pending)* | Spark | bounded implementation inside the card; **concludes nothing** | one Bounded Task Card | a PR with raw evidence, or an escalation naming the condition | Parker |
| **Lambert** | Knowledge projection and source curation | Gemini subscription, $0 incremental | Gemini ACP | Mac | curates source manifests; **read-only on SquadOps**, writes only `education/` in the Nostromo repo; artifacts are never a source | closed release lines, the lessons corpus, landed standards | pinned source manifests and the formats generated from them | Mother; blocks nothing |
| *(Kane)* | *harness experiment slot, not a crew member* | Brett's model, held constant | the harness under test | Spark | none | benchmark cases | outcome-class distributions | — |

## 49. Feature sequence, end to end

```text
owner objective ─▶ Mother opens tracking issue (Lane A) + #nostromo-<item>
                          │
                   @Ash (if external evidence or precedent needed) ─▶ artifact, linked
                          │
                   @Ripley ─▶ reads canonical GitHub in Ripley's worktree
                          │     authors the acceptance source; commits; posts the
                          │     framing + link + the risk-trigger line
                          │
              trigger? ───┴── no ──────────────────────────────┐
                   │ yes                                        │
              @Ash ─▶ measures the corpus the rule will apply  │
                   │     to; reports the count                  │
                   ▼                                            │
              @Dallas ─▶ challenges: claim, evidence inspected, │
                   │     blocking, non-blocking, unresolved,    │
                   │     falsification, recommendation          │
                   │     (armed with Ash's count)               │
                   ▼                                            │
              Ripley dispositions each blocking point IN THE     │
              ARTIFACT, commits, posts the summary              │
                   │                                            │
                   └────────────┬───────────────────────────────┘
                                ▼
                   owner acceptance ─▶ ACCEPTED (ruling recorded, dated)
                                ▼
                   @Parker ─▶ implements directly
                          └──▶ or writes Bounded Task Cards (squad-ops issues)
                                     │
                          Mother checks mandatory fields present
                                     │
                          @Brett per card ─▶ works in Brett's worktree
                                     │        ─▶ PR, or escalation
                                     ▼
                          Parker reviews against the card
                                     ▼
                   Dallas reviews Parker's own work where risk warrants
                                     ▼
                   approval recorded ─▶ merge (§12.1) ─▶ OBSERVING
                                     ▼
                   Ripley reads the observation ─▶ CLOSED; channel archived
```

## 50. Defect sequence, end to end

```text
finding arrives
  │  a verification-set record, a red on main, a live cycle verdict, an owner observation
  ▼
Mother opens the Finding Record (squad-ops issue) with identifiers and the QUOTED line,
opens the tracking issue (Lane B, FINDING), posts the header
  ▼
@Parker ────────────────────────────────────────────────┐
  ▼                                                      │
INVESTIGATING   Parker traces in Parker's worktree       │  ONE HOLDER
  ▼             updates Finding Record fields 2–4        │  Mother records,
DIAGNOSED       mechanism read to file:line              │  does not reassign,
  ▼             ruled-out causes recorded with evidence  │  does not interrupt
FIX_FRAMED      layer, seam, proof named + trigger line  │
  │                                                      │
  ├── T9 fired? ─▶ @Dallas challenges the DIAGNOSIS      │
  │               before the fix is built                │
  ▼                                                      │
IMPLEMENTING    Parker implements                        │
  │             or cuts a card for a bounded slice ─▶ Brett
  ▼                                                      │
VERIFYING       the replay; the WIRING test at the live  │
  │             caller; the affected suites              │
  │                                                      │
  ├── new seam discovered? ──▶ back to INVESTIGATING ────┘  (legal loop, same holder)
  ├── premise falsified? ────▶ ESCALATED; Finding Record corrected in place, dated
  ▼
REVIEW ─▶ Parker reviews Brett; Dallas reviews Parker where risk warrants
  ▼
MERGED ─▶ OBSERVING (the next shakeout or live cycle) ─▶ CLOSED
```

## 51. Parker → Brett sequence

```text
1. FRAME      Parker establishes the bounding proof exists.
              No proof ⇒ no card. Parker does the work instead.

2. WRITE      Parker opens the card as a squad-ops issue:
              objective · proof · mechanism · allowed scope · prohibited ·
              escalate-and-stop   [+ seam table · mirror rule · paired control
                                    when the seam has more than one reader]

3. CHECK      Mother verifies mandatory fields are PRESENT. Missing field ⇒
              returned to Parker with the field named. Mother judges nothing else.

4. ASSIGN     Mother @Brett in a thread: the envelope + the card URL.

5. LOAD       Brett's launcher fetches the card into the work-bootstrap layer.
              Brett does not receive the surrounding discussion.

6. VERIFY     Brett re-verifies the premise against current main and confirms the
              named proof RUNS and CAN FAIL.
                 ├─ proof absent / cannot fail / premise does not reproduce
                 │     ⇒ RETURN THE CARD. ESCALATED_CORRECTLY. Not a failure.
                 └─ otherwise continue

7. WORK       Brett implements in Brett's worktree, branch nostromo/brett/<item>,
              inside the allowed paths only.
                 └─ escalation condition fires at any point ⇒ stop, report which one

8. PROVE      Brett runs the named proof and the affected suites.
              Returns raw output with the paired control and what it did.
              Brett states what ran. Brett does not state that anything is clean.

9. PR         Brett opens the PR; the body is the Change Evidence contract, with
              `Closes #<card>`.

10. REVIEW    Parker checks five things (§19.1): objective met · scope held ·
              the proof ran and could have failed · no escalation condition ignored ·
              tests and evidence adequate with a control.
                 ├─ card was wrong    ⇒ Parker fixes the card and re-issues,
                 │                       classified as a FRAMING result, not Brett's
                 ├─ work incomplete   ⇒ request changes with the field named
                 └─ satisfied         ⇒ approve

11. MERGE     Per §12.1. Card issue closes with the PR.
```

## 52. Ripley ↔ Dallas sequence

```text
BEFORE IMPLEMENTATION  (risk-triggered — this is the primary interaction)

  Ripley ──▶ proposal + the acceptance source + the enumerated surface
             + "T2, T4 fired"
                     │
  Dallas  ◀──────────┘   reads the ARTIFACT and the REPOSITORY,
                         not the Buzz narrative
                     │
             returns:  Claim challenged      (quoted)
                       Evidence inspected    (what Dallas actually read)
                       Blocking objections   (each with the invariant + file:line)
                       Non-blocking concerns
                       Unresolved questions
                       Suggested falsification
                       Recommendation
                     │
  Ripley  ◀──────────┘
             dispositions EVERY blocking point IN THE ARTIFACT:
             numbered · ACCEPT / ACCEPT WITH SHAPE / ANSWERED / REJECTED ·
             what it changes · what it explicitly does not change
                     │
             ┌───────┴────────┐
             │                │
      converged          unresolved material disagreement
             │                │
             ▼                ▼
      implementation     OWNER RULES  (not averaged, not won by persistence)
        may begin        the ruling is written where the decision lives, dated
                                │
                                ▼
                         implementation may begin


AFTER IMPLEMENTATION  (Parker's PR, where risk warrants)

  Parker ──▶ PR + Change Evidence
                     │
  Dallas  ◀──────────┘   tests each claim against repository state
                         "byte-identical" ⇒ run the comparison
                         "regression green" ⇒ check it was the whole gate
                         "verified in container" ⇒ check it was a live call
                     │
             returns the same vocabulary, plus
             RETURNED FOR ARTIFACT where a claim may be true but
             the evidence does not establish it
                     │
  Parker  ◀──────────┘  supplies the artifact, not a restatement
```

## 53. Responsibility boundaries

### 53.1 Buzz

**Buzz owns.** Stable agent identity and addressing. Presence. Message delivery and the @mention that
constitutes a handoff event. Channel and thread scoping, which is also the context boundary. The routing
signal that tells Mother something happened. A durable, human-readable trace of the collaboration.

**Buzz does not own.** The work artifact. The design. The evidence. Any decision. The authoritative lifecycle
state. Any SquadOps concept — Buzz does not know what a cycle, a roll, or a gate decision is, and must never
be taught. Anything an agent will act on as fact.

**The operational rule.** A Buzz message may carry a link and a one-line summary. When a crew member states
a number, a path or a verdict in Buzz, that is a pointer to where the fact is recorded, and the receiving
agent reads it there. No agent treats a message as a source.

### 53.2 The harness

**The harness owns.** Executing the agent's turn. Tool invocation inside its permitted set. Reading and
writing the worktree it was given. Running commands and returning their real output. Speaking ACP to
`buzz-acp`. Enforcing the tool allowlist it was configured with.

**The harness does not own.** Identity, which is Buzz's and the launcher's. Authority, which is the persona's
and this document's. What work exists, which is GitHub's. Which model it uses or what it costs, which is the
launcher's and the provider boundary's. Whether its output is correct, which is the reviewer's.

**The boundary that matters.** The harness executes; it does not decide what to execute. A harness that
starts making routing or authority decisions has absorbed responsibility belonging to Mother or to the
constitution, and the correct fix is to move it back.

### 53.3 GitHub

**GitHub owns.** Canonical engineering truth. Code, branches, commits, pull requests, tests, CI results.
Design artifacts, standards, maps, SIPs and plans. Finding Records and Bounded Task Cards as issues. Change
Evidence as PR bodies. Rulings, written where the decision lives. Generated evidence: deploy identities,
pre-registrations, records. The crew's lifecycle state, as tracking issues in the `nostromo` repository.
Server-side enforcement of branch, path and review boundaries through rulesets.

**GitHub does not own.** Real-time coordination, which is Buzz's. Execution, which is the harness's and the
Spark's. Inference. The live deploy's state, which is only knowable from the deploy identity.

**The rule this boundary exists to serve.** If it is not in GitHub, it is not accepted. Anything the crew
agrees in conversation and does not write down did not happen, and a decision recorded only in a surface that
is later superseded is a decision that disappears.

## 54. SquadOps 1.8 entry criteria

Nostromo may modify real 1.8 code when all fourteen criteria in §43.1 hold. In short form:

1. Seven identities bootstrap and authenticate with stable keys.
2. Buzz routing reaches every allowlisted peer, and no one else.
3. Sessions recover from restart using GitHub and the tracking board.
4. Worktrees are isolated; Dallas reviews detached.
5. A Bounded Task Card reaches Brett complete, through Buzz, without owner relay.
6. Brett stays inside the card's allowed paths.
7. Parker catches a deliberately incorrect Brett change.
8. Dallas catches a planted high-risk trap.
9. Escalation reaches the right authority, and routine work does not trigger one.
10. No agent self-approves where independence is required.
11. The Spark interlock refuses deterministically.
12. Outcome classes are distinguishable in the records.
13. One feature flow and one defect flow complete end to end.
14. **Zero silent failures across all commissioning work.**

Criterion 14 is absolute and admits no threshold. The other thirteen are a minimum bar, not perfection, and
a criterion met with named remaining work is acceptable if the owner accepts the remaining work as a tracked
item.

## 55. Open decisions

Only what cannot be resolved from repository evidence. Everything else in this document is a recommendation,
made deliberately rather than deferred.

**OD-1. Brett's model and harness.** Whether a coding-tuned local variant outperforms the configured general
Qwen3.6 35B-A3B on bounded implementation, and whether OpenCode or `pi` is the better harness for it, cannot
be decided from the record — no local model has run this work. *Resolved by:* the §42 experiment and the
harness comparison, holding the model constant; neither needs ACP, so the comparison can precede any
integration work. *Interim:* Brett is commissioned on the configured model and OpenCode ACP.
*Consequence if unresolved:* Brett works, possibly below potential, which is acceptable.

**OD-2. Whether measurement needs its own role.** §37 assigns the function to Ripley and the owner and names
four conditions that would justify a dedicated Measurement Steward. Which way it goes depends on observed
load over a release line, which does not exist yet. *Resolved by:* one 1.8 line of observation.
*Interim:* Ripley carries it.

**OD-3. Whether Parker's $65 supports both framing and implementation.** The operating model gives Parker
two jobs, and the record's recent cadence was produced by frontier sessions with no per-session cap. Whether
one cap covers both at useful throughput is a measurement, not a judgment. *Resolved by:* one month of
observed spend. *Consequence:* if it does not, the options are reallocating from Ripley, raising the ceiling,
or reducing concurrency — an owner decision either way.

**OD-5. Whether Ash's subscription throughput supports a depended-on role.** Moving Ash onto the critical
production path of proof infrastructure assumes the rate limits leave enough capacity. The arithmetic in
§2.7 is sound; the throughput is not measured, because no local crew has run. *Resolved by:* one release
line of observed Ash availability. *Interim:* §9.4's release valve — a blocked implementer builds what they
need and Ash reviews the shape afterward, so Ash being unavailable never stops work.
*Consequence if wrong:* proof infrastructure moves to Parker, and Ash reverts to evaluation and research
only, which is still more than the original design gave it.

**OD-4. Whether the Lane B continuity rule survives contact with a real routed system.** The rule is derived
from a record where the holder was a person, and the claim that Mother's coordination will not fragment it
is an inference. *Resolved by:* Commissioning B, which is designed specifically to test it.
*Consequence if wrong:* Lane B needs a single frontier holder from trace through wiring test through
shakeout, with Mother reduced to observation only.

---

## 56. What success looks like

Not that the agents talk convincingly in Buzz.

> Whether their collaboration produces better, more reliable SquadOps changes with less frontier-model
> expenditure, while preserving or improving the engineering disciplines the repository learned through
> failure.

Measured as **paid tokens per passing change, at equal or better silent-failure count**, against a single
frontier engineer working the same cases. A reduction in paid tokens bought with one additional silent
failure is a worse result, not a cheaper one.

And underneath it, the division of labour this whole document exists to make operable:

> Frontier models spend their intelligence removing ambiguity, challenging dangerous assumptions and making
> expensive judgments. Local models perform as much bounded, mechanically provable engineering work as the
> evidence shows they can safely own.
