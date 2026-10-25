# Nostromo

Nostromo is a persistent, multi-agent software development crew whose first mission is to design, build, review, test, and evolve [SquadOps](https://github.com/backspring-labs/squad-ops).

It is deliberately external to SquadOps. It composes existing tools into a role-bounded crew rather than building a new agent framework:

| Concern | Owned by |
|---|---|
| Identity and collaboration | Buzz, hosted on the Jetson Orin Nano Super |
| Process supervision and observation | systemd supervises each role on the DGX Spark; Herdr observes |
| Agent harnesses | buzz-agent, Codex ACP, Claude ACP; Gemini ACP retained for deferred Lambert |
| Inference | Local TensorFold (Ollama rollback), or bounded provider APIs and subscriptions |
| Engineering truth | GitHub |

## Governing documents

- [Platform Spec — Development Crew Platform Specification](docs/specs/platform-spec.md): what Nostromo is and what it must guarantee.
- [Bootstrap Plan — Initial Crew and Infrastructure Bootstrap Plan](docs/specs/bootstrap-plan.md): how to bootstrap it, as probe-gated work packages.

- [Operating Model — Crew Operating Model and SquadOps 1.8 Commissioning Plan](docs/specs/crew-operating-model.md): how the crew works once it is live, and what must be true before it touches SquadOps 1.8 code. **Proposed, and partly in effect** — its §45 opens with which of its changes are running, as of 2026-09-23. The Platform Spec amendments it proposes have not been applied.

The plan governs execution. The specification governs architecture. Contradictions are logged in [docs/deviations.md](docs/deviations.md) rather than resolved silently.

## Crew

| Agent | Role | Host | Harness | Backing | Monthly cap |
|---|---|---|---|---|---:|
| Mother | Orchestrator | Spark | buzz-agent | Qwen3.8 27B via TensorFold | local |
| Ash | Read-only research and ideation | Spark | Codex ACP | GPT-6 Astra, ChatGPT Plus subscription | $20 fixed |
| Ripley | Warrant Officer | Spark | Codex ACP | GPT-5.6 Sol, OpenAI project `nostromo-ripley` | $25 hard |
| Dallas | Adversarial reviewer | Spark | Claude ACP | Claude Opus 5.5, Anthropic workspace `nostromo-dallas` | $25 hard |
| Parker | Implementation engineer | Spark | Codex ACP | GPT-5.6 Sol, OpenAI project `nostromo-parker` | $70 hard |
| Brett | Supporting engineer: bounded implementation, never concludes | Spark | buzz-agent | Qwen3.8 27B via TensorFold | local |
| Lambert | Navigator: release and learning drafts over closed work — **deferred** | Spark | Gemini ACP | Existing Gemini subscription | $0 incremental |

Configured envelope $140 against a $150 ceiling. Caps are enforced provider-side, never by prompt alone. Every role is hosted on the Spark as `nostromo@<role>`, in its own Unix account; the Mac runs no agents.

These are repository assignments, not a live health report. `crew/manifest.yaml` is authoritative for
runtime bindings; `crewctl status` on the Spark reports which roles are actually running. Lambert's
unit remains disabled pending a usable ACP harness (manifest note, 2026-10-03).

Each crew member carries a NIP-05 handle, `<name>@nostromo.backspring.xyz`, served and verified by the relay. Handles are for display and verification; public keys remain authoritative for routing and security.

## Layout

```text
.plugin/plugin.json     Buzz Persona Pack metadata (runtime roster is crew/manifest.yaml)
instructions.md         Crew constitution, appended to every persona prompt
crew/manifest.yaml      Canonical machine-readable crew registry (non-secret)
crew/budgets.yaml       Budget profiles and the monthly envelope
crew/capabilities.yaml  Capability-to-agent routing table Mother consumes
crew/lifecycle.yaml     Work-item lifecycle states
runtime/env/*.example   Shape of each agent's host-local secret file; placeholders only
docs/source-baseline.md Dependency ledger: pinned versions and provenance
docs/deviations.md      Implementation deviation log
infrastructure/jetson/  Buzz relay appliance: pinned overlay, install, upgrade and rehearsal, backup, probes, evidence
infrastructure/spark/   Crew host: launcher, systemd unit, crewctl, pinned runtime, evidence
infrastructure/buzz/    Identities and Buzz Desktop on the Mac: keys, profiles, desktop-upgrade.sh
infrastructure/github/  Rulesets and the squad-ops crew check
crew/personas/, crew/prompts/  Per-role persona and base prompt
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

The suite validates the manifests parse, the roster is exactly the seven canonical agents, capability routing resolves, budget profiles sum inside the envelope, host and supervisor assignments match the specification, no agent accepts messages from `anyone`, and no tracked file contains a secret-shaped value. Operator tests exercise `crewctl`'s actual manifest reader, JSON identity output, preflight identity checks, and local-role mode controls without contacting the Spark.

## Status recorded in the repository

As of 2026-10-24, the repository contains the seven role definitions, per-role systemd launcher,
GitHub App identities for Ripley, Parker, Dallas and Brett, budget-watch, and a private Jetson relay
at `wss://nostromo.backspring.xyz`. The Mac is the cockpit. The role workspaces are separate clones,
not shared git worktrees. Mother and Brett moved to TensorFold on 2026-10-13.

This is still a partly commissioned crew. The Operating Model's §45 records its staged adoption;
its broader role and lifecycle changes are not all applied. Consult the Bootstrap Plan's dated
status and the host evidence directories for work-package evidence rather than inferring readiness
from the existence of a launcher or a persona.

The Spark's `crewctl mode counted` stops local roles and keeps them down through reboot;
`crewctl mode development` resumes enabled local roles. This is a local-role guard, not a complete
lease or measurement-isolation guarantee. Checks for mutating crew work, in-flight SquadOps work,
and recorded memory conditions still need integration. See Operating Model §36.3.

## Open decisions

Recorded here until resolved; each will move into the specification, the plan, or `docs/deviations.md`.

Per-agent GitHub identities use organization-owned GitHub Apps. Branch rulesets constrain who can
push to crew namespaces; the required `nostromo crew checks` status check enforces path and commit
attribution boundaries before merge. GitHub refused path-restricting push rules on the public
repository, so path limits are not push-time restrictions (DEV-006). See
`infrastructure/github/squad-ops-check/README.md` and the plan, WP-1 §§8.7–8.9.

- **Lifecycle state store.** The specification defers where durable work-item state lives. Candidate: GitHub Issues on squad-ops with lifecycle labels.
- **Spark coordination.** The full transition checks and SquadOps lease integration remain to be
  commissioned; the mode file alone does not establish that a counted window is isolated.

## License

MIT — see [LICENSE](LICENSE). Secrets never live in this repository: provider keys and Nostr keys stay in each role's own home on the Spark, relay secrets in `secrets.env` on the Jetson. `.gitleaks.toml` allowlists the two public-by-design values that look like secrets (NIP-OA owner attestations, the RFC 6455 sample nonce); `gitleaks git --log-opts="--all" .` and `gitleaks dir .` should both report nothing.
