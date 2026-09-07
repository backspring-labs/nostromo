# Nostromo

Nostromo is a persistent, multi-agent software development crew whose first mission is to design, build, review, test, and evolve [SquadOps](https://github.com/backspring-labs/squad-ops).

It is deliberately external to SquadOps. It composes existing tools into a role-bounded crew rather than building a new agent framework:

| Concern | Owned by |
|---|---|
| Identity and collaboration | Buzz, hosted on the Jetson Orin Nano Super |
| Persistent development execution | Herdr, on the DGX Spark |
| Agent harnesses | OpenCode ACP, Codex ACP, Claude ACP, Gemini-compatible tooling |
| Inference | Local Ollama, or bounded provider APIs and subscriptions |
| Engineering truth | GitHub |

## Governing documents

- [NOSTROMO-0001 — Development Crew Platform Specification](docs/specs/NOSTROMO-0001-Development-Crew-Platform-Spec.md): what Nostromo is and what it must guarantee.
- [NOSTROMO-PLAN-0001 — Initial Crew and Infrastructure Bootstrap Plan](docs/specs/NOSTROMO-PLAN-0001-Initial-Crew-Infrastructure-Bootstrap.md): how to bootstrap it, as probe-gated work packages.

The plan governs execution. The specification governs architecture. Contradictions are logged in [docs/deviations.md](docs/deviations.md) rather than resolved silently.

## Crew

| Agent | Role | Host | Harness | Backing | Monthly cap |
|---|---|---|---|---|---:|
| Mother | Orchestrator | Spark | OpenCode ACP | Qwen3.6 35B-A3B via Ollama | local |
| Ash | Research and ideation | Mac | Codex ACP | ChatGPT Plus subscription | $20 fixed |
| Ripley | Architect | Spark | Codex ACP | GPT-5.6 Sol, OpenAI project `nostromo-ripley` | $27 hard |
| Dallas | Adversarial reviewer | Spark | Claude ACP | Claude Opus, Anthropic workspace `nostromo-dallas` | $27 hard |
| Parker | Implementation engineer | Spark | Codex ACP | GPT-5.6 Sol, OpenAI project `nostromo-parker` | $65 hard |
| Brett | QA and verification | Spark | OpenCode ACP | Qwen3.6 35B-A3B via Ollama | local |
| Lambert | Knowledge and Google specialist | Mac | Gemini ACP | Existing Gemini subscription | $0 incremental |

Configured envelope $139 against a $150 ceiling. Caps are enforced provider-side, never by prompt alone.

## Layout

```text
.plugin/plugin.json     Buzz Persona Pack manifest (roster is authoritative; personas land in WP-9)
instructions.md         Crew constitution, appended to every persona prompt
crew/manifest.yaml      Canonical machine-readable crew registry (non-secret)
crew/budgets.yaml       Budget profiles and the monthly envelope
crew/capabilities.yaml  Capability-to-agent routing table Mother consumes
crew/lifecycle.yaml     Work-item lifecycle states
runtime/env/*.example   Shape of each agent's host-local secret file; placeholders only
docs/source-baseline.md Dependency ledger: pinned versions and provenance
docs/deviations.md      Implementation deviation log
tests/                  Configuration and policy validation
```

Vocabulary: three words, three systems, kept deliberately separate.

- **Crew** is Nostromo's roster, the crew of the Nostromo. It is the only word used for the seven agents.
- **Squad** is a SquadOps concept: the agents SquadOps itself orchestrates inside a cycle. The crew builds SquadOps and is never a squad.
- **Team** is Buzz's word for its own deployment grouping, and the heading Buzz stamps on the injected instructions block. It appears in the specs only where they describe Buzz.

Secrets never live in this repository. Each host keeps its own agent secrets under `~/.config/nostromo/secrets/` with owner-only permissions.

## Checks

```bash
uv run pytest
```

The suite validates the manifests parse, the roster is exactly the seven canonical agents, capability routing resolves, budget profiles sum inside the envelope, host and supervisor assignments match the specification, no agent accepts messages from `anyone`, and no tracked file contains a secret-shaped value.

## Status

| Work package | State |
|---|---|
| WP-0 Repository scaffold | Done |
| WP-1 Provider boundaries | Next |
| WP-2 Jetson Buzz server | Next, parallel with WP-1 |
| WP-4 Spark base: Herdr, worktrees, Ollama/Qwen | Next, parallel with WP-1 |
| WP-3, WP-5 onward | Gated on the above |

## Open decisions

Recorded here until resolved; each will move into the specification, the plan, or `docs/deviations.md`.

- **Lifecycle state store.** The specification defers where durable work-item state lives. Candidate: GitHub Issues on squad-ops with lifecycle labels.
- **Per-agent GitHub identities.** Ripley and Parker push branches and open pull requests. The plan does not yet provision GitHub credentials per role.
- **Path-scoped write boundaries.** Codex sandboxing is directory-scoped. Enforcing "Ripley writes SIPs, not source" needs a GitHub-side check.
- **Reviewer checkout convention.** Git allows a branch in one worktree at a time. Dallas and Brett will review at a detached commit.
