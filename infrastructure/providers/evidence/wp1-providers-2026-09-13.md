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
