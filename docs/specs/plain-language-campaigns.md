# Plain-language campaigns

**Status:** proposed, 2026-11-01. Owner-directed exception to the harness freeze. Not built.

## The problem

On 2026-11-01, launching one ShelfNote campaign took all of this from the owner:
- a JSON definition, written by hand;
- an approval name, a channel ID and a thread ID;
- `campaignctl approve-definition --explain`;
- a line copied exactly. Desktop altered it (`docs/goals.md` became a Markdown link), so it no
  longer matched.
- an allowance created with a CLI command on the Spark;
- an event ID.

Mother then spent her whole round limit on a refused import and stopped without a word.

**The owner's requirement:** speak to the crew in normal language, with readable campaign goals, and
never need an ID, a command or a JSON document.

## What the owner does

```text
@Mother start a campaign on ShelfNote: work through the goals.md backlog, search first,
up to eight hours today.
```

Then, on the proposal card that comes back, one word:

```text
approve
```

Changes are asked for in words, such as "make it six increments" or "skip export", and produce a
new card. Status questions, decisions and stops are in words too ("how's ShelfNote going?", "stop
the ShelfNote campaign").

## The flow

1. **Mother recognizes a campaign request** and hands it to Ripley in a new thread in
   `#squadops-campaigns`. That thread becomes the campaign's thread.
2. **Ripley drafts the goal** from the product's own documents: what it is for, which backlog items,
   in what order, and how success is measured. The thread shows it as readable text. The
   structured goal travels in the message's record (see **Buzz is for people**).
3. **The draft step** (`campaignctl draft`, deterministic, no model) builds the full definition.
   - **Its inputs:** the goal, the product's entry in the project registry, and the request's size.
     It fills in the IDs, profiles, scope, policy limits, a generated name, the channel and the
     thread, the review count and the allowance.
   - **Its checks:** the broker validates the definition exactly as an approval would.
   - **Its output:** a readable card. The definition and allowance travel in the card's record, not
     in its text.
4. **Dallas challenges the draft** before the owner sees it. Is every goal testable? Is the scope
   right, and does it fit the product? Would the squad know what to build first? Dallas may attach
   suggested changes, as the persona allows.
   - **Nothing blocking:** the card goes to the owner, with Dallas's notes summarized.
   - **Blocking:** Ripley revises once.
   - **Still disagreeing:** the card goes to the owner showing both positions. Neither side wins by
     persistence (constitution, Disagreement).
5. **Mother posts the card:**

   > **ShelfNote: work the goals.md backlog**, search first
   > Up to 10 increments · stops after 8 hours, or Nov 4 9:02 am ET · reviews about $16 of a $25 allowance
   > Ripley rules each gate; Dallas checks each ruling · Dallas on the draft: not blocking (two notes)
   > *Reply **approve** to launch, or tell me what to change.*

6. **The owner replies "approve".** The broker launches, and the launch worker takes over.

## Approval by reply

Today an approval is a signed owner message containing an exact `campaign-definition:` line.
Proposed instead: **a signed owner reply to the card, whose first line is `approve`.**

- **What the broker verifies:**
  - the reply is signed by the owner's pinned key;
  - it is in an admitted campaign channel;
  - its reply tag names the card's event;
  - the card is a Mother-signed event whose record carries exactly one definition and one allowance.
- **What binds it:** the reply binds the exact definition and allowance through the card and its
  record, with nothing copied. The record is either a tagged companion event the card points to, or a
  digest of the record in the card's signed content. Desktop can no longer alter the approval.
- **Freshness** goes from 30 minutes to 24 hours. A reply can only approve the card it points to, so a
  stale or replayed reply can approve nothing else.
- **The allowance:** the same reply creates the card's allowance. That retires the owner's CLI
  `approve-budget`, and the user-ID shortcut with it, which delivers the signed-approvals change in
  the trust model.
- **Launch:** approval launches. There is no second message.
- **Nothing else changes:** only the owner approves, definitions stay immutable by name, and
  allowances stay within the $25 / 60-call ceiling.

## Buzz is for people, not a system log

Owner, 2026-11-01: Ripley and Dallas write to the thread in normal English, without campaign JSON.

**Today:** the JSON is in the message bodies because Buzz carries the signatures. The broker verifies
`campaign-job-result:`, `campaign-decision:`, `campaign-review:`, `campaign-launch:` and
`campaign-definition:` lines in the content of signed Buzz events. The watcher also pastes its
"Review control: {…}" state into its notices.

**Proposed: render and verify.** The full machine record isn't needed in Buzz. The signature exists to
make the thread a faithful public record: the words people read are the words the broker acted on.
Within the broker, the kernel's caller identity (`SO_PEERCRED`) already authenticates each worker.
- **The worker renders the English** as a fixed, deterministic function of its result: the verdict,
  the reasons and the next step. It posts it as a normal signed Buzz message.
- **It submits the full result to the broker** with that message's event ID.
- **The broker renders the same English from the result** and checks that the signed event says
  exactly that, and is signed by the role in the campaign's thread. Different words fail.
- **The binding** (campaign, gate, run, and for Dallas the ruling's digest) lives in the broker's
  record, matched by event ID. `campaignctl` shows it.

So the thread is all English, every message is signed, and there is no hidden tag, no second event
kind, and no relay change. A companion event of a non-chat kind (`buzz messages send --kind`) stays
a fallback, only if a record ever has to be verifiable on the relay alone.

**Owner approvals** still need the owner's signature, because the owner's key is the only proof of
approval. Under approval by reply, that signature is on a plain "approve".

**What the English says:**
- **Ripley:** the ruling and why, in a few sentences, with what the squad should do next.
- **Dallas:** blocking or not, the reasons, and any suggested change.
- **The watcher:** what changed, and what it means. For example: "The search increment was returned
  for revision; 2 of 34 reviews used; the squad is revising."

Fields such as event IDs, digests and request IDs stay in the record and out of the thread. An ID
appears only when a person needs one, which this design aims to make never.

## A readable control plane

Owner, 2026-11-01: Buzz is a human-readable collaboration and control plane, not a system log.
Beyond the English-only thread, that means:

**Who is doing what**
- **A separate identity for automatic posts.** The watcher and launch worker post today as Mother,
  so "Mother" sometimes means her judgement and sometimes a script. A non-model identity, for
  example "Campaign Desk", posts notices; Mother's name then means only Mother.
- **The squad as one actor.** "The squad is working on search", "The squad is revising the search
  proposal", with no breakdown by squad agent for now.
- **Whose move it is.** Every notice ends with who acts next: the squad, Ripley, Dallas, or the
  owner.

**When something needs the owner**
- **The owner is mentioned when it's the owner's move.** Escalations, parks, limit pauses and
  proposal cards tag the owner, so Desktop notifies them. Mentioning the owner starts no paid crew
  turn, while notices still mention no crew member.
- **One clear ask per card:** what happened, the options, and the reply to give ("approve",
  "continue", "stop"). Never a command.

**What the words say**
- **No IDs in what people read.** Campaigns are named for their product and number ("ShelfNote
  campaign 1"), increments for their feature ("search"), artifacts by filename. PRs and related
  messages are links.
- **Plain states and verdicts.** "The squad is proposing the next increment", not `at_proposal`;
  "sent back for revision", not `returned_for_revision`.
- **Times in ET, durations in words:** "started 10:46 am ET, about 40 minutes in".
- **Mother's own replies follow the same rules.** She gives an ID only when asked.

**At a glance**
- **A live campaigns canvas** in `#squadops-campaigns`, rendered by `sync-canvases.py` and refreshed
  on each state change. It shows each campaign, its stage, increments accepted out of the target,
  whose move it is (the owner's first), reviews used and hours left.

**Volume**
- **One post per meaningful change.** A ruling and Dallas's review become one "decided" post. A
  quiet campaign posts nothing.

## Pieces to build

| Piece | What | Where |
|---|---|---|
| **Project registry** | One file per product: readable name, `project_id`, requirements document, allowed scope, profiles, default policy, size presets | `campaigns/projects/<name>.yaml`, by PR |
| **Draft step** | Builds and validates a definition from a goal, the registry and a size; prints the card and the record | `campaignctl draft`, broker read-only |
| **Approval by reply** | Card format, reply verification, allowance creation, approve-and-launch | broker and launch worker |
| **Plain reads** | A campaign overview by product name: state, increments accepted, latest ruling, next step, reviews used | broker read, used by Mother |
| **Decision cards** | Escalations and limit pauses post a card saying what happened, the options, and "reply continue or stop". A signed reply decides. | watcher and broker |
| **Crew prompts** | Mother: recognize campaign requests and status questions; route drafting to Ripley and the challenge to Dallas. Ripley: the goal's structure. Dallas: the draft challenge. | personas and base prompts |

**Size presets** are stated on every card and changeable in words:
- small: 3 increments, 3 hours;
- medium: 6 increments, 6 hours;
- large: 10 increments, 8 hours.

Each preset's review count and allowance follow the runbook's per-increment estimate.

## Cost and time per proposal

- **Ripley's draft:** one interactive turn, on the order of $0.50–1.
- **Dallas's challenge:** one turn, on the order of $0.50–1. This comes from the Max credits once
  they are linked.
- **A revision,** if Dallas blocks, adds about the same again.
- **Time:** a few minutes before the card reaches the owner.

## Order of work

0. **Readable threads.** The watcher writes English. The review records move out of the message
   body (render and verify). Also in this phase: the Campaign Desk identity, whose-move-it-is
   lines, owner mentions on the owner's move, no IDs, plain states, ET times, and fewer posts. This comes first because it's the most visible, and it
   doesn't depend on the rest.
1. **Registry and draft step.** ShelfNote becomes the first registry entry, and Mother can post cards.
   Approval still uses today's line, copied from the card's code block.
2. **Approval by reply,** including the allowance and approve-and-launch. This retires owner-UID
   approvals.
3. **Plain reads and decision cards,** plus status in words, and the live campaigns canvas.

## Open questions

- **Projects not in the registry.** Should Mother ask the owner to add one, or should Ripley propose
  an entry by PR?
- **Proposals that are never approved.** Should a card expire after 24 hours, with Mother saying so?
- **Several campaigns on one product at once.** Refuse, or allow?
