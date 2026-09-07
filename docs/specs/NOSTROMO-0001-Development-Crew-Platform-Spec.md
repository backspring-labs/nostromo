# NOSTROMO-0001: Development Crew Runtime, Collaboration, and Infrastructure Specification

**Status:** Draft Design Baseline  
**Version:** 0.1  
**Date:** 2026-09-06  
**Owner:** Jason Ladd  
**Project:** Nostromo  
**Primary Product Under Development:** SquadOps  
**Document Class:** Nostromo Specification — **not** a SquadOps SIP  
**Companion Document:** Detailed implementation/execution plan — intentionally deferred

---

## 1. Abstract

Nostromo is a persistent, multi-agent software development crew whose initial mission is to design, build, review, test, and evolve the SquadOps platform.

Nostromo is intentionally **external to SquadOps**. It must not depend on SquadOps-native agent orchestration in order to build SquadOps, and it does not replace the SquadOps Improvement Proposal (SIP) process or other product governance. Nostromo is the development organization and runtime environment; SquadOps remains the product and retains its own architecture and approval mechanisms.

The crew will collaborate through **Buzz**, execute persistent development sessions through **Herdr** on a DGX Spark, use a mix of local and cloud model providers, and maintain its own version-controlled team definition in a private GitHub repository. A Jetson Orin Nano Super will host the always-on Buzz collaboration infrastructure. A Mac will serve as the human operator cockpit and will host lightweight cloud-backed crew members that do not need persistent Spark execution. Two Raspberry Pi 5 systems remain available for their originally intended Bitcoin and Ethereum node roles and are outside the Nostromo runtime.

The design deliberately separates five concerns:

1. **Identity and collaboration** — Buzz.
2. **Persistent development execution** — Herdr.
3. **Agent harnesses** — OpenCode, Codex ACP, Claude ACP, and Gemini-compatible tooling.
4. **Inference** — local Ollama/Qwen or provider APIs/subscriptions.
5. **Engineering truth** — GitHub repositories, branches, worktrees, SIPs, tests, and evidence.

This specification defines the overall architecture, crew, role boundaries, model and harness assignments, budget controls, runtime affinity, identity model, launch contract, repository structure, collaboration lifecycle, security boundaries, resilience requirements, and acceptance criteria.

It intentionally does **not** define the detailed commands, installation sequence, package versions, host-by-host setup procedure, provisioning scripts, or migration steps. Those belong in the companion execution plan.

---

## 2. Why Nostromo Exists

SquadOps is intended to become an agent-native platform capable of coordinating persistent identities, workloads, cycles, memories, verification, roles, and multiple runtime embodiments. It is not yet appropriate to require SquadOps to orchestrate the external development agents responsible for creating those capabilities.

The development environment therefore needs an independent crew that can:

- explore new SquadOps ideas with the owner;
- research external precedent;
- turn ideas into architecture and SIPs;
- challenge proposed designs before implementation;
- build approved work against the real SquadOps repository;
- run independent QA and deterministic verification;
- maintain a persistent working context over long development sessions;
- coordinate handoffs among specialized agents;
- preserve an auditable record of decisions and work;
- operate primarily from the DGX Spark without requiring the owner's Mac to stay attached;
- remain cost-bounded;
- be inspectable by the owner at any time;
- and provide a practical prototype of many of the identity, role, runtime, delegation, and collaboration concepts that SquadOps itself will eventually formalize.

Nostromo is therefore both a development crew and an architectural learning environment.

Its purpose is **not** to prematurely recreate SquadOps outside SquadOps. Its purpose is to use existing tools — Buzz, Herdr, ACP-compatible harnesses, GitHub, Ollama, and model-provider controls — to form a dependable development team while exposing useful lessons for SquadOps's future design.

---

## 3. Relationship to SquadOps Governance

Nostromo governance and SquadOps product governance are distinct.

### 3.1 Nostromo specification authority

This document governs:

- Nostromo crew composition;
- role ownership;
- model and harness selection;
- runtime placement;
- collaboration behavior;
- budget policy;
- identity configuration;
- infrastructure topology;
- development-workspace conventions;
- and Nostromo operational requirements.

Changes to those concerns may be managed in the Nostromo repository without creating a SquadOps SIP unless the change also alters SquadOps itself.

### 3.2 SquadOps authority remains intact

When Nostromo proposes or implements a change to SquadOps:

- a SquadOps SIP is still a SquadOps SIP;
- existing SquadOps acceptance and owner gates remain authoritative;
- Nostromo does not auto-accept product architecture merely because Ripley authored it;
- Nostromo does not bypass required acceptance because Dallas approved it;
- and Nostromo infrastructure decisions do not become SquadOps architecture by implication.

The distinction is:

> **Nostromo governs the crew that builds SquadOps. SquadOps governance governs the product that crew builds.**

---

## 4. Goals

### G-1 — Persistent crew

The primary engineering agents must remain available across terminal detaches, network interruptions, and ordinary Mac disconnects.

### G-2 — Explicit specialization

Each crew member must have a narrow, documented cognitive and operational role with clear ownership and non-ownership boundaries.

### G-3 — Stable identity independent of model

An agent's identity must survive changes in model, provider, harness, process supervisor, or host placement.

### G-4 — Direct collaboration

Agents must be able to address and hand work to one another through Buzz without requiring the owner to relay every message.

### G-5 — Repo-grounded engineering

Architecture, development, review, and verification agents must operate against real SquadOps repository state rather than isolated prompt context.

### G-6 — Independent review and QA

Architecture challenge, implementation, and verification must remain separate responsibilities to reduce correlated error and self-review.

### G-7 — Hard cost containment

Metered API use must be bounded through provider-side spend controls, isolated credentials, and role-specific budgets. A budget boundary must not depend solely on an agent following a prompt.

### G-8 — Owner inspectability

The owner must be able to inspect the crew's collaboration in Buzz, reconnect to Spark development sessions through Herdr, inspect GitHub artifacts, and identify which model/harness/provider is backing each crew member.

### G-9 — Reconstructability

A fresh machine with the Nostromo repository plus separately provisioned secrets should contain enough declarative information to reconstruct the intended team.

### G-10 — Minimal custom infrastructure

Nostromo should compose existing tools rather than create a new agent framework before evidence requires one.

### G-11 — Future portability

The crew should be capable of working on additional repositories beyond SquadOps without becoming structurally embedded in the SquadOps codebase.

---

## 5. Non-Goals

This specification does not attempt to:

- implement SquadOps-native agents;
- make Herdr a dependency of SquadOps;
- make Buzz part of the SquadOps runtime;
- recreate a general-purpose workflow engine around Buzz;
- replace GitHub as the engineering system of record;
- replace SIP governance;
- design application code for SquadOps;
- define detailed host installation commands;
- define an exact deployment sequence;
- define backup cron jobs or operational scripts;
- provision provider accounts;
- pin all binary versions;
- design a public Buzz service;
- run heavyweight inference on the Jetson;
- move Mother onto the Jetson;
- use the Raspberry Pi systems for Nostromo;
- or guarantee that a particular model remains permanent.

Those topics are either implementation-plan concerns or future evolution.

---

## 6. Normative Language

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** indicate requirement strength.

- **MUST / MUST NOT** — required for conformance.
- **SHOULD / SHOULD NOT** — preferred unless a documented reason justifies deviation.
- **MAY** — optional.

---

# Part I — Architecture

## 7. Architecture Principles

### 7.1 Identity is not embodiment

A Nostromo agent is not its Herdr pane, model session, Codex conversation, or provider API key.

Agent identity is a durable configuration composed of:

- a stable logical name;
- a Buzz/Nostr identity;
- a persona;
- team membership;
- capabilities;
- role constraints;
- and durable external work state.

Herdr, OpenCode, Codex, Claude, Ollama, and cloud models are replaceable runtime components.

### 7.2 Buzz is the collaboration substrate, not the brain

Buzz provides:

- agent and human identities;
- channels and threads;
- @mentions;
- signed events;
- shared collaboration context;
- Canvases/workbench material;
- workflow/event surfaces;
- search;
- presence;
- and agent-to-agent communication.

Buzz does not own the reasoning role of Mother and does not replace GitHub, Herdr, or the underlying agent harness.

### 7.3 Herdr owns persistence, not identity or ACP

Herdr is the persistent terminal/process runtime for the Spark-resident development crew.

Herdr MUST NOT be treated as the source of:

- Buzz identity;
- ACP configuration;
- provider identity;
- persona;
- team membership;
- or canonical workflow state.

A Herdr workspace/pane starts a Nostromo agent launcher. That launcher starts `buzz-acp`, and `buzz-acp` connects the agent to Buzz and spawns the configured ACP-speaking agent runtime.

### 7.4 GitHub is the engineering system of record

Canonical engineering state MUST reside in GitHub and the relevant repositories.

Buzz is the collaboration/workbench layer.

The guiding rule is:

> **GitHub artifact = record. Buzz Canvas/thread = workbench.**

SIPs, implementation plans, code, commits, PRs, tests, accepted decisions, and release evidence must not exist only in Buzz conversation history.

### 7.5 Deterministic controls beat prompt promises

Where a boundary can be enforced mechanically, it SHOULD be.

Examples:

- provider-side spend limits instead of only budget reminders;
- read-only permissions instead of telling a reviewer not to edit;
- independent worktrees instead of asking reviewers to ignore mutable local state;
- Buzz author allowlists instead of open agent endpoints;
- distinct provider credentials instead of a shared API key;
- CI/test evidence instead of an agent claiming that tests passed.

### 7.6 Role identity remains stable while implementation evolves

The role **Parker** should remain the implementation engineer even if Parker moves from GPT-5.6 Sol to another model, Codex to another harness, or Herdr to another persistent runtime in the future.

This is a core design constraint because it mirrors the identity/runtime separation SquadOps itself is attempting to achieve.

---

## 8. Physical Topology

The initial physical topology is:

```text
                                 GitHub
                        engineering source of truth
                                  ▲
                                  │
                  ┌───────────────┼────────────────┐
                  │               │                │
                  │               │                │
             MAC COCKPIT      JETSON ORIN      DGX SPARK
                  │            NANO SUPER           │
                  │               │                 │
          Buzz Desktop       Buzz server         Herdr
          owner identity     infrastructure       runtime
                  │               │                 │
          Ash + Lambert      relay/database     Mother
                  │          object/git state    Ripley
                  │               │              Dallas
                  └────── Buzz / WebSocket ───── Parker
                                  │              Brett
                                  │                 │
                                  │              Ollama
                                  │                 │
                                  │        Qwen3.6 35B-A3B
                                  │
                           collaboration plane
```

Two Raspberry Pi 5 systems are intentionally excluded:

```text
Raspberry Pi 5 #1 -> Bitcoin node
Raspberry Pi 5 #2 -> Ethereum node
```

They are not Nostromo infrastructure.

---

## 9. Host Responsibilities

### 9.1 DGX Spark — development/execution substrate

The Spark is the primary development ship.

It MUST host:

- Herdr;
- the persistent core Nostromo development crew;
- the SquadOps repository;
- isolated git worktrees for repo-facing specialists;
- local development dependencies required to build/test SquadOps;
- existing Ollama infrastructure;
- Qwen3.6 35B-A3B for local Nostromo inference;
- and SquadOps's own development/test runtime as appropriate.

The Spark MUST NOT be the sole host of Buzz's durable collaboration state.

The Spark MAY be restarted or heavily loaded for SquadOps experimentation without destroying the Buzz server.

### 9.2 Jetson Orin Nano Super — collaboration infrastructure

The Jetson will be the always-on Buzz infrastructure node.

It MUST host the production-oriented Buzz self-host stack, including the components required by the selected Buzz Compose deployment.

The current Buzz production Compose model includes:

- Buzz relay;
- PostgreSQL;
- Redis;
- MinIO;
- persistent git/media/data volumes;
- and optional TLS/reverse-proxy support.

The Jetson SHOULD use NVMe-backed storage for persistent Buzz data. Persistent database/event/object/git state MUST NOT depend primarily on a microSD card.

The Jetson's role in v1 is deliberately boring:

> **stable communications and collaboration infrastructure**

The Jetson MUST NOT host Mother merely because Mother communicates through Buzz.

The Jetson MAY later host lightweight supporting services, but such expansion is outside this baseline.

### 9.3 Mac — human control plane

The Mac is the owner's cockpit.

It SHOULD host:

- Buzz Desktop;
- the owner's Buzz identity;
- a clone of the Nostromo repository;
- GitHub tooling;
- a Herdr remote client or SSH access to Spark;
- Ash's lightweight persistent Buzz/ACP process;
- Lambert's lightweight Google-oriented process;
- and normal operator tools.

The Mac MUST NOT be required to stay connected for Spark-resident crew processes or the Buzz relay to remain alive.

### 9.4 Network

The systems SHOULD communicate over the owner's private network/overlay, with Tailscale preferred based on the existing environment.

The initial deployment SHOULD minimize public exposure.

If Buzz is exposed beyond the private network, authentication, TLS, membership controls, and additional hardening become mandatory before exposure.

---

# Part II — Crew Definition

## 10. Canonical Nostromo Roster

The v1 crew contains seven agents.

| Agent | Nostromo Role | Primary Responsibility | Host | Persistent Herdr Affinity | Harness | Model / Backing | Incremental Monthly Budget |
|---|---|---|---|---|---|---|---:|
| **Mother** | Orchestrator | Routing, lifecycle coordination, state, escalation | Spark | Yes | OpenCode ACP | Qwen3.6 35B-A3B via Ollama | ~$0 API |
| **Ash** | Research & Ideation | Exploration, research, IDEA convergence | Mac | No | Codex ACP-compatible path | ChatGPT Plus-backed Codex/ChatGPT auth | $20 fixed |
| **Ripley** | Architect | Architecture, SIP drafting, implementation planning | Spark | Yes | Codex ACP | GPT-5.6 Sol API | Hard cap $27 |
| **Dallas** | Adversarial Reviewer | Independent architecture/design challenge; final independent review | Spark | Yes | Claude ACP | Claude Opus API | Hard cap $27 |
| **Parker** | Implementation Engineer | Coding, debugging, build work, PR implementation | Spark | Yes | Codex ACP | GPT-5.6 Sol API | Hard cap $65 |
| **Brett** | QA / Verification | Tests, deterministic verification, evidence, failure diagnosis | Spark | Yes | OpenCode ACP | Qwen3.6 35B-A3B via Ollama | ~$0 API |
| **Lambert** | Knowledge & Google Specialist | Google ecosystem, instructional corpus, NotebookLM source maintenance | Mac | No | Gemini-compatible ACP/tooling | Existing Gemini subscription | $0 incremental |

Maximum intentionally allocated incremental cloud/subscription envelope:

```text
ChatGPT Plus             $20
Parker OpenAI cap        $65
Ripley OpenAI cap        $27
Dallas Anthropic cap     $27
                         ---
Configured envelope     $139
Target ceiling          $150
Buffer                   $11
```

The $11 difference is deliberate margin for accounting/cutoff lag and incidental variance. Existing Gemini spend and local electricity are not counted as incremental Nostromo API budget.

---

## 11. Crew Role Contracts

### 11.1 Mother — Orchestrator

**Question Mother answers:**  
> What happens next, and who should do it?

Mother owns:

- workflow coordination;
- work-item lifecycle awareness;
- capability-to-agent routing;
- delegation;
- follow-up;
- state transitions;
- routine retry and handoff mechanics;
- budget-awareness;
- surfacing blocked work;
- owner escalation when policy requires judgment;
- and synthesis of team status.

Mother does **not** own:

- product architecture;
- SIP authorship;
- implementation;
- independent code review;
- QA conclusions;
- research depth that belongs to Ash;
- or discretionary bypass of owner gates.

Mother MUST prefer delegation over doing specialist work herself.

Mother MUST use the team manifest to resolve responsibilities rather than embedding an unstructured set of hard-coded assumptions in the prompt.

Mother SHOULD be able to continue orchestration after its underlying model process restarts because durable work state is externalized.

### 11.2 Ash — Research & Ideation

**Question Ash answers:**  
> What could this be, what should we know, and has the idea converged enough for architecture?

Ash is the owner's default exploratory thinking partner inside Buzz.

Ash owns:

- exploratory discussion;
- idea expansion;
- external precedent research;
- alternatives;
- conceptual challenges;
- implications;
- synthesis;
- maintenance of a living IDEA workbench/Canvas;
- and identification of unresolved assumptions.

Ash does **not** own:

- formal SquadOps architecture;
- final SIP design;
- production code;
- QA;
- or product acceptance.

Ash SHOULD hand converged concepts to Ripley through Mother rather than silently converting ideation into architecture.

Ash's subscription-backed configuration MUST NOT silently fall back to metered OpenAI API usage.

### 11.3 Ripley — Architect

**Question Ripley answers:**  
> How should this fit into SquadOps?

Ripley owns:

- repository-grounded architectural analysis;
- review of existing SIP precedent;
- compatibility with SquadOps architecture;
- architecture option analysis;
- SIP authorship;
- revisions responding to Dallas;
- and post-acceptance implementation planning.

Ripley MAY write architecture/SIP artifacts in an isolated worktree/branch.

Ripley MUST NOT be the primary implementation engineer for work Ripley designed.

Ripley MUST treat Dallas's adversarial review as independent input rather than a subordinate approval formality.

Unresolved material disagreement between Ripley and Dallas MUST escalate rather than being silently averaged away.

### 11.4 Dallas — Adversarial Reviewer

**Question Dallas answers:**  
> What is wrong with this, what assumptions fail, and should this be accepted?

Dallas owns independent challenge.

Dallas SHOULD:

- look for architectural contradictions;
- identify hidden coupling;
- attack assumptions;
- challenge scope;
- test claims against repository evidence;
- identify governance or security concerns;
- look for insufficient acceptance criteria;
- and distinguish genuine blocking issues from preferences.

Dallas MUST remain independent from Ripley's model/provider family where practical.

Dallas MUST NOT rewrite the proposal simply to make it conform to Dallas's preferred design.

Dallas SHOULD state blocking objections, non-blocking concerns, and unresolved questions distinctly.

Dallas MAY also perform a final independent review after implementation/QA where warranted.

### 11.5 Parker — Implementation Engineer

**Question Parker answers:**  
> How do we build the accepted design correctly?

Parker owns:

- production code;
- implementation changes;
- debugging;
- unit/integration test implementation associated with the code change;
- build repair;
- branch/commit work;
- PR preparation;
- and responding to Brett's verified failures.

Parker receives an accepted design and sufficiently mature implementation plan.

Parker MUST NOT redefine accepted architecture opportunistically during implementation. Material architecture deviations MUST be returned to Ripley/Mother and, where required, the owner.

Parker is expected to be the largest metered-cloud consumer in Nostromo and therefore receives the largest provider hard cap.

### 11.6 Brett — QA / Verification

**Question Brett answers:**  
> Does it actually work, and can we prove it?

Brett owns:

- acceptance verification;
- deterministic tests;
- test execution;
- build/lint/typecheck execution;
- evidence collection;
- failure reproduction;
- failure classification;
- regression verification;
- and QA conclusions.

Brett is explicitly separate from Dallas.

Dallas asks whether the design is right.  
Brett asks whether the implementation demonstrably satisfies it.

Brett SHOULD depend heavily on deterministic tooling and evidence rather than expensive free-form model judgment.

Brett MUST NOT silently repair Parker's production implementation.

When verification fails, Brett hands evidence and diagnosis back to Parker.

Brett uses the general Qwen3.6 35B-A3B model in v1, **not a coding-specialized variant**, because the role is verification and evidence reasoning rather than primary code generation.

### 11.7 Lambert — Knowledge & Google Specialist

**Question Lambert answers:**  
> How do we keep the learning and Google knowledge surface current?

Lambert owns:

- maintaining a Google-oriented instructional projection of SquadOps;
- curating canonical source material into the selected Google knowledge surface;
- maintaining sources used by NotebookLM;
- and supporting instructional summaries/audio/podcast workflows where available.

Lambert is not on the critical engineering path.

GitHub remains canonical. Lambert's artifacts are projections of canonical source material.

Loss of Gemini/NotebookLM availability MUST NOT block SquadOps development.

---

# Part III — Collaboration Model

## 12. Shared Team Instructions

Nostromo MUST maintain one shared `instructions.md` that functions as the crew's constitution.

It SHOULD define:

- mission;
- role boundaries;
- owner authority;
- collaboration etiquette;
- delegation rules;
- artifact hierarchy;
- handoff expectations;
- evidence requirements;
- conflict handling;
- budget behavior;
- escalation policy;
- and lifecycle semantics.

Role-independent rules MUST be placed in team instructions rather than duplicated across seven persona prompts.

Persona prompts SHOULD focus on:

1. what the agent owns;
2. what the agent does not own;
3. required inputs;
4. required outputs;
5. handoff conditions;
6. authority boundaries.

---

## 13. SquadOps Development Lifecycle

The baseline development lifecycle is:

```text
Jason / Roadmap
      │
      ▼
IDEA / EXPLORE
      │
      ▼
Ash
research + convergence
      │
      ▼
Mother
routes mature concept
      │
      ▼
Ripley
architecture / SIP
      │
      ▼
Dallas
adversarial review
      │
      ├── objections ──> Ripley revision ──┐
      │                                    │
      └────────────────────────────────────┘
      │
      ▼
SquadOps acceptance gate / Jason as required
      │
      ▼
Ripley
implementation plan
      │
      ▼
Parker
implementation
      │
      ▼
Brett
QA / deterministic verification
      │
      ├── failures ──> Parker fixes ───────┐
      │                                    │
      └────────────────────────────────────┘
      │
      ▼
Dallas
final independent review when applicable
      │
      ▼
merge / close / observe
      │
      ▼
Lambert
refresh instructional projection
```

Not every work item requires every stage. Mother may choose an abbreviated path for low-risk tasks only when that choice complies with SquadOps governance and owner policy.

---

## 14. Lifecycle States

Nostromo SHOULD use a machine-readable lifecycle model compatible with:

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

The exact storage implementation is deferred.

Lifecycle state MUST NOT exist only in Mother's private conversation memory.

A restart of Mother must not erase the authoritative status of work.

---

## 15. Handoff Contract

Every specialist handoff SHOULD include:

- work-item identifier;
- current lifecycle state;
- canonical GitHub references;
- relevant Buzz Canvas/thread;
- expected receiving capability;
- explicit request;
- acceptance criteria or question;
- known unresolved issues;
- and required return condition.

Example semantics:

```text
Ripley -> Mother:
SIP draft ready.
Canonical artifact: ...
Unresolved: ...
Request: adversarial_review.

Mother resolves adversarial_review -> Dallas.

Dallas -> Mother/Ripley:
Blocking: ...
Non-blocking: ...
Evidence: ...
Disposition required: revision.
```

Handoffs should be explicit events rather than inferred from silence.

---

## 16. Owner Authority and Escalation

The owner retains authority over at least:

- material architectural acceptance;
- changes that materially expand scope;
- destructive changes;
- security-sensitive decisions;
- policy exceptions;
- unresolved architecture disagreement;
- meaningful budget reallocation;
- provider/model changes that materially alter cost or capability;
- and any decision explicitly reserved by SquadOps governance.

Mother SHOULD NOT continuously request permission for routine mechanical work.

Mother SHOULD escalate decisions, not chores.

---

## 17. Buzz Channel Model

Nostromo SHOULD use:

### Control channel

A stable control/meta channel for:

- crew presence;
- operating status;
- major work-item announcements;
- blocked work;
- budget status;
- and owner-level coordination.

### Work-item channels

Meaningful initiatives SHOULD receive dedicated channels.

Examples:

```text
#nostromo-control
#memory-console
#cross-cycle-memory
#runtime-embodiment
```

A dedicated work-item channel reduces context pollution and aligns well with Buzz's channel-scoped ACP conversation behavior.

Threads SHOULD be used for focused sub-conversations.

---

## 18. Buzz Canvas Usage

Canvas SHOULD serve as the living collaborative workbench for:

- IDEA evolution;
- research notes;
- unresolved questions;
- decision synthesis;
- review matrices;
- and temporary collaboration artifacts.

A Canvas MUST NOT be treated as the sole durable record of accepted engineering work.

Accepted artifacts must move to GitHub.

---

# Part IV — Buzz and Identity Architecture

## 19. Buzz Deployment Model

Buzz will run on the Jetson using the production-oriented self-host deployment model, not the repository's local developer stack.

The deployment MUST use durable volumes for database/event/object/git state.

The initial relay SHOULD operate as a closed/private team service.

Production controls SHOULD include:

- authentication token enforcement;
- relay membership restrictions;
- stable relay identity;
- persistent storage;
- health/readiness checks;
- and backups.

Exact Compose files, environment values, hostnames, certificates, and installation commands are execution-plan concerns.

---

## 20. Stable Agent Identity

Each Nostromo agent MUST receive a unique, stable Buzz/Nostr keypair.

The stable public identity SHOULD be recorded in the Nostromo team manifest.

The private key MUST NOT be committed to GitHub.

An agent's stable identity MUST survive:

- Herdr restart;
- Spark restart;
- Mac restart;
- harness upgrade;
- model upgrade;
- provider change;
- ACP adapter replacement;
- and relocation to a different process supervisor.

If Parker changes from Codex to another ACP harness, Buzz should still see Parker.

---

## 21. Buzz Author Policy

Nostromo agents MUST NOT run with an unrestricted `anyone` inbound author policy in the baseline deployment.

Each collaboration-capable agent SHOULD use Buzz's `allowlist` behavior.

The allowlist SHOULD contain the public identities of authorized Nostromo collaborators. The registered owner remains authorized.

This permits:

```text
Jason -> Mother
Mother -> Ripley
Ripley -> Dallas
Dallas -> Ripley
Mother -> Parker
Parker -> Brett
Brett -> Parker
```

while rejecting untrusted relay participants.

The team manifest SHOULD be capable of generating or validating these allowlists.

---

## 22. `buzz-acp` Role

For every ACP-connected Nostromo agent, `buzz-acp` is the outer collaboration process.

Conceptually:

```text
Buzz Relay
    ▲
    │ WebSocket
    │
buzz-acp
    │
    │ ACP over child-process transport
    ▼
ACP-speaking harness
    │
    ▼
model/provider
```

`buzz-acp` owns:

- the Buzz connection;
- Buzz/Nostr agent identity;
- inbound event filtering;
- channel/thread context delivery;
- team/persona context delivery;
- agent lifecycle around ACP turns;
- and collaboration back to Buzz.

The ACP-speaking child owns agent execution.

---

## 23. Buzz Persona Pack Compatibility

The Nostromo repository SHOULD be authored to align with Buzz's Persona Pack specification.

At minimum this means preserving a structure compatible with:

```text
.plugin/plugin.json
agents/*.persona.md
instructions.md
skills/*/SKILL.md
.mcp.json
```

where useful.

However, the v1 design MUST recognize current Buzz limitations:

1. Persona Packs are a useful portable, git-authored definition format.
2. Buzz Desktop does not currently provide a direct Persona-Pack-to-running-team import path equivalent to its agent/team snapshot imports.
3. Persona Pack hooks are not yet a reliable execution mechanism for critical lifecycle control.
4. Some behavioral definition fields remain in evolution.
5. Current persona prompt injection is implemented as a `[System]` prefix in the message path rather than guaranteed native model-system-prompt semantics.
6. MCP secret interpolation from pack definitions must not be assumed to solve secret distribution.
7. Team deployment UI behavior must not be trusted to preserve all custom harness semantics until validated.

Therefore:

> **Nostromo will author team definitions like a Buzz Persona Pack, but v1 runtime launch is explicitly controlled by Nostromo launch configuration.**

This avoids coupling the crew to immature team-deployment mechanics while preserving compatibility with Buzz's intended direction.

---

# Part V — Herdr and Runtime Affinity

## 24. Herdr Deployment Model

Herdr will run on the DGX Spark.

The preferred logical structure is:

```text
Herdr named session: nostromo

  workspace: mother-control
      primary agent pane: Mother

  workspace: ripley-architecture
      primary agent pane: Ripley

  workspace: dallas-review
      primary agent pane: Dallas

  workspace: parker-development
      primary agent pane: Parker

  workspace: brett-verification
      primary agent pane: Brett
```

The exact names are not normative.

This clarifies terminology:

- Nostromo has one persistent Herdr runtime namespace/session;
- individual crew members have persistent workspace/pane affinity within it;
- additional panes may be created for logs, test runners, servers, or investigations.

If the eventual Herdr implementation makes separate named sessions materially superior, the execution plan may adapt while preserving per-agent persistence and isolation.

---

## 25. Herdr Responsibilities

Herdr MUST provide:

- persistent terminal ownership;
- reattachment after owner disconnect;
- durable development processes across terminal detach;
- dedicated working directories;
- inspectability from the Mac;
- and a stable place to run each Spark agent's launcher.

Herdr SHOULD expose useful process/agent state where its integrations support it.

Nostromo MUST NOT rely on Herdr-specific agent-state detection as the only source of truth for lifecycle status.

---

## 26. Spark Agent Process Tree

The canonical process shape is:

```text
Herdr workspace/pane
      │
      ▼
Nostromo launcher
      │
      ▼
buzz-acp
      │
      ▼
ACP-speaking harness
      │
      ▼
model/provider
```

Examples:

```text
Mother
Herdr -> launcher -> buzz-acp -> OpenCode ACP -> Ollama -> Qwen3.6 35B-A3B

Ripley
Herdr -> launcher -> buzz-acp -> Codex ACP -> OpenAI -> GPT-5.6 Sol

Dallas
Herdr -> launcher -> buzz-acp -> Claude ACP -> Anthropic -> Claude Opus

Parker
Herdr -> launcher -> buzz-acp -> Codex ACP -> OpenAI -> GPT-5.6 Sol

Brett
Herdr -> launcher -> buzz-acp -> OpenCode ACP -> Ollama -> Qwen3.6 35B-A3B
```

Herdr does not connect to Buzz.  
`buzz-acp` connects to Buzz.

---

## 27. Mac Agent Process Affinity

Ash and Lambert do not require Spark Herdr sessions.

### Ash

```text
Mac persistent process
      │
      ▼
buzz-acp
      │
      ▼
Codex ACP-compatible adapter
      │
      ▼
ChatGPT subscription authentication
```

Ash SHOULD use a persistent Mac process supervisor or Buzz-managed local-agent mechanism once validated.

Ash MUST use a stable Buzz identity independent of the local process manager.

### Lambert

```text
Mac persistent process
      │
      ▼
buzz-acp or supported Buzz integration
      │
      ▼
Gemini-compatible ACP/tool path
      │
      ▼
existing Google/Gemini subscription
```

The exact Gemini/Buzz adapter must be validated during execution planning.

Lambert's role definition is stable even if the adapter changes.

---

# Part VI — Harness and Model Strategy

## 28. Local Inference

Mother and Brett use:

**Qwen3.6 35B-A3B through Ollama on the DGX Spark.**

Rationale:

- local inference cost;
- appropriate general agent reasoning;
- sparse MoE model suitable for responsive agent turns;
- current Ollama availability;
- avoidance of unnecessary additional inference runtimes;
- and separation of orchestration/verification from expensive cloud coding roles.

The selected baseline is the **general** model, not a coding-specific variant.

The initial Ollama build may be quantized as appropriate for Spark operation, but the exact tag/quantization is an execution-plan decision that should be benchmarked and pinned.

### 28.1 Relationship to existing SquadOps Qwen model

SquadOps currently uses Qwen3.8 27B as a predominant local model.

Nostromo does not require SquadOps to change that model.

The expected usage pattern is largely phase-separated:

```text
Nostromo development/collaboration phase
    -> Mother/Brett local inference

SquadOps execution/cycle phase
    -> SquadOps local inference
```

Continuous heavy simultaneous inference is not a v1 requirement.

Ollama remains the single local inference control plane unless measured evidence later justifies another runtime.

---

## 29. Cloud Inference

### Ripley

- Harness: Codex ACP
- Model: GPT-5.6 Sol
- Provider: OpenAI API
- Credential boundary: dedicated Ripley OpenAI Project/service account/key
- Monthly hard cap: $27

### Parker

- Harness: Codex ACP
- Model: GPT-5.6 Sol
- Provider: OpenAI API
- Credential boundary: dedicated Parker OpenAI Project/service account/key
- Monthly hard cap: $65

### Dallas

- Harness: Claude ACP
- Model family: Claude Opus
- Provider: Anthropic API
- Credential boundary: dedicated Dallas Anthropic Workspace/key
- Monthly hard cap: $27

Dallas intentionally uses a different provider/model family from Ripley and Parker to reduce correlated architectural review failure.

---

## 30. Subscription-Backed Agents

### Ash

Ash uses the owner's ChatGPT Plus subscription through a compatible Codex/ChatGPT authentication path.

The deployment MUST verify that:

- subscription authentication is active;
- no metered OpenAI API key is present as an implicit fallback;
- Ash can receive/respond through Buzz;
- and Ash does not consume the Parker or Ripley API projects.

If subscription-backed ACP integration cannot be made reliable, the architecture must stop and surface the issue rather than silently convert Ash to API billing.

### Lambert

Lambert uses the existing Gemini subscription and is treated as $0 incremental Nostromo budget.

Direct NotebookLM automation is not assumed. Lambert may maintain Google sources that NotebookLM consumes.

---

## 31. Model Substitution Policy

Models and harnesses are runtime bindings, not identity.

They MAY change if:

- capability improves;
- cost improves;
- reliability improves;
- provider support changes;
- or benchmark evidence warrants change.

A model/harness change MUST preserve:

- agent role;
- stable Buzz identity;
- permissions;
- budget boundary;
- expected handoff contract;
- and observable configuration.

Material provider/cost changes require owner approval.

---

# Part VII — Budget and Cost Controls

## 32. Monthly Budget Policy

Nostromo's intended incremental monthly ceiling is **$150**.

The baseline configured envelope is **$139**.

The remaining margin is deliberate.

---

## 33. Hard Provider Boundaries

Prompt-level instructions such as "do not spend over $65" are insufficient.

Metered API agents MUST have provider-enforced spend boundaries where supported.

### OpenAI

Parker and Ripley MUST use separate OpenAI projects or equivalent isolated provider boundaries.

Target hard caps:

```text
Parker  $65
Ripley  $27
```

They MUST NOT share a key that allows one role to consume the other's entire envelope.

### Anthropic

Dallas MUST use a dedicated Anthropic Workspace or equivalent isolated billing boundary.

Target hard cap:

```text
Dallas  $27
```

### Budget exhaustion

When a role's provider boundary is exhausted:

- the agent MUST stop metered use;
- Mother MUST surface the blocked condition;
- the system MUST NOT silently route to an unrestricted credential;
- the system MUST NOT borrow another agent's API key;
- and any reallocation requires explicit owner action.

---

## 34. Burn-Velocity Controls

Rate limits SHOULD also be configured so a runaway loop cannot burn the monthly allocation immediately.

The detailed values belong in the execution plan.

---

## 35. Local Cost Policy

Mother and Brett MUST default to local Ollama inference.

They SHOULD NOT opportunistically route to cloud models merely because the local model is slower.

A cloud fallback for a local role requires an explicit policy change and associated budget boundary.

---

# Part VIII — GitHub Repository and Configuration

## 36. Nostromo Repository

A separate **private GitHub repository** SHOULD be created:

```text
nostromo
```

Nostromo MUST NOT be implemented as a fork of Buzz.

Nostromo MUST NOT live solely inside the SquadOps repo.

Dependency direction:

```text
Buzz + Herdr + model/harness ecosystem
                │
                ▼
             Nostromo
                │
                ▼
          builds SquadOps
```

The repository should eventually be capable of defining a development crew for other Backspring repositories without structural redesign.

---

## 37. Proposed Repository Layout

The initial repository SHOULD resemble:

```text
nostromo/
├── README.md
├── NOSTROMO-0001.md
│
├── .plugin/
│   └── plugin.json
│
├── instructions.md
│
├── agents/
│   ├── mother.persona.md
│   ├── ash.persona.md
│   ├── ripley.persona.md
│   ├── dallas.persona.md
│   ├── parker.persona.md
│   ├── brett.persona.md
│   └── lambert.persona.md
│
├── skills/
│   ├── squadops-repo/
│   │   └── SKILL.md
│   ├── sip-authoring/
│   │   └── SKILL.md
│   ├── verification/
│   │   └── SKILL.md
│   └── ...
│
├── .mcp.json
│
├── team/
│   ├── manifest.yaml
│   ├── lifecycle.yaml
│   ├── permissions.yaml
│   └── budgets.yaml
│
├── runtime/
│   ├── manifests/
│   │   ├── mother.yaml
│   │   ├── ash.yaml
│   │   ├── ripley.yaml
│   │   ├── dallas.yaml
│   │   ├── parker.yaml
│   │   ├── brett.yaml
│   │   └── lambert.yaml
│   │
│   ├── launchers/
│   │   ├── nostromo-agent
│   │   └── host adapters...
│   │
│   └── env/
│       └── *.example
│
├── infrastructure/
│   ├── buzz/
│   │   └── declarative configuration/templates
│   ├── herdr/
│   │   └── workspace/session definitions
│   └── mac/
│       └── local process definitions
│
├── workflows/
│   └── lifecycle/workflow definitions
│
├── docs/
│   ├── architecture.md
│   ├── operations.md
│   ├── security.md
│   └── troubleshooting.md
│
└── tests/
    └── configuration and policy validation
```

This structure is directional rather than a command to create every file immediately.

The execution plan may simplify the initial scaffold while preserving the separation of concerns.

---

## 38. Team Manifest

`team/manifest.yaml` SHOULD be the canonical machine-readable crew registry.

It SHOULD represent fields such as:

```text
logical agent name
capability
Buzz public key
host affinity
harness
model/provider
process supervisor
workspace/worktree
permission profile
budget profile
respond-to policy
```

Example semantics:

```text
capability: adversarial_review
        │
        ▼
team manifest
        │
        ▼
agent: Dallas
        │
        ▼
Buzz public identity
```

Mother SHOULD ultimately be able to consume the same manifest used by deployment tooling.

---

## 39. Runtime Manifests

Each agent SHOULD have a runtime manifest separate from the natural-language persona.

A runtime manifest is configuration, not personality.

Example conceptual fields:

```yaml
agent: parker
host: spark
supervisor: herdr
harness: codex-acp
provider: openai
model: gpt-5.6-sol
workspace_profile: implementation
budget_profile: parker
respond_to: allowlist
```

Exact schema is deferred to implementation planning.

---

## 40. Version-Control Rule

GitHub SHOULD contain everything necessary to reconstruct the intended configuration **except secrets and transient runtime/session state**.

Version control includes:

- personas;
- shared instructions;
- public Buzz identities;
- logical roles;
- capability mappings;
- harness/model assignments;
- permission policies;
- provider project/workspace logical names;
- host affinity;
- worktree conventions;
- startup interface;
- budget limits;
- Buzz configuration templates;
- Herdr workspace definitions;
- validation rules;
- and documentation.

---

# Part IX — Secrets and Authentication

## 41. Secrets Must Remain Out of Repository

The Nostromo repository MUST NOT contain:

- Buzz/Nostr private keys;
- OpenAI API keys;
- Anthropic API keys;
- Google tokens;
- ChatGPT auth tokens;
- GitHub PATs;
- Buzz server auth tokens;
- database passwords;
- MinIO secrets;
- or other credentials.

Example files may name required environment variables but MUST contain placeholders only.

---

## 42. Host-Local Secret Boundaries

Spark agent secrets SHOULD be maintained in a host-local protected configuration area, conceptually:

```text
~/.config/nostromo/secrets/
    mother.env
    ripley.env
    dallas.env
    parker.env
    brett.env
```

Mac agent secrets/auth state SHOULD remain in equivalent protected local storage.

The exact secret manager may evolve.

File-based storage is acceptable for v1 only if permissions and backup handling are appropriate.

---

## 43. Dedicated Provider Identities

Cloud agents SHOULD have dedicated provider credentials.

Parker's credentials must not be Ripley's credentials.

Dallas uses its own Anthropic boundary.

This allows:

- spend isolation;
- audit attribution;
- key rotation;
- model restriction;
- revocation;
- and usage diagnosis.

---

# Part X — Agent Launch Contract

## 44. Generic Launcher Principle

Nostromo SHOULD converge on one generic launcher interface rather than seven unrelated shell scripts.

Conceptually:

```text
nostromo-agent start mother
nostromo-agent start ripley
nostromo-agent start dallas
nostromo-agent start parker
nostromo-agent start brett
nostromo-agent start ash
nostromo-agent start lambert
```

The actual command syntax is an implementation-plan concern.

The launcher resolves:

```text
version-controlled runtime manifest
        +
team manifest
        +
persona
        +
shared instructions
        +
host-local secrets/auth
        +
host/runtime context
        ↓
effective buzz-acp launch
```

---

## 45. Launcher Responsibilities

The launcher MUST:

1. resolve the selected agent;
2. verify required persona/configuration exists;
3. load the correct stable Buzz private identity from host-local secrets;
4. use the configured Buzz relay;
5. configure owner/allowlist policy;
6. select the correct ACP child harness;
7. select the correct provider/model environment;
8. establish the correct working directory;
9. inject shared team instructions;
10. inject the role persona;
11. configure the Buzz MCP/tool bridge required by the child;
12. fail closed when required configuration is missing;
13. avoid provider fallback that could bypass budget boundaries;
14. launch `buzz-acp` as the primary long-running agent process;
15. expose a non-secret effective-configuration summary for diagnostics;
16. avoid printing private keys/tokens;
17. support deterministic restart of the same logical identity.

Where appropriate, the final process launch SHOULD replace the wrapper process rather than leave unnecessary shell supervision layers.

---

## 46. Required Buzz Launch Inputs

The launcher must account for Buzz runtime settings equivalent to:

- agent private identity;
- relay URL;
- relay/API authentication;
- agent command;
- agent arguments;
- optional Buzz MCP command;
- system/persona content;
- team instructions;
- inbound author policy;
- author allowlist;
- owner identity;
- agent working directory;
- timeouts/parallelism;
- and provider-specific environment.

The exact current Buzz environment-variable names must be verified and pinned in the implementation plan rather than copied blindly from this design document.

---

## 47. ACP Child Bindings

The baseline binding is:

```text
Mother -> OpenCode ACP
Ash    -> Codex ACP-compatible adapter
Ripley -> Codex ACP
Dallas -> Claude ACP
Parker -> Codex ACP
Brett  -> OpenCode ACP
Lambert-> Gemini-compatible ACP/tool adapter
```

Changing an ACP adapter MUST NOT mint a new Buzz identity.

---

# Part XI — Repo and Workspace Isolation

## 48. SquadOps Worktrees

Repo-facing specialists SHOULD receive independent git worktrees.

Baseline:

```text
/worktrees/
    ripley/
    dallas/
    parker/
    brett/
```

### Ripley worktree

Used for:

- architectural repository inspection;
- SIP drafting;
- architecture artifacts;
- planning artifacts.

### Dallas worktree

Used for:

- independent review;
- repository validation;
- adversarial evidence gathering.

Dallas should not perform its review inside Parker's mutable implementation tree.

### Parker worktree

Used for:

- production implementation;
- build/debug loop;
- commits/branch/PR work.

### Brett worktree

Used for:

- independent verification;
- test execution;
- evidence reproduction;
- acceptance checking.

Mother MAY use a read-oriented checkout or repository metadata tools but SHOULD NOT require a writable production worktree.

Ash and Lambert do not require Spark worktrees in v1.

---

## 49. Working Directory as Runtime Context

Each ACP session MUST be started with an intentional working directory.

A repo-facing agent's working directory must not accidentally default to the Nostromo repo when the work item requires SquadOps.

The runtime manifest SHOULD distinguish:

- Nostromo configuration repo;
- SquadOps worktree;
- and temporary/evidence directories.

---

# Part XII — Permissions

## 50. Least Privilege

Each role SHOULD receive only the tools and mutation rights required by its job.

### Mother

Allowed:

- Buzz communication;
- work-item/state operations;
- GitHub status/metadata where needed;
- read-oriented repository context;
- budget/status tools.

Restricted or denied:

- arbitrary production code edits;
- routine production commits;
- unrestricted shell;
- provider-credential mutation.

### Ash

Allowed:

- Buzz;
- Canvas;
- research;
- read-oriented GitHub context.

Denied by default:

- production repository writes;
- merges;
- deployments.

### Ripley

Allowed:

- repository read;
- architecture/SIP artifact writes;
- planning artifacts;
- safe analysis commands.

Restricted:

- production implementation changes except explicitly authorized architecture artifacts.

### Dallas

Allowed:

- repository read;
- diff/history/search;
- tests/checks required to validate review claims;
- review comments/evidence.

Denied by default:

- production code modification;
- merge.

### Parker

Allowed:

- production branch/worktree changes;
- build/test/debug commands;
- commits/PR preparation;
- implementation tooling.

Restricted:

- bypassing accepted architecture;
- overriding reviewer/QA evidence without resolution.

### Brett

Allowed:

- repository read;
- test/build/lint/typecheck;
- logs;
- evidence generation;
- deterministic verification.

Denied by default:

- production implementation edits;
- silent remediation.

### Lambert

Allowed:

- canonical source read;
- designated Google knowledge-surface writes.

Denied:

- production code modification;
- product acceptance.

---

## 51. OpenCode Permission Enforcement

Mother and Brett use OpenCode and SHOULD use its permission system to enforce role boundaries mechanically.

The exact allow/ask/deny command patterns are deferred to the execution plan.

Prompts alone are not sufficient protection.

---

# Part XIII — Reliability, Continuity, and Recovery

## 52. Durable State Model

No agent may depend on an indefinitely preserved LLM conversation as the sole source of:

- identity;
- workflow state;
- product decision;
- task status;
- acceptance;
- or canonical requirements.

Durable state must be reconstructable from:

- GitHub;
- Buzz event/thread history;
- team/runtime manifests;
- work-item metadata;
- and persisted collaboration artifacts.

This is especially important because ACP child sessions or `buzz-acp` processes may restart.

---

## 53. Process Recovery

If an agent process dies:

1. the same logical agent must be restartable;
2. it must use the same Buzz identity;
3. it must recover the correct worktree;
4. it must rejoin the intended channels;
5. it must not create a new logical crew member;
6. and it must be able to determine current work from durable state.

Loss of short-term conversational context is acceptable if durable work state is sufficient to resume safely.

---

## 54. Host Failure Expectations

### Jetson unavailable

Impact:

- Buzz collaboration unavailable or degraded.

Must not cause:

- corruption of SquadOps git history;
- loss of provider credentials;
- automatic creation of replacement identities.

Recovery requires restoring the same durable Buzz state or an intentionally managed recovery.

### Spark unavailable

Impact:

- core development crew unavailable;
- local inference unavailable;
- SquadOps build/test unavailable.

Buzz on Jetson should remain alive.

### Mac unavailable

Impact:

- owner cockpit unavailable;
- Ash/Lambert may be unavailable.

Core Spark crew and Buzz relay should remain alive.

This is a deliberate benefit of separating the three hosts.

---

## 55. Provider Exhaustion/Failure

If OpenAI or Anthropic becomes unavailable or a hard cap is reached:

- the affected role transitions to blocked;
- Mother reports the condition;
- no silent credential substitution occurs;
- no unrestricted fallback occurs;
- and the owner decides whether to wait, reallocate, or change runtime binding.

---

# Part XIV — Observability

## 56. Required Operational Visibility

Nostromo SHOULD expose enough information to answer:

- Is Buzz healthy?
- Is the Jetson storage healthy?
- Which crew members are online?
- Which Herdr workspaces/panes are active?
- Which work item is each agent associated with?
- Which harness/model/provider is each agent using?
- Which worktree is each repo-facing agent in?
- How much API budget remains?
- Which work items are blocked?
- What was the last handoff?
- Which tests failed?
- Which agent produced a given decision or review?

---

## 57. Observability Sources

Initial observability may be composed from:

- Buzz presence/events/search;
- Herdr status/sidebar;
- GitHub PR/issue/check state;
- provider usage dashboards;
- Ollama runtime state;
- Jetson container health;
- Buzz relay readiness/metrics;
- structured launcher logs.

A custom dashboard is not required for v1.

---

## 58. Logging

Logs MUST NOT emit:

- private Buzz keys;
- provider API keys;
- auth tokens;
- session credentials;
- or other secrets.

Launchers SHOULD log the effective non-secret configuration, such as:

```text
agent=parker
host=spark
harness=codex-acp
provider=openai
model=gpt-5.6-sol
workspace=/worktrees/parker
respond_to=allowlist
budget_profile=parker
```

This materially improves diagnosis without exposing credentials.

---

# Part XV — Security

## 59. Security Baseline

Nostromo SHOULD initially operate as a private development environment.

Requirements include:

- private Nostromo GitHub repository;
- private network/overlay access;
- Buzz membership/authentication controls;
- encrypted transport where traffic crosses untrusted networks;
- host firewalling;
- least-privilege provider keys;
- no secrets in git;
- protected local secret files;
- explicit agent author allowlists;
- provider spend limits;
- independent credentials by role;
- and regular backups of durable Buzz data.

---

## 60. Supply-Chain Discipline

Buzz, Herdr, ACP adapters, OpenCode, Ollama, and other agent tooling are privileged development dependencies.

The execution plan SHOULD:

- pin versions or immutable commits/images where practical;
- document provenance;
- avoid blindly tracking `main` in a stable deployment;
- define an update process;
- and verify compatibility before upgrades.

Nostromo MUST be reconstructable against a known dependency set.

---

# Part XVI — Decision Ledger

## 61. Accepted Baseline Decisions

### D-001 — Separate project

Nostromo is a separate project/repository, not a SquadOps SIP and not a Buzz fork.

### D-002 — Buzz on Jetson

The Jetson Orin Nano Super is the Buzz infrastructure host.

### D-003 — Raspberry Pis remain blockchain nodes

The two Raspberry Pi 5 systems remain available for Bitcoin and Ethereum node duties.

### D-004 — Spark is the development ship

The DGX Spark hosts persistent core engineering agents, Ollama, worktrees, and SquadOps build/test execution.

### D-005 — Mac is the cockpit

The Mac hosts Buzz Desktop, the owner surface, Herdr remote access, Ash, and Lambert.

### D-006 — Seven-agent crew

The canonical v1 crew is Mother, Ash, Ripley, Dallas, Parker, Brett, and Lambert.

### D-007 — Five Spark-resident persistent agents

Mother, Ripley, Dallas, Parker, and Brett have persistent Herdr affinity on Spark.

### D-008 — Two lightweight Mac agents

Ash and Lambert run outside Spark and do not require Herdr.

### D-009 — Local model

Mother and Brett use Qwen3.6 35B-A3B through Ollama.

### D-010 — No coding variant for QA/orchestration by default

Mother and Brett start on the general model.

### D-011 — Existing SquadOps model remains independent

SquadOps may continue using Qwen3.8 27B for its own cycles.

### D-012 — Single local inference runtime

Ollama remains the local inference runtime; vLLM or another server is not added without measured need.

### D-013 — Cloud model specialization

Ripley and Parker use GPT-5.6 Sol; Dallas uses Claude Opus for model-family independence.

### D-014 — Ash uses ChatGPT Plus

Ash consumes the $20 ChatGPT Plus subscription through a validated subscription-backed path and must not silently fall back to metered API billing.

### D-015 — Lambert uses existing Gemini subscription

Lambert's incremental Nostromo budget is treated as zero.

### D-016 — Hard budget boundaries

Provider-side role-specific spend limits are mandatory for metered API agents.

### D-017 — $139 configured envelope

Parker $65 + Ripley $27 + Dallas $27 + Plus $20 = $139.

### D-018 — Buzz identity is durable

Stable Buzz/Nostr identity is independent of Herdr/harness/model.

### D-019 — Buzz collaboration uses allowlists

Nostromo agents are not open to arbitrary relay authors.

### D-020 — GitHub is canonical

Buzz is the collaborative workbench; GitHub is the engineering record.

### D-021 — Separate worktrees

Ripley, Dallas, Parker, and Brett receive independent SquadOps worktrees.

### D-022 — Persona-Pack-shaped source

The Nostromo repo follows Buzz Persona Pack concepts where useful but does not depend on current Persona Pack/Desktop deployment automation.

### D-023 — Explicit launch contract

Nostromo launch configuration, not Herdr itself, defines ACP/harness/model/identity wiring.

### D-024 — Generic launcher

The design should converge on a common `nostromo-agent` launcher rather than seven unrelated startup scripts.

---

# Part XVII — Formal Requirements

## 62. Project Requirements

### NSTR-PROJ-001
A private GitHub repository MUST serve as the source of truth for Nostromo configuration.

### NSTR-PROJ-002
Nostromo MUST remain separable from the SquadOps repository and governance.

### NSTR-PROJ-003
The repository MUST contain a machine-readable team manifest.

### NSTR-PROJ-004
The repository MUST contain version-controlled persona definitions and shared team instructions.

### NSTR-PROJ-005
The repository MUST not contain runtime secrets.

---

## 63. Identity Requirements

### NSTR-ID-001
Each agent MUST have a unique stable Buzz identity.

### NSTR-ID-002
Private Buzz keys MUST remain outside git.

### NSTR-ID-003
Agent identity MUST survive replacement of its model or harness.

### NSTR-ID-004
Agent public identities SHOULD be represented in the team manifest.

### NSTR-ID-005
Agent-to-agent inbound communication MUST be restricted to authorized identities.

---

## 64. Runtime Requirements

### NSTR-RUN-001
Mother, Ripley, Dallas, Parker, and Brett MUST have persistent Spark process affinity.

### NSTR-RUN-002
Herdr MUST provide the persistent terminal/process substrate for those agents.

### NSTR-RUN-003
Herdr MUST NOT be treated as the source of ACP configuration.

### NSTR-RUN-004
Each Spark agent MUST be launchable through a deterministic Nostromo launch definition.

### NSTR-RUN-005
Each Spark agent MUST launch or own a `buzz-acp` process configured with the correct stable Buzz identity.

### NSTR-RUN-006
`buzz-acp` MUST spawn the intended ACP-speaking harness.

### NSTR-RUN-007
Repo-facing agents MUST start in the intended working directory.

### NSTR-RUN-008
Restarting a process MUST NOT create a new logical agent identity.

---

## 65. Buzz Requirements

### NSTR-BUZZ-001
The Jetson Orin Nano Super MUST host the persistent Buzz server infrastructure.

### NSTR-BUZZ-002
Buzz durable data MUST reside on reliable persistent storage.

### NSTR-BUZZ-003
The relay SHOULD operate closed/private in v1.

### NSTR-BUZZ-004
Buzz MUST remain available when the Mac disconnects.

### NSTR-BUZZ-005
Buzz SHOULD remain available when Spark is restarted.

### NSTR-BUZZ-006
Crew members MUST be able to directly @mention authorized peers.

### NSTR-BUZZ-007
A work-item channel strategy SHOULD prevent indefinite accumulation of unrelated ACP context.

---

## 66. Model and Harness Requirements

### NSTR-MOD-001
Mother MUST use OpenCode ACP with local Qwen3.6 35B-A3B in the baseline.

### NSTR-MOD-002
Brett MUST use OpenCode ACP with local Qwen3.6 35B-A3B in the baseline.

### NSTR-MOD-003
Ripley MUST use a Codex ACP path backed by the dedicated OpenAI architecture budget.

### NSTR-MOD-004
Parker MUST use a Codex ACP path backed by the dedicated OpenAI implementation budget.

### NSTR-MOD-005
Dallas MUST use a Claude ACP path backed by a dedicated Anthropic budget.

### NSTR-MOD-006
Ash MUST use a subscription-backed ChatGPT/Codex path without an API fallback.

### NSTR-MOD-007
Lambert MUST use the existing Gemini ecosystem without becoming a critical-path engineering dependency.

---

## 67. Budget Requirements

### NSTR-BUD-001
Incremental intended monthly Nostromo spend MUST remain below $150 absent explicit owner action.

### NSTR-BUD-002
The configured baseline envelope MUST not exceed $139.

### NSTR-BUD-003
Parker's provider boundary MUST cap metered use at $65/month.

### NSTR-BUD-004
Ripley's provider boundary MUST cap metered use at $27/month.

### NSTR-BUD-005
Dallas's provider boundary MUST cap metered use at $27/month.

### NSTR-BUD-006
Provider exhaustion MUST fail closed rather than silently use a different credential.

### NSTR-BUD-007
Mother and Brett MUST default to local inference with no unapproved metered fallback.

---

## 68. Collaboration Requirements

### NSTR-COL-001
Shared team instructions MUST define role and handoff conventions.

### NSTR-COL-002
Each persona MUST define both responsibilities and non-responsibilities.

### NSTR-COL-003
Mother MUST route specialist work rather than absorb it.

### NSTR-COL-004
Dallas MUST remain independent from Ripley for architecture review.

### NSTR-COL-005
Brett MUST remain independent from Parker for acceptance verification.

### NSTR-COL-006
Failed QA MUST return evidence to Parker rather than being silently repaired by Brett.

### NSTR-COL-007
Unresolved material Ripley/Dallas disagreement MUST be escalated.

### NSTR-COL-008
Canonical accepted work MUST be represented in GitHub.

### NSTR-COL-009
Nostromo MUST respect SquadOps SIP/owner governance for product decisions.

---

## 69. Security Requirements

### NSTR-SEC-001
No provider or Buzz private credential may be committed to the Nostromo repository.

### NSTR-SEC-002
Provider keys SHOULD be role-specific.

### NSTR-SEC-003
Agent inbound Buzz policy MUST NOT default to unrestricted `anyone`.

### NSTR-SEC-004
Logs MUST redact secrets.

### NSTR-SEC-005
The Buzz server SHOULD initially be private-network oriented.

### NSTR-SEC-006
Supply-chain dependencies SHOULD be pinned for stable operation.

---

# Part XVIII — Current Platform Constraints to Respect

## 70. Buzz Constraints

The implementation plan must account for the current state of Buzz rather than designing against future promises.

Known design-relevant constraints include:

- Persona Packs are git-friendly and portable but not equivalent to Desktop team snapshots.
- Desktop currently requires separate handling to instantiate personas/teams from hand-authored pack source.
- Persona hooks are not a suitable v1 dependency for critical orchestration.
- Persona/team instructions are currently injected through the Buzz ACP prompt path; identity reinforcement should be explicit.
- Per-persona/pack MCP configuration exists, but secret interpolation behavior must be validated rather than assumed.
- `buzz-acp` provides the real runtime boundary for identity, relay connectivity, respond-to policy, and ACP child launch.
- Allowlist behavior must be explicitly configured.
- The current self-host production path uses the production Compose bundle rather than the root development Compose configuration.

These constraints are not reasons to avoid Buzz. They are reasons to keep Nostromo's source-of-truth configuration explicit and reconstructable.

---

## 71. Herdr Constraints

Herdr is a terminal workspace manager, not an agent orchestrator.

It provides persistent sessions/workspaces/panes and can recognize supported coding-agent processes.

The implementation must not assume that every `buzz-acp`-wrapped process will automatically expose perfect Herdr semantic status.

Process persistence is the hard requirement. Rich status integration is a bonus.

---

# Part XIX — Acceptance Criteria

## 72. Project-Level Acceptance

Nostromo v1 is considered architecturally realized when the following are true.

### AC-01 — Repository

A private Nostromo GitHub repository exists and contains the team specification, personas, shared instructions, machine-readable crew/runtime configuration, and no secrets.

### AC-02 — Buzz server

The Jetson Orin Nano Super runs the selected production Buzz stack with durable storage and survives a Mac disconnect.

### AC-03 — Owner cockpit

The Mac can connect through Buzz Desktop as the owner and can inspect/attach to Spark Herdr environments.

### AC-04 — Stable crew identities

All seven agents have stable Buzz identities. Restarting a process does not create a new agent persona.

### AC-05 — Spark persistence

Mother, Ripley, Dallas, Parker, and Brett run persistently on Spark under Herdr-managed terminal/workspace persistence.

### AC-06 — Correct harness binding

Each of the five Spark agents is demonstrably backed by its intended ACP harness.

### AC-07 — Correct model/provider binding

Each agent's effective model/provider matches the team manifest.

### AC-08 — Local model operation

Mother and Brett successfully use the local Ollama Qwen3.6 35B-A3B path without metered cloud fallback.

### AC-09 — Ash subscription path

Ash can receive/respond in Buzz using subscription-backed authentication with no OpenAI API key fallback.

### AC-10 — Budget isolation

Parker, Ripley, and Dallas use independent provider billing/credential boundaries with the defined hard caps.

### AC-11 — Author isolation

Authorized Nostromo peers can @mention one another. Unauthorized relay users cannot invoke the crew.

### AC-12 — Worktree isolation

Ripley, Dallas, Parker, and Brett operate against separate SquadOps worktrees.

### AC-13 — End-to-end collaboration

A representative low-risk SquadOps work item successfully traverses:

```text
Ash -> Mother -> Ripley -> Dallas -> Ripley/acceptance
-> Parker -> Brett -> Dallas/Mother
```

with evidence of each handoff in Buzz and canonical artifacts in GitHub.

### AC-14 — Process restart

At least one Spark agent can be deliberately restarted and resume under the same identity without corrupting work or minting a replacement identity.

### AC-15 — Host independence

Shutting the Mac does not stop Buzz or Spark agents. Restarting Spark does not destroy Buzz's collaboration state.

### AC-16 — Canonical record

Accepted design, implementation, and verification results are recoverable from GitHub even if transient agent sessions are lost.

---

# Part XX — Risks and Mitigations

## 73. Risk: Buzz team-deployment features evolve

**Risk:** Nostromo overfits current Desktop deployment behavior.

**Mitigation:** Store source as Persona-Pack-shaped configuration but launch explicitly through a Nostromo runtime contract.

---

## 74. Risk: Agent persona drift

**Risk:** Long collaboration context causes agents to absorb another role.

**Mitigation:**

- explicit role/non-role boundaries;
- shared team instructions;
- role-specific tool permissions;
- independent workspaces;
- repeated Buzz persona context;
- and tests that verify expected handoff behavior.

---

## 75. Risk: Hidden API overspend

**Risk:** subscription authentication fails or a role uses a shared API credential.

**Mitigation:**

- no Ash API fallback;
- dedicated provider projects/workspaces;
- provider hard caps;
- rate limits;
- per-role credentials;
- fail-closed launchers.

---

## 76. Risk: Mother becomes a second orchestration framework

**Risk:** Nostromo recreates SquadOps prematurely inside Mother's prompt.

**Mitigation:**

Mother performs intelligent routing and coordination, while durable workflow state and mechanical constraints increasingly move to manifests, GitHub, Buzz workflows, and deterministic policy.

---

## 77. Risk: Herdr session becomes identity

**Risk:** process persistence is confused with durable agent identity.

**Mitigation:** stable Buzz keys and version-controlled logical role definitions live outside Herdr.

---

## 78. Risk: Shared repo state corrupts review independence

**Risk:** reviewer/tester sees or changes Parker's mutable local state.

**Mitigation:** independent git worktrees and least-privilege roles.

---

## 79. Risk: Jetson becomes overloaded with unrelated AI workloads

**Risk:** collaboration infrastructure becomes unstable.

**Mitigation:** v1 Jetson role is Buzz infrastructure only. Additional services require explicit capacity evaluation.

---

## 80. Risk: Local-model contention with SquadOps cycles

**Risk:** Nostromo and SquadOps compete for Spark resources.

**Mitigation:** normal operating model assumes development/collaboration and heavyweight SquadOps cycle execution are largely phase-separated. Ollama remains the common local inference runtime.

---

# Part XXI — Intentional Deferrals to the Execution Plan

## 81. Execution Plan Must Define

The companion plan should later determine:

- exact GitHub repository creation sequence;
- initial directory scaffold;
- dependency/version pins;
- Jetson OS prerequisites;
- NVMe mount/storage paths;
- Docker/Compose installation;
- Buzz Compose configuration;
- Buzz hostname/TLS/private-network strategy;
- Buzz owner creation and membership;
- database/media/git backup procedure;
- Herdr installation;
- Herdr named session/workspace creation;
- SquadOps worktree creation;
- Ollama Qwen3.6 model tag/quantization benchmark;
- OpenCode configuration;
- Codex ACP installation/auth;
- Claude ACP installation/auth;
- Gemini adapter validation;
- Buzz identity/key generation;
- secret-file placement and permissions;
- provider project/workspace setup;
- spend caps and rate limits;
- actual launcher implementation;
- Mac process supervision;
- end-to-end smoke test;
- restart tests;
- budget tests;
- and operational runbooks.

The execution plan SHOULD be phase-oriented and test-driven.

This specification should not be retroactively bloated with those commands unless a requirement changes.

---

# Part XXII — Reference Baseline

## 82. External Design References

This specification was grounded against the current public behavior/documentation of:

### Buzz

- `block/buzz` main README
- Buzz Persona Pack Specification
- `buzz-acp` README/configuration
- Buzz Remote Agents formal specification
- Buzz NIP agent/persona definitions
- Buzz production Compose deployment
- Buzz current self-host configuration examples

Relevant observed concepts:

- stable Nostr agent identities;
- `buzz-acp` as the live agent collaboration harness;
- configurable ACP child commands;
- owner/allowlist author gates;
- persona + team-instruction layering;
- channel-scoped context;
- Persona Pack portable source structure;
- production relay stack with Postgres/Redis/MinIO;
- and explicit separation of secrets from persona content.

### Herdr

- `herdrdev/herdr`
- Herdr agent guide and concepts

Relevant observed concepts:

- persistent background terminal ownership;
- named sessions;
- workspaces/tabs/panes;
- remote reattachment;
- recognized coding-agent state;
- and Herdr's deliberate position as a runtime for existing coding tools rather than a replacement harness.

### Ollama/Qwen

- current Ollama Qwen3.6 35B-A3B listing
- current Ollama Qwen3.8 27B listing

The exact model build used in production should be benchmarked and pinned by the implementation plan.

### Provider/Harness Ecosystem

- Codex ACP authentication/runtime documentation
- OpenCode agent/permission/provider documentation
- Claude ACP adapter documentation
- current OpenAI model/API controls
- current Anthropic workspace/billing controls

Provider and adapter behavior may change; the implementation plan must revalidate exact commands and limits at setup time.

---

# Part XXIII — Final Architecture Statement

Nostromo v1 is a seven-agent development crew built from independent, replaceable layers:

```text
                       JASON
                        │
                 Buzz Desktop / Mac
                        │
                        ▼
              JETSON ORIN NANO SUPER
                   Buzz infrastructure
                        │
            signed collaboration/events
                        │
        ┌───────────────┴────────────────┐
        │                                │
        ▼                                ▼
      MAC                            DGX SPARK
   Ash / Lambert                       Herdr
                                    persistent crew
                                        │
                            ┌───────────┼────────────┐
                            │           │            │
                          Mother      Ripley       Dallas
                            │           │            │
                          Parker      Brett          ...
                            │
                            ▼
                      SquadOps repo
                         GitHub
```

The fundamental contracts are:

> **Buzz owns collaboration and stable social identity.**

> **Herdr owns persistent Spark development processes.**

> **`buzz-acp` owns the bridge from Buzz identity/events to an ACP-speaking agent.**

> **OpenCode, Codex, Claude, and Gemini-compatible tooling own agent execution.**

> **Ollama and cloud providers own inference.**

> **GitHub owns canonical engineering truth.**

> **Mother coordinates work but does not become the architecture, implementation, or verification specialist.**

> **Nostromo builds SquadOps; it does not replace SquadOps.**

This architecture is intentionally simple enough to deploy with existing tools, explicit enough to reconstruct and audit, and sufficiently separated to evolve each runtime component without losing the persistent identity and collaborative structure of the crew.

---

## 83. Next Artifact

The next document should be:

**NOSTROMO-PLAN-0001 — Initial Crew and Infrastructure Bootstrap Plan**

That plan should consume this specification as its requirements baseline and translate it into a sequenced implementation with host-by-host setup, commands, verification probes, rollback points, and completion evidence.

It should not redesign the architecture unless implementation evidence reveals a contradiction in this specification.
