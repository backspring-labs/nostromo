# Campaign control from Buzz

Nostromo is a Buzz crew. This adapter lets it operate SquadOps campaigns against a target
application; it does not make Nostromo GitHub the campaign database.

## Authority and cost

| Responsibility | Crew member | Enforced interface |
|---|---|---|
| Definition, scope, limits, exceptions | Owner | Local owner UID or signed owner approval |
| Create, start, pause, own-pause resume, abort, package, Spark lease | Mother | `campaignctl` operations |
| Plan and increment gate decisions; closing interpretation | Ripley | Role UID plus signed decision |
| Independent review of the exact proposed gate decision | Dallas | Signed review bound to decision digest |
| Implementation in the target repository | Parker | Existing repository controls |
| Bounded implementation and deterministic evidence | Brett | Existing task-card controls; leased local window |
| Research and knowledge projection | Ash, Lambert | Existing capability routing |
| Polling, transition notices, factual closing record | Deterministic watcher | Read interface and Buzz publication |

The broker has three separate private-key JWT clients: `campaign-operations`
(`campaign-supervisor`), `campaign-review` (`campaign-supervisor`, `operator`), and
`campaign-evidence` (`campaign-triage`). SquadOps bundles scopes into these roles. The broker
exposes only its command allowlist; no raw API, generic cycle write, admin role, or owner
override is exposed to the crew. OIDC keys are broker-only; access tokens stay in memory.
The kernel's Unix peer UID determines the caller. No role impersonation field is accepted.

Definitions without an explicit automation opt-in never dispatch paid reviews. The bounded
queue below requires a separate immutable owner allowance. SquadOps policy token and elapsed
limits are runtime boundaries, not a provider billing cap. No model or subscription is switched.

## Install on Spark

Run from the tested source checkout on Spark as the owner:

```bash
python3 infrastructure/spark/bin/prepare-campaign-auth.py --channels \
  60cf6624-62d1-4c37-9522-f6dbf884fd25 d6eb31a3-a79a-42cb-b812-21101736b1f1
sudo bash infrastructure/spark/bin/install-campaign-control.sh "$PWD" \
  "$HOME/.config/nostromo/campaign-provision"
```

Preparation uses the existing Keycloak owner's bootstrap login in memory to provision only
the three service clients, and proves each can read the deployed API. It creates no admin
grant. Keep its staging directory owner-only; it contains recovery copies of signing keys.
The root installer installs immutable executable files, keys, units, and a polkit rule allowing
only the broker account to start/stop `nostromo@mother` and `nostromo@brett`. It grants no sudo
or Docker access. An interactive sudo prompt must be completed by the owner.
The owner is added to the `nostromo` group for socket access; use a fresh SSH login afterward.

Deploy this source's constitution, capability table, and role prompts using the existing
`push-repo.sh` workflow. Existing turns retain their old prompts until their next launch.
Check `systemctl is-active nostromo-campaign-broker nostromo-campaign-watch
nostromo-campaign-window.timer` and inspect the journal. Do not enable campaign starts until
the socket's live role refusals have been checked.

## Definition and operation protocol

`campaignctl COMMAND --args FILE` accepts a JSON object; `--args -` reads stdin. Reads include
`status`, `log`, `ledger`, `package`, `escalations`, `lease`, and `packet`, each with
`{"campaign":"cmp_..."}`. `tracked` takes `{}`. No shell command is passed through.

Additional read-only evidence commands:

- `progress`: campaign ID → launched cycles, runs, verification outcomes and waiting gates.
- `cycle`: campaign + cycle IDs; `run` and `checkpoints`: campaign + cycle + run IDs.
- `artifacts`: campaign + cycle, optionally run; paginated internally, refuses oversized lists.
- `artifact`: campaign + artifact IDs; complete UTF-8 bytes up to 256 KiB, checked against the
  vault size/hash and campaign/project/cycle membership. Binary/oversized content is refused.
- `automation`: campaign ID → durable control state, deadline, jobs, reservations and usage.

The read principal does not expose the currently executing task. `progress` says so explicitly;
run checkpoints describe completed work, and must not be presented as current-task telemetry.

Owner `approve-definition` takes `name`, `definition`, `channel`, and `thread`. The definition
contains `project_id`, `objective`, `policy`, optional `scenario_suite`, and optional
`crew: {"require_dallas":true,"paid_dispatches":0,"inference_mode":"shared"}`. Its positive cycle, elapsed, and token
bounds and allowed scope are mandatory. A name's entire approved content is immutable. The
canonical definition digest is recorded on creation. Approve a new name for any amendment.
Each approval authorizes one campaign creation, including an unresolved creation attempt;
Mother cannot multiply the authorization by using fresh request IDs.

## Bounded review opt-in

Before commissioning, verify the provider projects have enough remaining headroom within the
monthly owner budget. The role keys cannot read provider billing administration; local usage
reports are estimates, not proof of remaining credits. No claim here extends to unrelated
manual harness usage on the same provider project.

The local owner first uses `approve-budget` with an object such as:

```json
{"name":"review-pilot-20261025","cap_microusd":5000000,"max_dispatches":8,"expires_at":"2026-10-26T12:00:00Z"}
```

This is an example, not an installed approval. A budget name is immutable. Both the attended
test and later overnight definition should reference the **same** allowance so they cannot
each spend its full value independently. First-pilot caps above $10 or twenty calls are refused.
An opted-in definition adds:

```json
{"crew":{"require_dallas":true,"inference_mode":"shared","paid_dispatches":8,"automation":{"budget":"review-pilot-20261025","not_after":"2026-10-26T11:00:00Z"}}}
```

The earlier absolute `not_after` or start-intent time plus `policy.max_elapsed_s` is persisted
before start. It cannot reset on restart. The no-model Mother timer checks it every thirty
seconds and requests campaign abort (including active-cycle cancellation) through the existing
API. API unavailability can delay abort; it is reported as unreadable, never safe completion.
SquadOps' own token bound remains additional protection. The shared TensorFold engine stays up.

Ripley and Dallas have separate timer-driven workers under their actual Unix UIDs. Each claims
one durable job, which reserves **563,200 microdollars ($0.5632)** before accessing its private
provider key. Accounting uses at most 65,536 serialized request bytes plus 4,096 framing tokens,
8,192 output tokens including reasoning, $5/M input, $20/M output and 10% regional allowance.
No tools, conversation history, automatic provider retry, premium service tier, model fallback,
or additional agent mention is allowed. Actual usage is retained separately; reservations are
never refunded automatically. One call's allowance is preserved for closing interpretation.

The pinned models are `gpt-5.6-sol` and `claude-opus-5-5`; pricing was verified on October 24,
2026 and this implementation refuses new calls after November 1 until reviewed. Sources:
[OpenAI model pricing](https://developers.openai.com/api/docs/models/gpt-5.6-sol),
[OpenAI token limits](https://developers.openai.com/api/docs/guides/token-counting),
[Claude model pricing](https://platform.claude.com/docs/en/models/opus-5-5/overview), and
[Claude Messages API](https://platform.claude.com/docs/en/api/messages/create).

At a live gate, Ripley proposes a verdict citing packet evidence. Dallas reviews that exact
decision and binding independently. Only a non-blocking, signed Dallas response permits
Ripley's deterministic submission. There is no automatic disagreement/revision loop. Missing
evidence, an oversized complete packet, a reserved owner choice, blocking review, provider
failure, stale/uncertain writes or exhausted allowance parks the campaign for owner inspection.
The remaining runtime cutoff still applies. Never resume around a parked control state.

The review packet includes selected authoritative planning, proposal and verification records
in full, with hashes, and discloses its selection. It does not include all source files. A
proposal ruling authorizes implementation; it does not certify the resulting source or UI.
Source requiring closer inspection is available via `artifact`. A reviewer must hold when the
selected evidence is insufficient. No test result may be invented to fill that gap.

Successful closure queues one signed Ripley interpretation and the watcher updates the canonical
Buzz post. A late cutoff or parked/failed review can leave interpretation explicitly pending;
the factual report still records the outcome and retained reservations. Provider responses
survive in the role's private `~/.local/state/nostromo-reviews/job_*.json` recovery files.
These records never authorize another provider call. Review workers add no sudo/polkit grant.

Check `nostromo-campaign-advance.timer`, `nostromo-campaign-review@ripley.timer`, and
`nostromo-campaign-review@dallas.timer` after installation. Existing zero-paid approvals retain
their prior behavior. Passing unit tests is not live commissioning: exercise one attended
feature increment, its independent review, actual implementation acceptance and closing analysis
before enabling an unattended definition.

For remote owner approval, `campaignctl approve-definition --args approval.json --explain`
prints the `campaign-definition: {...}` line. The owner publishes that exact line in an
allowed campaign channel; Mother imports it with `--decision EVENT_ID`. The broker verifies
the owner's manifest public key, event signature, channel, payload, and freshness.

Mother uses:

- `create`: `{"definition":"approved-name","reason":"..."}`.
- `start`, `pause`, `resume`, `abort`, `materialize`, `lease-give`:
  `{"campaign":"cmp_...","reason":"..."}`.
- `lease-take`: the same plus `expires_in_s`.
- `open-window`: `{"campaign":"cmp_..."}`, only at an open increment gate, under the
  broker's own live lease.

Every operational write requires a stable `--request-id`. Retrying the same completed request
returns its receipt. A request with an ambiguous transport outcome is refused on retry; inspect
the runtime/control log and reconcile as owner before further action. Never guess success or
mint a fresh ID to repeat an unresolved write. `resume` accepts no owner action and SquadOps
rejects attempts to resume somebody else's pause.

Starting an exclusive campaign stops Mother's own local harness. Announce the accepted request and its
ID before submitting `start`, and make start the last action of that turn. The independent
broker completes the action and stores its receipt even if the role-side client disappears.

## Gate protocol

Ripley prepares a JSON file with `campaign`, `cycle`, `run`, `decision`, and substantive
`notes`; increment rulings also carry the SquadOps `binding` and, when required,
`classification` and `classification_rationale`. Use the exact current runtime gate binding.

```bash
campaignctl increment --args ruling.json --request-id ruling-001 --explain
```

The output gives two exact single lines: `campaign-decision: {...}` and
`campaign-review: {...}`. Ripley publishes the first under her own Buzz identity. Dallas
independently examines the packet and publishes the second only if that exact decision has
no blocking finding. A signature on a different decision, campaign, cycle, or run is refused.
If Dallas has a blocking finding, report it in the thread and revise; do not sign a false
nonblocking review. Ripley then submits:

```bash
campaignctl increment --args ruling.json --request-id ruling-001 \
  --decision RIPLEY_EVENT_ID --review DALLAS_EVENT_ID
```

Use `plan` for `progress_plan_review`; `increment` is `progress_increment_ruling`. The broker
verifies both signed messages, live run/cycle/campaign membership, and absence of an existing
gate decision. It records their event IDs in the runtime notes and submits as an agent through
Ripley's service principal. Mother cannot submit either gate. Owner-only escalations remain
owner-only; there is no `answer` or action-bearing `resume` shortcut.

## Spark windows and recovery

New approvals default to **shared** inference: Mother stays online and Brett shares bounded
work through one worker, at most 20 model rounds and 900 seconds per turn. Declare
`crew.inference_mode: exclusive` for counted verification. Existing approvals migrate as
exclusive and are never reinterpreted in place. The independent `crewctl mode counted`
launcher guard still prevents local inference during measured runs. Shared inference does
not authorize repository mutation, deployment changes or merges outside existing role rules.

The following lease/quiescence rules apply to exclusive approvals. Shared gate submission
still releases a broker-owned lease if one was explicitly taken, but does not stop the crew.

Before start, gate submission, or lease release, the broker persists a reboot guard, stops
Mother and Brett, and verifies both unit state and zero MainPID. It never stops TensorFold,
which the squad also needs. The watcher can reopen local roles at an increment gate only
after taking the broker's own lease. A ten-second guard closes the window sixty seconds
before expiry, including across restart. Failed stops prevent the squad action.

This is a campaign-specific interlock, not full protection against every external Spark
workload. Generic external runs remain the separate isolation work tracked in Nostromo #1.
After an exclusive campaign closes, the local guard remains closed. The owner restores sharing
with `campaignctl restore-shared --args -` and `{"campaign":"cmp_..."}`. The broker verifies
all registered campaigns completed, the global box is quiet without a supervisor lease,
and only TensorFold is loaded on the pinned model. The host also refuses while counted mode
holds the Spark and starts only enabled Mother/Brett services. Do not clear a guard merely
because a watcher read failed. A root install
alone does not launch a campaign or alter the running inference server.

See [shared inference deployment and validation](shared-inference.md) for the one-shot job that
waits for the current diagnostic before testing two lanes and restoring the local crew.

## Closing record

The watcher polls every five minutes without model calls. It posts state changes in the
approved campaign thread without agent mentions. After three failed readings it explicitly
reports UNREADABLE. It upserts a stable Buzz long-form post, `closing-CAMPAIGN_ID`, on closure;
restarts update the same coordinate. Large runtime records are referenced by campaign ID,
retrieval command, and canonical digest rather than overflowing the relay message limit.

Ripley submits `analysis` with `{"campaign":"cmp_...","analysis":"...","evidence":[...]}`.
`--explain` prints the exact `campaign-analysis: {...}` line to publish, then pass its event ID
with `--decision`. The watcher updates the existing Buzz post. Analysis must state what
improved, what failed, interventions, unknowns, crew cost (or explicitly unavailable), and
recommended next work, citing runtime evidence. A factual closure without this section stays
explicitly pending; it is not an app-quality verdict. Repository fixes resulting from the
analysis go through the target application's PR/review process.

## First commissioning probe

The owner's initial authorization is one local `group_run` calibration diagnostic: at most
one cycle, no increments, repairs, retries, automatic paid dispatch, or automatic owner
decisions. No campaign launches until root installation and live authorization checks pass.
Use the deployed local TensorFold squad profile and a separately approved, immutable
definition derived from the deployed version's calibration recipe. Any gate requiring the
owner or a metered review parks the probe. Report the actual outcome and token ledger in Buzz;
the probe demonstrates wiring, not readiness for unattended app improvement.
