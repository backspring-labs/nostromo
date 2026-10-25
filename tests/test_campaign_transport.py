"""Credential separation, real RSA assertion proof and inference-window refusal controls."""
import base64
import json
import subprocess
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from runtime.campaigns.auth import API, Refused, assertion
from runtime.campaigns.host import Window


def test_token_transport_preserves_configured_issuer_host(tmp_path):
    key = tmp_path/"key.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)],
                   capture_output=True, check=True)
    key.chmod(0o600)
    client = {"client_id": "review", "token_url": "http://spark:8180/realms/local/protocol/openid-connect/token",
              "token_connect_url": "http://127.0.0.1:8180/realms/local/protocol/openid-connect/token",
              "key_file": str(key), "kid": "review-v1"}
    api = API({"clients": {"review": client}})
    seen = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, maximum): return b'{"access_token":"fixture-only","expires_in":300}'
    def open_request(request, **kwargs):
        seen.append(request)
        return Response()
    api.opener = SimpleNamespace(open=open_request)
    assert api.token("review") == "fixture-only"
    assert seen[0].full_url == client["token_connect_url"]
    assert seen[0].get_header("Host") == "spark:8180"
    from urllib.parse import parse_qs
    signed = parse_qs(seen[0].data.decode())["client_assertion"][0].split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(signed + "=" * (-len(signed) % 4)))
    assert claims["aud"] == client["token_url"]


def test_real_rsa_assertion_verifies_and_is_short_lived(tmp_path):
    key, public = tmp_path/"client.pem", tmp_path/"public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)],
                   capture_output=True, check=True)
    key.chmod(0o600)
    public.write_bytes(subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout"], capture_output=True, check=True).stdout)
    client = {"client_id": "review", "token_url": "http://keycloak/token", "key_file": str(key), "kid": "review-v1"}
    token = assertion(client, now=100)
    header, claims, signature = token.split(".")
    decoded = json.loads(base64.urlsafe_b64decode(claims + "=" * (-len(claims) % 4)))
    assert decoded["iss"] == decoded["sub"] == "review"
    assert decoded["aud"] == client["token_url"]
    assert decoded["iat"] == 100 and decoded["exp"] == 160
    proof = tmp_path/"signature.bin"
    proof.write_bytes(base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)))
    command = ["openssl", "dgst", "-sha256", "-verify", str(public), "-signature", str(proof)]
    assert subprocess.run(command, input=(header+"."+claims).encode(), capture_output=True).returncode == 0
    assert subprocess.run(command, input=(header+"."+claims+"x").encode(), capture_output=True).returncode != 0
    assert key.read_text().strip() not in token
    assert token != assertion(client, now=100), "each assertion needs a fresh jti"


def test_readable_or_symlinked_signing_key_is_refused(tmp_path):
    key = tmp_path/"key.pem"
    key.write_text("not a real key")
    key.chmod(0o644)
    client = {"client_id": "review", "token_url": "http://keycloak/token", "key_file": str(key), "kid": "review-v1"}
    with pytest.raises(Refused, match="owner-only"):
        assertion(client)
    key.chmod(0o600)
    linked = tmp_path/"linked"
    linked.symlink_to(key)
    with pytest.raises(Refused, match="owner-only"):
        assertion({**client, "key_file": str(linked)})


@pytest.fixture
def window(tmp_path):
    meminfo = tmp_path/"meminfo"
    meminfo.write_text("MemAvailable: 123456 kB\nSwapFree: 456 kB\n")
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        if args[1] == "show":
            return SimpleNamespace(returncode=0, stdout="ActiveState=inactive\nMainPID=0\n")
        return SimpleNamespace(returncode=0, stdout="enabled\n" if args[1] == "is-enabled" else "")

    return Window(tmp_path/"squad-window", run=run, meminfo=meminfo), calls


def test_closing_window_records_guard_before_stopping_both_roles(window):
    box, calls = window
    original = box.run

    def assert_guard(args, **kwargs):
        assert box.flag.exists(), "the reboot guard must precede stopping the first role"
        return original(args, **kwargs)

    box.run = assert_guard
    box.close()
    assert json.loads(box.flag.read_text())["memory"]["MemAvailable"] == "123456 kB"
    assert [c for c in calls if c[1] == "stop"] == [
        ["systemctl", "stop", "nostromo@mother"], ["systemctl", "stop", "nostromo@brett"]]
    assert all("tensorfold" not in " ".join(c).lower() for c in calls)


def test_failed_local_stop_does_not_clear_the_reboot_guard(window):
    box, _ = window
    box.run = lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="denied")
    with pytest.raises(Refused, match="could not stop"):
        box.close()
    assert box.flag.exists()


def test_local_window_requires_enough_lease_and_closes_before_expiry(window, monkeypatch):
    box, calls = window
    box.close()
    soon = (datetime.now(UTC)+timedelta(seconds=30)).isoformat()
    with pytest.raises(Refused, match="close to expiry"):
        box.open(soon)
    assert box.flag.exists()
    future = datetime.now(UTC)+timedelta(seconds=300)
    box.open(future.isoformat())
    assert not box.flag.exists()
    assert len([c for c in calls if c[1] == "start"]) == 2
    monkeypatch.setattr("runtime.campaigns.host.time.time", lambda: future.timestamp()-59)
    box.expire()
    assert box.flag.exists()
    assert not box.flag.with_name("crew-window-lease").exists()


def test_failed_opening_start_recloses_the_window(window):
    box, _ = window
    original = box.run
    def fail(args, **kwargs):
        if args[1] == "start":
            return SimpleNamespace(returncode=1, stdout="failed")
        return original(args, **kwargs)
    box.run = fail
    with pytest.raises(Refused, match="failed to start"):
        box.open((datetime.now(UTC)+timedelta(seconds=300)).isoformat())
    assert box.flag.exists()


def test_return_to_shared_refuses_counted_mode_and_only_starts_enabled_local_roles(window):
    box, calls = window
    mode = box.flag.with_name("mode")
    mode.write_text("counted\n")
    box.close()
    before = len(calls)
    with pytest.raises(Refused, match="verification mode"):
        box.restore_shared(mode)
    assert len(calls) == before and box.flag.exists()
    mode.write_text("development\n")
    original = box.run
    def disabled_brett(args, **kwargs):
        if args[1] == "is-enabled" and args[-1] == "nostromo@brett":
            return SimpleNamespace(returncode=1, stdout="disabled")
        return original(args, **kwargs)
    box.run = disabled_brett
    box.restore_shared(mode)
    assert not box.flag.exists()
    assert [c[-1] for c in calls[before:] if c[1] == "start"] == ["nostromo@mother"]
