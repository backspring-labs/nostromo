#!/usr/bin/env python3
"""Enforce Nostromo crew path boundaries on a pull request.

A crew branch is `nostromo/<role>/...`. Each role may only touch the paths its role owns,
declared in .github/nostromo-path-boundaries.yml. Anything that is not a crew branch is
none of this check's business and passes immediately.

This exists because GitHub refuses push rules on public source repositories, so the branch
rulesets that guarantee *who* may write to a namespace cannot also constrain *what* they
write. See Nostromo DEV-006.

Usage:
  check_nostromo_path_boundaries.py --branch <head-ref> --files-from <path|->
  check_nostromo_path_boundaries.py --branch <head-ref> --files a/b.py c/d.py

Exit 0 = allowed. Exit 1 = a boundary was crossed, or the branch names a role with no rules.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

import yaml

DEFAULT_RULES = Path(".github/nostromo-path-boundaries.yml")
CREW_PREFIX = "nostromo/"


def matches(path: str, pattern: str) -> bool:
    """`dir/**` means at or below dir/. Everything else is fnmatch. Nothing else.

    Deliberately narrow: fnmatch's `*` crosses `/`, which makes `src/*` mean more than a
    reader expects. Keeping the vocabulary tiny is worth more here than expressiveness.
    """
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def role_of(branch: str) -> str | None:
    """`nostromo/parker/fix-thing` -> `parker`. Anything else -> None."""
    if not branch.startswith(CREW_PREFIX):
        return None
    rest = branch[len(CREW_PREFIX):]
    role, sep, _ = rest.partition("/")
    return role if sep and role else None


def violations(files: list[str], role: str, rules: dict) -> list[str]:
    out: list[str] = []
    for pattern in rules.get("universal_forbidden", []):
        for f in files:
            if matches(f, pattern):
                out.append(f"{f} — no crew role may change this (it is part of the boundary itself)")

    spec = rules["roles"][role]
    if "allowed" in spec:
        allowed = spec["allowed"]
        for f in files:
            if not any(matches(f, p) for p in allowed):
                out.append(f"{f} — {role} may only touch: {', '.join(allowed)}")
    else:
        for pattern in spec.get("forbidden", []):
            for f in files:
                if matches(f, pattern):
                    out.append(f"{f} — {role} may not touch {pattern}")
    # Preserve order, drop duplicates: one line per file is what a reader wants.
    seen, uniq = set(), []
    for v in out:
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--branch", required=True, help="pull request head ref")
    ap.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--files-from", help="file of newline-separated paths, or - for stdin")
    src.add_argument("--files", nargs="*", help="paths directly")
    args = ap.parse_args(argv)

    if args.files is not None:
        files = [f.strip() for f in args.files if f.strip()]
    elif args.files_from == "-":
        files = [ln.strip() for ln in sys.stdin if ln.strip()]
    else:
        files = [ln.strip() for ln in Path(args.files_from).read_text().splitlines() if ln.strip()]

    role = role_of(args.branch)
    if role is None:
        print(f"not a Nostromo crew branch ({args.branch or '<empty>'}) — no boundary applies")
        return 0

    rules = yaml.safe_load(args.rules.read_text())

    if role not in rules.get("roles", {}):
        # Fail closed. A namespace with no declared boundary is an unreviewed boundary.
        print(f"FAIL: branch {args.branch} names crew role '{role}', which has no rules in {args.rules}")
        print("      Add its boundary before using the namespace, or rename the branch.")
        return 1

    found = violations(files, role, rules)
    if not found:
        print(f"ok: {len(files)} changed file(s) are inside {role}'s boundary")
        return 0

    print(f"FAIL: {len(found)} path boundary violation(s) on branch {args.branch}\n")
    for v in found:
        print(f"  {v}")
    print(f"\n{role}'s boundary is declared in {args.rules}.")
    print("If the work genuinely belongs outside it, it belongs to a different role — hand it off")
    print("rather than widening the boundary. Widening is an owner decision.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
