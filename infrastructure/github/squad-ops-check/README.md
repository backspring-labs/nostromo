# SquadOps crew checks

The crew's branch rulesets guarantee **who** may write to `nostromo/<role>/**`. They cannot
constrain **what** that identity writes, because GitHub refuses push rules on public source
repositories: a branch ruleset rejects `file_path_restriction` outright, and a push ruleset comes back
`Source public repos cannot have push rules`. See `docs/deviations.md`, DEV-006.

This is the substitute. It is a required status check rather than a push rule, so a wrong file can still
land on a crew branch — it just cannot merge, which is what matters given merging is owner-reserved.

## What it does

On every pull request it reads the head branch. If the branch is not `nostromo/<role>/...` it reports
success immediately and says nothing further. If it is, it makes two assertions and reports **both**
results, so a reader is never sent to fix one thing twice.

**Paths.** The changed files stay inside that role's declared boundary.

**Attribution.** Every commit is authored by that role's bot. This matters because the branch ruleset
guarantees only one App may *push* to a namespace, while the commit *author* is a separate field any git
config can set. A launcher that fails to export the author variables produces commits under whatever
identity the host happens to hold, and nothing announces it. The expected address is **derived from
GitHub** at check time rather than restated here, so the bot account stays the single owner of that fact.

| Role | Boundary |
|---|---|
| `ripley` | may not touch `src/**`, `adapters/**`, `tests/**` |
| `parker` | may not touch `sips/**` |
| `brett` | may not touch `sips/**`, `docs/architecture/**` |
| `ash` | **allowlist**: `tests/**` only |
| every role | may not touch the three files that define this boundary |

Ash is an allowlist rather than a denylist because the author of a proof must not be able to modify the
thing proved. Parker's exclusion of `sips/**` is not an obstacle to the amendment discipline: a divergence
from an accepted design returns to Ripley, which Operating Model §6 already requires, and this makes that
structural rather than remembered.

## Why it fails closed

A branch naming a role with no declared boundary **fails**. A namespace nobody has bounded is an unreviewed
boundary, not an unrestricted one. That is why `nostromo/mother/...` is rejected today: Mother has no
SquadOps write flow yet, and the day it does, its boundary gets declared before its namespace is used.

## Why the fixtures matter more than the code

A guard proves it fires on the commit that motivated it, and a check that cannot fail is no check at all.
`fixtures/cases.yaml` carries 18 path cases and 5 attribution cases, and `tests/test_crew_pr_checks.py` additionally asserts that **every declared role has both a passing and a
failing case**. A role covered only by green cases is a role whose boundary has never been demonstrated.

Run them here, before any of this reaches SquadOps:

```bash
uv run pytest tests/test_crew_pr_checks.py -q
```

## Installing it in squad-ops

`files/` mirrors the SquadOps tree. Copy it across in one pull request:

```text
.github/nostromo-crew-boundaries.yml            the rules
.github/workflows/nostromo-crew-checks.yml      the workflow
scripts/dev/check_nostromo_crew_pr.py           the checker
```

Then add **`nostromo crew checks`** to `main`'s required status checks. It passes trivially for every
pull request that is not from a crew branch, so it does not change how the owner works.

Two implementation details that are load-bearing. The job has **no `if:` condition**, because a required
check that reports "skipped" can leave a pull request waiting for a status that never arrives. And it reads
the changed files from the API rather than `git diff`, so it needs no history fetch and behaves identically
for a pull request opened from a fork.

## Where the rules live, and why not here

In `squad-ops`, because that is where they are enforced and a reader debugging a failed check should find
them next to the thing that failed. Keeping a second copy in `crew/manifest.yaml` would give one fact two
owners, which is the drift pattern the SquadOps record documents repeatedly. The copy in this directory is
the staging area for the pull request, not a second source of truth; once installed, `squad-ops` is
authoritative and this directory tracks it.
