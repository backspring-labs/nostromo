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

- [Platform Spec — Development Crew Platform Specification](docs/specs/platform-spec.md): what Nostromo is and what it must guarantee.
- [Bootstrap Plan — Initial Crew and Infrastructure Bootstrap Plan](docs/specs/bootstrap-plan.md): how to bootstrap it, as probe-gated work packages.

- [Operating Model — Crew Operating Model and SquadOps 1.8 Commissioning Plan](docs/specs/crew-operating-model.md): how the crew works once it is live, and what must be true before it touches SquadOps 1.8 code. **Proposed, and partly in effect** — its §45 opens with which of its changes are running, as of 2026-09-23. The Platform Spec amendments it proposes have not been applied.

The plan governs execution. The specification governs architecture. Contradictions are logged in [docs/deviations.md](docs/deviations.md) rather than resolved silently.

## Crew

| Agent | Role | Host | Harness | Backing | Monthly cap |
|---|---|---|---|---|---:|
| Mother | Orchestrator | Spark | buzz-agent | Qwen3.6 35B-A3B via Ollama | local |
| Ash | Research and ideation — **not yet running** | Spark | Codex ACP | ChatGPT Plus subscription | $20 fixed |
| Ripley | Warrant Officer | Spark | Codex ACP | GPT-5.6 Sol, OpenAI project `nostromo-ripley` | $25 hard |
| Dallas | Adversarial reviewer | Spark | Claude ACP | Claude Opus 5.5, Anthropic workspace `nostromo-dallas` | $25 hard |
| Parker | Implementation engineer | Spark | Codex ACP | GPT-5.6 Sol, OpenAI project `nostromo-parker` | $70 hard |
| Brett | Supporting engineer: bounded implementation, never concludes | Spark | buzz-agent | Qwen3.8 27B via Ollama | local |
| Lambert | Navigator: the release cut and knowledge projection — **not yet running** | Spark | Gemini ACP | Existing Gemini subscription | $0 incremental |

Configured envelope $140 against a $150 ceiling. Caps are enforced provider-side, never by prompt alone. Every role is hosted on the Spark as `nostromo@<role>`, in its own Unix account; the Mac runs no agents.

Each crew member carries a NIP-05 handle, `<name>@nostromo.backspring.xyz`, served and verified by the relay. Handles are for display and verification; public keys remain authoritative for routing and security.

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

The suite validates the manifests parse, the roster is exactly the seven canonical agents, capability routing resolves, budget profiles sum inside the envelope, host and supervisor assignments match the specification, no agent accepts messages from `anyone`, and no tracked file contains a secret-shaped value.

## Status

| Work package | State |
|---|---|
| WP-0 Repository scaffold | Done |
| WP-1 Provider boundaries | Next |
| WP-2 Jetson Buzz server | Done 2026-09-08. Relay at `wss://nano.tailc69e7d.ts.net` (Tailscale Serve TLS, tailnet only), closed, pinned by digest, reboot-proven. Carried to WP-3: real owner pubkey replaces the placeholder. Runbook: `infrastructure/jetson/README.md` |
| WP-4 Spark base: Herdr, worktrees, Ollama/Qwen | Next, parallel with WP-1 |
| WP-3, WP-5 onward | Gated on the above |

## Open decisions

Recorded here until resolved; each will move into the specification, the plan, or `docs/deviations.md`.

Resolved 2026-09-07: per-agent GitHub identities and path-scoped write boundaries. Ripley and Parker are organization-owned GitHub Apps, and `squad-ops` rulesets enforce branch namespaces and path limits server-side. See the plan, WP-1 sections 8.7 to 8.9, and NSTR-ID-006.

- **Lifecycle state store.** The specification defers where durable work-item state lives. Candidate: GitHub Issues on squad-ops with lifecycle labels.
- **Reviewer checkout convention.** Git allows a branch in one worktree at a time. Dallas and Brett will review at a detached commit.

## License

MIT — see [LICENSE](LICENSE). Secrets never live in this repository: provider keys and Nostr keys stay in each role's own home on the Spark, relay secrets in `secrets.env` on the Jetson. `.gitleaks.toml` allowlists the two public-by-design values that look like secrets (NIP-OA owner attestations, the RFC 6455 sample nonce); `gitleaks git --log-opts="--all" .` and `gitleaks dir .` should both report nothing.
