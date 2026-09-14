# OpenCode permission profiles

NOSTROMO-PLAN-0001 §11.11, amended by NOSTROMO-0002 §2.1 and §45.4. Pinned to **OpenCode 1.18.30**;
the permission identifiers below were read out of that build, not from documentation, because the
plan warns that the V1 and V2 syntaxes must not be mixed.

Identifiers this version accepts: `read`, `edit`, `write`, `bash`, `webfetch`, `task`, `question`,
`plan_enter`, `plan_exit`, `doc_comment`, `doc_tag`, `external_account`, `external_directory`,
`external_output`. Actions: `allow`, `ask`, `deny`. `bash` takes either a single action or a map of
glob → action.

**These files are a default, not the control.** `OPENCODE_PERMISSION` in the environment merges over
the config file, so the launcher injects the role's profile at start rather than trusting a file the
agent could edit. A profile an agent can rewrite is a suggestion.

## Brett — bounded implementation, never conclusion

Brett is **Parker's local-model assistant**. He exists to take bounded work off the frontier budget:
work that is specified well enough for a local model to execute, so Parker's tokens go to the parts
that need frontier judgement. Two consequences, and they are the same consequence:

- He **may edit, commit, and push to `nostromo/brett/**`** — inverted from the plan, which denied it
  when he was a verification role (NOSTROMO-0002 §2.1). Offloading work means doing work.
- He **may never conclude**. `gh pr merge` and `gh pr review` are denied, `task` is denied so he
  cannot spawn an agent to conclude on his behalf, and `question` is **allowed** because escalating
  is his correct output when the card runs out.

The benchmark on 2026-09-13 measured exactly this: the local model got the classification right and
**declined to name what it could not see**, escalating instead — an honest fail. The same model with
reasoning enabled talked itself into a confident wrong answer on the task reserved for the owner.
Brett's value is bounded execution plus honest escalation; the moment he concludes, the budget saved
has bought the failure mode the SquadOps record is full of.

`git push` to any namespace but his own is denied, which duplicates the branch ruleset deliberately:
the ruleset is the control, this is the early, legible error.

## Mother — routing only

Mother reads and routes. No edit, no write, no commit, no arbitrary shell — only the read-only git
and `gh` verbs needed to see state. `webfetch` and `task` denied. `question` allowed, because
routing to the owner is an answer.

Mother runs with **reasoning off** (`docs/source-baseline.md`): with reasoning on she routed an
architecture commitment — the owner's decision — to Ripley at high confidence five times out of five.
