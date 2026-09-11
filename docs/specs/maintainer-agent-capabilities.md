# Capabilities of a SquadOps maintainer agent — rev 2

**What this is.** Every ability an agent needs to develop, operate and maintain *this*
repository and *this* box, named concretely: the commands, services, ports, paths and traps
that the work actually consists of. Derived from work done under the owner's direction.

**The one exclusion.** SquadOps' own collaboration model — how its agent roster divides work,
how its cycles and gates sequence that work — must not bleed into how a maintainer team
divides *its* labour. Those are two unrelated designs that happen to share a repository. The
SquadOps runtime, its CLI, its database and its infrastructure ARE in scope here, as the
machinery being operated.

**MECE claim.** Each capability appears once. Domains are cut by the kind of judgement
required, because that determines delegability. §11 (disciplines) qualifies how every other
domain is exercised and is not a domain of tasks.

**Tier.** `L` = a local model can own it end to end. `L+` = local execution after frontier
framing. `F` = frontier judgement required, because being wrong is expensive, silent, or hard
to detect. **Tiering is cost of being wrong, not difficulty.**

---

## 0. The surface — what exists

An agent cannot be tiered against work it cannot see. This is the operable inventory.

**Services** (`docker compose`, 19 defined): `postgres` :5432 · `redis` :6379 · `rabbitmq`
:5672/:15672 · `runtime-api` :8001 · `prefect-server` :4200 · `squadops-keycloak` :8180 ·
`langfuse` :3001 · `grafana` :3000 · `prometheus` :9090 · `otel-collector` :4317/:4318 ·
`caddy` :4040 · `squadops-console` · `sandbox-service` :8002 (127.0.0.1 only) · agent
containers `max` `neo` `nat` `eve` `data` `bob` `joi`.

**Off-compose, on the host:** Ollama :11434 with models under `/usr/share/ollama`; `earlyoom`;
systemd timers `squadops-backup.timer`, `squadops-docker-prune.timer`.

**CLI** (`.venv/bin/squadops`): `status` `login` `logout` `doctor` `bootstrap` `projects`
`cycles` `runs` `squad-profiles` `request-profiles` `artifacts` `baseline` `auth` `models`
`agent` `assignment`.

**Config inventories:** `config/projects.yaml` (the canonical project registry — the Postgres
`projects` table can hold retired rows the API ignores) · `config/squad-profiles.yaml`
(`smoke`, `lite`, `full`, `full-38`, `full-38-atlas`) · `src/squadops/contracts/cycle_request_profiles/profiles/*.yaml`
· `config/profiles/bootstrap/*.yaml`.

**Evidence stores:** `data/artifacts/<project>/<cycle>/<run>/art_*/` · `var/verification_sets/<set>/`
· Postgres tables `cycle_runs`, `cycle_registry`, `cycle_gate_decisions`,
`run_verification_summaries`, `run_checkpoints`, `focus_leases`, `agent_runtime_state`,
`artifact` · container logs · LangFuse.

**Infra assets:** `infra/migrations/` (applied at runtime-api startup, baked into its image) ·
`infra/00-create-databases.sh` (mounted by compose) · `infra/auth/squadops-realm-*.json` ·
`infra/systemd/*.service|.timer` (templates with `__USER__`/`__REPO_ROOT__`).

---

## 1. Comprehension and retrieval

| # | Capability | Tier |
|---|---|---|
| 1.1 | Locate the owner of a concern across `src/squadops/`, `adapters/`, `scripts/`, `infra/` | L |
| 1.2 | Trace a value across module boundaries to every consumer (e.g. row → normalizer → record → signature) | F |
| 1.3 | Enumerate every construction/call site by AST or grep, broader than the change being made | F |
| 1.4 | Read rationale out of comments, commit messages, SIPs under `sips/`, and plans under `docs/plans/` | L+ |
| 1.5 | Diff two commits scoped to paths that matter (`git diff --stat A B -- src/ adapters/`) | L |
| 1.6 | Distinguish a registry/catalogue entry from an active requirement (e.g. a model in `model_registry.py` vs one a bootstrap profile requires) | F |
| 1.7 | Reconstruct a prior decision and its reason before contradicting it | F |

## 2. Change authoring

| # | Capability | Tier |
|---|---|---|
| 2.1 | Write a fix at the layer that owns the defect, having established which layer that is | F |
| 2.2 | Single-source duplicated logic (e.g. one row-builder for two call sites; one timer installer for N units) | F |
| 2.3 | Extract a function/module with an explicit contract, behaviour preserved | F |
| 2.4 | Apply a fully specified mechanical edit across known sites | L |
| 2.5 | Match surrounding idiom, naming, comment density | L+ |
| 2.6 | Put content behind the seam that owns it — prompts via `PromptService`/`prompts/fragments/`, never inline literals; config in `config/`, not code constants | F |
| 2.7 | Respect repository rules: no edits to `dist/`, generated manifests, `docker-compose.yml` service names; version bumps only via `scripts/maintainer/version_cli.py` | L+ |
| 2.8 | Conform to the API route lanes (`docs/architecture/api-route-lanes.md`) before adding any route | F |
| 2.9 | Keep task-type identifiers correct: strings at the boundary, `TaskType` members at the core, properties over identity, tables over if/elif | F |

## 3. Test and guard authoring

| # | Capability | Tier |
|---|---|---|
| 3.1 | Name the bug a test catches before writing it; decline otherwise | F |
| 3.2 | Write the **wiring** test that enters where the cycle enters, not only the seam test | F |
| 3.3 | Pair every positive assertion with a control that must not fire | F |
| 3.4 | Prove a new test fails against pre-fix code by reverting and re-running | F |
| 3.5 | Parametrize a guard over a live registry, not a hand-listed set | F |
| 3.6 | Bound stored evidence (chars, list items) on anything persisted per round | L+ |
| 3.7 | Scan executable lines only when guarding source text, so a guard cannot fail on its own docs | F |
| 3.8 | Satisfy `scripts/dev/lint_test_quality.py`; register any new `@pytest.mark.X` in `pyproject.toml` | L+ |
| 3.9 | Table every seam that evaluates a criterion before binding a typed check onto artifacts | F |

## 4. Static quality enforcement

| # | Capability | Tier |
|---|---|---|
| 4.1 | Run `ruff check .` and `ruff format .` **separately** — chaining hides the format step when check exits non-zero | L |
| 4.2 | Fix a lint cause rather than suppress the rule; name a constant rather than silence the enum-shadow guard | F |
| 4.3 | Keep architecture guards green: `tests/unit/architecture/` (forbidden imports, task-type literals, docs version sync, route lanes, host timers) | L+ |

## 5. Local execution and regression

| # | Capability | Tier |
|---|---|---|
| 5.1 | Run `./scripts/dev/run_regression_tests.sh` (the full gate) and `run_affected_tests.sh [--branch]` | L |
| 5.2 | Run targeted `pytest` by file, class, or domain marker | L |
| 5.3 | Extract the real assertion from a failure summary, not a substring match in a test name | L+ |
| 5.4 | Re-run the *same* invocation that surfaced a failure when judging whether it pre-existed | F |
| 5.5 | Distinguish a failure caused by the change from one merely revealed by it | F |

## 6. Integration: version control and CI

| # | Capability | Tier |
|---|---|---|
| 6.1 | Branch before any change; never commit to `main` | L |
| 6.2 | Compose commit messages via `git commit -F <file>` — backticks in `-m` shell-expand and silently delete text | L+ |
| 6.3 | Write a commit/PR body that explains why, with evidence and rejected alternatives | F |
| 6.4 | Satisfy the closure check: `Closes #N` to an **open issue**, or `Refs #N — remaining:`, or `No issue:`; verify with `scripts/dev/check_pr_closure.sh` | L+ |
| 6.5 | Create/update PRs with `gh pr create --body-file`; `gh pr edit` fails here (projectCards GraphQL) — PATCH via `gh api` instead | L+ |
| 6.6 | Read CI state with `gh pr checks N` tab output (`$2` = pass/fail/pending); **not** `--json .conclusion`, which is `""` when pending | L+ |
| 6.7 | Wait on CI without blocking the session; verify the exact predicate in the foreground first; treat blank as pending, never as done | F |
| 6.8 | Read **every** job including non-required (`fresh-venv install`, `release packages captured`, `dependency audit`, `integration`) and treat a new red as a regression | F |
| 6.9 | Diagnose a CI failure from `gh run view --log-failed`, separating the assertion from matched noise | F |
| 6.10 | Merge (`--squash --delete-branch`), pull, and confirm resulting state independently | L |
| 6.11 | Manage worktrees: add detached, symlink `.venv`/`data`, add both to `info/exclude`, keep the tree clean | L+ |

## 7. Deployment and container operations

| # | Capability | Tier |
|---|---|---|
| 7.1 | `./scripts/dev/ops/rebuild_and_deploy.sh [all\|agents\|runtime-api\|console]`; read `rebuild_deploy.log`, not stdout; `--wait` is not a flag | L+ |
| 7.2 | Build agent packages (`scripts/dev/build_agent.py <role>`) before a Docker build | L+ |
| 7.3 | Build the sandbox image (`scripts/dev/build_sandbox_env_image.sh`) and keep its tag in step with `sandbox/environment.py` | F |
| 7.4 | **Verify loaded, not built** — `docker exec squadops-<svc> python -c` making a live call with its paired control; a symbol import proves nothing | F |
| 7.5 | Inspect service health and image ids (`docker compose ps`, `docker inspect`) | L |
| 7.6 | Read container logs over an explicit UTC window (`docker logs --since`) | L+ |
| 7.7 | Know which services carry which surface: runtime-api seeds skeletons and ships `examples/`; agent images do not | F |
| 7.8 | Manage image/cache lifecycle: `docker system df`, `image prune`, `builder prune --max-used-space`; know that dangling images pin build-cache bytes so ordering decides what is actually freed | F |
| 7.9 | Never `docker system prune -a` or `volume prune` on a deploy box — the volumes hold Postgres data | F |

## 8. Runtime, data and identity operations

| # | Capability | Tier |
|---|---|---|
| 8.1 | Authenticate: `squadops login -u squadops-admin -p admin123` (seeded dev credential in `infra/auth/squadops-realm-local.json`) — never an owner escalation | L |
| 8.2 | Recover from a 401 in order: silent refresh → POST the token endpoint to see why → re-login | L+ |
| 8.3 | Manage the Keycloak realm: `scripts/dev/ops/keycloak_realm_sync.py`, `scripts/dev/lint_realm_exports.py`; admin console :8180 | F |
| 8.4 | Query Postgres read-only via `docker compose exec -T postgres psql`, discovering schema (`information_schema.columns`) rather than assuming column names | L+ |
| 8.5 | Understand database isolation: `squadops` (deployment) vs `squadops_test`; the test role must not reach the deployment DB | F |
| 8.6 | Inspect and drain RabbitMQ (`rabbitmqctl list_queues`, `delete_queue`); recognise retired naming schemes and orphaned queues | L+ |
| 8.7 | Read Prefect flow/task state at :4200 and via `prefect_flow_state` translation; know it is the per-task lane, not the cycle lane | L+ |
| 8.8 | Read LangFuse generations at :3001 / public API for prompt and reasoning evidence; know it is the LLM-generation lane | L+ |
| 8.9 | Apply and verify migrations — `infra/migrations/` runs at runtime-api startup, baked into the image | F |
| 8.10 | Operate backups: `scripts/dev/ops/backup_db.sh [--verify]`, `install_timer.sh squadops-backup`; a dump nobody restored is a hypothesis | F |
| 8.11 | Manage host memory containment (`earlyoom` thresholds, `vm.swappiness`) and read them from the **running process**, not the declared unit | F |
| 8.12 | Manage Ollama: `ollama list/rm/pull`, `/api/tags`, `/api/generate`; know the bandwidth ceiling bounds decode and that models live in `/usr/share/ollama` | F |
| 8.13 | Run `squadops doctor <profile> [--check X] [--json]` and act on each category | L+ |
| 8.14 | Run `squadops bootstrap <profile>` and report setup defects at source rather than silently patching | L+ |

## 9. Cycle execution and measurement

| # | Capability | Tier |
|---|---|---|
| 9.1 | Create a cycle: `squadops cycles create <project> --squad-profile <p> --request-profile <r> --set k=v --notes …`; resolve the project from `config/projects.yaml`, never the DB table | L+ |
| 9.2 | Inspect: `cycles show/list`, `runs list/show/checkpoints`, `artifacts list` (positional order is always project → cycle → run) | L |
| 9.3 | Record a gate decision (`runs gate … --approve`) — gates never self-approve | F |
| 9.4 | Cancel a run through the CLI, not the DB; killing a driver leaves `cycle_runs.status='running'` and every later preflight refuses | F |
| 9.5 | Author a verification-set config: project, profiles, overrides, roll count, gate/launch/shakeout notes, probes | F |
| 9.6 | Design a `loaded_checks` probe per service, each a live call with a paired control | F |
| 9.7 | Demonstrate a probe fails on a deploy lacking its target before trusting it to pass | F |
| 9.8 | Run `verification_set_driver.py preflight` and interpret every refusal (dirty tree, runs in flight, unreleased focus leases, unrun probes, image drift) | L+ |
| 9.9 | Launch detached (`setsid nohup … & disown`) so the driver survives the supervising session; re-attach a dead driver's cycle | F |
| 9.10 | Read a record: separate verdict, boot audit, texture, and unanswerable fields | F |
| 9.11 | Distinguish `observed(value)` / `asked_none` / `unaskable(reason)` and never fold one into a count | F |
| 9.12 | Decide by a pre-stated rule whether a finding supersedes the deploy it ran on | F |
| 9.13 | Protect perishable evidence — a record's texture derives from container logs, so a rebuild destroys it permanently | F |
| 9.14 | Keep the driver's checkout on the same tree the images were built from, or its probes ask the wrong questions | F |
| 9.15 | Regenerate a pinned fixture only as a deliberate, classified, owner-cleared act | F |

## 10. Governance, release and records

| # | Capability | Tier |
|---|---|---|
| 10.1 | File an issue stating defect, mechanism, evidence, scope, and what is deliberately excluded | F |
| 10.2 | Keep plan tables accurate when work lands the plan does not name | F |
| 10.3 | Classify a divergence against the established taxonomy rather than justifying it ad hoc | F |
| 10.4 | Author/amend architecture standards under `docs/architecture/`, including what they do not fix | F |
| 10.5 | Amend a SIP in the PR that diverges from it, as a new numbered section; never edit `updated_at` by hand | F |
| 10.6 | Move SIP status only via `scripts/maintainer/update_sip_status.py` with `SQUADOPS_MAINTAINER=1` | L+ |
| 10.7 | Execute the release cut: `version_cli.py bump` → markers in sync → CHANGELOG rotate → ROADMAP entry → SIP sweep → tag → capture package | F |
| 10.8 | Capture a release package with `build_release_package.py`, reading the preview before `--write` | F |
| 10.9 | Verify dependency governance: `audit_dependencies.sh` against `requirements/*.lock`, exceptions justified in `audit-ignore.txt` | L+ |
| 10.10 | Maintain traceability: issue → branch → PR → evidence → plan row | L+ |

## 11. Cross-cutting disciplines

Not tasks. These qualify every domain above, and are the difference between producing evidence
and producing the appearance of it.

| # | Discipline | Tier |
|---|---|---|
| 11.1 | Verify before asserting; carry file and line for every load-bearing claim | F |
| 11.2 | Apply the strictest verification to *reassuring* claims, not alarming ones | F |
| 11.3 | Make verification broader than the change it checks | F |
| 11.4 | Treat a check that cannot fail as no check at all | F |
| 11.5 | Before removing anything, name the evidence it produced and who consumed it | F |
| 11.6 | Require, don't default, at a composition seam | F |
| 11.7 | Test the exact predicate that will be armed; re-test it if edited | F |
| 11.8 | Treat blank, empty, or missing as failure, never as success | F |
| 11.9 | Read recurrence as a root-cause signal, not coincidence | F |
| 11.10 | Know whether over- or under-discrimination is the expensive direction for the case at hand | F |
| 11.11 | Reject a fix shaped like a list that will grow, in favour of one that states a rule | F |
| 11.12 | Prove a fix at the wiring, not only at the seam it patches | F |

## 12. Continuity

| # | Capability | Tier |
|---|---|---|
| 12.1 | Capture a durable lesson with its cause, so it changes behaviour rather than restating a rule | F |
| 12.2 | Record resumable state before long-running or interruptible work | F |
| 12.3 | Distinguish what is worth retaining from what the repository already records | F |
| 12.4 | Correct or delete retained knowledge that proves wrong | F |
| 12.5 | Verify a retained fact still holds before acting on it | F |

## 13. Collaboration and judgement

| # | Capability | Tier |
|---|---|---|
| 13.1 | Propose before state-changing, outward-facing or irreversible action | F |
| 13.2 | Distinguish what genuinely needs the owner (sudo, credentials, rulings) from what the agent can resolve | F |
| 13.3 | Report faithfully — failures, partial work, steps skipped | F |
| 13.4 | Correct an error plainly and continue, without ruminating | F |
| 13.5 | Raise a concern once, then proceed on the ruling | F |
| 13.6 | Recognise when a literal instruction would skip necessary work, and say so before acting | F |
| 13.7 | Lead with a recommendation and its reasoning, not a survey of options | F |
| 13.8 | State a stopping rule before entering a loop that could repeat indefinitely | F |
| 13.9 | Report in the reader's units — times in ET, though logs and records are UTC | L |

---

## Suggested role clusters

Cut so each role owns a coherent judgement domain and handoffs are artifacts, not conversation.

| Role | Owns | Notes |
|---|---|---|
| **Investigator** | §1, and diagnosis across §7–9 | Traces defects to the owning line; never merges |
| **Implementer** | §2, §4 | Writes the change; hands evidence to Verifier |
| **Verifier** | §3, §5 | Owns whether a check can fail; can veto a merge |
| **Integrator** | §6 | Branch/PR/CI/merge hygiene; L+ except 6.3, 6.7–6.9 |
| **Platform operator** | §7, §8 | Containers, DB, IdP, broker, Prefect, LangFuse, Ollama, host |
| **Measurement steward** | §9 | Set configs, probes, drivers, records; owns supersede calls |
| **Recorder** | §10, §12 | Issues, plans, SIPs, release cut, retained knowledge |

§11 is owned by every role — it is not delegable. §13 stays with whichever role holds the owner
relationship and should **not** be distributed: escalations must arrive on one channel.

## Allocation notes

- **The local/frontier line is cost of being wrong.** Running the regression gate is easy and
  safely local. Deciding whether a red pre-existed is equally "easy" and is not, because a
  wrong answer there is invisible and propagates.
- **Anything concluding "clean", "green", "passing" or "safe" is frontier** — or returns raw
  evidence for a frontier model to conclude from. The expensive errors here are false
  negatives dressed as confirmations.
- **Local models are strongest at collection**: run it, gather it, extract the fields, hand
  back raw output without a verdict.
- **Every delegation needs a paired control.** A subordinate reporting success on a task it
  could not have failed is the same defect as a test that can only pass.
- **Long-running work must outlive its supervisor.** Detach it, log it to disk, and make the
  watcher disposable — the watcher is the fragile part, never the work.
