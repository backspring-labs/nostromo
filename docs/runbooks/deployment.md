# Deploying Nostromo to the Spark

**Merge a pull request to main, then run `infrastructure/spark/bin/deploy-spark.sh` from the Mac.**
That's all a routine change needs: no sudo, no copying, nothing pushed from a working tree. It works
for code, prompts, personas, the manifest, runbooks, and the campaign runtime alike.

## How it works

- **A release is one commit.** The supervisor account (`nostromo`) fetches GitHub `main`
  anonymously (the repository is public), and `git archive`s the commit, read-only, into
  `/opt/nostromo/releases/<sha>`. Then `/opt/nostromo/current` is repointed at it, atomically.
- **Everything reads through `current`:**
  - `/opt/nostromo/nostromo-src` is a link to it. That covers the harness launcher, prompts,
    personas, the manifest, crewctl and budget-watch.
  - `/usr/local/lib/nostromo`, `/usr/local/bin/campaignctl` and `/usr/local/share/nostromo` are
    root-owned directories of links into it. That covers the campaign code, its entry points, and the
    installed runbooks and review personas.
  - One commit is live for all of it, and `deploy-spark.sh status` says which.
- **Only merged work deploys.** A commit that isn't on GitHub `main` is refused. A pull request's
  review is the approval, and the deploy itself is mechanical.
  - `--allow-unmerged "<reason>"` deploys a commit that is on some GitHub branch, for a trial the
    owner has approved. `status` shows it as UNMERGED until it's merged.
  - Agents never use it on their own judgement.
- **Before anything points at a release, it is checked:**
  - every Python file compiles;
  - every shell script parses;
  - every campaign module imports, in a clean interpreter.
- **A deploy drains first.** It pauses the campaign timers and waits up to 120 s for any running
  worker (it never kills one), then switches and restarts the campaign broker, the campaign watcher and
  budget-watch.
  - It checks they stay up and that the broker answers on its socket.
  - If they don't, it switches back to the previous release, restarts again, and says so.
  - Either way it resumes the timers it paused.
- **No root.** Root never runs release code. The supervisor restarts exactly those units through
  `48-nostromo-release.rules`, a list of unit names. Every unit that runs release code runs as a crew
  or service account, never root (`tests/test_release_deploy.py` checks this).

## What a deploy does not do

- **It doesn't restart crew harnesses.** A restart cancels an in-flight turn. A harness keeps the
  persona it launched with, though base prompts and files read during a turn come from the new release
  at once. `status` lists the harnesses that started before the live release. Restart them with
  `rollout.sh` (canary first) when the crew is quiet.
- **It doesn't change infrastructure.** Unit files, polkit rules, sudoers, accounts, keys and the
  broker's config still need an authenticated, password-prompted install
  (`install-campaign-control.sh`, `install-units.sh`, `install-budget-watch.sh`). A pull request
  that changes a unit file is merged and deployed as usual, and also needs that install to take
  effect. Say so in the pull request.

## Commands

```bash
infrastructure/spark/bin/deploy-spark.sh                  # deploy the head of GitHub main
infrastructure/spark/bin/deploy-spark.sh status           # live commit, main, units, stale harnesses
infrastructure/spark/bin/deploy-spark.sh rollback         # back to the previous release, if it's on main
infrastructure/spark/bin/deploy-spark.sh deploy <commit>  # an earlier commit on main
infrastructure/spark/bin/rollout.sh                       # then restart the crew, canary first
```

- On the Spark, the same commands are `python3 -I /opt/nostromo/current/infrastructure/spark/bin/nostromo-release.py …`,
  run as `nostromo`.
- Five releases are kept, plus the live one and the previous one.
- Each deploy is appended to `/opt/nostromo/state/releases.jsonl`.

`rollback` passes the same gate as a deploy, checked against main as it is now. If the previous
release was an unmerged trial, `rollback --allow-unmerged "<reason>"` needs the owner's approval
again. Without that, deploy the main commit you want instead.

## Root steps run from a fresh clone, never from `/opt/nostromo`

The supervisor owns `/opt/nostromo`, and AI sessions work as the supervisor. So a script there could
change between the owner reading it and root running it. Any root step (the one-time adoption below,
or a later `install-*.sh`) runs from a private root-owned clone of GitHub at the exact commit:

```bash
sudo bash -c 'set -e; D=$(mktemp -d); git -C "$D" init -q
  git -C "$D" fetch -q --depth 1 https://github.com/backspring-labs/nostromo.git COMMIT
  git -C "$D" checkout -q FETCH_HEAD; cd "$D"; exec "$@"' _ <command> [args]
```

## First adoption (once)

1. Stage the release as the supervisor, from the Mac. Before adoption there is no `current` to run
   the tool from:

   ```bash
   ssh nostromo@spark 'python3 -I - stage' < infrastructure/spark/bin/nostromo-release.py
   ```

2. Adopt it as root, from a fresh clone of the same commit. `COMMIT` appears twice:

   ```bash
   sudo bash -c 'set -e; D=$(mktemp -d); git -C "$D" init -q
     git -C "$D" fetch -q --depth 1 https://github.com/backspring-labs/nostromo.git COMMIT
     git -C "$D" checkout -q FETCH_HEAD
     python3 -I "$D/infrastructure/spark/bin/install-release-deploy.py" COMMIT'
   ```

The installer does these, in order:
- refuses unless the staged release is byte-identical to that clone;
- drains;
- switches the paths to links;
- installs the polkit rule and `nostromo@.service`;
- moves `nostromo-deploy`, its sudoers rule and its state to `/var/backups/nostromo-release-adopt-*`;
- starts and checks the daemons.

A failure at any step after the drain puts every change back in reverse order, restarts the daemons
that were running, and resumes the timers it paused.

## Stored state

Rollback is code-only. Campaign state, keys, budgets and provider reservations are never rewound. A
release must read the state its predecessor wrote. An incompatible migration needs attended
maintenance, not a routine deploy.

## History

From 2026-10-26 to 2026-10-27 the campaign code was deployed by a root helper, `nostromo-deploy`,
through a password-free sudo rule. Prompts were deployed separately, by `push-repo.sh` from
whatever branch the Mac had checked out. That allowed two different commits to be live at once. It
also allowed an unmerged branch to run the crew, and changes to the manifest or the helper itself
required the sudo setup to be run again. `install-release-deploy.py` moved the Spark to releases once,
and moved the helper, its sudoers rule and its state to `/var/backups/nostromo-release-adopt-*`.
