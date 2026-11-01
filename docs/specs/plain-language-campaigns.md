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
   in what order, and how success is measured. The result is readable text plus one structured
   `campaign-goal:` line.
3. **The draft step** (`campaignctl draft`, deterministic, no model) builds the full definition.
   - **Its inputs:** the goal, the product's entry in the project registry, and the request's size.
     It fills in the IDs, profiles, scope, policy limits, a generated name, the channel and the
     thread, the review count and the allowance.
   - **Its checks:** the broker validates the definition exactly as an approval would.
   - **Its output:** a readable card, with the definition as a record underneath.
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
  - the card is a Mother-signed event carrying exactly one `campaign-definition:` line and one
    `campaign-allowance:` line.
- **What binds it:** the card's event ID is the hash of its full content, so the reply binds the exact
  definition and allowance with nothing copied. Desktop can no longer alter the approval.
- **Freshness** goes from 30 minutes to 24 hours. A reply can only approve the card it points to, so a
  stale or replayed reply can approve nothing else.
- **The allowance:** the same reply creates the card's allowance. That retires the owner's CLI
  `approve-budget`, and the user-ID shortcut with it, which delivers the signed-approvals change in
  the trust model.
- **Launch:** approval launches. There is no second message.
- **Nothing else changes:** only the owner approves, definitions stay immutable by name, and
  allowances stay within the $25 / 60-call ceiling.

## Pieces to build

| Piece | What | Where |
|---|---|---|
| **Project registry** | One file per product: readable name, `project_id`, requirements document, allowed scope, profiles, default policy, size presets | `campaigns/projects/<name>.yaml`, by PR |
| **Draft step** | Builds and validates a definition from a goal, the registry and a size; prints the card and the record | `campaignctl draft`, broker read-only |
| **Approval by reply** | Card format, reply verification, allowance creation, approve-and-launch | broker and launch worker |
| **Plain reads** | A campaign overview by product name: state, increments accepted, latest ruling, next step, reviews used | broker read, used by Mother |
| **Decision cards** | Escalations and limit pauses post a card saying what happened, the options, and "reply continue or stop". A signed reply decides. | watcher and broker |
| **Crew prompts** | Mother: recognize campaign requests and status questions; route drafting to Ripley and the challenge to Dallas. Ripley: the `campaign-goal:` format. Dallas: the draft challenge. | personas and base prompts |

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

1. **Registry and draft step.** ShelfNote becomes the first registry entry, and Mother can post cards.
   Approval still uses today's line, copied from the card's code block.
2. **Approval by reply,** including the allowance and approve-and-launch. This retires owner-UID
   approvals.
3. **Plain reads and decision cards,** plus status in words.

## Open questions

- **Projects not in the registry.** Should Mother ask the owner to add one, or should Ripley propose
  an entry by PR?
- **Proposals that are never approved.** Should a card expire after 24 hours, with Mother saying so?
- **Several campaigns on one product at once.** Refuse, or allow?
