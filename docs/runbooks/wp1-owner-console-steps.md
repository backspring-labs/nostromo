# WP-1 owner console steps: provider and GitHub boundaries

Owner-side steps for NOSTROMO-PLAN-0001 WP-1 (§8.1 to §8.9). Every item here is a browser action only the owner can take. Everything after it (key placement on the Spark, rulesets, attribution probes, evidence) is assistant work and is listed at the end. Verified against the provider documentation on 2026-09-09; console labels may drift, the intent does not.

Rules that apply throughout:

- One boundary per metered role. Parker, Ripley, and Dallas never share a key, a project, or a workspace.
- Caps are enforced by the provider, not by prompt. A notification threshold is not a cap.
- Keys are shown once. Save each one straight into a file on the Mac, never into chat, never into the repo: `~/.config/nostromo/secrets/<role>/` with `chmod 700` on the directory and `chmod 600` on files. The assistant later moves them to the Spark over SSH without reading them.
- What to report back after each section is listed as **Report** and contains no secrets.

## 1. OpenAI: two projects with enforced hard limits

Console: https://platform.openai.com

### 1.1 Organization sanity check first

1. Settings → Organization → **Limits** (organization level). Note whether an organization hard limit exists and its amount.
2. It must leave room for `$70 + $25 = $95` of Nostromo spend on top of any other API workloads billed to this organization. If an existing limit is lower than that, raise it.

   **Set 2026-09-13: `100`.** (The recommendation was `110`, derived as the sum of the project caps plus
   about 15%. The owner set `100`, which leaves `$5` of headroom over the `$95` of caps — enough for
   realistic enforcement lag, which is a propagation window measured in cents rather than dollars.)

   **The headroom is `$5`, so two changes require raising this limit**, and both are silent failures if
   missed: adding any other API work to this organization, since the limit spans every project; and raising
   a project cap without moving the organization limit with it.

   **Add any other API work billed to this organization**, because the limit spans every project. Check the
   usage page grouped by project first. If other usage is substantial and variable, a separate organization
   for Nostromo is cleaner than a limit that has to accommodate two unrelated things.

   This is the third fence, not the first. With prepaid credits and a `95` monthly reload limit, the card
   cannot be charged more than `95` in a month regardless of any spend limit. The organization limit exists
   to produce a clean, diagnosable error instead of silent balance exhaustion.
3. Settings → Organization → **Billing**: confirm a payment method or prepaid balance exists. Projects bill to the organization.

### 1.2 Project `nostromo-parker`, cap $70

1. Settings → Organization → **Projects** → **Create project** → name `nostromo-parker` → Create.
2. Open the project → **Limits** → under **Spend** select **Edit spend limit**.
3. **Monthly spend limit**: `70`. Turn on **Enforce a hard limit**. **Save**. If the page only offers a notification or budget without the enforce toggle, stop and report; the plan requires enforcement.
4. Optional but useful: an alert threshold at `55` so you hear about it before the cutoff.
5. **Model allow-listing: do it.** The list is a checkbox set, so this is a few clicks. **Leave only `gpt-5.6-sol` checked** and uncheck everything else, on both projects.

   The reason is cost, not tidiness. Newer frontier models appear in this list enabled by default — `gpt-6-astra` was checked on first creation, 2026-09-13 — and a newer model is very likely more expensive per token. A harness pointed at the wrong model would burn the cap several times faster for identical work, and would do it silently. Restricting the project turns that into a loud failure, which is the same reason the spend limit is enforced provider-side rather than trusted to configuration.

   Per-model rate limits are optional; the defaults are fine for a single agent.

   The exact identifier is pinned in `docs/source-baseline.md`. If it ever differs from `crew/manifest.yaml`, the manifest is the design intent and the console is the fact — reconcile before launching anything.
6. **Service accounts** (in the project's settings) → **Create** → name `parker`. This yields the key. A service-account key belongs to the project, not to your user, so it survives changes to your own account. Save it as `~/.config/nostromo/secrets/parker/openai.key`.
7. Do not create a second key in this project for anything else.

### 1.3 Project `nostromo-ripley`, cap $25

Repeat 1.2 with name `nostromo-ripley`, **Monthly spend limit** `25`, **Enforce a hard limit** on, service account `ripley`, key saved as `~/.config/nostromo/secrets/ripley/openai.key`.

### 1.3a Starting mid-month

The spend limit is a **safety cap**, not a monthly allowance, and it should carry the correct year-round
value. The monthly cycle resets tracked spend to zero and leaves the configured limit alone, so a prorated
limit stays prorated until someone changes it back, and the failure is silent: the agent stops early next
month for no visible reason.

**Recommended when setting up part-way through a month.** Set the limits at their full values and bound the
month with the credit balance instead, which needs no un-doing:

| Control | Value now | Change at the start of the next full month |
|---|---|---|
| Project limits | `70` and `25`, enforce on | nothing |
| Initial credit purchase | `$50` | — |
| Auto reload | `$10` when the balance drops below `$5` | unchanged |
| Monthly reload limit | `$50` | raise to `$95` |

**If you prefer prorated caps instead**, multiply each cap by the fraction of the month remaining, and put a
calendar reminder on the first of the next month to raise all of them back. Set up on 2026-09-13, with
eighteen of thirty days left, that is 60%: Parker `42`, Ripley `15`, Dallas `15`. The reminder is what makes
this version safe; without it the prorated numbers become the permanent ones.

**The reload limit is derived, not chosen.** Set it to the **sum of the enforced project caps**, which is
`70 + 25 = 95`. That makes it a number anyone can re-derive and audit rather than a magic figure whose
reasoning has to be remembered, and it keeps the second fence exactly in line with the first. The same rule
gives Anthropic `25`, the sum of its one workspace limit.

Enforcement lag means recorded spend can slightly exceed a cap, so in a month where both projects run to
their limits the last few requests may return `insufficient_quota` (balance exhausted, account-wide) rather
than `project_spend_limit_exceeded` (that project only). That is a difference in which error you see, not in
how much you spend, and the $10 of headroom between the $140 configured envelope and the $150 ceiling
absorbs it at the budget level.

**Note on the first partial month.** Until the crew is commissioned, the only metered traffic is the
attribution probes in §5 — one small request per key. Real burn begins when Parker starts implementing,
which is gated behind WP-10.

### 1.4 Behaviour to expect at the cap

When tracked spend reaches a project hard limit, requests billed to that project return HTTP `429` with error code `project_spend_limit_exceeded`. Enforcement is not instantaneous, so recorded spend can slightly exceed the amount. The limit resets on the next monthly cycle, or when you raise or remove it. An organization hard limit applies across all projects and produces its own error code.

**Report:** the two project IDs (`proj_…`), the organization hard limit amount if any, and confirmation that both projects show the enforce toggle on.

## 2. Anthropic: one workspace with a spend limit

Console: https://platform.claude.com

1. **Settings → Workspaces** → **Create workspace** → name `nostromo-dallas`, pick a colour → **Create**. It must be a new workspace: the Default Workspace cannot carry limits.

   Starting mid-month, apply §1.3a here too: keep the workspace limit at its full `25` and bound the month with a smaller initial purchase, `$25` at the start of a full month or `$20` when part-way through, with the monthly reload limit also `25` by the same derivation rule.
2. Open the workspace → **Spend limits** tab → monthly spend limit `25`, plus an alert threshold around `20`. Workspace limits can be set lower than the organization's limits but not higher, and organization limits always apply as well, so confirm the organization limit under Settings leaves room for `$25` on top of your other Anthropic usage.
3. **Rate limits** tab: confirm the Opus tier is available to the workspace, and **record the exact model identifier** for the same reason as §1.2 step 5 — the manifest says only `model_family: opus`. Leave the values at the organization defaults unless you want single-agent ceilings.
4. Switch into the workspace using the **Workspaces** selector in the top-left, then **API keys** → **Create Key** → name `dallas`. The key must be scoped to this single workspace, not a multi-workspace key. Save it as `~/.config/nostromo/secrets/dallas/anthropic.key`.
5. Nothing else is created in this workspace.

Every API response carries an `anthropic-workspace-id` header, which is how the assistant's test request proves attribution: the header must equal the `wrkspc_…` ID of `nostromo-dallas`, and the request must appear under that workspace's usage.

**Report:** the workspace ID (`wrkspc_…`), the organization spend limit amount, and confirmation that the key is single-workspace.

## 3. GitHub: two Apps owned by backspring-labs

Console: https://github.com/organizations/backspring-labs/settings/apps

### 3.1 Register `nostromo-parker`

1. Organization **Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App**.
2. **GitHub App name**: `nostromo-parker`. Names are unique across all of GitHub; if it is taken, use `backspring-nostromo-parker` and report the name you used.
3. **Homepage URL**: `https://github.com/backspring-labs/nostromo`.
4. **Callback URL**: leave empty. Leave the user-authorization options at their defaults; this App never acts on behalf of users.
5. **Webhook**: untick **Active**. No webhook URL or secret.
6. **Permissions → Repository permissions**: **Contents** = Read and write; **Pull requests** = Read and write; **Metadata** = Read-only (set automatically). Everything else stays No access. **Organization permissions** and **Account permissions**: none.
7. **Where can this GitHub App be installed?**: **Only on this account**.
8. **Create GitHub App**.
9. On the App's **General** page note the **App ID** near the top.
10. Scroll to **Private keys** → **Generate a private key**. A `.pem` file downloads (`nostromo-parker.<date>.private-key.pem`). Move it out of Downloads immediately to `~/.config/nostromo/secrets/parker/github-app.pem`, `chmod 600`. Generate exactly one key; keys never expire and are revoked manually, and the App can hold up to 25 for rotation.
11. Left sidebar **Install App** → **Install** next to `backspring-labs` → **Only select repositories** → choose `squad-ops` only → **Install**. The page you land on has the installation ID at the end of its URL, `…/settings/installations/<number>`. Note the number; the assistant can also read it through the API.

### 3.2 Register `nostromo-ripley`

Repeat 3.1 with the name `nostromo-ripley`, key at `~/.config/nostromo/secrets/ripley/github-app.pem`, installed on `squad-ops` only.

### 3.3 What not to do

- Do not install either App on `nostromo` or any other repository.
- Do not grant organization-level permissions, Administration, Workflows, or Actions.
- Do not create Apps for Dallas, Brett, or Mother yet; they get identities when their write flows are commissioned in WP-9 and WP-10.
- Do not put your personal token into any crew file. The Apps are the only GitHub credentials the crew will ever hold.

**Report:** for each App, the slug (from its URL), the App ID, and the installation ID.

## 4. Ash and Lambert

These are terminal steps on the Mac rather than console steps, and the assistant drives them when WP-1 is executed. Ash logs into Codex with your ChatGPT Plus account and must have no `OPENAI_API_KEY` or `CODEX_API_KEY` anywhere in its environment. Lambert uses your existing Gemini login. Both interactive logins are typed at the prompt with the `!` prefix when asked.

## 5. What the assistant does once the reports arrive

1. Reads the two OpenAI projects and the Anthropic workspace through their admin surfaces where available, and sends one tiny test request per key from the Spark, confirming attribution by project and by the workspace response header.
2. Records the documented cutoff behaviour per provider in the evidence, without any burn test (§8.11).
3. Moves each key from `~/.config/nostromo/secrets/<role>/` on the Mac to the Spark's role-local secret file over SSH, never through chat, and confirms `ash.env`, `mother.env`, and `brett.env` carry no metered key at all (§8.10).
4. Confirms both Apps through the API, resolves each bot user (`<slug>[bot]`) and its numeric ID for the commit identity, and records slug, App ID, installation ID, and bot login in `crew/manifest.yaml` (§8.7, §8.8).
5. Creates the four `squad-ops` rulesets, exports them to `infrastructure/github/rulesets/`, and runs the attribution and rejection probes on disposable `nostromo/<name>/probe` branches (§8.9).
6. Writes the WP-1 evidence and ticks the plan's Provider and GitHub checklists (§8.12), then the gate in §8.13 lifts for Ripley, Dallas, and Parker.
