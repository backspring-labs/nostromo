# Owner console steps: the `nostromo-dallas` and `nostromo-brett` GitHub Apps

NOSTROMO-0002 §45.4. Both are registered the same way as `nostromo-parker` and `nostromo-ripley`
(`wp1-owner-console-steps.md` §3.1), and **only the permission table differs**. The differences are
the whole point, so they are spelled out rather than left as "same as before".

Report back, for each: the **slug** (from the App's URL), the **App ID**, and the **installation ID**.

---

## Common steps

1. Organization **Settings** → **Developer settings** → **GitHub Apps** → **New GitHub App**.
2. **GitHub App name**: as below. Names are globally unique; if taken, use `backspring-nostromo-<role>`
   and report the name used.
3. **Homepage URL**: `https://github.com/backspring-labs/nostromo`.
4. **Callback URL**: empty. Leave user-authorization options at their defaults — these Apps never act
   on behalf of a user, and no client secret is generated. An unused credential is an unnecessary one.
5. **Webhook**: untick **Active**. No URL, no secret.
6. **Permissions** — the table for the role, and nothing else. **Organization permissions** and
   **Account permissions**: none at all.
7. **Where can this GitHub App be installed?** → **Only on this account**.
8. **Create GitHub App**, then note the **App ID** on the General page.
9. **Private keys** → **Generate a private key**. Move the `.pem` out of Downloads immediately:
   `~/.config/nostromo/secrets/<role>/github-app.pem`, then `chmod 600`. Generate exactly one.
10. **Install App** → **Install** next to `backspring-labs` → **Only select repositories** →
    `squad-ops` only → **Install**. The installation ID is the last path segment of the URL you land
    on: `…/settings/installations/<number>`.

---

## `nostromo-dallas` — the reviewer

| Permission | Level | Why |
|---|---|---|
| **Pull requests** | **Read and write** | submit reviews. This is the entire point: §14 requires a review from a non-author, and a ruleset can only see a review actually submitted to GitHub |
| **Contents** | **Read-only** | read the diff under review |
| **Issues** | **Read-only** | read the Finding Record and the card the work claims to satisfy |
| **Metadata** | Read-only | automatic |

**Contents is read-only deliberately, and this is not an oversight to be corrected later.** The
reviewer must not be able to fix what it reviews. Dallas also gets **no branch namespace** — there is
no `nostromo/dallas/**` ruleset, because Dallas never pushes.

Without this App the independence model is unenforceable and Dallas degrades to opining in Buzz
while somebody else merges on its say-so — the stamp-instead-of-review failure the crew exists to end
(807 of 935 merged PRs in the record carry a one-word review).

## `nostromo-brett` — the bounded implementer

| Permission | Level | Why |
|---|---|---|
| **Contents** | **Read and write** | push to `nostromo/brett/**`. Brett is Parker's local-model assistant and offloading work means doing work |
| **Pull requests** | **Read and write** | open and update his own PRs |
| **Issues** | **Read-only** | fetch the Bounded Task Card. **He never edits it** — a bounded worker who can rewrite his own boundary is not bounded |
| **Metadata** | Read-only | automatic |

Note Brett gets Issues **read**, where Parker and Ripley have read *and write*: they author Finding
Records and task cards, Brett only executes them.

---

## What not to do

- Do not install either App on `nostromo` or any repository other than `squad-ops`.
- Do not grant Administration, Workflows, or Actions, or any organization-level permission.
  `workflows: write` is withheld from every crew identity: an agent that can edit workflow
  definitions can edit the checks that gate its own merges.
- Do not give Dallas Contents write "so it can fix small things". That is the failure, not a convenience.

## What the assistant does with the report

Confirms both Apps through the API, resolves each bot user and its numeric id for the commit
identity, records slug / App ID / installation ID / bot login in `crew/manifest.yaml`, binds each
worktree's `user.email` and credential helper, adds the `nostromo-brett-branches` ruleset (and
deliberately none for Dallas), and probes both directions — that Brett can push to his namespace and
not to another's, and that Dallas can submit a review and cannot push at all.
