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
CHECKER = BASE / "files" / "scripts" / "dev" / "check_nostromo_crew_pr.py"
RULES = BASE / "files" / ".github" / "nostromo-crew-boundaries.yml"
_F = yaml.safe_load((BASE / "fixtures" / "cases.yaml").read_text())
CASES = _F["cases"]
ATTRIB = _F["attribution_cases"]


def run(branch: str, files: list[str], authors=None, expected=None):
    cmd = [sys.executable, str(CHECKER), "--branch", branch, "--rules", str(RULES), "--files", *files]
    if expected is not None:
        cmd += ["--expected-author", expected]
    if authors is not None:
        cmd += ["--authors", *authors]
    return subprocess.run(cmd, capture_output=True, text=True)


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
    from check_nostromo_crew_pr import matches

    assert matches("src/a/b.py", "src/**")
    assert matches("src", "src/**")
    assert not matches("srcx/a.py", "src/**")
    assert not matches("a/src/b.py", "src/**")
    assert matches(".github/x.yml", ".github/x.yml")


@pytest.mark.parametrize("case", ATTRIB, ids=[c["name"] for c in ATTRIB])
def test_attribution_case(case):
    """The ruleset controls who may push; the commit author is a separate field it cannot see."""
    r = run(case["branch"], case["files"], case["authors"], case["expected_author"])
    want = 0 if case["expect"] == "pass" else 1
    assert r.returncode == want, (
        f"{case['name']}: expected {case['expect']}, got rc={r.returncode}\n"
        f"{case.get('why', '')}\n{r.stdout}{r.stderr}"
    )


def test_attribution_control_set_contains_both_outcomes():
    assert {c["expect"] for c in ATTRIB} == {"pass", "fail"}


def test_both_failures_are_reported_together():
    """A run that stops at the first failure hides the second, and the reader fixes one thing twice."""
    r = run("nostromo/parker/x", ["sips/SIP-0001.md"],
            ["someone@example.com"], "328771233+nostromo-parker[bot]@users.noreply.github.com")
    assert r.returncode == 1
    assert "path boundary violation" in r.stdout
    assert "not parker's identity" in r.stdout


def test_attribution_is_skipped_rather_than_assumed_when_unknown():
    """No expected author must not silently read as 'attribution fine'."""
    r = run("nostromo/parker/x", ["src/a.py"], ["anyone@example.com"], None)
    assert r.returncode == 0
    assert "attribution not checked" in r.stdout


def test_the_default_rules_path_resolves(tmp_path):
    """The one path the fixtures never exercised, because they always pass --rules.

    A rename left DEFAULT_RULES pointing at a file that no longer existed, and every test
    stayed green because each supplied the argument explicitly. Caught only by running the
    check for real. This asserts the default the workflow actually relies on.
    """
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / RULES.name).write_text(RULES.read_text())
    r = subprocess.run(
        [sys.executable, str(CHECKER), "--branch", "nostromo/parker/x", "--files", "sips/SIP-1.md"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    assert r.returncode == 1, f"default rules path did not resolve:\n{r.stdout}{r.stderr}"
    assert "may not touch sips/**" in r.stdout


def test_the_default_rules_filename_matches_the_shipped_file():
    """Belt and braces: the constant and the file on disk cannot drift apart again."""
    sys.path.insert(0, str(CHECKER.parent))
    from check_nostromo_crew_pr import DEFAULT_RULES

    assert DEFAULT_RULES.name == RULES.name
