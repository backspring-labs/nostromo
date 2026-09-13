# Exported squad-ops rulesets

GitHub is the authority for these; these files are a committed copy so drift is detectable and the
boundary is reconstructable if a ruleset is deleted. They carry server-assigned fields (`id`, `node_id`,
timestamps, `_links`) which must be stripped before a restore.

Re-export after any change:

```sh
for id in 23189673 23189751; do
  name=$(gh api repos/backspring-labs/squad-ops/rulesets/$id --jq .name)
  gh api repos/backspring-labs/squad-ops/rulesets/$id > "infrastructure/github/rulesets/$name.json"
done
```

Compare what is live against what is committed:

```sh
for f in infrastructure/github/rulesets/*.json; do
  id=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["id"])' "$f")
  diff <(gh api repos/backspring-labs/squad-ops/rulesets/$id | python3 -m json.tool) \
       <(python3 -m json.tool "$f") && echo "$f unchanged"
done
```

`bypass_actors[].actor_id` is the **App id**, not the installation id: 4931663 is `nostromo-parker`,
4931773 is `nostromo-ripley`. `current_user_can_bypass: never` is the field that records the owner being
inside the boundary rather than above it.
