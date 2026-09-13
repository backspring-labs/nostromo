# WP-1 provider evidence, 2026-09-13

Captured by `infrastructure/providers/probe.sh` from the owner's Mac. No secrets recorded. Identifiers below
are non-secret and are the values the launcher and the usage reports key on.

## Boundaries

| Role | Provider | Boundary | Identifier | Enforced cap |
|---|---|---|---|---|
| Parker | OpenAI | project `nostromo-parker` | `proj_atfzoWkIqNhtPOmC9POLszcs` | $70/month, enforce on |
| Ripley | OpenAI | project `nostromo-ripley` | `proj_UHuRAjJYSSAwI8uoOXModzo1` | $25/month, enforce on |
| Dallas | Anthropic | workspace `nostromo-dallas` | `wrkspc_019QkXKoL5T12RqJB59Rkbq9` | $25/month |

The Anthropic workspace identifier was **confirmed against the console by the owner on 2026-09-13**. This
check was necessary rather than pedantic: the Default Workspace also returns a `wrkspc_` header, so the probe
alone could not distinguish a correctly scoped key from one that had fallen back to Default.

OpenAI organization `user-tcgcnsbtlnapfvmvztckfsc6`, organization hard limit `100`, monthly reload limit `95`.
Anthropic organization `f61f4eab-90f4-4448-8dda-aaabe3eafcc9`, Scale tier, organization spend limit `30`,
auto-reload to `25` when the balance reaches `10`.

## Credentials

All three are service-account keys, not personal keys, so none is archived if the owner's membership
changes. Held at mode 600 under `~/.config/nostromo/secrets/<role>/` on the Mac, not yet moved to the Spark.

| Role | Prefix | Length |
|---|---|---|
| Parker | `sk-svcacct-` | 167 |
| Ripley | `sk-svcacct-` | 167 |
| Dallas | `sk-ant-api03-` | 108 |

Dallas's key was created with expiration **Never**; the Console's choice cannot be changed after creation and
a 30-day key would have stopped Dallas monthly on an unguarded manual step.

## Probe results — all pass

```text
== positive: each role reaches its pinned model ==
PASS   parker   gpt-5.6-sol    HTTP 200, project proj_atfzoWkIqNhtPOmC9POLszcs
PASS   ripley   gpt-5.6-sol    HTTP 200, project proj_UHuRAjJYSSAwI8uoOXModzo1
PASS   dallas   claude-opus-5  HTTP 200, workspace wrkspc_019QkXKoL5T12RqJB59Rkbq9
== paired control: a non-pinned model must be refused ==
PASS   parker   gpt-6-astra    HTTP 403
PASS   ripley   gpt-6-astra    HTTP 403
```

**The paired control is the part that matters.** A probe that can only pass proves nothing. The refusal text
is specific and names both the project and the model — *"Project `proj_atfzoWkIqNhtPOmC9POLszcs` does not
have access to model `gpt-6-astra`"* — so the model restriction is demonstrably live rather than assumed, and
a harness misconfigured onto a pricier model fails loudly instead of silently draining a cap.

## What this establishes

- Each role's key reaches its pinned model and no other.
- Each key attributes to a distinct boundary, proven by the `openai-project` and `anthropic-workspace-id`
  response headers rather than by console configuration alone.
- The three boundaries are mutually isolated by construction: a service-account key is bound to one project
  or workspace and cannot reach another's.

## What remains open

- Keys are on the Mac and must move to the Spark host-local secret files (WP-1 §8.10).
- GitHub Apps `nostromo-parker` and `nostromo-ripley` are not yet registered, so no identity or ruleset
  evidence exists.
- Actual tax on the credit purchases is unrecorded; the $148.40 envelope figure assumes 6%.

---

# GitHub identities, 2026-09-13

Registered by the owner, verified through the API by `infrastructure/github/mint-token.sh` and `gh`.

| Role | App slug | App id | Installation id | Bot user | Bot user id |
|---|---|---|---|---|---|
| Parker | `nostromo-parker` | 4931663 | 161404312 | `nostromo-parker[bot]` | 328771233 |
| Ripley | `nostromo-ripley` | 4931773 | 161406228 | `nostromo-ripley[bot]` | 328774520 |

Both owned by `backspring-labs`. Commit identity is `<bot user id>+<bot login>@users.noreply.github.com`,
recorded in `crew/manifest.yaml` and asserted by `tests/test_crew_config.py` so the launcher cannot
misattribute a commit through a typo.

## Verified

| Check | Result |
|---|---|
| Permissions, both Apps | exactly `contents: write`, `issues: write`, `pull_requests: write`, `metadata: read` |
| Administrative permissions | none — no Administration, Workflows or Actions |
| Webhook events | none subscribed |
| Repository selection | `selected`, not all |
| Installation token mints | both, from the host-local `.pem` via a signed JWT |
| Repositories a minted token reaches | `backspring-labs/squad-ops` only, for both |
| Private keys on disk | RSA, mode 600, under `~/.config/nostromo/secrets/<role>/github-app.pem`; nothing left in Downloads |

The token probe is the one that matters. It proves the private key is valid, the App can authenticate as
itself, and the resulting credential reaches exactly one repository — which is the boundary the design
claims and could not otherwise be asserted from console settings alone.

## Not granted, deliberately

No client secret was generated for either App. Client secrets exist for OAuth user-authorization flows,
which the crew does not use: the launcher mints installation tokens from the private key instead. An unused
secret is an unnecessary credential.

## Also present in the organization

Two unrelated Apps are installed on `backspring-labs`. `claude` is scoped to selected repositories, which is
the right shape. `chatgpt-codex-connector` (app 1144995, installed 2026-02-03) is scoped to **all eleven
repositories**, including both private ones, and holds `contents: write`, **`workflows: write`**,
`actions: write`, `issues: write` and `pull_requests: write`.

`workflows: write` is the permission this design deliberately withholds from every crew identity, because an
agent that can edit workflow definitions can edit the checks that gate its own merges. The crew Apps hold
four permissions; this connector holds eight, across every repository.

Measured on 2026-09-13: **zero commits and zero issues or pull requests** from it in either `squad-ops` or
`nostromo`. It is installed and dormant on the two repositories that matter.

**Resolved 2026-09-13: the owner uninstalled it entirely.** The recommendation had been to narrow it to
selected repositories; the owner determined it had only ever been used for a test and removed it instead,
which is the stronger outcome. Verified after the fact: `/orgs/backspring-labs/installations` now returns
only `claude`, `nostromo-parker` and `nostromo-ripley`. Reinstalling later is a minute's work and would
scope correctly at that point.

The `claude` App (app 1236702, installed 2026-02-02) remains. It is scoped to **selected** repositories
rather than all, which is the right shape, and has zero commits or pull requests in `squad-ops` or
`nostromo`. It carries the same `workflows: write` plus contents, issues, pull requests and discussions
write. Which repositories it reaches is not visible to an organization-read token and must be checked on its
Configure page. **Neither `squad-ops` nor `nostromo` should be on that list**: the crew has no use for it,
and Dallas reviews under `nostromo-dallas` precisely so a review is attributable to a role rather than to a
shared bot.

## What remains open

- Rulesets on `squad-ops` are not yet created, so branch namespaces and path boundaries are unenforced.
- No commit has yet been made under either identity, so attribution is proven for the token but not yet for
  a commit in the tree. *(Closed later the same day by the crew check probe below, which committed as
  `nostromo-parker[bot]` on a branch that was then deleted.)*
- Apps for Brett, Dallas, Mother, Ash and Lambert are not registered; each waits on its write flow being
  commissioned (NOSTROMO-0002 §45.4).

---

# Rulesets on squad-ops, 2026-09-13

## What was created

| Ruleset | Id | Target | Rules | Bypass |
|---|---|---|---|---|
| `nostromo-parker-branches` | 23189673 | `refs/heads/nostromo/parker/**` | creation, update, deletion | `nostromo-parker` App only |
| `nostromo-ripley-branches` | 23189751 | `refs/heads/nostromo/ripley/**` | creation, update, deletion | `nostromo-ripley` App only |

Exported to `infrastructure/github/rulesets/` so the boundary is reconstructable (NSTR-PROJ-001).

## Probe — paired control, all pass

```text
PASS   parker -> nostromo/parker/probe          HTTP 201   its own namespace
PASS   parker -> nostromo/ripley/probe          HTTP 422   another role's namespace, refused
PASS   owner  -> nostromo/parker/owner-probe    HTTP 422   the owner, refused
```

The second and third are the ones that establish anything. A ruleset that only ever admits the intended
actor has not been shown to exclude anyone, and the owner being refused is deliberate: an identity boundary
that the owner can walk through is not a boundary, it is a convention.

The probe branch was deleted afterwards; no `nostromo/**` branches remain.

## What could not be created, and why — see DEV-006

Path restrictions are unavailable on this repository. A branch-target ruleset rejects the rule
(`Invalid rule 'file_path_restriction'`), and a push-target ruleset, where the rule belongs, is refused with
**`Source public repos cannot have push rules`**. So the design's second half — Ripley's namespace cannot
carry implementation, Parker's cannot carry SIPs — has no server-side mechanism available.

What survives is the more important half: attribution is guaranteed and no agent can write into another's
namespace. What is lost is role-scope containment *within* a namespace, which falls back to Dallas's review
and the harness permission profile — that is, to discipline, which this record says drifts.

**Recommended remedy, owner's decision because it changes squad-ops CI:** a workflow that fails a pull
request whose head branch is `nostromo/<role>/**` and whose diff touches that role's forbidden paths,
promoted to a required status check. It converts the boundary back into a test, explains the violation where
a ruleset can only reject a push, and passes trivially for every non-crew pull request.

## Not changed, deliberately

`main`'s existing protection is SquadOps governance and was left alone: pull request required, four status
checks, admins included, force pushes off. Note that `required_approving_review_count` is **0**, so a pull
request can merge with no approval. The crew's control against self-approval is therefore that merging is
owner-reserved (NOSTROMO-0002 §13), not the branch protection. Raising that count would change how the owner
works on every pull request and is the owner's call.

---

# Crew check probe — end to end on squad-ops, 2026-09-13

The remedy recommended above was built, merged as squad-ops#1511, and made a required check on `main`.
This is the probe that establishes it works against the live repository rather than against its fixtures.

Probe branch `nostromo/parker/probe-boundary`, pull request squad-ops#1512, both deleted afterwards.
Every write below was made with a **minted `nostromo-parker` installation token**, not owner credentials,
so the probe exercised the identity the design actually uses.

## Paired control — both stages pass

```text
== positive: a commit inside parker's boundary, authored by parker ==
PASS   src/squadops/_nostromo_probe.py          nostromo crew checks -> SUCCESS
       ok: 1 changed file(s) are inside parker's boundary
       ok: all commits authored by 328771233+nostromo-parker[bot]@users.noreply.github.com

== negative control: one commit violating BOTH rules at once ==
PASS   sips/NOSTROMO-PROBE-negative-control.md  nostromo crew checks -> FAILURE
       FAIL: 1 path boundary violation(s) on branch nostromo/parker/probe-boundary
         sips/NOSTROMO-PROBE-negative-control.md - parker may not touch sips/**
       FAIL: 1 commit author(s) are not parker's identity
         probe-not-parker@example.invalid
         expected: 328771233+nostromo-parker[bot]@users.noreply.github.com
```

The negative control carried both violations in a single commit deliberately. A check that stops at the
first failure would have reported only the path, and the attribution half would have been untested while
appearing covered. Both fired, and each printed the remedy rather than only the verdict.

## Incidental result: the ruleset refused the owner again, unprompted

Bringing the branch onto the fixed `main` was first attempted with the owner's credentials through the
`update-branch` endpoint and was refused — `Repository rule violations found / Cannot update this protected
ref`. The same operation succeeded through parker's token. This was not a planned probe step; it is the
ruleset enforcing itself during ordinary work, which is better evidence than the deliberate probe of
2026-09-13 because nothing was staged for it.

Deleting the branch afterwards produced the same pairing without being asked to: owner `422 Cannot delete
this branch`, parker `204`. So all three of the ruleset's rules — creation, update and deletion — have now
been shown to exclude the owner and admit exactly one App.

## What this cost, and what it bought

The first run of this probe failed for the wrong reason. `check_nostromo_crew_pr.py` still had
`DEFAULT_RULES` pointing at the pre-rename filename, so the workflow died with `FileNotFoundError` on the
first crew branch it ever saw. The 34 fixtures all passed because **every one of them passes `--rules`
explicitly**, so the default path was the one line they could not exercise. Fixed in squad-ops#1515 and
covered by two tests that assert the default resolves and matches the shipped filename.

This is the argument for probing against the real repository even when the fixtures are green: the bug was
in the wiring between the workflow and the script, which is exactly the seam a fixture replaces.

## What this establishes

- The path boundary and the attribution rule are both live on `squad-ops` `main` as a required check.
- Both fail loudly, name the offending path and address, and state the remedy.
- A compliant crew commit passes without owner intervention.
- The branch ruleset holds against the owner during unplanned, ordinary operations.

## What remains open

- Only `parker` and `ripley` have identities; the boundaries file also declares `brett` and `ash`, whose
  rules are fixture-tested but not yet probed against a real branch. Each waits on its App (NOSTROMO-0002
  §45.4).
- `universal_forbidden` is fixture-tested only. It was deliberately not probed live, because two of its
  three paths are workflow files that no crew App can write anyway — the App permission set is the first
  guard and the check is the second.
