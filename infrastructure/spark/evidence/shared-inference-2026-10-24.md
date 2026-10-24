# Shared inference commissioning — 2026-10-24

The owner authorized this change after the single calibration diagnostic completed. The
calibration was accepted and the campaign ended at its one-cycle limit; its closing record
remains in Buzz. No new campaign or metered review was dispatched for this transition.

Observed on Spark after the root broker upgrade:

- `shared-ready` reported contract 1. The earlier approval retained exclusive mode and its
  original definition digest. New approvals default shared; counted verification stays exclusive.
- The owner job checked the runtime box, stopped the existing engine, verified its memory
  release, and started the same image/checkpoint/drafter with `--parallel 2`. The 65,536-token
  context and 20-GiB reserve were retained. Squad clients reconnected on TensorFold.
- Synthetic prompts tokenized to **47,792** and **31,781** tokens. Each generated 1,024 tokens,
  first alone and then concurrently. Both concurrent streams emitted before either completed.
  Each concurrent output hash matched its same-seed solo output.
- Available memory stayed above **63.648 GiB**, with **0 MiB swap growth**. Parallel requests
  reused cached prefixes; their timings are not a controlled cold-cache speedup comparison.
- The candidate's deploy record was written as `dep_829488ad32ce`.

Restoration first stopped safely because the legacy installation had no explicit Spark mode
file: the old launcher had assumed development mode when absent. The owner recorded that mode
through `crewctl mode development`, then the broker's guarded `restore-shared` succeeded. The
probe was not repeated. The owner job's state preserves the recovery and records completion.

Mother and Brett were then observed active with zero automatic restarts. Their running
processes used one worker each; Brett's actual configuration was 20 model rounds and 900 seconds
per turn. Separate role keys each completed a tiny local inference returning `READY`.
The closed-window and lease files were cleared through the broker rather than removed manually.

Validation before deployment: **192 Nostromo tests passed on Linux** and **845 affected
SquadOps scripts/bootstrap tests passed on Linux**. The frozen counted-verification recipe was
not modified. Source review is in Nostromo #5 and SquadOps #2742; neither PR is merged by this
commissioning record.
