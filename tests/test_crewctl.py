"""Operator-visible manifest values and the existing local-role mode guard.

These enter through crewctl's real reader/commands. Host services are substituted: the suite
must never contact the Spark, stop a real unit, or require a role's secret files.
"""

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CREWCTL = ROOT / "infrastructure/spark/bin/crewctl"


@pytest.fixture
def ctl(monkeypatch):
    monkeypatch.setenv("NOSTROMO_REPO", str(ROOT))
    namespace = runpy.run_path(str(CREWCTL))
    # A runpy function retains its execution globals; patch those rather than the returned copy.
    return namespace["agents"].__globals__


def test_real_manifest_keeps_operator_fields_on_both_sides_of_github_blocks(ctl):
    expected = yaml.safe_load((ROOT / "crew/manifest.yaml").read_text())["agents"]
    actual = ctl["agents"]()
    assert list(actual) == list(expected)
    fields = {
        "buzz_pubkey", "buzz_auth_tag", "nip05", "host", "supervisor", "harness", "provider",
        "model", "respond_to", "capability", "ollama_tag", "workdir", "github_identity",
    }
    for role, cfg in expected.items():
        for field in fields & cfg.keys():
            assert actual[role].get(field) == cfg[field], (role, field)
        if "github" in cfg:
            for field in ("app_slug", "bot_login", "commit_email"):
                assert actual[role]["github"][field] == cfg["github"][field], (role, field)


@pytest.mark.parametrize("github_first", [False, True])
def test_github_block_position_does_not_change_role_identity(ctl, tmp_path, github_first):
    github = "    github:\n      app_slug: example-app\n      bot_login: example[bot]\n"
    scalar = "    buzz_pubkey: example-public-key\n    respond_to: allowlist\n"
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("agents:\n  example:\n" +
                        (github + scalar if github_first else scalar + github) +
                        "  other:\n    provider: tensorfold\n")
    ctl["MANIFEST"] = manifest
    assert ctl["agents"]() == {
        "example": {
            "buzz_pubkey": "example-public-key", "respond_to": "allowlist",
            "github": {"app_slug": "example-app", "bot_login": "example[bot]"},
        },
        "other": {"provider": "tensorfold"},
    }


@pytest.mark.parametrize("role", ["ripley", "parker", "dallas", "brett"])
def test_describe_cli_reports_the_manifest_identity(role):
    result = subprocess.run(
        [sys.executable, str(CREWCTL), "--json", "describe", role],
        env={**os.environ, "NOSTROMO_REPO": str(ROOT)},
        capture_output=True, text=True, check=True,
    )
    actual = json.loads(result.stdout)
    expected = yaml.safe_load((ROOT / "crew/manifest.yaml").read_text())["agents"][role]
    assert actual["buzz_pubkey"] == expected["buzz_pubkey"]
    assert actual["nip05"] == expected["nip05"]
    assert actual["respond_to"] == "allowlist"
    assert actual["owner_attestation"] == "present"
    assert actual["github_app"] == expected["github"]["app_slug"]
    assert actual["github_bot"] == expected["github"]["bot_login"]


def test_preflight_does_not_invent_missing_manifest_identity(ctl, monkeypatch, capsys):
    # Exercise the same command Mother uses to diagnose a stopped role. Other host checks can
    # fail on this machine; the manifest checks must report the real values, without network I/O.
    monkeypatch.setitem(ctl, "ollama_tags", lambda: None)
    ctl["cmd_check"](SimpleNamespace(role="ripley", json=True), ctl["agents"]())
    checks = json.loads(capsys.readouterr().out)["results"][0]["checks"]
    identity = {c["check"]: c for c in checks
                if c["check"].startswith("manifest ") or c["check"] == "owner attestation"}
    assert identity["manifest buzz_pubkey"]["ok"]
    assert identity["manifest respond_to"]["ok"]
    assert identity["owner attestation"]["ok"]


@pytest.fixture
def mode_host(ctl, monkeypatch, tmp_path):
    mode_file = tmp_path / "spark-mode"
    monkeypatch.setitem(ctl, "MODE_FILE", mode_file)
    states = {role: {"active": "active", "enabled": "enabled"} for role in ctl["agents"]()}
    calls = []

    def systemctl(*args):
        calls.append(args)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setitem(ctl, "systemctl", systemctl)
    monkeypatch.setitem(ctl, "unit_state", lambda role: states[role])
    return mode_file, states, calls


def test_counted_mode_stops_both_local_roles_and_persists_the_guard(ctl, mode_host, capsys):
    mode_file, _, calls = mode_host
    assert ctl["cmd_mode"](SimpleNamespace(mode="counted", json=True), ctl["agents"]()) == 0
    assert mode_file.read_text() == "counted\n"
    assert ctl["spark_mode"]() == "counted"
    assert set(calls) == {("stop", "nostromo@mother"), ("stop", "nostromo@brett")}
    assert json.loads(capsys.readouterr().out)["roles"] == {"mother": "stopped", "brett": "stopped"}


@pytest.mark.parametrize("role", ["mother", "brett"])
def test_counted_mode_refuses_a_local_start_before_systemctl(ctl, mode_host, capsys, role):
    mode_file, _, calls = mode_host
    mode_file.write_text("counted\n")
    args = SimpleNamespace(command="start", role=[role], json=True, force=False)
    assert ctl["cmd_unitop"](args, ctl["agents"]()) == 1
    assert calls == []
    error = json.loads(capsys.readouterr().out)
    assert error["role"] == role
    assert "counted mode" in error["error"]


def test_development_mode_resumes_only_enabled_local_roles(ctl, mode_host, capsys):
    mode_file, states, calls = mode_host
    mode_file.write_text("counted\n")
    states["mother"]["active"] = "inactive"
    states["brett"] = {"active": "inactive", "enabled": "disabled"}
    assert ctl["cmd_mode"](SimpleNamespace(mode="development", json=True), ctl["agents"]()) == 0
    assert calls == [("start", "nostromo@mother")]
    assert mode_file.read_text() == "development\n"
    assert json.loads(capsys.readouterr().out)["roles"]["brett"] == "left alone: unit is disabled"


def test_failed_stop_keeps_counted_guard_and_returns_failure(ctl, mode_host, monkeypatch, capsys):
    mode_file, _, calls = mode_host

    def fail_stop(*args):
        calls.append(args)
        return SimpleNamespace(returncode=1, stderr="stop denied", stdout="")

    monkeypatch.setitem(ctl, "systemctl", fail_stop)
    assert ctl["cmd_mode"](SimpleNamespace(mode="counted", json=True), ctl["agents"]()) == 1
    assert mode_file.read_text() == "counted\n"
    assert len(calls) == 2
    assert all("stop FAILED" in value for value in json.loads(capsys.readouterr().out)["roles"].values())
