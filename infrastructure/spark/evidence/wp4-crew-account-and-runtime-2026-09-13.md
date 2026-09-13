# WP-4 evidence, part 2 — the crew account, the runtime, and the harness

**Date.** 2026-09-13. **Host.** `spark`. Covers NOSTROMO-PLAN-0001 §11.2–§11.5 and §11.10.
Part 1 covers the preflight, the Ollama baseline and the local-model benchmark.

---

## The finding that shaped everything below

The Spark is both the owner's SquadOps workstation and the crew's execution host. The owner's
account holds `~/.ssh/id_ed25519` — the key `origin` pushes with — a `gh` token with `repo` scope,
and membership of the `docker` group, which is root-equivalent on this box.

An agent running as that account could push to any branch as the owner. **The crew check only fires
on `nostromo/<role>/**` heads**, so a push to `fix/anything` is subject to no path boundary, no
attribution check and no ruleset. It could merge its own pull request with the owner's token,
defeating both the owner-reserved merge and Dallas's independent review.

Everything WP-1 established holds only while the crew cannot reach the owner's credentials. The
OpenCode permission profiles of §11.11 are harness configuration, not a security boundary; a shell
escape walks past them. The boundary has to be the filesystem.

**Owner decision, 2026-09-13: a separate unprivileged account.**

---

## §11.2b The crew account

Created by `infrastructure/spark/bin/create-crew-user.sh`, run by the owner under `sudo`.

| | |
|---|---|
| User | `nostromo`, uid 1001 |
| Groups | `nostromo` only — **not** `sudo`, `docker`, `adm` or `ollama` |
| Home | `/home/nostromo`, mode 750 |
| Owner's home | tightened to mode 750 in the same run |
| SSH | the owner's existing key, so `ssh nostromo@spark` works from the Mac |
| Shared runtime root | `/opt/nostromo`, owned by `nostromo`, mode 755 |

`/opt/nostromo` is world-readable deliberately. If the crew is later split into one account per role,
each reads the same runtime rather than installing its own copy.

### The boundary, verified from inside it

`verify-crew-boundary.sh` runs **as the crew account**, which is the position an agent occupies;
root simulating that position is a weaker test. Eleven checks, seven of which must be denied:

```text
must be denied:
  PASS  read the owner's SSH private key
  PASS  read the owner's gh token
  PASS  list the owner's home
  PASS  read the owner's squad-ops clone
  PASS  reach the docker socket
  PASS  sudo
  PASS  write the owner's home
must be permitted:
  PASS  write its own home
  PASS  write the runtime root
  PASS  reach Ollama over HTTP
  PASS  reach github.com
```

11/11.

### A bug worth recording, because it is the second of its kind today

The first version of `create-crew-user.sh` carried its own copy of these checks and reported **all
eight as failures** on a boundary that was holding perfectly. It compared the result `fail` against
the literal string `expect-fail`, so no check could ever match. The output said
`expected expect-fail, got fail` — the answer was in the parentheses.

This is the same shape as the benchmark bug in part 1 and as squad-ops#1515: **verification code
that reports the wrong answer while looking like it ran.** The fix was not to patch the comparison
but to delete the duplicate — `verify-crew-boundary.sh` now owns the checks and the setup script
calls it. One fact, one owner. The check function also rejects an expectation that is not exactly
`pass` or `fail`, so the same class of bug fails loudly instead of inverting a result.

---

## §11.2 The Nostromo repository on the Spark

Deploy keys are disabled organization-wide on `backspring-labs`, so the crew account cannot clone
from GitHub. See **DEV-007**. The repository is pushed from the Mac into a bare repository in the
crew account's home and cloned from there (`infrastructure/spark/bin/push-repo.sh`).

The crew account therefore holds the manifests and launch configuration and **no GitHub credential
at all**, which is stronger than the read-only deploy key originally intended. The generated deploy
key was deleted rather than left unused.

---

## §11.3 Runtime, pinned

Installed by `infrastructure/spark/bin/install-base.sh` into `/opt/nostromo/runtime`, entirely in
user space, no sudo. Versions in `versions.lock` beside it.

| Component | Version | Integrity |
|---|---|---|
| Node | `v24.21.0` Krypton LTS | verified against `SHASUMS256.txt` |
| uv | `0.12.13` | verified against the published `.sha256` |
| Herdr | `v0.9.0` | no upstream checksum; `9c8db20f…f0d2` recorded on first install and enforced after |
| OpenCode | `1.18.30` | npm integrity |

Node is pinned rather than managed by a version manager: one fewer moving part, and the launcher
needs a path that does not shift under it. `>= 22` is the binding constraint, from
`claude-agent-acp`.

---

## §11.3–§11.5 Herdr

Session `nostromo`, its own socket at `~/.config/herdr/sessions/nostromo/herdr.sock`.

### Persistence — the probe that matters

A ticking process was started in pane `w1:p1`, then **every client was killed**:

```text
clients attached: 0
ticks at  6s (no client attached):  6
ticks at 14s (no client attached): 14
ticks after reattach:              19
pane readable after reattach:      yes
```

The process ran with nothing attached at all, which is a stronger result than detach-and-reattach.

### Remote attach from the Mac, with its own paired control

Herdr `v0.9.0` installed on the Mac at `~/.local/bin/herdr` — user space, no sudo, removable with
one `rm`. The first attempt **refused**:

```text
matching herdr 0.9.0 is not installed on nostromo@spark (session nostromo) for linux-aarch64.
```

That refusal is the control. Herdr looks for the binary at the literal path `$HOME/.local/bin/herdr`
and the install had put it in the shared runtime root; a symlink resolved it. Verified from the
Spark side while the Mac client was attached:

```text
3958965 /opt/nostromo/runtime/bin/herdr server
3966302 /home/nostromo/.local/bin/herdr --session nostromo remote-client-bridge
```

A `remote-client-bridge` process is what proves the attach, rather than a TUI that drew something.

### §11.4 Workspaces

`mother-control`, `ripley-architecture`, `dallas-review`, `parker-development`, `brett-verification`
— the five the plan names. NOSTROMO-0002 would add `ash` and `lambert`, both now resident on the
Spark; not created, because that spec is unapproved.

---

## §11.10 OpenCode, and §11.13's gate

Provider registered against `http://localhost:11434/v1`; `opencode models ollama` lists
`ollama/qwen3.6:35b-a3b`.

### ACP — the surface the design actually uses

```text
initialize     OK  0.7s  {'name': 'OpenCode', 'version': '1.18.30'}
session/new    OK  0.3s
session/prompt OK  1.8s  stopReason=end_turn
tool calls     ['read']
answer         `backoff(3)` returns 8 (seconds): `2 ** 3`
```

Three consecutive runs, 1.6–2.7 s each. A real tool call against a real file, with the right answer.
**§11.13's gate — "OpenCode→Ollama works independently" — is met**, and it is met on the path
`buzz-acp` will drive rather than on a convenience CLI.

### `opencode run` does not work, and it does not matter

It succeeded twice — including the same file-read task — and then hung on every later invocation,
stopping after `message=init`, before session creation, with no error at any log level. Ruled out:
the flags, the state directory, a held database lock, a respawn loop, Ollama health, and network
reachability. Recorded as **DEV-008**. It is not in the crew's path.

Two hypotheses were formed and discarded along the way — that `--print-logs` was the differentiator,
and that file-versus-pipe redirection was — each disproved by the next measurement. Recorded because
the sequence is the useful part: both looked convincing on three data points.

---

## What remains in WP-4

| Item | Blocked on |
|---|---|
| §11.6–11.7 crew worktrees on squad-ops, and validating each | the App private keys moving from the Mac to the crew account (WP-1 §8.10), then a credential helper minting per-role tokens |
| §11.11 Mother and Brett OpenCode permission profiles | nothing; next after the worktrees |
| Tool-call reliability through OpenCode, at volume | worth folding into the §11.9 benchmark now that ACP is proven |
| `ash` and `lambert` workspaces | NOSTROMO-0002 approval |
