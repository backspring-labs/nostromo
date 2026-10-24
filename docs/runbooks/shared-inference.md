# Shared TensorFold use after commissioning

The owner authorized this change only after the current single-calibration diagnostic ends.
It does not approve another cycle, a paid review, an automatic owner decision, or a benchmark
policy exception. A framing run ending is insufficient: the named campaign must be completed.

Ordinary new campaigns default to shared inference. Mother stays online, and Brett has one
worker, 20 model rounds and a 900-second turn bound. The existing task-card and repository
boundaries still apply. Existing approvals retain exclusive mode; counted verification uses
an explicit exclusive approval and the existing counted-mode launcher guard.

The pinned TensorFold CUDA recipe defaults to one lane. Concurrent requests can queue there;
two-lane generation requires explicit `--parallel 2`. The separate candidate recipe preserves
the pinned checkpoint, drafter, image, sampling, 65,536-token context and 20-GiB memory reserve.
It does not replace the frozen counted-verification recipe. Use the latter for measured sets.

## Deferred owner job

`infrastructure/spark/bin/apply-shared-inference.py` runs as the Spark owner in a transient
user systemd scope started from a fresh owner SSH login. This preserves the owner's newly granted
socket group; a long-lived desktop user manager may still have its old group list. The process
uses `setpriv --no-new-privs`, a 1-GiB cgroup limit and a 25-hour scope lifetime. It has no root
permissions. The root-owned broker update must be installed
first; until `shared-ready` reports contract 1, the job waits without changing the engine.
It also waits for the named campaign's explicit `completed` state. Unreadable status, pauses
and escalations never count as completion. The wait expires after 24 hours without an engine
change if the conditions never become true.

After completion it uses the existing SquadOps engine-switch helper under its host lock. That
helper refuses every open campaign and running, queued or paused run; only then does it restart
the existing TensorFold container from the two-lane candidate and recheck the model clients.
The isolated helper fixes multi-key parsing and preserves the registry's independent Mother
and Brett keys. No second model server or checkpoint is loaded beside the existing one.

The probe sends two synthetic contexts of about 48,000 and 32,000 tokens, first alone and then
together, with fixed seeds and at most 1,024 output tokens per request. It verifies both streams
emit before either finishes, rather than mistaking queued HTTP connections for parallel decode.
It compares output hashes against solo runs, records usage/first-token latency/elapsed time,
and samples host memory throughout. Less than 20 GiB available or more than 64 MiB swap growth
cancels validation. Reports contain hashes and statistics, not keys or prompt bodies.

Only a passing probe enables two lanes. The subsequent `restore-shared` broker command
checks global quiescence again, clears the old window and starts enabled Mother/Brett units.
The Spark mode must be explicitly recorded. On an older installation that assumed development
mode without a file, use the existing supervisor's `crewctl mode development` before guarded
restoration; the campaign startup guard still prevents an early local launch.
If engine switching, validation or deploy recording fails, the helper restores the unchanged
one-lane TensorFold recipe and records the rollback. Once that baseline is verified and recorded,
the crew returns to shared use with serialized requests, and the job records `complete_with_fallback`.
There is no automatic retry of the parallel candidate. If restoring or recording the baseline
fails, or the box is no longer quiet, the crew stays stopped and the owner job records a blocked state.

State and probe files are owner-only under `~/.config/nostromo/shared-inference/`. Inspect:

```bash
systemctl --user status nostromo-shared-inference-postcycle.scope
cat ~/.config/nostromo/shared-inference/state.json
```

Root installation updates only the broker code and units; it does not itself perform the
deferred engine switch. The owner job's readiness checks enforce the ordering even if the
installer runs before the current cycle finishes.
