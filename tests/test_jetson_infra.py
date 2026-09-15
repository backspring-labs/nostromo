"""Invariants for the Jetson Buzz relay deployment (Bootstrap Plan WP-2).

These guard the boundaries the plan cares about: the relay is pinned, closed, bound only to the
tailnet, configured from a repo-managed file that can never carry a secret, and in step with the
crew manifest and the source baseline.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
JETSON = ROOT / "infrastructure" / "jetson"
BUZZ = JETSON / "buzz"

SECRET_KEYS = {
    "BUZZ_RELAY_PRIVATE_KEY",
    "BUZZ_GIT_HOOK_HMAC_SECRET",
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "BUZZ_S3_ACCESS_KEY",
    "BUZZ_S3_SECRET_KEY",
    # Added 2026-09-13 with the DNS-01 certificate. Long-lived by necessity — Cloudflare has no
    # short-lived exchange — so it is scoped to one zone's DNS and probe.sh checks it every run.
    "CLOUDFLARE_API_TOKEN",
}
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class _OverlayLoader(yaml.SafeLoader):
    """SafeLoader that understands Compose's !override and !reset merge tags."""


def _tagged(loader, node):
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return loader.construct_scalar(node)


_OverlayLoader.add_constructor("!override", _tagged)
_OverlayLoader.add_constructor("!reset", _tagged)


def _env_pairs(path: Path) -> dict:
    pairs = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        pairs[key.strip()] = value.strip()
    return pairs


@pytest.fixture(scope="module")
def buzz_env() -> dict:
    return _env_pairs(BUZZ / "buzz.env")


@pytest.fixture(scope="module")
def secrets_template() -> dict:
    return _env_pairs(BUZZ / "secrets.env.template")


@pytest.fixture(scope="module")
def lock() -> dict:
    return _env_pairs(BUZZ / "upstream.lock")


@pytest.fixture(scope="module")
def overlay() -> dict:
    return yaml.load((BUZZ / "compose.nostromo.yml").read_text(), Loader=_OverlayLoader)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return yaml.safe_load((ROOT / "crew" / "manifest.yaml").read_text())


def test_relay_hostname_matches_crew_manifest(buzz_env, manifest):
    host = manifest["relay"]["hostname"]
    assert buzz_env["BUZZ_DOMAIN"] == host
    assert buzz_env["BUZZ_MEDIA_SERVER_DOMAIN"] == host
    for key in ("RELAY_URL", "BUZZ_MEDIA_BASE_URL", "BUZZ_CORS_ORIGINS"):
        url_host = re.sub(r"^[a-z]+://", "", buzz_env[key]).split("/")[0].split(":")[0]
        assert url_host == host, f"{key} points at {url_host}, manifest says {host}"


def test_relay_image_pinned_by_digest_and_matches_lock(buzz_env, lock):
    image = buzz_env["BUZZ_IMAGE"]
    assert image.startswith("ghcr.io/block/buzz@sha256:")
    assert DIGEST.search(image)
    assert image.split("@", 1)[1] == lock["BUZZ_IMAGE_INDEX_DIGEST"]
    assert HEX64.match(lock["BUZZ_COMMIT"][:64]) or re.match(r"^[0-9a-f]{40}$", lock["BUZZ_COMMIT"])
    assert re.match(r"^[0-9a-f]{64}$", lock["SHA256_COMPOSE_YML"])


def test_dependency_images_pinned_by_digest(overlay):
    services = overlay["services"]
    for name in ("postgres", "redis", "minio", "minio-init"):
        assert DIGEST.search(services[name]["image"]), f"{name} is not pinned by digest"


def test_secrets_never_live_in_the_repo_managed_env(buzz_env, secrets_template):
    assert not SECRET_KEYS & set(buzz_env), "buzz.env must never carry a secret key"
    assert set(secrets_template) == SECRET_KEYS
    for key, value in secrets_template.items():
        assert value.startswith("CHANGE_ME"), f"{key} in the template is not a placeholder"


def test_relay_is_closed(buzz_env):
    assert buzz_env["BUZZ_REQUIRE_AUTH_TOKEN"] == "true"
    assert buzz_env["BUZZ_REQUIRE_RELAY_MEMBERSHIP"] == "true"


def test_owner_pubkey_is_valid_hex_when_set(buzz_env):
    # A malformed value is a relay startup error; an absent one is a startup error in closed mode.
    assert HEX64.match(buzz_env.get("RELAY_OWNER_PUBKEY", "")), "RELAY_OWNER_PUBKEY must be 64 hex chars"


def test_relay_binds_loopback_only(buzz_env, overlay):
    # Tailscale Serve is the only tailnet entry point; the plaintext port never leaves the host.
    assert "BUZZ_BIND_IP" not in buzz_env, "the tailnet binding was retired when Serve went live"
    ports = overlay["services"]["relay"]["ports"]
    assert ports, "overlay must take over the relay port list"
    for entry in ports:
        assert entry.startswith("127.0.0.1:"), entry


def test_relay_urls_use_tls_through_serve(buzz_env):
    assert buzz_env["RELAY_URL"].startswith("wss://")
    assert buzz_env["BUZZ_MEDIA_BASE_URL"].startswith("https://")
    assert buzz_env["BUZZ_CORS_ORIGINS"].startswith("https://")
    for key in ("RELAY_URL", "BUZZ_MEDIA_BASE_URL", "BUZZ_CORS_ORIGINS"):
        assert ":3000" not in buzz_env[key], f"{key} must go through Serve on 443, not the relay port"


def test_overlay_splits_env_into_repo_and_host_files(overlay):
    assert overlay["services"]["relay"]["env_file"] == ["buzz.env", "secrets.env"]


def test_source_baseline_records_the_pin(lock):
    baseline = (ROOT / "docs" / "source-baseline.md").read_text()
    assert lock["BUZZ_IMAGE_INDEX_DIGEST"] in baseline
    assert lock["BUZZ_COMMIT"][:7] in baseline


def test_jetson_scripts_are_executable():
    for name in ("install.sh", "bootstrap-remote.sh", "buzzctl", "backup.sh", "probe.sh"):
        path = JETSON / "bin" / name
        assert path.exists(), name
        assert path.stat().st_mode & 0o111, f"{name} is not executable"
