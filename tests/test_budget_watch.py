"""budget-watch: which journal lines pause a role, and until when.

The positive case is the real line from 2026-09-28, when Dallas's Anthropic workspace had spent its
month and buzz-acp retried the refusal for 25 minutes. The negatives are the errors that must never
pause a role: a transient rate limit and an overloaded provider recover on their own.
"""

import datetime as dt
import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("budget_watch", str(ROOT / "infrastructure/spark/bin/budget-watch"))
_spec = importlib.util.spec_from_loader("budget_watch", _loader)
bw = importlib.util.module_from_spec(_spec)
_loader.exec_module(bw)

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 9, 28, 15, 36, tzinfo=UTC)

# Verbatim from `journalctl -u nostromo@dallas`, colour codes and all.
REAL = (
    "\x1b[2m2026-09-28T15:36:24.046849Z\x1b[0m \x1b[33m WARN\x1b[0m \x1b[2mbuzz_acp\x1b[0m\x1b[2m:\x1b[0m "
    'agent_returned (application error — pipe intact) agent=0 outcome="error" '
    "configured_model=claude-opus-5-5 pid=917504 error=Agent reported error (code -32603): Internal error: "
    "API Error: 400 You have reached your specified workspace API usage limits. You will regain access "
    "on 2026-10-01 at 00:00 UTC."
)


def returned(error: str) -> str:
    return f'agent_returned (application error — pipe intact) agent=0 outcome="error" error={error}'


def test_the_real_refusal_pauses_until_the_stated_reset():
    v = bw.classify(bw.text(list(REAL.encode())), NOW)  # journald's byte-array form
    assert v == {"kind": "budget", "provider": "anthropic", "reset": dt.datetime(2026, 10, 1, tzinfo=UTC), "stated": True}


def test_a_refusal_without_a_stated_reset_waits_for_the_next_month():
    v = bw.classify(returned("API Error: 429 You exceeded your current quota (insufficient_quota)"), NOW)
    assert v == {"kind": "budget", "provider": "openai", "reset": dt.datetime(2026, 10, 1, tzinfo=UTC), "stated": False}
    december = dt.datetime(2026, 12, 20, tzinfo=UTC)
    assert bw.classify(returned("Your credit balance is too low"), december)["reset"] == dt.datetime(2027, 1, 1, tzinfo=UTC)


def test_transient_errors_never_pause():
    for error in (
        "API Error: 429 rate_limit_error: Number of request tokens has exceeded your per-minute rate limit",
        "API Error: 529 overloaded_error: Overloaded",
        "API Error: 500 api_error: Internal server error",
        "model not found",
    ):
        assert bw.classify(returned(error), NOW) is None, error


def test_only_a_failed_turn_counts():
    ok = 'agent_returned agent=0 outcome="ok" note="reached your specified workspace API usage limits"'
    assert bw.classify(ok, NOW) is None
    assert bw.succeeded(ok)
    assert bw.classify("a user quoting: reached your specified workspace API usage limits", NOW) is None


def test_the_unit_name_gives_the_role():
    line = '{"_SYSTEMD_UNIT": "nostromo@dallas.service", "MESSAGE": "hello"}'
    assert bw.parse(line) == ("dallas", "hello")
    assert bw.parse('{"_SYSTEMD_UNIT": "ollama.service", "MESSAGE": "x"}')[0] is None


def test_local_roles_are_never_paused():
    bw.MANIFEST = ROOT / "crew" / "manifest.yaml"
    assert bw.local_roles() == {"mother", "brett"}


def test_a_saved_pause_is_reapplied_after_a_reboot(tmp_path, monkeypatch):
    """A paused role's unit stays enabled, so a reboot starts it; the saved state must stop it again.
    Found on 2026-09-28, when a power blip rebooted the Spark with Dallas paused."""
    import json
    (tmp_path / "dallas.json").write_text(json.dumps({"role": "dallas", "paused_until": "2026-10-01T00:00:00+00:00"}))
    (tmp_path / "ripley.json").write_text(json.dumps({"role": "ripley", "paused_until": "2026-09-01T00:00:00+00:00"}))
    calls = []

    class R:
        returncode, stderr = 0, ""
        def __init__(self, out): self.stdout = out

    def fake(*args):
        calls.append(args)
        return R("active\n")

    monkeypatch.setattr(bw, "STATE", tmp_path)
    monkeypatch.setattr(bw, "systemctl", fake)
    bw.enforce_saved(NOW)
    assert ("stop", "--no-block", "nostromo@dallas") in calls
    assert not any(c[0] == "stop" and c[-1] == "nostromo@ripley" for c in calls), "an expired pause must not stop anything"


# Verbatim from `journalctl -u nostromo@dallas`, 2026-10-03, after the model was set where Claude Code
# reads it and the bundled Claude Code turned out too old for it. buzz-acp retried this with backoff.
REAL_MODEL = (
    "2026-10-03T14:24:31.804959Z  WARN buzz_acp: agent_returned (application error — pipe intact) agent=0 "
    'outcome="error" configured_model=claude-opus-5-5 pid=428642 error=Agent reported error (code -32603): '
    "Internal error: API Error: 400 Claude Code 2.1.274 does not support this model; version 2.1.280 or "
    "newer is required."
)


def test_an_unsupported_model_pauses_until_the_configuration_changes():
    assert bw.classify(REAL_MODEL, NOW) == {"kind": "model", "provider": "model", "reset": None, "stated": False}
    # "model not found" stays excluded: buzz-acp dead-letters it at once, without the retries.
    assert bw.classify(returned("model not found"), NOW) is None


def test_a_model_pause_lifts_only_when_the_configuration_changes(tmp_path, monkeypatch):
    import json
    state = tmp_path / "dallas.json"
    state.write_text(json.dumps({"role": "dallas", "paused_for": "model", "paused_until": None,
                                 "config_fingerprint": "before-the-fix"}))
    calls = []

    class R:
        returncode, stderr = 0, ""
        def __init__(self, out): self.stdout = out

    def fake(*args):
        calls.append(args)
        return R("enabled\n" if args[0] == "is-enabled" else "inactive\n")

    monkeypatch.setattr(bw, "STATE", tmp_path)
    monkeypatch.setattr(bw, "systemctl", fake)
    monkeypatch.setattr(bw, "fingerprint", lambda: "before-the-fix")
    bw.resume_due()
    assert state.exists() and not any(c[0] == "start" for c in calls), "an unchanged configuration must stay paused"
    monkeypatch.setattr(bw, "fingerprint", lambda: "after-the-fix")
    bw.resume_due()
    assert ("start", "--no-block", "nostromo@dallas") in calls and not state.exists()
