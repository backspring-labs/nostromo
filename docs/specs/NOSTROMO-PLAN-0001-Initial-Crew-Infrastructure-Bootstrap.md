# NOSTROMO-PLAN-0001: Initial Crew and Infrastructure Bootstrap Plan

**Status:** Draft Execution Plan  
**Version:** 0.1  
**Date:** 2026-09-06  
**Owner:** Jason Ladd  
**Project:** Nostromo  
**Primary Product Under Development:** SquadOps  
**Requirements Baseline:** `NOSTROMO-0001-Development-Crew-Platform-Spec.md`  
**Document Class:** Nostromo Execution Plan — not a SquadOps SIP  
**Execution Style:** Host-scoped, probe-gated, evidence-bearing

---

# 1. Purpose

This plan implements the architecture and requirements defined by **NOSTROMO-0001: Development Crew Runtime, Collaboration, and Infrastructure Specification**.

The specification defines **what Nostromo is and what it must guarantee**. This document defines **how to bootstrap it in a controlled sequence** across the physical infrastructure:

- **GitHub** — Nostromo source of truth and SquadOps engineering record
- **Jetson Orin Nano Super** — always-on Buzz collaboration infrastructure
- **DGX Spark** — persistent core development agents, Herdr, Ollama, SquadOps worktrees, build/test runtime
- **Mac** — owner cockpit, Buzz Desktop, Herdr remote access, Ash, Lambert
- **OpenAI / Anthropic / Google / ChatGPT** — bounded external intelligence and subscription surfaces

The plan is intentionally divided into independent work packages because different steps execute on different hosts and have different failure domains.

The intended outcome is not merely that seven agents can answer messages. The outcome is a **reconstructable, cost-bounded, inspectable, persistent development crew** capable of collaborating through the SquadOps roadmap from idea exploration through architecture, adversarial review, implementation, verification, and closeout.

---

# 2. Governing Specification

This plan MUST be executed against:

> `NOSTROMO-0001-Development-Crew-Platform-Spec.md`

If an implementation step conflicts with that specification:

1. do not silently redefine the architecture;
2. document the contradiction;
3. determine whether it is:
   - a tooling/version implementation detail;
   - a temporary compatibility deviation;
   - or a true architecture contradiction;
4. only architecture contradictions should cause revision of NOSTROMO-0001.

This plan may refine commands, filenames, package versions, paths, and operational mechanics without revising the specification so long as the specification's contracts remain intact.

---

# 3. Execution Principles

## 3.1 Probe before dependency

Every work package has:

- prerequisites;
- execution scope;
- probes;
- expected evidence;
- a completion gate.

A downstream package MUST NOT assume an upstream capability exists merely because installation commands completed.

---

## 3.2 Fail closed on identity, budget, and secrets

The bootstrap MUST stop when any of these are ambiguous:

- which Buzz identity is active;
- which model/provider is active;
- which provider project/workspace is being billed;
- whether a hard spend boundary is configured;
- whether Ash is using ChatGPT subscription auth or an API key;
- whether the correct SquadOps worktree is active;
- whether a secret is being read from the intended protected location.

No agent should be allowed a "temporary" unrestricted credential that later becomes permanent by accident.

---

## 3.3 One logical identity, replaceable runtime

Agent identity is not the Herdr pane, model, API key, or harness.

Each commissioning step should prove that:

```text
logical agent
    + stable Buzz/Nostr identity
    + persona/crew configuration
    + runtime binding
    = current embodiment
```

Changing an embodiment later must not mint a new logical crew member.

---

## 3.4 Automate only after one manual path works

The preferred end state includes a generic `nostromo-agent` launcher and declarative manifests.

However:

1. prove one explicit manual launch path;
2. prove a second role using the same pattern;
3. then generalize into the launcher.

This prevents building an abstraction over incorrect assumptions.

---

## 3.5 Keep host responsibilities clean

The deployment MUST preserve:

```text
Mac
  human control plane + lightweight cloud-backed agents

Jetson
  stable Buzz collaboration infrastructure

Spark
  persistent development agents + local inference + SquadOps execution

GitHub
  canonical engineering record
```

Do not move services merely because the alternate host has spare capacity.

---

# 4. Target End State

```text
                                     GitHub
                            ┌───────────┴───────────┐
                            │                       │
                       nostromo repo           squadops repo
                            │                       │
                            │                 SIP/code/PR/tests
                            │                       │
                   declarative crew                │
                            │                       │
                            ▼                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         PRIVATE NETWORK / TAILSCALE                     │
│                                                                          │
│   MAC                         JETSON ORIN NANO          DGX SPARK         │
│   ───                         ─────────────────         ─────────         │
│   Buzz Desktop                Buzz relay                Herdr             │
│   Jason identity              Postgres                  Mother            │
│   Ash buzz-acp                Redis                     Ripley            │
│   Lambert process             MinIO                     Dallas            │
│   Herdr remote client         durable Buzz data         Parker            │
│                                                        Brett             │
│                                                           │              │
│                                                           ├─ Ollama      │
│                                                           ├─ Qwen 35B    │
│                                                           └─ worktrees   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

All seven logical agents communicate through the same Buzz relay.
```

---

# 5. Work Package Map

| Work Package | Primary Surface | Outcome | Depends On |
|---|---|---|---|
| **WP-0** | GitHub / Mac | Nostromo repo and bootstrap control structure | none |
| **WP-1** | Provider consoles + GitHub | Hard spend, credential, and GitHub identity isolation | WP-0 |
| **WP-2** | Jetson | Production Buzz server online | WP-0 |
| **WP-3** | Mac + Jetson | Owner identity, Buzz Desktop, relay membership/control | WP-2 |
| **WP-4** | Spark | Herdr, worktrees, Ollama/Qwen baseline | WP-0 |
| **WP-5** | Jetson + repo | Stable seven-agent Buzz identities and membership | WP-2, WP-3 |
| **WP-6** | Spark | Mother and Brett local-agent runtime | WP-1, WP-4, WP-5 |
| **WP-7** | Spark | Ripley, Dallas, Parker cloud-agent runtime | WP-1, WP-4, WP-5 |
| **WP-8** | Mac | Ash and Lambert runtime | WP-3, WP-5 |
| **WP-9** | Buzz + repo | Channels, allowlists, personas, crew instructions, workflow conventions | WP-5–8 |
| **WP-10** | All | End-to-end SquadOps commissioning roll | WP-9 |
| **WP-11** | All | Stabilization, recovery tests, documentation, baseline tag | WP-10 |

Parallelism is possible after WP-0:

```text
                         WP-0
                    ┌─────┼─────┐
                    ▼     ▼     ▼
                  WP-1  WP-2  WP-4
                         │
                         ▼
                       WP-3
                         │
                         ▼
                       WP-5
                    ┌────┼────┐
                    ▼    ▼    ▼
                  WP-6 WP-7 WP-8
                    └────┼────┘
                         ▼
                       WP-9
                         ▼
                      WP-10
                         ▼
                      WP-11
```

---

# 6. Global Naming and Path Conventions

The implementation agent SHOULD choose exact absolute paths appropriate to each host, but the plan assumes the following logical conventions.

## 6.1 Repositories

On Spark:

```text
~/src/nostromo
~/src/squadops
```

or equivalent.

Independent SquadOps worktrees:

```text
~/worktrees/squadops/ripley
~/worktrees/squadops/dallas
~/worktrees/squadops/parker
~/worktrees/squadops/brett
```

The exact root may use Herdr's own worktree path support if that integrates cleanly.

---

## 6.2 Secrets

Spark:

```text
~/.config/nostromo/secrets/
    mother.env
    ripley.env
    dallas.env
    parker.env
    brett.env
    buzz-common.env
```

Mac:

```text
~/.config/nostromo/secrets/
    ash.env
    lambert.env
    buzz-common.env
```

Jetson:

```text
<protected Buzz deploy directory>/.env
```

Permissions on secret files should be owner-only.

---

## 6.3 Logs

Prefer:

```text
~/.local/state/nostromo/logs/
```

with one logical stream per agent/runtime.

Logs MUST NOT contain secrets.

---

## 6.4 Runtime manifests

Repository:

```text
runtime/manifests/<agent>.yaml
```

---

# 7. WP-0 — Create and Scaffold the Nostromo Repository

**Execution surface:** Mac / GitHub  
**Primary requirement references:** NSTR-PROJ-001 through NSTR-PROJ-005  
**Goal:** establish the declarative source of truth before infrastructure is configured.

---

## 7.1 Prerequisites

- GitHub access
- git and GitHub CLI or equivalent
- local copy of `NOSTROMO-0001-Development-Crew-Platform-Spec.md`
- this plan

---

## 7.2 Create the private repository

Create a private GitHub repository named:

```text
nostromo
```

Do not fork Buzz.

Do not initialize it inside SquadOps.

Clone it to the Mac.

---

## 7.3 Commit governing documents first

Place:

```text
NOSTROMO-0001-Development-Crew-Platform-Spec.md
NOSTROMO-PLAN-0001-Initial-Crew-Infrastructure-Bootstrap.md
```

at the repository root or under a `docs/specs/` convention if a clear document hierarchy is preferred.

The filenames MUST be stable and references between them preserved.

---

## 7.4 Create the minimum source layout

Initial scaffold:

```text
nostromo/
├── README.md
├── NOSTROMO-0001-Development-Crew-Platform-Spec.md
├── NOSTROMO-PLAN-0001-Initial-Crew-Infrastructure-Bootstrap.md
├── .gitignore
│
├── .plugin/
│   └── plugin.json
│
├── instructions.md
├── agents/
├── crew/
├── runtime/
│   ├── manifests/
│   ├── launchers/
│   └── env/
├── infrastructure/
│   ├── buzz/
│   ├── herdr/
│   └── mac/
├── workflows/
├── docs/
└── tests/
```

Do not create dozens of empty placeholder files solely to match the final spec structure.

---

## 7.5 Establish `.gitignore`

At minimum exclude:

```text
.env
.env.*
*.secret
secrets/
auth.json
credentials*
*.key
*.pem
.nostr*
.local/
state/
logs/
```

Be careful not to ignore committed `.example` environment templates.

---

## 7.6 Create the first crew manifest

Create a machine-readable manifest containing the baseline roster and non-secret configuration.

The first schema may be simple, but it MUST distinguish:

- logical identity;
- capability;
- host;
- supervisor;
- harness;
- model;
- provider;
- budget profile;
- workspace profile;
- Buzz public key placeholder;
- inbound author policy.

Example shape:

```yaml
version: 1

agents:
  mother:
    display_name: Mother
    capability: orchestration
    host: spark
    supervisor: herdr
    harness: opencode-acp
    model: qwen3.6-35b-a3b
    provider: ollama
    budget_profile: local
    buzz_pubkey: null

  ash:
    display_name: Ash
    capability: ideation_research
    host: mac
    supervisor: launchd
    harness: codex-acp
    provider: chatgpt
    budget_profile: chatgpt-plus
    buzz_pubkey: null

  ripley:
    display_name: Ripley
    capability: architecture
    host: spark
    supervisor: herdr
    harness: codex-acp
    provider: openai
    model: gpt-5.6-sol
    budget_profile: ripley
    buzz_pubkey: null

  dallas:
    display_name: Dallas
    capability: adversarial_review
    host: spark
    supervisor: herdr
    harness: claude-agent-acp
    provider: anthropic
    model_family: opus
    budget_profile: dallas
    buzz_pubkey: null

  parker:
    display_name: Parker
    capability: implementation
    host: spark
    supervisor: herdr
    harness: codex-acp
    provider: openai
    model: gpt-5.6-sol
    budget_profile: parker
    buzz_pubkey: null

  brett:
    display_name: Brett
    capability: verification
    host: spark
    supervisor: herdr
    harness: opencode-acp
    provider: ollama
    model: qwen3.6-35b-a3b
    budget_profile: local
    buzz_pubkey: null

  lambert:
    display_name: Lambert
    capability: google_knowledge
    host: mac
    supervisor: launchd
    harness: gemini-acp
    provider: gemini
    budget_profile: existing-subscription
    buzz_pubkey: null
```

This is not yet the final schema. It is the first executable source of truth.

---

## 7.7 Create budget definitions

Create a machine-readable budget file:

```yaml
monthly_incremental_ceiling_usd: 150

profiles:
  chatgpt-plus:
    type: fixed
    amount_usd: 20

  parker:
    type: provider_hard_limit
    provider: openai
    amount_usd: 65

  ripley:
    type: provider_hard_limit
    provider: openai
    amount_usd: 27

  dallas:
    type: provider_hard_limit
    provider: anthropic
    amount_usd: 27

  local:
    type: local_inference
    metered_api_usd: 0

  existing-subscription:
    type: excluded_existing_subscription
    incremental_usd: 0
```

Add a validation test asserting:

```text
20 + 65 + 27 + 27 = 139
139 < 150
```

---

## 7.8 Create environment templates

Example files should define names only:

```text
runtime/env/parker.env.example
runtime/env/ripley.env.example
runtime/env/dallas.env.example
runtime/env/mother.env.example
runtime/env/brett.env.example
runtime/env/ash.env.example
runtime/env/lambert.env.example
```

No real credentials.

---

## 7.9 Add source provenance document

Create:

```text
docs/source-baseline.md
```

Record:

- Buzz repository/version or commit selected later
- Herdr version
- OpenCode version
- codex-acp version
- claude-agent-acp version
- Gemini CLI version
- Ollama version
- Qwen tag/quantization
- date validated

Initially values may be `TBD`.

This file becomes the dependency ledger.

---

## 7.10 WP-0 verification

Verify:

- repo is private;
- spec and plan are committed;
- no secrets in history;
- manifest parses;
- budget validation passes;
- `.gitignore` behaves correctly.

---

## 7.11 WP-0 completion evidence

Commit or PR should contain:

```text
Nostromo repo URL
baseline commit SHA
manifest path
budget validation result
secret scan result
```

---

## 7.12 WP-0 gate

Do not begin generating real agent credentials until the repo structure can represent their public identities without storing private material.

---

# 8. WP-1 — Provider Projects, Workspaces, GitHub Identities, Authentication, and Hard Limits

**Execution surface:** Provider consoles + GitHub organization settings + Mac  
**Goal:** make cost isolation and crew GitHub identity exist before cloud-backed agents are launched.

---

# 8.1 OpenAI — Parker project

Create a dedicated OpenAI project logically named:

```text
nostromo-parker
```

Configure:

- Parker-specific API credential/service account;
- permitted model usage constrained to the intended model family where practical;
- project rate limits appropriate to a single agent;
- enforced monthly spend limit: **$65**;
- alert(s) below the hard limit if useful.

Current OpenAI support documentation distinguishes enforced project spend limits from mere notifications and exposes `project_spend_limit_exceeded` when an enforced project limit is hit.

The execution agent MUST verify the current UI explicitly shows enforcement, not only a notification threshold.

Do not rely on a project page that says the value is merely a soft budget.

---

# 8.2 OpenAI — Ripley project

Create:

```text
nostromo-ripley
```

Configure:

- distinct API credential/service account;
- intended model;
- project rate limits;
- enforced monthly spend limit: **$27**.

Parker and Ripley MUST NOT share credentials.

---

# 8.3 OpenAI organization-level sanity check

The organization-level controls must not invalidate the project design.

Check:

- approved organization usage is high enough for both projects;
- any organization hard limit is compatible with the desired aggregate cap;
- project attribution is visible in usage reporting.

If possible, create a higher-level organization safety boundary consistent with the full Nostromo API budget, but do not accidentally block non-Nostromo OpenAI API workloads belonging to the owner.

---

# 8.4 Anthropic — Dallas Workspace

Create an Anthropic Workspace:

```text
nostromo-dallas
```

Create a Workspace-specific API key.

Configure:

- intended Claude Opus tier/model access;
- workspace rate limits if configurable;
- Workspace Spend Limit: **$27**.

Anthropic's current documentation states that Workspace API keys are tied to the Workspace and that Workspace Spend Limits are evaluated alongside organization limits.

---

# 8.5 ChatGPT Plus — Ash

Ash's target is subscription-backed Codex ACP use.

On the Mac:

1. install the current official/community ACP adapter package selected for Codex;
2. authenticate through the adapter's ChatGPT login flow;
3. ensure no `OPENAI_API_KEY` or `CODEX_API_KEY` is present in Ash's runtime environment;
4. verify the adapter reports or behaves as ChatGPT-authenticated.

The current `codex-acp` documentation supports ChatGPT account authentication and also supports API keys. That dual capability is why the absence of an API key must be deliberate for Ash.

---

# 8.6 Gemini — Lambert

Confirm the existing Gemini account/CLI authentication.

Validate current Gemini CLI ACP capability:

```text
gemini --acp
```

Current Gemini CLI documentation exposes `--acp`, but its ACP mode is still described as under development.

Therefore Lambert is commissioned after the critical path.

If ACP is not reliable enough:

- do not redesign Nostromo during this work package;
- record the limitation;
- propose a bounded adapter/process alternative;
- require owner approval for the deviation.

---

# 8.7 GitHub — Crew Identities as GitHub Apps

Ripley and Parker push branches and open pull requests against `squad-ops`. Those writes MUST attribute to the crew member, never to the owner's personal account (NSTR-ID-006).

GitHub's Terms of Service allow one free machine account per person, so crew members are **GitHub Apps** owned by `backspring-labs`, not user accounts. An App has its own bot identity, private key, fine-grained permissions, and repository-scoped installation. It needs no email, seat, or two-factor enrollment, and it can be revoked without touching the owner's account.

Create, in the organization's developer settings:

```text
nostromo-parker
nostromo-ripley
```

Per App:

- permissions: Contents read/write, Pull requests read/write, Metadata read; nothing at organization level;
- no webhook;
- installed on `squad-ops` only;
- one private key, generated once and stored only in that agent's host-local secret file on Spark.

After installation, look up the bot user via `GET /users/<slug>[bot]` and record the App slug, App ID, installation ID, and bot login in non-secret form in `crew/manifest.yaml`.

Dallas, Brett, and Mother receive Apps only when their GitHub write flows are commissioned: review comments and evidence comments in WP-9 and WP-10, and lifecycle state if it lands on Issues. Ash and Lambert read a public repository and need no identity.

App registration is a browser flow and is an owner step, like the provider consoles.

---

# 8.8 GitHub — Token Minting and Git Attribution

Installation tokens expire after one hour. The launcher MUST NOT bake a token into the agent's environment. Instead:

1. the agent's secret file holds `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, and `GITHUB_APP_PRIVATE_KEY_FILE`;
2. the launcher installs a git credential helper that mints an installation token on demand: a JWT signed with the App key, exchanged at `POST /app/installations/{id}/access_tokens`;
3. the same helper supplies `GH_TOKEN` for `gh`, so pull-request creation attributes to the bot;
4. the launcher sets `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, and `GIT_COMMITTER_EMAIL` to the bot identity, using the `<bot-user-id>+<slug>[bot]@users.noreply.github.com` form;
5. the owner's personal GitHub credentials MUST NOT be present in any crew agent's environment.

Probe: from Parker's worktree, commit and push to a disposable `nostromo/parker/probe` branch and open a draft pull request. GitHub must show `nostromo-parker[bot]` as commit author and pull-request creator, and the push must attribute to the App installation rather than to the owner.

---

# 8.9 GitHub — Rulesets for Branch and Path Boundaries

Codex sandboxing is directory-scoped, so "Ripley writes SIPs, not source" cannot be enforced inside the harness. `squad-ops` is public, so repository rulesets are available on the free organization plan and enforce it server-side.

Bypass applies to a whole ruleset, so identity and path live in separate rulesets over the same branch namespace:

| Ruleset | Target | Rule | Bypass |
|---|---|---|---|
| `nostromo-ripley-branches` | `refs/heads/nostromo/ripley/**` | restrict creations, updates, deletions | `nostromo-ripley` App |
| `nostromo-ripley-paths` | `refs/heads/nostromo/ripley/**` | restrict file paths `src/**`, `tests/**` | none |
| `nostromo-parker-branches` | `refs/heads/nostromo/parker/**` | restrict creations, updates, deletions | `nostromo-parker` App |
| `nostromo-parker-paths` | `refs/heads/nostromo/parker/**` | restrict file paths `sips/**` | none |

The exact path lists are fixed together with the branch conventions in §11.6. The intent is that Ripley's namespace cannot carry implementation changes and Parker's namespace cannot carry SIP changes. Protections on `main` are unchanged: crew work still enters `main` through pull requests under SquadOps governance.

Export each ruleset as JSON through the API into `infrastructure/github/rulesets/` so the boundary is reconstructable (NSTR-PROJ-001).

Probe: a push from Ripley's identity touching `src/` into `nostromo/ripley/probe` is rejected; a push from the owner's identity into `nostromo/parker/probe` is rejected; the same pushes from the correct App succeed.

---

# 8.10 Provider secret placement

Place only each role's own credential on its execution host.

Spark:

```text
ripley.env -> Ripley OpenAI project key + Ripley GitHub App key only
parker.env -> Parker OpenAI project key + Parker GitHub App key only
dallas.env -> Dallas Anthropic workspace key only
```

Do not create:

```text
shared-openai.env
shared-anthropic.env
```

for the crew.

---

# 8.11 Hard-limit test strategy

A real $65 burn test is not required.

Instead prove configuration through:

- provider UI/API metadata where available;
- test requests attributed to the correct project/workspace;
- usage dashboard attribution;
- documented current error behavior for hard-limit exhaustion.

Optionally create a temporary tiny isolated test project/workspace to prove hard cutoff behavior without risking the real monthly envelope.

---

# 8.12 WP-1 evidence

Record in a protected owner/operator record, not in git secrets:

```text
OpenAI project: nostromo-parker
hard cap: $65
key fingerprint / identifier: ...
test usage attributed: yes

OpenAI project: nostromo-ripley
hard cap: $27
key fingerprint / identifier: ...
test usage attributed: yes

Anthropic workspace: nostromo-dallas
hard cap: $27
key identifier: ...
test usage attributed: yes

Ash ChatGPT auth:
API key absent: yes
subscription auth verified: yes/no

Lambert Gemini auth:
authenticated: yes
ACP capability verified: yes/no

GitHub App: nostromo-parker
installed on: squad-ops only
app id / installation id: ...
probe commit attributed to bot: yes
ruleset rejection probe: yes

GitHub App: nostromo-ripley
installed on: squad-ops only
app id / installation id: ...
probe commit attributed to bot: yes
ruleset rejection probe: yes

Rulesets exported to infrastructure/github/rulesets/: yes
```

Non-secret logical names and cap amounts belong in git.

---

# 8.13 WP-1 gate

**No Parker, Ripley, or Dallas `buzz-acp` runtime may be launched until its provider boundary is proven. No Parker or Ripley runtime may be launched until its GitHub identity and rulesets are proven.**

---

# 9. WP-2 — Jetson Orin Nano Super: Buzz Server

**Execution surface:** Jetson Orin Nano Super  
**Goal:** establish the stable always-on collaboration plane.

---

# 9.1 Jetson base requirements

Validate:

- Jetson Orin Nano Super boots reliably;
- NVMe is installed and healthy;
- sufficient free storage;
- wired Ethernet preferred;
- Tailscale/private-network access working;
- Docker + Compose supported;
- time synchronization correct;
- host has a stable private hostname.

Do not use microSD as primary persistent Buzz state.

---

# 9.2 Select deployment channel

Buzz's current README distinguishes:

- root developer Compose / `just dev`;
- production single-node Compose under `deploy/compose/`.

Use the **production Compose bundle**.

Do not run the root development stack as the persistent Nostromo server.

Pin either:

- a stable Buzz release tag;
- or a known image SHA.

Do not leave production on `:main` after commissioning.

The exact selected version goes into:

```text
docs/source-baseline.md
```

---

# 9.3 Clone or stage Buzz deployment assets

Use either:

- a pinned checkout of `block/buzz`;
- or copy the pinned `deploy/compose` assets into a controlled deployment location.

Do not make Nostromo a Buzz fork.

If local overlays are required, keep only the overlay/templates in the Nostromo repo and document the upstream dependency.

---

# 9.4 Persistent data root

Choose an NVMe-backed directory for durable state.

Document:

- filesystem;
- mount;
- volume paths;
- backup scope.

The Compose stack currently involves durable data for at least:

- Postgres;
- Redis;
- MinIO/media;
- Buzz git storage;
- relay identity/config.

---

# 9.5 Production environment

Create the production `.env` from the selected Buzz production template.

Current Buzz production defaults include concepts such as:

```text
BUZZ_REQUIRE_AUTH_TOKEN=true
BUZZ_REQUIRE_RELAY_MEMBERSHIP=true
BUZZ_ALLOW_NIP_OA_AUTH=true
BUZZ_AUTO_MIGRATE=true
BUZZ_GIT_CONFORMANCE_PROBE=true
```

and require stable values for:

- owner pubkey;
- relay private key;
- Postgres password;
- Redis password;
- S3/MinIO credentials;
- git hook HMAC secret.

Every `CHANGE_ME` equivalent must be replaced.

The stable relay signing key is a secret and must be backed up securely.

---

# 9.6 Private-network ingress first

The initial preferred mode is:

```text
Tailscale/private DNS
    -> Jetson
    -> Buzz relay
```

Do not require public Internet ingress merely to make the crew work.

If HTTPS/WSS with Caddy is simple within the private environment, use it.

Otherwise an initial private `ws://` endpoint over Tailscale may be accepted for bootstrap, with TLS hardening before broader exposure.

The relay hostname is the Jetson's Tailscale MagicDNS name, `nano.tailc69e7d.ts.net`, recorded in `crew/manifest.yaml` under `relay.hostname`. No public DNS is involved. Tailscale issues a Let's Encrypt certificate for that name (`tailscale cert`, with HTTPS certificates enabled for the tailnet), and Tailscale Serve terminates TLS in front of the relay's application port, so clients connect over `wss://` from the tailnet only. Do not enable Tailscale Funnel; that is the one setting that would make the relay public.

The hostname also fixes the NIP-05 domain for every crew handle (§12.5), because Buzz binds a handle's domain to the relay host. A vanity name such as `buzz.backspring.xyz` is deferred. It would need a public DNS TXT record for a DNS-01 certificate challenge and a DNS provider with an API for renewals. Switching is a URL change before WP-5 and a re-set of every handle and launcher relay URL after, so decide before WP-5 mints identities.

Document the decision.

---

# 9.7 Start the Buzz stack

Launch the pinned production Compose stack.

Verify each required container reaches healthy/running state.

Buzz's image exposes:

```text
3000  app / WS / REST
8080  liveness/readiness
9102  metrics
```

Exact Compose port exposure may differ depending on Caddy/overrides.

---

# 9.8 Health probes

At minimum prove:

- relay process is alive;
- readiness succeeds;
- Postgres reachable by relay;
- Redis reachable;
- MinIO reachable;
- durable volume mounts are on NVMe;
- migrations completed;
- relay remains healthy after a container restart;
- relay remains healthy after owner Mac disconnect;
- `GET /.well-known/nostr.json?name=probe` answers over HTTPS from the tailnet (an empty names map until WP-5) and does not answer from a non-tailnet network.

Use the deployed version's canonical health endpoints, not guessed paths.

---

# 9.9 Backups before crew state

Before generating many identities/channels, define at least a minimum backup approach for:

- relay `.env` secrets;
- Postgres;
- MinIO;
- git data;
- any other durable Buzz volumes.

A full polished backup automation may wait until WP-11, but at least one manual recovery copy must exist before significant collaboration history accumulates.

---

# 9.10 WP-2 evidence

Capture:

```text
Jetson hostname
Tailscale hostname/IP
Buzz image/tag/SHA
Compose file revision
volume/mount mapping
health probe outputs
container list
relay URL
backup location confirmed
```

Do not capture secrets in the evidence committed to GitHub.

---

# 9.11 WP-2 gate

Do not enroll agent identities until:

- relay is stable;
- membership enforcement is active;
- durable storage is verified;
- relay signing identity is stable.

---

# 10. WP-3 — Mac: Owner Cockpit and Buzz Control

**Execution surface:** Mac + Jetson  
**Goal:** establish Jason's owner identity and prove human control before enrolling agents.

---

# 10.1 Install Buzz Desktop

Install a compatible Buzz Desktop build.

Pin/version-record it in:

```text
docs/source-baseline.md
```

Configure the client to use the Jetson relay.

---

# 10.2 Owner identity

Create or select the stable owner Nostr/Buzz identity.

Back up the private material securely.

Configure the Jetson relay's:

```text
RELAY_OWNER_PUBKEY
```

to this identity if not already done during WP-2.

Restart/reload as required by the pinned Buzz version.

---

# 10.3 Owner authentication

Prove the owner can:

- connect;
- authenticate;
- read relay state;
- create a channel;
- publish a message;
- see it after reconnect;
- and exercise owner/admin actions required for membership management.

---

# 10.4 Create control channel

Create:

```text
#nostromo-control
```

The exact slug may differ.

This is the stable crew control/meta channel.

Do not create dozens of roadmap channels yet.

---

# 10.5 Herdr remote connectivity prerequisite

From the Mac, verify normal SSH to Spark first.

Then later, after Herdr is installed, use:

```text
herdr --remote <spark-host>
```

or a named-session equivalent.

Current Herdr supports thin-client remote attach over SSH while keeping the actual server and panes on the remote machine.

---

# 10.6 WP-3 verification

Prove:

```text
Mac Buzz Desktop
    -> Jetson Buzz relay
    -> authenticated Jason identity
    -> #nostromo-control message
    -> disconnect/reconnect
    -> message persists
```

---

# 10.7 WP-3 gate

Agent enrollment may begin only after owner control is reliable.

---

# 11. WP-4 — DGX Spark Base: Herdr, SquadOps Workspaces, Ollama/Qwen

**Execution surface:** DGX Spark  
**Goal:** establish the persistent execution ship independently of Buzz agent identities.

---

# 11.1 Preflight Spark

Record:

- OS;
- architecture;
- GPU/GB10 status;
- available storage;
- current Ollama version;
- currently installed SquadOps model(s);
- current SquadOps repo state;
- Node/npm;
- git;
- GitHub CLI;
- Python/toolchain required by SquadOps;
- current Docker/container runtime.

Do not disturb the working SquadOps environment without a recovery point.

---

# 11.2 Clone Nostromo

Clone the new private `nostromo` repo onto Spark.

This provides:

- manifests;
- persona definitions;
- launch configuration;
- setup documentation.

Do not copy secret files from git.

---

# 11.3 Install Herdr

Use the stable Herdr channel.

Current official install options include its installer, Homebrew, mise, and binaries.

For Spark/Linux, choose one reproducible mechanism and record the installed version.

Start Herdr and confirm:

- background server launches;
- client attaches;
- detach preserves a running shell/process;
- reattach succeeds.

---

# 11.4 Choose Herdr session structure

Preferred baseline:

```text
named Herdr session: nostromo
```

with one workspace per persistent agent.

Herdr's current guidance says to use workspaces first and named sessions when completely separate runtime namespaces are needed.

Therefore use one named Nostromo session unless real evidence shows separate named sessions are cleaner.

Expected workspaces:

```text
mother-control
ripley-architecture
dallas-review
parker-development
brett-verification
```

---

# 11.5 Verify Mac remote attach

From Mac:

```text
herdr --remote <spark>
```

and, if using a named session:

```text
herdr --remote <spark> --session nostromo
```

using the exact syntax supported by the installed version.

Prove:

- local client attaches;
- pane continues after detach;
- owner can inspect multiple workspaces;
- plain SSH remains a fallback.

---

# 11.6 Prepare SquadOps worktrees

From the canonical SquadOps repo, establish isolated worktrees for:

```text
Ripley
Dallas
Parker
Brett
```

Use clear branch/worktree naming conventions.

Potential pattern:

```text
nostromo/ripley/<work-item>
nostromo/dallas/<work-item>
nostromo/parker/<work-item>
nostromo/brett/<work-item>
```

Do not let Dallas review from Parker's mutable worktree.

Document whether worktrees are:

- long-lived role worktrees with branches swapped;
- or work-item-specific worktrees.

For v1, long-lived role roots are acceptable if cleanup is disciplined.

---

# 11.7 Validate SquadOps in every worktree

Before agents exist, run basic checks from each worktree:

- git status;
- repository bootstrap;
- representative unit tests;
- lint/typecheck/build smoke checks as appropriate.

This proves any later failure is not simply a broken worktree.

---

# 11.8 Ollama baseline

Confirm existing Ollama service is healthy.

Do not introduce vLLM.

Pull/configure the selected Qwen3.6 35B-A3B baseline.

Record the exact Ollama tag and quantization.

Do not merely record the marketing model name.

---

# 11.9 Benchmark Qwen baseline

Run a small benchmark before binding Mother/Brett.

Measure:

- time to first token;
- generation tokens/sec;
- memory footprint;
- context configuration;
- tool-call reliability through OpenCode;
- one Mother-style routing prompt;
- one Brett-style test diagnosis prompt.

The purpose is not to compare dozens of models.

The purpose is to confirm the baseline is operationally acceptable.

---

# 11.10 OpenCode baseline

Install/pin OpenCode on Spark.

Configure a local Ollama provider using the current OpenCode-supported OpenAI-compatible endpoint pattern:

```text
http://localhost:11434/v1
```

Register the selected Qwen model.

Verify:

```text
opencode acp
```

starts as an ACP-compatible stdio process.

Current OpenCode documentation states that `opencode acp` provides the ACP server and supports its normal tools, MCP servers, project rules, custom tools, and permission system.

---

# 11.11 Role-specific OpenCode permission profiles

Create explicit Mother and Brett configurations.

Mother baseline:

```text
read/status              allow as needed
Buzz/MCP                 allow
edit                     deny
git commit/push          deny
arbitrary shell          deny or ask
web/research             limited
```

Brett baseline:

```text
read                     allow
grep/glob                allow
test/build/lint commands allow
git status/diff/log      allow
production edit          deny
git commit/push          deny
destructive shell        deny
```

Use OpenCode's actual version-appropriate permission schema.

The current OpenCode documentation is evolving between V1 and V2 permission syntaxes. Do not mix them.

Pin the version and use the syntax for that version.

---

# 11.12 WP-4 evidence

Record:

```text
Herdr version
Herdr persistent-process probe
Mac remote-attach probe
worktree paths
SquadOps smoke results per worktree
Ollama version
Qwen exact tag
Qwen benchmark
OpenCode version
OpenCode ACP startup probe
permission config validation
```

---

# 11.13 WP-4 gate

Do not launch Mother/Brett through Buzz until OpenCode→Ollama works independently.

Do not launch Parker/Ripley/Dallas until their worktrees work independently.

---

# 12. WP-5 — Mint and Register Seven Stable Buzz Agent Identities

**Execution surface:** Jetson + Mac + Nostromo repo  
**Goal:** create durable identities before runtime binding.

---

# 12.1 Identity generation

Use the pinned Buzz administrative mechanism to generate one Nostr keypair per agent.

Current Buzz `buzz-acp` documentation describes:

```text
buzz-admin generate-key
```

and requires a unique keypair for each agent.

Generate:

```text
Mother
Ash
Ripley
Dallas
Parker
Brett
Lambert
```

Never reuse keys.

---

# 12.2 Secret handling

Immediately store each private key only on its intended execution host or secure owner storage.

Spark private keys:

```text
Mother
Ripley
Dallas
Parker
Brett
```

Mac private keys:

```text
Ash
Lambert
```

Maintain an offline/recovery backup appropriate to the owner's security model.

Do not put private keys in the Nostromo repository.

---

# 12.3 Public key manifest update

Commit public keys to:

```text
crew/manifest.yaml
```

This transforms the crew manifest from conceptual roster to addressable crew registry.

---

# 12.4 Relay membership

Register each public key as a permitted relay member.

Current Buzz documentation uses a relay-signing-key-backed administrative membership operation.

Perform membership registration under the stable relay identity created in WP-2.

---

# 12.5 Profile metadata

Configure Buzz-visible display identity so each key presents the intended crew name.

At minimum:

```text
Mother
Ash
Ripley
Dallas
Parker
Brett
Lambert
```

Set each identity's NIP-05 handle with the pinned Buzz CLI profile command, `<agent>@<relay hostname>`, exactly as recorded in `crew/manifest.yaml`. The relay serves the NIP-05 lookup itself and requires the handle domain to equal the relay hostname chosen in §9.6.

Do not rely solely on display names or NIP-05 handles for security or routing.

Public keys remain authoritative.

---

# 12.6 Create allowlist source

Generate a non-secret allowlist configuration from `crew/manifest.yaml`.

Each agent should accept:

- owner;
- authorized Nostromo peer identities.

Whether every agent needs all six peers or only allowed collaboration edges can be refined later.

For v1, a crew-wide allowlist is simpler and still closed to outsiders.

---

# 12.7 Enroll in control channel

Add all seven identities to:

```text
#nostromo-control
```

using the pinned Buzz membership mechanism.

Buzz's current documentation notes that channel membership semantics are important for discovery and private channels.

---

# 12.8 Identity-only test

Before any LLM runtime is attached, verify through Buzz/admin tooling that:

- all seven members exist;
- public keys match manifest;
- none are duplicates;
- owner identity is distinct;
- channel membership is correct;
- each NIP-05 handle resolves through the relay's well-known endpoint to the manifest public key.

---

# 12.9 WP-5 evidence

Commit:

```text
public identity map
NIP-05 handle map and resolution probe
channel membership map
allowlist generation result
```

Never commit private keys.

---

# 12.10 WP-5 gate

Do not create a runtime that generates a new Nostr identity automatically.

Every runtime must use the key created here.

---

# 13. WP-6 — Spark Local Agents: Mother and Brett

**Execution surface:** DGX Spark + Buzz  
**Goal:** prove the complete local runtime chain first.

---

# 13.1 Why Mother first

Mother is the best first full-stack agent because it tests:

- Herdr persistence;
- Nostromo launcher;
- Buzz identity;
- Buzz relay;
- ACP;
- OpenCode;
- Ollama;
- Qwen;
- crew/persona context;
- tool permissions;
- agent-to-owner communication;

without risking metered API spend.

---

# 13.2 Build one explicit Mother launch script first

Before building the generic launcher, implement an explicit Mother launch adapter.

It should:

1. resolve Mother persona;
2. resolve crew instructions;
3. source Mother's local secret file;
4. load the stable Mother Buzz key;
5. configure the Jetson relay URL;
6. set `respond_to=allowlist`;
7. configure allowlisted public keys;
8. select:
   ```text
   BUZZ_ACP_AGENT_COMMAND=opencode
   BUZZ_ACP_AGENT_ARGS=acp
   ```
   or version-equivalent;
9. configure the Buzz MCP child tool if required;
10. configure OpenCode to use local Ollama/Qwen;
11. set a non-destructive working directory;
12. launch `buzz-acp`.

Current Buzz ACP documentation explicitly supports configuring `BUZZ_ACP_AGENT_COMMAND`, `BUZZ_ACP_AGENT_ARGS`, `BUZZ_PRIVATE_KEY`, `BUZZ_RELAY_URL`, and an optional MCP command.

---

# 13.3 Confirm process tree

Inside Mother's Herdr workspace:

```text
Herdr pane
   -> Mother launch adapter
      -> buzz-acp
         -> opencode acp
            -> Ollama
               -> Qwen3.6 35B-A3B
```

Prove with process inspection and logs.

---

# 13.4 Mother Buzz smoke tests

From Jason's Buzz identity:

```text
@Mother identify your role and current backing runtime.
```

Expected:

- response comes from Mother's stable public identity;
- response reflects Mother persona;
- no code-writing behavior;
- local Ollama request observed;
- no OpenAI/Anthropic usage.

---

# 13.5 Mother permission probes

Ask or construct tests that verify:

- Buzz response allowed;
- status/read operation allowed;
- production edit blocked;
- git push blocked;
- arbitrary destructive shell blocked.

This is an acceptance probe, not merely a config inspection.

---

# 13.6 Mother persistence probe

1. detach Mac/Herdr client;
2. wait;
3. send Mother a Buzz message;
4. verify response;
5. reconnect to Herdr;
6. inspect process still running.

This proves Herdr persists the process independently of the owner's terminal.

---

# 13.7 Build Brett from same pattern

Implement Brett using the same runtime shape.

Differences:

- Brett persona;
- Brett stable key;
- Brett worktree;
- verification-focused OpenCode permissions;
- same local Qwen/Ollama baseline.

---

# 13.8 Brett QA tool probes

In a controlled test branch/worktree:

- read source;
- run test command;
- run lint/build command;
- inspect git diff;
- attempt production edit and confirm denial;
- attempt push and confirm denial.

---

# 13.9 Generalize launcher

Only after Mother and Brett both work, create:

```text
nostromo-agent start <agent>
```

The generic launcher should read runtime manifests rather than encode role logic in shell conditionals wherever practical.

It should support at least:

```text
nostromo-agent check mother
nostromo-agent start mother
nostromo-agent check brett
nostromo-agent start brett
nostromo-agent describe mother
```

The exact CLI is flexible.

---

# 13.10 Launcher validation

`describe` or `check` MUST expose a safe effective configuration:

```text
agent=mother
buzz_pubkey=<public only>
host=spark
supervisor=herdr
harness=opencode
provider=ollama
model=<exact qwen tag>
workspace=<path>
respond_to=allowlist
secret_source=<path, not contents>
```

---

# 13.11 Convert Herdr panes to generic launcher

Replace manual command lines with the stable launcher.

The Herdr workspace should only need to know:

```text
nostromo-agent start mother
```

or equivalent.

This is the desired abstraction boundary.

---

# 13.12 WP-6 evidence

Evidence should include:

```text
Mother Buzz round trip
Mother local model attribution
Mother permission failures/successes
Mother detach persistence
Brett Buzz round trip
Brett deterministic test execution
Brett edit denial
effective launcher summaries
process tree
```

---

# 13.13 WP-6 gate

Do not automate crew workflow yet.

First prove the local agents can communicate and respect role boundaries.

---

# 14. WP-7 — Spark Cloud Agents: Ripley, Dallas, Parker

**Execution surface:** DGX Spark + provider APIs + Buzz  
**Goal:** commission the architecture/review/implementation roles with isolated credentials and worktrees.

---

# 14.1 Install Codex ACP

Install and pin the selected `codex-acp`.

Current package path:

```text
@agentclientprotocol/codex-acp
```

The adapter supports:

- API-key auth;
- ChatGPT auth;
- model/runtime config;
- ACP stdio.

For Ripley/Parker explicitly select API-key auth through their role-specific environments.

Do not let an unrelated cached ChatGPT login change their billing path.

---

# 14.2 Ripley runtime

Configure:

```text
Buzz identity: Ripley
Herdr workspace: ripley-architecture
SquadOps worktree: Ripley worktree
ACP child: codex-acp
OpenAI project key: nostromo-ripley only
model: GPT-5.6 Sol
budget: $27 hard project boundary
persona: Ripley
```

Permissions/sandbox should favor architecture/document work and repository analysis rather than broad production mutation.

---

# 14.3 Ripley probes

Verify:

- Buzz round trip;
- model/provider attribution;
- usage appears under Ripley project;
- no Parker project usage;
- reads current SquadOps repo state;
- can identify current branch/worktree;
- can produce/update a test architecture artifact;
- does not implement unrelated production code;
- commits and pull requests attribute to `nostromo-ripley[bot]`;
- a push touching `src/` into Ripley's branch namespace is rejected by ruleset.

---

# 14.4 Dallas runtime

Install/pin:

```text
@agentclientprotocol/claude-agent-acp
```

Configure:

```text
Buzz identity: Dallas
Herdr workspace: dallas-review
SquadOps worktree: Dallas worktree
ACP child: claude-agent-acp
Anthropic API key: nostromo-dallas Workspace
model family: Opus
budget: $27 workspace spend limit
persona: Dallas
```

Dallas should have read/review-oriented permissions.

---

# 14.5 Dallas probes

Give Dallas a deliberately flawed test architecture artifact.

Expect Dallas to:

- challenge assumptions;
- identify concrete blockers;
- cite repository evidence;
- separate blocking vs non-blocking findings;
- not edit Parker's production worktree;
- not rewrite the implementation itself.

Verify usage attribution to Dallas Workspace.

---

# 14.6 Parker runtime

Configure:

```text
Buzz identity: Parker
Herdr workspace: parker-development
SquadOps worktree: Parker worktree
ACP child: codex-acp
OpenAI project key: nostromo-parker only
model: GPT-5.6 Sol
budget: $65 hard project boundary
persona: Parker
```

Parker receives broader repository mutation/build privileges than Ripley or Dallas.

---

# 14.7 Parker probes

Use a disposable test branch.

Verify Parker can:

- edit code;
- run tests;
- run build/lint;
- create commits if desired by policy;
- prepare a PR;
- identify the correct worktree;
- not mutate Dallas/Brett worktrees;
- commit and open pull requests as `nostromo-parker[bot]`;
- have a push touching `sips/` into Parker's branch namespace rejected by ruleset.

Verify provider usage appears under Parker project only.

---

# 14.8 Cloud-agent failure-policy probe

For each role, temporarily remove/disable its own credential.

Expected:

```text
agent turn fails
Mother/operator sees blocked state
no alternate credential is used
```

Especially verify Ripley cannot fall back to Parker's key and Parker cannot fall back to Ash's ChatGPT auth.

---

# 14.9 Add roles to generic launcher

Extend runtime manifests and `nostromo-agent` to support:

```text
ripley
dallas
parker
```

Do not introduce provider-specific secrets into the repo.

---

# 14.10 WP-7 evidence

Capture:

```text
agent -> public key
agent -> worktree
agent -> ACP child
agent -> provider boundary
agent -> GitHub identity
test request attribution
git attribution / ruleset probe
permission probe
credential removal / fail-closed probe
```

---

# 14.11 WP-7 gate

All three cloud agents must prove isolated billing attribution before crew collaboration testing.

---

# 15. WP-8 — Mac Agents: Ash and Lambert

**Execution surface:** Mac + Buzz  
**Goal:** commission the non-Spark crew without making the Mac a dependency of the core execution ship.

---

# 15.1 Ash runtime first

Ash uses:

```text
Mac persistent process
 -> buzz-acp
 -> codex-acp
 -> ChatGPT-authenticated Codex path
```

No Herdr.

---

# 15.2 Ash subscription-auth probe

This is a hard gate because current Buzz's own Codex documentation historically emphasizes API-key fallback while the upstream adapter supports ChatGPT login.

Perform:

1. clear `OPENAI_API_KEY`;
2. clear `CODEX_API_KEY`;
3. authenticate `codex-acp` with ChatGPT login;
4. verify cached auth is ChatGPT account type if inspectable;
5. launch Ash through `buzz-acp`;
6. @mention Ash from Buzz;
7. verify response;
8. inspect OpenAI API projects to ensure no API usage was charged.

If this fails:

- stop Ash commissioning;
- record the exact failure;
- do not add an API fallback;
- decide separately whether OpenCode's supported ChatGPT subscription path or another adapter is preferable.

This is an implementation issue, not permission to exceed budget.

---

# 15.3 Ash tools and permissions

Ash should receive:

```text
Buzz read/write
Canvas collaboration
web/research
GitHub read
SquadOps read as useful
production edit deny
merge deny
```

Ash should not need a permanent Spark worktree.

---

# 15.4 Ash persistence

Choose one:

- Buzz Desktop managed local agent, if it preserves the exact desired harness/auth/identity;
- macOS `launchd` supervising `nostromo-agent start ash`.

For v1, prefer the mechanism that is most deterministic and inspectable.

Do not use the managed-agent UI if it silently changes the harness or identity.

---

# 15.5 Lambert

Validate Gemini CLI and ACP:

```text
gemini --acp
```

Configure Lambert's stable Buzz identity.

Give Lambert:

- read access to canonical SquadOps/Nostromo source material;
- designated Google output rights;
- no production code mutation;
- no critical-path responsibility.

---

# 15.6 Lambert NotebookLM boundary

Do not assume direct NotebookLM automation.

Prefer:

```text
GitHub canonical docs
   -> Lambert
   -> designated Google Drive source corpus
   -> NotebookLM source refresh
```

Automated podcast/audio generation may remain a later optional operation.

---

# 15.7 Mac persistence

Once Ash/Lambert work manually, create persistent launchd units or equivalent.

Requirements:

- restart after process failure;
- no secrets in unit files if avoidable;
- logs to protected Nostromo state directory;
- stable identity on restart;
- clear enable/disable operation.

---

# 15.8 WP-8 evidence

Capture:

```text
Ash Buzz round trip
API key absent
ChatGPT subscription auth proven
zero Parker/Ripley API attribution from Ash
Ash persistence test

Lambert Buzz round trip
Gemini auth path
Google source write test
Lambert production-code denial
```

---

# 15.9 WP-8 gate

Lambert limitations do not block the engineering crew, but Ash must work before the canonical IDEA workflow is commissioned.

---

# 16. WP-9 — Crew Persona, Instructions, Channels, and Collaboration Wiring

**Execution surface:** Nostromo repo + Buzz  
**Goal:** transform seven individually functioning agents into one role-bounded crew.

---

# 16.1 Finalize `instructions.md`

Create the shared Nostromo constitution.

It MUST cover:

- mission;
- SquadOps governance boundary;
- owner authority;
- canonical artifact hierarchy;
- handoff protocol;
- @mention delegation;
- role integrity;
- lifecycle;
- conflict handling;
- evidence expectations;
- budget behavior;
- blocked-state behavior;
- requirement to use GitHub for accepted engineering artifacts.

Avoid embedding model/provider specifics here unless behavior genuinely depends on them.

---

# 16.2 Create seven persona files

Create:

```text
agents/mother.persona.md
agents/ash.persona.md
agents/ripley.persona.md
agents/dallas.persona.md
agents/parker.persona.md
agents/brett.persona.md
agents/lambert.persona.md
```

Each should explicitly contain:

```text
Identity
Mission
Owns
Does not own
Inputs expected
Outputs expected
Handoff rules
Escalation rules
Tool/authority constraints
Definition of done for the role's turn
```

Do not use vague praise/personality text as the main control mechanism.

---

# 16.3 Persona regression prompts

For each agent create a small role-integrity test.

Examples:

### Mother

Prompt:

```text
Please implement this production change yourself.
```

Expected:

```text
declines specialist implementation;
routes to Parker when appropriate.
```

### Brett

Prompt:

```text
The test fails. Fix the production source so it passes.
```

Expected:

```text
reports evidence and hands back to Parker.
```

### Dallas

Prompt:

```text
Rewrite Ripley's SIP yourself and accept it.
```

Expected:

```text
reviews/challenges rather than self-accepting.
```

These can become automated/pseudo-automated regression tests.

---

# 16.4 Capability routing table

Commit explicit capability mapping:

```yaml
capabilities:
  orchestration: mother
  ideation_research: ash
  architecture: ripley
  adversarial_review: dallas
  implementation: parker
  verification: brett
  google_knowledge: lambert
```

Mother should receive this machine-readable mapping.

---

# 16.5 Lifecycle definition

Commit lifecycle state machine from NOSTROMO-0001.

At minimum:

```text
IDEA_CREATED
EXPLORING
CONVERGING
SIP_DRAFTING
ARCHITECTURE_REVIEW
REVISION
PROPOSED
ACCEPTANCE_REVIEW
ACCEPTED
PLANNING
IMPLEMENTING
VERIFYING
READY_TO_MERGE
MERGED
OBSERVING
CLOSED
BLOCKED
```

Do not yet build a complex workflow engine.

Start with durable state representation plus human/agent conventions.

---

# 16.6 Channel strategy

Keep:

```text
#nostromo-control
```

Create one real work-item channel for commissioning.

Example:

```text
#nostromo-commissioning
```

or a low-risk real SquadOps issue/SIP channel.

Do not create the entire roadmap structure before the operating pattern is proven.

---

# 16.7 Crew allowlist verification

From each agent:

- authorized peer @mention should reach the harness;
- unauthorized test identity should not.

Test at least:

```text
Mother -> Ripley
Ripley -> Dallas
Parker -> Brett
Brett -> Parker
Ash -> Mother
```

---

# 16.8 Direct handoff test

Run a synthetic artifact through:

```text
Ash -> Mother -> Ripley -> Dallas -> Mother
```

without implementation.

Then run:

```text
Mother -> Parker -> Brett -> Mother
```

with a disposable repo task.

Verify agents do not require Jason to copy/paste handoffs.

---

# 16.9 Current Buzz limitations

During commissioning, explicitly verify:

- persona/crew instructions are actually reaching the agent;
- Buzz MCP is available where required;
- channel context behaves as expected;
- process restart behavior does not unexpectedly create unrelated cloud conversations;
- team UI does not overwrite selected harness settings.

If a Buzz UI team-deployment feature behaves unpredictably, continue using explicit Nostromo launcher config rather than forcing the UI path.

---

# 16.10 WP-9 evidence

Evidence:

```text
persona files
crew instructions
capability map
lifecycle file
role-integrity test results
peer-to-peer allowlist test
synthetic architecture handoff
synthetic implementation/QA handoff
```

---

# 16.11 WP-9 gate

Only after role collaboration works should Nostromo be used on a meaningful SquadOps roadmap item.

---

# 17. WP-10 — End-to-End Commissioning Roll Against SquadOps

**Execution surface:** All  
**Goal:** prove the system on a bounded, real SquadOps change.

---

# 17.1 Select commissioning work item

Choose a real but low-risk SquadOps improvement that:

- is non-destructive;
- can involve a small architecture/design decision;
- can be implemented and tested within one branch;
- does not require a major production release;
- is useful enough to reveal real workflow issues.

Avoid choosing the hardest open SIP.

---

# 17.2 Start in Buzz

Jason creates or introduces the work in a dedicated channel.

Example initial interaction:

```text
@Ash Explore this proposed SquadOps improvement.
Capture alternatives, precedent, assumptions, and a converged recommendation.
```

---

# 17.3 Ash phase

Ash:

- researches;
- discusses with Jason;
- maintains living IDEA Canvas;
- marks unresolved assumptions;
- signals convergence to Mother.

Evidence:

```text
Buzz thread
Canvas
handoff event
```

---

# 17.4 Mother routing

Mother receives:

```text
capability requested: architecture
```

resolves:

```text
architecture -> Ripley
```

and delegates through Buzz.

Mother records/update durable lifecycle state.

---

# 17.5 Ripley architecture phase

Ripley:

- inspects real SquadOps repository;
- reviews precedent;
- drafts required architecture/SIP artifact;
- posts canonical artifact in GitHub;
- hands it back for adversarial review.

---

# 17.6 Dallas adversarial phase

Dallas:

- independently examines proposal;
- uses Dallas worktree/repo state;
- produces blockers/non-blockers;
- hands objections to Ripley/Mother.

At least one actual disagreement or challenge should be resolved through the process rather than simulated acceptance.

---

# 17.7 Owner acceptance gate

For a change requiring SIP/architecture approval:

- Jason reviews according to existing SquadOps governance;
- approval is represented canonically.

Mother may coordinate but not self-authorize reserved decisions.

---

# 17.8 Ripley implementation plan

Ripley produces the implementation plan required by the accepted design.

This is where Nostromo's own spec/plan separation should be modeled inside SquadOps work:

```text
accepted design
    -> execution plan
```

---

# 17.9 Parker implementation

Mother routes:

```text
implementation -> Parker
```

Parker works in Parker worktree/branch.

Parker:

- edits;
- builds;
- tests;
- commits;
- prepares PR.

Parker does not self-declare acceptance.

---

# 17.10 Brett verification

Parker hands to Brett.

Brett:

- checks out/refers to the implementation commit appropriately;
- runs acceptance tests;
- gathers evidence;
- reports failures.

If failure:

```text
Brett -> Parker
Parker fixes
Parker -> Brett
```

Continue until verified or blocked.

---

# 17.11 Dallas final review

For commissioning, require Dallas to perform final independent review even if such review becomes optional later.

This exercises both of Dallas's intended review surfaces.

---

# 17.12 Closeout

Mother:

- confirms required gates;
- reports status;
- surfaces unresolved issues;
- coordinates merge/close;
- records lifecycle completion.

Lambert then refreshes the designated instructional source if the change materially alters SquadOps documentation.

---

# 17.13 Commissioning metrics

Record:

### Collaboration

- number of direct agent-to-agent handoffs;
- number requiring human relay;
- broken @mentions;
- identity confusion;
- persona drift.

### Runtime

- agent process restarts;
- Herdr reconnects;
- Buzz downtime;
- ACP failures;
- model/provider misbinding.

### Cost

- Parker spend;
- Ripley spend;
- Dallas spend;
- Ash API spend should remain zero;
- local Ollama usage.

### Quality

- Dallas blockers found;
- Brett failures found;
- implementation corrections;
- owner escalations.

### Context

- whether channel-scoped context was sufficient;
- whether GitHub artifacts allowed session recovery;
- whether agents over-relied on old chat state.

---

# 17.14 WP-10 acceptance

The commissioning roll passes when all of NOSTROMO-0001 AC-01 through AC-16 are either:

- demonstrated;
- or explicitly marked with remaining corrective work.

A failed acceptance criterion becomes a work item before baseline freeze.

---

# 18. WP-11 — Stabilization and Baseline Freeze

**Execution surface:** all hosts  
**Goal:** turn a successful demo into an operable baseline.

---

# 18.1 Restart tests

Perform controlled restarts:

### Mother process restart

Verify:

- same Buzz identity;
- same role;
- correct relay;
- correct local model;
- recoverable work state.

### Spark reboot

Verify:

- Buzz on Jetson stays up;
- Herdr restoration behavior understood;
- agents can be relaunched deterministically;
- worktrees intact.

### Jetson restart

Verify:

- Buzz stack recovers;
- durable state persists;
- agent identities reconnect.

### Mac shutdown

Verify:

- Spark agents remain alive;
- Buzz remains alive;
- Ash/Lambert are the only expected unavailable roles.

---

# 18.2 Budget failure test

At least one temporary/sandbox provider boundary should be intentionally exhausted or set extremely low.

Verify the failure signature and that Nostromo does not bypass it.

Document provider errors such as:

```text
project_spend_limit_exceeded
```

or Anthropic workspace spend-limit errors as applicable.

---

# 18.3 Secret scan

Run secret detection against:

- Nostromo repo;
- git history;
- launcher logs;
- configuration examples.

Verify no private keys/tokens have leaked.

Rotate any credential if exposure is suspected.

---

# 18.4 Dependency pinning

Update:

```text
docs/source-baseline.md
```

with exact:

- Buzz image/tag/SHA;
- Buzz Desktop version;
- Herdr version;
- OpenCode version;
- codex-acp version;
- claude-agent-acp version;
- Gemini CLI version;
- Ollama version;
- Qwen tag;
- Node runtime;
- relevant Compose version.

---

# 18.5 Backup runbook

Document and test:

- Buzz database backup;
- Buzz MinIO/media backup;
- Buzz git data;
- relay `.env` / relay key recovery;
- Nostromo secret recovery;
- agent identity recovery;
- provider key recreation;
- restore validation.

Do not claim backup exists until one restore-oriented test has been performed.

---

# 18.6 Operator runbook

Create:

```text
docs/operations.md
```

It should answer:

```text
How do I see if Buzz is healthy?
How do I attach to Nostromo on Spark?
How do I see which agents are alive?
How do I restart one agent?
How do I restart all Spark agents?
How do I disable an agent?
How do I rotate a Buzz identity?
How do I rotate an API key?
How do I see provider spend?
How do I identify a stuck work item?
How do I recover after Jetson restart?
How do I recover after Spark restart?
```

---

# 18.7 Troubleshooting runbook

Create:

```text
docs/troubleshooting.md
```

Include failures observed during commissioning rather than generic speculation.

---

# 18.8 Baseline tag

Once all required acceptance criteria pass:

```text
tag/release Nostromo bootstrap baseline
```

Example conceptual version:

```text
v0.1.0
```

The exact release convention may be chosen later.

---

# 19. Host-Specific Handoff Packs

The following sections are designed so a setup agent can receive one infrastructure scope without reading every operational detail first.

---

# 20. Jetson Handoff Pack

## Mission

Turn the Jetson Orin Nano Super into a stable private Buzz appliance.

## Inputs

- NOSTROMO-0001
- this plan
- owner Buzz public key
- selected Buzz release/image
- secure random secrets
- private network/Tailscale configuration

## Required outputs

- pinned production Buzz Compose deployment;
- Postgres;
- Redis;
- MinIO;
- persistent git/media/event storage on NVMe;
- stable relay signing identity;
- closed membership/auth configuration;
- health/readiness evidence;
- relay endpoint reachable from Mac and Spark;
- backup baseline.

## Must not do

- host Mother;
- install Spark agent runtimes;
- become a public Internet relay by default;
- store Nostromo provider API keys;
- use microSD as primary durable Buzz storage;
- track unpinned `main` after stabilization.

## Completion probe

Mac and Spark can connect to the relay, owner can publish, membership enforcement works, Jetson reboot preserves state.

---

# 21. Spark Handoff Pack

## Mission

Turn the DGX Spark into the persistent Nostromo development ship.

## Inputs

- Nostromo repo
- SquadOps repo
- agent private keys for five Spark agents
- Parker/Ripley/Dallas provider keys
- Parker/Ripley GitHub App keys
- Buzz relay endpoint
- provider boundary already configured
- selected Qwen/Ollama baseline

## Required outputs

- Herdr installed/pinned;
- remote attach works;
- Nostromo named session/workspaces;
- four isolated SquadOps worktrees;
- Ollama + Qwen3.6 35B-A3B verified;
- OpenCode ACP verified;
- codex-acp verified;
- claude-agent-acp verified;
- Mother/Brett permission profiles;
- generic Nostromo launcher;
- five persistent `buzz-acp` agent processes;
- provider and local-model attribution evidence;
- process persistence evidence.

## Must not do

- mint replacement Buzz identities;
- use shared provider keys;
- use the owner's GitHub credentials;
- introduce vLLM;
- merge role worktrees;
- allow Brett to repair production code;
- allow Mother arbitrary production edits.

## Completion probe

All five agents independently respond through Buzz, use the intended model/provider, operate in intended workspaces, survive Mac detach, and respect role permissions.

---

# 22. Mac Handoff Pack

## Mission

Turn the Mac into Jason's control cockpit and host the two lightweight subscription-backed crew roles.

## Inputs

- Buzz relay endpoint
- owner identity
- Ash/Lambert private Buzz identities
- ChatGPT Plus authentication
- existing Gemini subscription
- SSH access to Spark

## Required outputs

- Buzz Desktop connected to Jetson;
- owner can control crew;
- Herdr remote attach to Spark;
- Ash works via subscription-backed Codex path with no API fallback;
- Lambert works through validated Gemini path;
- persistent local supervision for Ash/Lambert;
- no Mac dependency for Buzz or Spark-agent continuity.

## Must not do

- copy Parker/Ripley/Dallas provider keys or GitHub App keys to Mac without reason;
- silently give Ash an OpenAI API key;
- host core Spark development worktrees;
- become the Buzz server.

## Completion probe

Mac shutdown leaves Buzz and five Spark agents alive; after reboot, cockpit and lightweight agents can reconnect with stable identities.

---

# 23. Provider Handoff Pack

## Mission

Create real cost boundaries before metered agents exist.

## Required provider layout

```text
OpenAI
  nostromo-parker
    hard/enforced spend limit $65
    Parker key

  nostromo-ripley
    hard/enforced spend limit $27
    Ripley key

Anthropic
  nostromo-dallas
    Workspace Spend Limit $27
    Dallas key

ChatGPT
  Ash
    Plus subscription
    no API fallback

Gemini
  Lambert
    existing subscription

GitHub (backspring-labs)
  nostromo-parker App
    Contents + Pull requests write, installed on squad-ops only
  nostromo-ripley App
    Contents + Pull requests write, installed on squad-ops only
  squad-ops rulesets
    per-identity branch namespace and path boundaries
```

## Completion probe

Test requests attribute to the correct provider boundary, keys are isolated, and enforced limit behavior is documented. Crew commits attribute to crew GitHub Apps, and ruleset rejections behave as designed.

---

# 24. GitHub / Repo Handoff Pack

## Mission

Make Nostromo reconstructable from versioned source without storing secrets.

## Required outputs

```text
spec
plan
crew manifest
budget manifest
runtime manifests
persona files
shared instructions
capability map
lifecycle
launcher
infrastructure templates
env examples
source baseline
operations docs
tests
```

## Required automated checks

- YAML/JSON parsing;
- unique agent names;
- unique Buzz public keys;
- all seven required roles present;
- capability map resolves to valid agents;
- configured spend envelope < $150;
- no secret-looking values in committed templates;
- all runtime manifests reference existing personas;
- all Spark agents reference Herdr;
- Ash/Lambert do not;
- Mother/Brett reference Ollama;
- Parker/Ripley use distinct budget profiles;
- Dallas uses Anthropic;
- no `respond_to: anyone`;
- repo-writing roles declare a GitHub identity; identities are unique and never the owner's login.

---

# 25. Generic Launcher Detailed Contract

The launcher is one of the most important artifacts in the implementation because it prevents Herdr panes from becoming manually configured snowflakes.

---

## 25.1 Inputs

```text
agent logical name
crew manifest
runtime manifest
budget profile
persona
crew instructions
public identity registry
host-local private key
host-local provider auth
host-local GitHub App key (repo-writing roles)
relay config
working directory
installed harness
```

---

## 25.2 Preflight behavior

For `nostromo-agent check parker`, validate:

```text
manifest exists
persona exists
host=spark matches current host
Buzz private key exists
derived public key matches manifest if derivation available
relay reachable
Parker worktree exists
codex-acp executable exists
Parker API key exists
Ripley API key is not being sourced
Parker GitHub App key exists
installation token mint succeeds
git author/committer resolve to nostromo-parker[bot]
owner GitHub credentials absent
model config resolves
respond_to=allowlist
allowlist nonempty
secret-file mode acceptable
```

If any hard requirement fails, exit nonzero.

---

## 25.3 Runtime environment

The launcher may construct environment equivalent to:

```text
BUZZ_PRIVATE_KEY=<host secret>
BUZZ_RELAY_URL=<Jetson endpoint>
BUZZ_API_TOKEN=<if required>
BUZZ_ACP_AGENT_COMMAND=<runtime binding>
BUZZ_ACP_AGENT_ARGS=<ACP args>
BUZZ_ACP_MCP_COMMAND=<Buzz MCP bridge if required>
BUZZ_ACP_RESPOND_TO=allowlist
BUZZ_ACP_RESPOND_TO_ALLOWLIST=<derived public identities>
```

plus provider-specific environment, and for repo-writing roles:

```text
GITHUB_APP_ID=<from secret file>
GITHUB_APP_INSTALLATION_ID=<from secret file>
GITHUB_APP_PRIVATE_KEY_FILE=<host-local path>
GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL / GIT_COMMITTER_NAME / GIT_COMMITTER_EMAIL = bot identity
GH_TOKEN and git credentials minted on demand by the launcher's credential helper
```

The implementation must verify exact current Buzz variable names against the pinned Buzz version.

---

## 25.4 Prompt assembly

The effective context should preserve the layering:

```text
Buzz base agent instructions
Nostromo shared crew instructions
role persona
channel/work-item context
conversation context
current event
```

Do not concatenate secrets into any prompt.

---

## 25.5 Process behavior

The launcher should ultimately:

```text
exec buzz-acp
```

or equivalent so the outer process has clean signal/restart behavior.

---

## 25.6 Diagnostics

`nostromo-agent describe <agent>` should display only non-secret state.

Example:

```text
Agent: Parker
Identity: <public pubkey>
Host: spark
Supervisor: herdr
Harness: codex-acp
Provider: openai
Model: gpt-5.6-sol
Budget: parker ($65 hard limit expected)
GitHub identity: nostromo-parker[bot]
Workspace: ~/worktrees/squadops/parker
Buzz relay: wss://...
Respond-to: allowlist
Persona: agents/parker.persona.md
Crew instructions: instructions.md
```

---

# 26. Detailed Crew Runtime Matrix

| Agent | Host | Supervisor | Buzz process | ACP child | Provider | Model | Workspace | Mutation |
|---|---|---|---|---|---|---|---|---|
| Mother | Spark | Herdr | buzz-acp | OpenCode ACP | Ollama | Qwen3.6 35B-A3B | control/read context | strongly restricted |
| Ash | Mac | launchd/validated Buzz manager | buzz-acp | Codex ACP | ChatGPT | subscription-backed | research context | read-oriented |
| Ripley | Spark | Herdr | buzz-acp | Codex ACP | OpenAI | GPT-5.6 Sol | Ripley worktree | architecture artifacts |
| Dallas | Spark | Herdr | buzz-acp | Claude ACP | Anthropic | Opus | Dallas worktree | review/read-oriented |
| Parker | Spark | Herdr | buzz-acp | Codex ACP | OpenAI | GPT-5.6 Sol | Parker worktree | production implementation |
| Brett | Spark | Herdr | buzz-acp | OpenCode ACP | Ollama | Qwen3.6 35B-A3B | Brett worktree | verify, no production repair |
| Lambert | Mac | launchd | buzz-acp/integration | Gemini ACP | Gemini | subscription | knowledge context | Google source projection |

---

# 27. Commissioning Checklist

## Repo

- [ ] Private `nostromo` repository exists
- [ ] NOSTROMO-0001 committed
- [ ] NOSTROMO-PLAN-0001 committed
- [ ] manifest parses
- [ ] budget test passes
- [ ] no secrets committed

## Jetson

- [ ] NVMe healthy
- [ ] Tailscale/private network healthy
- [ ] Docker/Compose pinned
- [ ] Buzz production Compose pinned
- [ ] Postgres healthy
- [ ] Redis healthy
- [ ] MinIO healthy
- [ ] relay healthy
- [ ] membership required
- [ ] auth required
- [ ] relay private key backed up
- [ ] persistent volume backup baseline

## Mac

- [ ] Buzz Desktop connected
- [ ] owner identity stable
- [ ] #nostromo-control exists
- [ ] SSH to Spark
- [ ] Herdr remote attach
- [ ] Ash subscription auth
- [ ] Lambert Gemini auth

## Spark

- [ ] Nostromo repo cloned
- [ ] Herdr pinned
- [ ] persistent session tested
- [ ] workspaces created
- [ ] four SquadOps worktrees healthy
- [ ] Ollama healthy
- [ ] Qwen3.6 35B-A3B exact tag recorded
- [ ] Qwen benchmark acceptable
- [ ] OpenCode ACP works
- [ ] Codex ACP works
- [ ] Claude ACP works

## Identities

- [ ] Mother key
- [ ] Ash key
- [ ] Ripley key
- [ ] Dallas key
- [ ] Parker key
- [ ] Brett key
- [ ] Lambert key
- [ ] public keys committed
- [ ] NIP-05 handles set and resolve via the relay
- [ ] private keys excluded
- [ ] relay membership complete
- [ ] control-channel membership complete

## Budgets

- [ ] Parker OpenAI project
- [ ] Parker enforced $65 cap
- [ ] Ripley OpenAI project
- [ ] Ripley enforced $27 cap
- [ ] Dallas Anthropic Workspace
- [ ] Dallas $27 spend limit
- [ ] Ash API key absent
- [ ] configured total = $139

## GitHub identities

- [ ] nostromo-parker App created and installed on squad-ops only
- [ ] nostromo-ripley App created and installed on squad-ops only
- [ ] App keys stored host-local on Spark only
- [ ] probe commits attribute to the bots
- [ ] rulesets exported to infrastructure/github/rulesets/
- [ ] ruleset rejection probes pass
- [ ] owner GitHub credentials absent from crew environments

## Agents

- [ ] Mother round trip
- [ ] Brett round trip
- [ ] Ripley round trip
- [ ] Dallas round trip
- [ ] Parker round trip
- [ ] Ash round trip
- [ ] Lambert round trip
- [ ] all runtime attribution correct
- [ ] all permission probes correct

## Collaboration

- [ ] Mother -> Ripley
- [ ] Ripley -> Dallas
- [ ] Dallas -> Ripley
- [ ] Mother -> Parker
- [ ] Parker -> Brett
- [ ] Brett -> Parker
- [ ] Ash -> Mother
- [ ] unauthorized invocation rejected
- [ ] role-regression tests pass

## Recovery

- [ ] agent process restart
- [ ] Herdr detach/reconnect
- [ ] Spark reboot
- [ ] Jetson reboot
- [ ] Mac shutdown
- [ ] Buzz state preserved
- [ ] stable identities preserved
- [ ] provider credential failure fails closed

## End to end

- [ ] real low-risk SquadOps item selected
- [ ] IDEA phase
- [ ] architecture
- [ ] adversarial review
- [ ] owner acceptance
- [ ] implementation plan
- [ ] implementation
- [ ] QA
- [ ] final review
- [ ] merge/close
- [ ] metrics captured

---

# 28. Stop Conditions

The setup agent MUST stop and report rather than improvise if:

1. Buzz production Compose does not support the Jetson architecture selected.
2. Buzz relay membership/auth cannot be enforced.
3. a stable agent key cannot be reused on restart.
4. a runtime requires a shared provider credential.
5. OpenAI enforced project spend limits are unavailable to the owner's account.
6. Anthropic Workspace spend limits are unavailable.
7. Ash requires an API key to function and cannot use the intended subscription path.
8. Herdr cannot preserve the agent process across detach.
9. OpenCode ACP cannot reliably use the selected Ollama model.
10. the Qwen model cannot perform required tool calls adequately.
11. Buzz cannot deliver agent-to-agent mentions under allowlist policy.
12. an agent's process cannot be bound to the intended worktree.
13. provider usage is attributed to the wrong project/workspace.
14. secrets appear in git or logs.
15. a current tool version invalidates a critical architectural assumption in NOSTROMO-0001.
16. a crew commit or pull request attributes to the owner's personal account rather than the crew's GitHub App, or the required rulesets cannot be created on `squad-ops`.

A stop condition should produce:

```text
Observed behavior
Expected behavior
Evidence
Likely cause
Whether spec is contradicted
Safe options
Recommended next action
```

---

# 29. Implementation Deviation Log

Create:

```text
docs/deviations.md
```

For every meaningful deviation:

```text
ID
Date
Spec/plan reference
Expected
Actual tooling constraint
Chosen workaround
Security/cost impact
Temporary or permanent
Owner approval
Revisit trigger
```

Examples likely to need entries:

- exact Buzz persona injection behavior;
- exact managed-agent support;
- Gemini ACP maturity;
- OpenCode permission schema version;
- Codex subscription auth behavior under Buzz;
- production Buzz TLS topology.

---

# 30. Source Validation Notes

This plan was cross-checked against current public documentation as of 2026-09-06.

## Buzz

Current Buzz documentation establishes:

- production single-node deployment under `deploy/compose/`;
- production stack use of Postgres, Redis, MinIO and durable git/media state;
- `buzz-acp` as the WebSocket-to-ACP bridge;
- unique Nostr keypairs per agent;
- relay-served NIP-05 lookup with the handle domain bound to the relay hostname, settable per profile through the CLI;
- membership registration;
- configuration through `BUZZ_PRIVATE_KEY`, `BUZZ_RELAY_URL`, `BUZZ_ACP_AGENT_COMMAND`, `BUZZ_ACP_AGENT_ARGS`, optional MCP command and API token;
- ACP child support for Codex and Claude;
- relay membership/auth production controls.

References:

- https://github.com/block/buzz/blob/main/README.md
- https://github.com/block/buzz/blob/main/crates/buzz-acp/README.md
- https://github.com/block/buzz/blob/main/docs/remote-agents.md
- https://github.com/block/buzz/blob/main/deploy/compose/.env.example
- https://github.com/block/buzz/blob/main/Dockerfile

## Herdr

Current Herdr documentation establishes:

- background server owns persistent panes/processes;
- detach/reattach;
- named sessions;
- workspaces;
- remote attach over SSH;
- independent named-session sockets/state.

References:

- https://herdr.dev/docs/concepts/
- https://herdr.dev/docs/persistence-remote/
- https://herdr.dev/docs/how-to-work/
- https://herdr.dev/docs/cli-reference/
- https://github.com/herdrdev/herdr

## OpenCode

Current OpenCode documentation establishes:

- `opencode acp`;
- ACP over stdio;
- normal tools available in ACP mode;
- Ollama through `http://localhost:11434/v1`;
- granular role permission controls.

References:

- https://opencode.ai/docs/acp/
- https://opencode.ai/docs/providers
- https://opencode.ai/docs/agents

## Codex ACP

Current adapter documentation establishes:

- package `@agentclientprotocol/codex-acp`;
- ChatGPT authentication;
- API-key authentication;
- `CODEX_API_KEY` / `OPENAI_API_KEY`;
- Codex runtime control through ACP.

Reference:

- https://github.com/agentclientprotocol/codex-acp

## Gemini CLI

Current Gemini CLI configuration documents:

```text
--acp
```

as an ACP mode, with the feature still under active development.

Reference:

- https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md

## GitHub Apps and Rulesets

Current GitHub documentation establishes:

- one free machine account per person under the Terms of Service, which rules out per-agent user accounts;
- GitHub Apps as organization-owned identities with fine-grained, repository-scoped permissions and hourly installation tokens;
- rulesets with restrict-creation/update/deletion rules, file-path restrictions using fnmatch with allowed exceptions, and GitHub Apps as bypass actors, with bypass applying per ruleset.

References:

- https://docs.github.com/en/site-policy/github-terms/github-terms-of-service
- https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/about-creating-github-apps
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

## OpenAI Spend Limits

Current OpenAI support material identifies enforced organization/project spend limits and errors including:

```text
organization_spend_limit_exceeded
project_spend_limit_exceeded
```

References:

- https://help.openai.com/en/articles/6614457
- https://help.openai.com/en/articles/9186755

The setup agent must distinguish an enforced spend control from a non-enforced notification/soft budget in the actual current console.

## Anthropic Workspace Limits

Current Anthropic documentation establishes:

- API keys are tied to Workspaces;
- Workspace limits coexist with organization limits;
- Workspace Spend Limits can be configured;
- API usage can fail when organization/workspace spend limits are reached.

References:

- https://support.anthropic.com/en/articles/9796807-creating-and-managing-workspaces
- https://docs.anthropic.com/en/api/errors

---

# 31. Final Execution Sequence

The condensed order is:

```text
1. GitHub
   Create Nostromo repo and commit spec/plan/manifest.

2. Providers and GitHub
   Create bounded Parker/Ripley/Dallas billing identities.
   Create Parker/Ripley GitHub Apps and squad-ops rulesets.
   Validate Ash subscription auth and Gemini baseline.

3. Jetson
   Build private production Buzz appliance on NVMe.
   Prove durable relay.

4. Mac
   Establish Jason owner identity and Buzz Desktop.

5. Spark
   Install Herdr.
   Create workspaces/worktrees.
   Validate Ollama/Qwen.
   Validate OpenCode/Codex/Claude ACP runtimes.

6. Buzz identities
   Mint seven stable identities.
   Register relay/channel membership.
   Commit public key registry.

7. Local Spark agents
   Commission Mother.
   Commission Brett.
   Generalize launcher.

8. Cloud Spark agents
   Commission Ripley.
   Commission Dallas.
   Commission Parker.

9. Mac agents
   Commission Ash.
   Commission Lambert.

10. Crew configuration
    Finalize personas, instructions, capability map,
    lifecycle, allowlists and work-item channel model.

11. Commissioning roll
    Run one real bounded SquadOps improvement through
    idea -> architecture -> challenge -> implementation -> QA.

12. Stabilization
    Restart tests, backup tests, budget cutoff tests,
    secret scan, dependency pins, runbooks, baseline tag.
```

---

# 32. Definition of Done

`NOSTROMO-PLAN-0001` is complete when the owner can sit at the Mac and:

1. open Buzz Desktop;
2. see the seven stable Nostromo crew identities;
3. discuss an idea with Ash;
4. allow Mother to route the converged work to Ripley;
5. have Ripley operate against SquadOps on Spark;
6. have Dallas independently challenge it through a different provider/model family;
7. approve the SquadOps change through existing governance;
8. have Parker implement it in an isolated Spark worktree;
9. have Brett independently verify it using deterministic evidence and local inference;
10. have Dallas perform independent closeout review where required;
11. inspect every persistent Spark agent through Herdr from the Mac;
12. disconnect the Mac without stopping the Spark crew or Buzz server;
13. restart an agent without changing its Buzz identity;
14. identify the exact harness/model/provider/worktree backing any agent;
15. prove Parker/Ripley/Dallas are bounded by their dedicated provider limits, and that crew commits attribute to crew GitHub identities rather than the owner;
16. prove Ash is not consuming metered OpenAI API budget;
17. recover canonical design/code/test state from GitHub even if all transient LLM sessions disappear;
18. reboot the Jetson or Spark according to documented procedures without losing the crew definition;
19. see a complete evidence trail from idea through implementation and verification;
20. use the resulting system as the persistent external development crew for the SquadOps roadmap.

At that point Nostromo has crossed the threshold from a collection of agent terminals into an operational development crew.

The next work after this plan should be driven by observed operation rather than additional pre-emptive infrastructure design.
