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

**Recommended owner action: narrow it to selected repositories, excluding `squad-ops` and `nostromo`.** Not
removal, since it is OpenAI's official connector and legitimate wherever it is actually used. Only scope is
adjustable; an App declares its own permissions and the installer chooses only which repositories they apply
to.

This is design hygiene rather than a live exposure. The rulesets in §8.9 do constrain it, because a GitHub
App is not a bypass actor unless named as one and this one will not be. The residual is that an identity
with `workflows: write` can alter the definition of a check a ruleset requires — an edit those same rulesets
would see. The stronger argument is simply that a dormant parallel path holding broader access than any crew
member makes the boundary model harder to reason about while buying nothing.

## What remains open

- Rulesets on `squad-ops` are not yet created, so branch namespaces and path boundaries are unenforced.
- No commit has yet been made under either identity, so attribution is proven for the token but not yet for
  a commit in the tree.
- Apps for Brett, Dallas, Mother, Ash and Lambert are not registered; each waits on its write flow being
  commissioned (NOSTROMO-0002 §45.4).
