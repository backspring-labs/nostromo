# Source Baseline

Dependency ledger for Nostromo (NOSTROMO-PLAN-0001 §7.9, §18.4). Buzz, Herdr, the ACP adapters, OpenCode, and Ollama are privileged development dependencies and must be reconstructable against a known set.

**Pinned** is what is actually installed and validated on a host. **Observed latest** is what upstream published when this table was last refreshed, recorded so the next work package starts from a known point. A row is pinned only when its work package has verified it in place.

| Component | Pinned | Observed latest (2026-09-07) | Source | Validated |
|---|---|---|---|---|
| Buzz relay image | TBD (WP-2) | tag `v0.5.2`; `main` at `3c7f288c60d67df78577b237e27c3dfc8831aaa1` | https://github.com/block/buzz | — |
| Buzz Desktop | TBD (WP-3) | `desktop-v0.5.23` (2026-09-05) | https://github.com/block/buzz/releases | — |
| Buzz Compose bundle | TBD (WP-2) | `deploy/compose/` at the pinned relay commit | https://github.com/block/buzz/tree/main/deploy/compose | — |
| buzz-acp | TBD (WP-6) | ships with the Buzz relay commit | https://github.com/block/buzz/tree/main/crates/buzz-acp | — |
| Buzz Persona Pack spec | TBD | `crates/buzz-persona/PERSONA_PACK_SPEC.md` at `3c7f288` | https://github.com/block/buzz/blob/main/crates/buzz-persona/PERSONA_PACK_SPEC.md | — |
| Herdr | TBD (WP-4) | `v0.8.2` (2026-08-19) | https://github.com/herdrdev/herdr | — |
| OpenCode (`opencode-ai`) | TBD (WP-4) | `1.18.29` | https://opencode.ai/docs/acp/ | — |
| `@agentclientprotocol/codex-acp` | TBD (WP-7) | `1.10.0` | https://github.com/agentclientprotocol/codex-acp | — |
| `@agentclientprotocol/claude-agent-acp` | TBD (WP-7) | `0.75.1` | https://www.npmjs.com/package/@agentclientprotocol/claude-agent-acp | — |
| Gemini CLI (`@google/gemini-cli`) | TBD (WP-8) | `0.58.0` | https://github.com/google-gemini/gemini-cli | — |
| Ollama on Spark | TBD (WP-4) | unknown until Spark preflight | https://ollama.com | — |
| Qwen3.6 35B-A3B Ollama tag and quantization | TBD (WP-4) | benchmark before pinning | https://ollama.com/library | — |
| Node runtime on Spark | TBD (WP-4) | — | — | — |
| Docker / Compose on Jetson | TBD (WP-2) | — | — | — |

## Refresh procedure

1. Record the observed-latest column before starting a work package that installs the component.
2. Install and validate on the target host.
3. Move the exact version, tag, or commit into the Pinned column and date the Validated column.
4. Do not track `main` after commissioning (NOSTROMO-0001 §60).
