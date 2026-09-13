# WP-4 evidence, part 3 — crew worktrees on squad-ops

**Date.** 2026-09-13. **Host.** `spark`, crew account `nostromo`.
Covers NOSTROMO-PLAN-0001 §11.6–§11.7.

---

## Layout

```text
~/squadops.git                      bare clone, 19 MiB, shared object store
~/worktrees/squadops/ripley         detached at main
~/worktrees/squadops/parker         detached at main
~/worktrees/squadops/brett          detached at main
~/worktrees/squadops/dallas         detached at main
```

**Bare, not a working clone.** There is no primary checkout, so there is nowhere to commit by
accident and no branch that two roles could both hold. Each worktree is detached at `main`; the
launcher creates `nostromo/<role>/<work-item>` in the role's own worktree when work starts.

It is a **separate clone from the owner's** `~jladd/Code/squad-ops`, which carries 18 worktrees of
its own under `.claude/worktrees/` and an `origin` that pushes with the owner's SSH key. Sharing
that clone would have put the owner's push credential one `git push` away from every agent.

Long-lived role roots with branches swapped, which the plan permits for v1 (§11.6).

### Disk

`du` reports 6.1 GiB per `.venv`, and all four together **6.3 GiB** — uv hardlinks into its cache,
so four role environments cost about what one costs. The whole crew tree is 6.5 GiB of 522 GiB free.
The first figure is a `du` artifact: shared inodes are charged to whichever directory it walks first,
which is why `brett` initially appeared to be 6.1 GiB against 125 MiB for the others.

---

## Identity and credentials, bound per worktree

`extensions.worktreeConfig` is on, so each worktree carries its own `config.worktree`:

| Role | `user.email` | credential helper |
|---|---|---|
| ripley | `328774520+nostromo-ripley[bot]@users.noreply.github.com` | `credential-helper.sh ripley` |
| parker | `328771233+nostromo-parker[bot]@users.noreply.github.com` | `credential-helper.sh parker` |
| brett | *(none — App not registered)* | `credential-helper.sh brett` |
| dallas | *(none — App not registered)* | `credential-helper.sh dallas` |

The bare repository itself carries no identity, so nothing can commit from it.

`credential-helper.sh` mints an installation token on demand through `mint-token.sh`, which now
reads the App and installation ids from `crew/manifest.yaml` rather than the environment. Nothing
is written to disk: the clone URL was rewritten to remove the token immediately after cloning, and
no token appears anywhere under `~/squadops.git` or in `~/.gitconfig`.

**Residual, stated plainly.** Binding the credential to the worktree is a convention while the whole
crew shares one Unix account: a process in parker's worktree could invoke the helper with `dallas`.
It becomes enforcement when roles get their own accounts. Nothing here forecloses that.

---

## Probes

### The fetch control failed, and taught the right lesson

The first control was "brett has no App, so brett's fetch must fail". It **succeeded** — because
**squad-ops is public and an unauthenticated fetch needs no credential at all**. Which also means
the parker and ripley fetches proved nothing about credentials either.

A push is the operation that requires authentication, so the probe moved there.

### Authentication, per role

`git push --dry-run`, which authenticates and writes nothing:

```text
parker   -> nostromo/parker   ACCEPTED
ripley   -> nostromo/ripley   ACCEPTED
brett    -> nostromo/brett    REFUSED
    no App private key at /home/nostromo/.config/nostromo/secrets/brett/github-app.pem
    could not mint a token for brett; is the App registered and the key present?
```

### Namespace, for real

A dry-run authenticates but the server never evaluates rulesets on it, so `parker -> nostromo/ripley`
came back ACCEPTED under `--dry-run` and that result means nothing. Repeated as a real push from the
crew account:

```text
remote: error: GH013: Repository rule violations found for refs/heads/nostromo/ripley/cred-probe.
remote: - Cannot create ref due to creations being restricted.
```

No branches were created; `git ls-remote --heads origin 'nostromo/*'` is empty. This is WP-1's
ruleset probe repeated from the host the crew will actually push from.

### The credential helper, both directions

```text
host=github.com          -> username=x-access-token, password=<token>
host=evil.example.com    -> nothing emitted
```

---

## §11.7 Validation — the repository's own gate

`validate-worktrees.sh` runs `scripts/dev/run_regression_tests.sh`, which is what CI runs: `ruff
check`, `ruff format --check`, the test-quality lint, and the full unit suite. A lighter substitute
would not have served the stated purpose, which is to prove a later failure is not simply a broken
worktree.

```text
brett    git status clean   GATE PASSED  36s  (10229 passed, 5 skipped, 135 warnings in 32.71s)
dallas   git status clean   GATE PASSED  36s  (10229 passed, 5 skipped, 135 warnings in 32.77s)
parker   git status clean   GATE PASSED  30s  (10229 passed, 5 skipped, 135 warnings in 28.43s)
ripley   git status clean   GATE PASSED  35s  (10229 passed, 5 skipped, 135 warnings in 32.61s)
```

Dallas gets the same environment as everyone else although Dallas reviews rather than writes. A
reviewer who cannot run the suite cannot test a claim against repository state, and hardlinking
makes the uniformity free.

### What the validation caught, which is the point of having it

The first run failed **109 of 10,229 tests**, all in `tests/unit/cycles/`. The visible symptoms were
`RuntimeError: coroutine raised StopIteration`, dispatch counts of zero, and `assert 0 == 3` — all of
which read like a genuinely broken build.

**CI was green on the same commit** (`629a9327`, `lint + regression` success). That is what
established the worktree differed from CI rather than the commit being bad, and it is exactly why
§11.7 exists.

The cause was one line several frames down:

```text
PermissionError: [Errno 13] Permission denied: '/tmp/squadops/runs/run_001/prd.md'
```

SquadOps materializes run roots under `/tmp/squadops` unless `SQUADOPS_RUN_ROOT` says otherwise.
On the Spark that directory is **already owned by the owner's account** from their own test runs, so
the crew account could not write into it. Each role now gets `~/.cache/squadops/<role>/runs` — per
role rather than per account, so two roles cannot collide with each other either.

**This is a consequence of the crew-account decision and would have appeared the first time an agent
ran the suite.** Any hardcoded shared path under `/tmp` is a collision between the owner and the
crew; this is the first one found and probably not the last. The launcher preflight should assert
`SQUADOPS_RUN_ROOT` is set and writable before an agent starts.

### Three bugs in the validation script, all the same shape

1. `git status --porcelain | wc -l` discards git's exit code, so a git that **failed** reported zero
   lines and read as "clean". Every worktree was broken — `core.bare` is inherited from a bare repo
   and each needed `core.bare=false` — and the script called them all healthy.
2. The installs were chained `if ! A && B`, which parses `(!A) && B`, so B never ran when A
   succeeded. The pinned test requirements were never installed and the gate then failed on a
   missing `ruff`, which looked like a gate problem and was not.
3. The pass line scraped ANSI escapes into the summary.

The first two are the same failure as squad-ops#1515, the benchmark's token budget, and
`create-crew-user.sh` comparing `fail` to `expect-fail`: **verification code that reports the wrong
answer while appearing to run.** Status and exit code are now captured separately, the installs are
two checked steps, and `ruff` and `pytest` are asserted present afterwards.

---

## What remains in WP-4

| Item | State |
|---|---|
| §11.11 Mother and Brett OpenCode permission profiles | next; nothing blocks it |
| Brett and Dallas GitHub Apps | owner action (NOSTROMO-0002 §45.4); worktrees are ready and will bind identity the moment the manifest carries one |
| Ash worktree and Lambert read-only checkout | NOSTROMO-0002 approval |
| Launcher preflight assertions | `SQUADOPS_RUN_ROOT` set and writable; the role's App key present; the worktree's `user.email` matching the manifest |
