"""The path boundary check, run against its paired control.

DEV-006: GitHub refuses push rules on public source repositories, so the branch rulesets
that guarantee *who* may write to a crew namespace cannot constrain *what* they write.
This check is the substitute, and these fixtures are what make it trustworthy: a guard
proves it fires on the commit that motivated it, and a check that cannot fail is no check.
"""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "infrastructure" / "github" / "squad-ops-check"
CHECKER = BASE / "files" / "scripts" / "dev" / "check_nostromo_path_boundaries.py"
RULES = BASE / "files" / ".github" / "nostromo-path-boundaries.yml"
CASES = yaml.safe_load((BASE / "fixtures" / "cases.yaml").read_text())["cases"]


def run(branch: str, files: list[str]):
    return subprocess.run(
        [sys.executable, str(CHECKER), "--branch", branch, "--rules", str(RULES), "--files", *files],
        capture_output=True, text=True,
    )


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_case(case):
    r = run(case["branch"], case["files"])
    want = 0 if case["expect"] == "pass" else 1
    assert r.returncode == want, (
        f"{case['name']}: expected {case['expect']}, got rc={r.returncode}\n"
        f"{case.get('why', '')}\n{r.stdout}{r.stderr}"
    )


def test_the_control_set_contains_both_outcomes():
    """A fixture set that only ever passes proves the checker cannot fail."""
    outcomes = {c["expect"] for c in CASES}
    assert outcomes == {"pass", "fail"}


def test_every_declared_role_has_both_a_passing_and_a_failing_case():
    """Per-role paired control. A role covered only by passing cases is untested."""
    roles = yaml.safe_load(RULES.read_text())["roles"]
    for role in roles:
        prefix = f"nostromo/{role}/"
        got = {c["expect"] for c in CASES if c["branch"].startswith(prefix)}
        assert got == {"pass", "fail"}, f"{role}: only {got or 'no cases'}"


def test_the_boundary_protects_itself():
    """Every file that defines the boundary is unwritable by every role."""
    rules = yaml.safe_load(RULES.read_text())
    for role in rules["roles"]:
        for guarded in rules["universal_forbidden"]:
            r = run(f"nostromo/{role}/x", [guarded])
            assert r.returncode == 1, f"{role} could change {guarded}"


def test_a_role_with_no_rules_fails_closed():
    """A crew namespace nobody has bounded must not be an unrestricted one."""
    assert run("nostromo/undeclared/x", ["README.md"]).returncode == 1


def test_a_non_crew_branch_is_never_this_check_s_business():
    assert run("feat/anything", [".github/nostromo-path-boundaries.yml", "src/x.py"]).returncode == 0


def test_pattern_vocabulary_is_the_documented_two():
    """`dir/**` is at-or-below; everything else is fnmatch. Nothing subtler."""
    sys.path.insert(0, str(CHECKER.parent))
    from check_nostromo_path_boundaries import matches

    assert matches("src/a/b.py", "src/**")
    assert matches("src", "src/**")
    assert not matches("srcx/a.py", "src/**")
    assert not matches("a/src/b.py", "src/**")
    assert matches(".github/x.yml", ".github/x.yml")
