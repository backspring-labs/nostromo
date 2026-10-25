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

The initial adapter never automatically dispatches paid reviews. A missing Ripley or Dallas
review stays pending until an authorized human requests it. SquadOps policy token and elapsed
limits are runtime boundaries, not a provider billing cap; use local-only recipes for the first
probe and inspect usage afterward. No model or subscription is switched by this adapter.

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

Owner `approve-definition` takes `name`, `definition`, `channel`, and `thread`. The definition
contains `project_id`, `objective`, `policy`, optional `scenario_suite`, and optional
`crew: {"require_dallas":true,"paid_dispatches":0,"inference_mode":"shared"}`. Its positive cycle, elapsed, and token
bounds and allowed scope are mandatory. A name's entire approved content is immutable. The
canonical definition digest is recorded on creation. Approve a new name for any amendment.
Each approval authorizes one campaign creation, including an unresolved creation attempt;
Mother cannot multiply the authorization by using fresh request IDs.

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
