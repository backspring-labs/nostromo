# Source Baseline

Dependency ledger for Nostromo (NOSTROMO-PLAN-0001 §7.9, §18.4). Buzz, Herdr, the ACP adapters, OpenCode, and Ollama are privileged development dependencies and must be reconstructable against a known set.

**Pinned** is what is actually installed and validated on a host. **Observed latest** is what upstream published when this table was last refreshed, recorded so the next work package starts from a known point. A row is pinned only when its work package has verified it in place.

| Component | Pinned | Observed latest | Source | Validated |
|---|---|---|---|---|
| Buzz relay image | `ghcr.io/block/buzz@sha256:496c38cc235db7cbbbe9706e67e5dfe9b14ba987d9fd309a8fe6b81d967151ce` (multi-arch index; arm64 child `sha256:b47bf3ec968a2c68031b69dc7cbcf4499b3811c87969650a7fecae1689cce1b2`), built from commit `c045321a7fb3ca8939f28519ce7a555a6f597728` (2026-09-08); relay reports `0.2.1` in NIP-11 | 2026-09-08: `main` at `c045321a`; newest source tag `v0.5.2`; ghcr publishes only `main`, `latest`, and digest tags | https://github.com/block/buzz | 2026-09-08 on nano (`infrastructure/jetson/evidence/`) |
| Buzz Desktop | TBD (WP-3) | `desktop-v0.5.23` (2026-09-05) | https://github.com/block/buzz/releases | — |
| Buzz Compose bundle | `deploy/compose/compose.yml` at `c045321a`, sha256 `01ea2d7754a9ea7bf4eac42006af32c85a465fc53e41ef1a8ef371e01a0a0489` (`infrastructure/jetson/buzz/upstream.lock`); `run.sh` not used, see DEV-003 | same commit | https://github.com/block/buzz/tree/main/deploy/compose | 2026-09-08 on nano |
| Postgres (Buzz dependency) | `postgres:17-alpine@sha256:18cfe3ef5e6815560c98237d6216d1e5119702fb0f3894c8785dd58b8bbe5d73` | upstream Compose floats `17-alpine` | https://hub.docker.com/_/postgres | 2026-09-08 on nano |
| Redis (Buzz dependency) | `redis:7-alpine@sha256:ff02b58f971e7d7d156a1267e283fcbbeee91773b6aa36c49dac28ecfe28eadf` | upstream Compose floats `7-alpine` | https://hub.docker.com/_/redis | 2026-09-08 on nano |
| MinIO server (Buzz dependency) | `minio/minio:RELEASE.2025-09-07T16-13-09Z@sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e` | upstream pins the same release tag | https://hub.docker.com/r/minio/minio | 2026-09-08 on nano |
| MinIO client (bucket init) | `minio/mc:RELEASE.2025-08-13T08-35-41Z@sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727` | upstream pins the same release tag | https://hub.docker.com/r/minio/mc | 2026-09-08 on nano |
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
| OpenAI model, Ripley and Parker | `gpt-5.6-sol` — exact API identifier confirmed in the project model list 2026-09-13 | 2026-09-13, same list: `gpt-6-astra`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5-pro`, `gpt-5.5`, `gpt-5.4-pro`, `gpt-5.3-codex` | https://platform.openai.com | project model list restricted to this id alone (WP-1 §1.2) |
| Anthropic model, Dallas | TBD (WP-1) — `crew/manifest.yaml` carries only `model_family: opus` | — | https://platform.claude.com | — |
| Docker / Compose on Jetson | Docker `29.8.0` (build `88096ef`), Compose `v5.5.1`, data root `/mnt/ssd/docker` | preinstalled on the Jetson | https://docs.docker.com/engine/ | 2026-09-08 on nano |
| Jetson OS | Ubuntu `22.04.5 LTS` (JetPack), aarch64, root on microSD, NVMe at `/mnt/ssd` | — | — | 2026-09-08 |
| Tailscale on Jetson | `1.102.3`, MagicDNS `nano.tailc69e7d.ts.net`, HTTPS certificates enabled, Serve `https://nano.tailc69e7d.ts.net` (tailnet only) proxying to `127.0.0.1:3000`, Funnel off | — | https://tailscale.com | 2026-09-08 |

## Refresh procedure

1. Record the observed-latest column before starting a work package that installs the component.
2. Install and validate on the target host.
3. Move the exact version, tag, or commit into the Pinned column and date the Validated column.
4. Do not track `main` after commissioning (NOSTROMO-0001 §60).
