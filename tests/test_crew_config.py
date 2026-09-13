"""Validation of Nostromo's declarative crew configuration.

Implements the automated checks in NOSTROMO-PLAN-0001 §7.10 and §24 against the
requirements in NOSTROMO-0001. Every test names the requirement it enforces.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CREW = ROOT / "crew"
ENV = ROOT / "runtime" / "env"

EXPECTED_AGENTS = {"mother", "ash", "ripley", "dallas", "parker", "brett", "lambert"}
SPARK_AGENTS = {"mother", "ripley", "dallas", "parker", "brett"}  # NSTR-RUN-001
MAC_AGENTS = {"ash", "lambert"}  # D-008
LOCAL_AGENTS = {"mother", "brett"}  # NSTR-MOD-001, NSTR-MOD-002
REPO_WRITING_AGENTS = {"ripley", "parker"}  # NSTR-ID-006, plan §8.7

REQUIRED_AGENT_FIELDS = {
    "display_name",
    "capability",
    "host",
    "supervisor",
    "harness",
    "provider",
    "budget_profile",
    "workspace_profile",
    "respond_to",
    "buzz_pubkey",
    "nip05",
}

LIFECYCLE_STATES = [  # NOSTROMO-0001 §14
    "IDEA_CREATED",
    "EXPLORING",
    "CONVERGING",
    "SIP_DRAFTING",
    "ARCHITECTURE_REVIEW",
    "REVISION",
    "PROPOSED",
    "ACCEPTANCE_REVIEW",
    "ACCEPTED",
    "PLANNING",
    "IMPLEMENTING",
    "VERIFYING",
    "READY_TO_MERGE",
    "MERGED",
    "OBSERVING",
    "CLOSED",
    "BLOCKED",
]

# Secret-shaped values that must never appear in tracked files (NSTR-SEC-001, NSTR-PROJ-005).
SECRET_PATTERNS = {
    "openai/anthropic api key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "nostr secret key": re.compile(r"\bnsec1[02-9ac-hj-np-z]{58}\b"),
    "github token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "aws access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "google api key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "pem private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "hex private key assignment": re.compile(r"(?i)(private_key|nsec|secret_key)\s*[=:]\s*[0-9a-f]{64}\b"),
}


@pytest.fixture(scope="session")
def manifest() -> dict:
    return yaml.safe_load((CREW / "manifest.yaml").read_text())


@pytest.fixture(scope="session")
def agents(manifest) -> dict:
    return manifest["agents"]


@pytest.fixture(scope="session")
def budgets() -> dict:
    return yaml.safe_load((CREW / "budgets.yaml").read_text())


@pytest.fixture(scope="session")
def capabilities() -> dict:
    return yaml.safe_load((CREW / "capabilities.yaml").read_text())["capabilities"]


@pytest.fixture(scope="session")
def lifecycle() -> dict:
    return yaml.safe_load((CREW / "lifecycle.yaml").read_text())


@pytest.fixture(scope="session")
def plugin() -> dict:
    return json.loads((ROOT / ".plugin" / "plugin.json").read_text())


# --- Roster (NSTR-PROJ-003, D-006) -------------------------------------------------


def test_roster_is_exactly_the_seven_canonical_agents(agents):
    assert set(agents) == EXPECTED_AGENTS


def test_every_agent_has_required_fields(agents):
    for name, agent in agents.items():
        missing = REQUIRED_AGENT_FIELDS - set(agent)
        assert not missing, f"{name} missing {sorted(missing)}"
        assert "model" in agent or "model_family" in agent, f"{name} needs model or model_family"


def test_display_names_are_unique(agents):
    names = [a["display_name"] for a in agents.values()]
    assert len(names) == len(set(names))


# --- Identity (NSTR-ID-001, NSTR-ID-004) ---------------------------------------------


def test_public_keys_are_unique_when_set(agents, manifest):
    keys = [a["buzz_pubkey"] for a in agents.values() if a["buzz_pubkey"]]
    owner = manifest.get("owner", {}).get("buzz_pubkey")
    if owner:
        keys.append(owner)
    assert len(keys) == len(set(keys)), "duplicate Buzz public keys"


def test_public_keys_are_hex64_when_set(agents, manifest):
    hex64 = re.compile(r"^[0-9a-f]{64}$")
    candidates = {n: a["buzz_pubkey"] for n, a in agents.items()}
    candidates["owner"] = manifest.get("owner", {}).get("buzz_pubkey")
    for name, key in candidates.items():
        if key is not None:
            assert hex64.match(key), f"{name} buzz_pubkey is not a 64-char hex pubkey"


# --- NIP-05 handles (NOSTROMO-0001 §20, plan §12.5) ---------------------------------

NIP05 = re.compile(r"^[a-z0-9._-]+@[a-z0-9.-]+$")


def test_nip05_handles_follow_agent_name_at_relay_host(agents, manifest):
    host = manifest["relay"]["hostname"]
    for name, agent in agents.items():
        handle = agent["nip05"]
        assert NIP05.match(handle), f"{name}: {handle} is not local@domain"
        local, domain = handle.split("@", 1)
        assert local == name, f"{name}: NIP-05 local part must equal the agent name"
        assert domain == host, f"{name}: NIP-05 domain must match relay hostname {host}"


def test_nip05_handles_are_unique_including_owner(agents, manifest):
    handles = [a["nip05"] for a in agents.values()] + [manifest["owner"]["nip05"]]
    assert len(handles) == len(set(handles))


def test_relay_is_private(manifest):
    assert manifest["relay"]["exposure"] == "private-tailnet"


# --- GitHub identity (NSTR-ID-006, plan §8.7) ----------------------------------------


def test_repo_writing_roles_declare_a_github_identity(agents):
    for name in REPO_WRITING_AGENTS:
        assert agents[name].get("github_identity"), f"{name} needs a GitHub App identity"
        assert agents[name].get("branch_namespace") == f"nostromo/{name}", name


def test_github_identities_are_unique_and_never_the_owner(agents, manifest):
    owner_login = manifest["owner"]["github_login"]
    identities = [a["github_identity"] for a in agents.values() if a.get("github_identity")]
    assert len(identities) == len(set(identities)), "duplicate GitHub identities"
    assert owner_login not in identities, "a crew member must not reuse the owner's GitHub login"


def test_read_only_roles_have_no_github_identity(agents):
    for name in MAC_AGENTS:
        assert not agents[name].get("github_identity"), f"{name} reads a public repo and needs no identity"


def test_repo_writing_templates_carry_github_app_fields():
    wanted = {"GITHUB_APP_ID", "GITHUB_APP_INSTALLATION_ID", "GITHUB_APP_PRIVATE_KEY_FILE"}
    for name in REPO_WRITING_AGENTS:
        keys = set(_assignments((ENV / f"{name}.env.example").read_text()))
        assert wanted <= keys, f"{name}: missing {wanted - keys}"
        assert not any(k in keys for k in ("GH_TOKEN", "GITHUB_TOKEN")), f"{name}: tokens are minted, never stored"


# --- Host and supervisor (NSTR-RUN-001, NSTR-RUN-002, D-007, D-008) -----------------


def test_spark_agents_use_herdr(agents):
    for name in SPARK_AGENTS:
        assert agents[name]["host"] == "spark", name
        assert agents[name]["supervisor"] == "herdr", name


def test_mac_agents_do_not_use_herdr(agents):
    for name in MAC_AGENTS:
        assert agents[name]["host"] == "mac", name
        assert agents[name]["supervisor"] != "herdr", name


# --- Model and harness bindings (NSTR-MOD-001 .. NSTR-MOD-007, D-013) ---------------


def test_local_agents_use_ollama_via_opencode(agents):
    for name in LOCAL_AGENTS:
        assert agents[name]["provider"] == "ollama", name
        assert agents[name]["harness"] == "opencode-acp", name
        assert agents[name]["budget_profile"] == "local", name


def test_ripley_and_parker_use_openai_with_distinct_boundaries(agents):
    for name in ("ripley", "parker"):
        assert agents[name]["provider"] == "openai", name
        assert agents[name]["harness"] == "codex-acp", name
    assert agents["ripley"]["budget_profile"] != agents["parker"]["budget_profile"]
    assert agents["ripley"]["provider_boundary"] != agents["parker"]["provider_boundary"]


def test_dallas_uses_anthropic_independently_of_ripley(agents):
    dallas, ripley = agents["dallas"], agents["ripley"]
    assert dallas["provider"] == "anthropic"
    assert dallas["harness"] == "claude-agent-acp"
    assert dallas["provider"] != ripley["provider"], "NSTR-COL-004 model-family independence"
    assert dallas["harness"] != ripley["harness"]


def test_ash_is_subscription_backed(agents):
    assert agents["ash"]["provider"] == "chatgpt"
    assert agents["ash"]["budget_profile"] == "chatgpt-plus"


def test_lambert_is_zero_incremental(agents):
    assert agents["lambert"]["provider"] == "gemini"
    assert agents["lambert"]["budget_profile"] == "existing-subscription"


# --- Author policy (NSTR-SEC-003, NSTR-ID-005, D-019) --------------------------------


def test_no_agent_responds_to_anyone(agents):
    for name, agent in agents.items():
        assert agent["respond_to"] != "anyone", name


def test_every_agent_uses_allowlist(agents):
    for name, agent in agents.items():
        assert agent["respond_to"] == "allowlist", name


# --- Capability routing (NSTR-COL-003, plan §16.4) -----------------------------------


def test_capability_map_resolves_to_valid_agents(capabilities, agents):
    for capability, agent in capabilities.items():
        assert agent in agents, f"{capability} -> {agent} is not a crew member"
        assert agents[agent]["capability"] == capability, f"{agent} manifest capability disagrees"


def test_capability_map_is_a_bijection(capabilities, agents):
    assert set(capabilities.values()) == set(agents)
    assert set(capabilities) == {a["capability"] for a in agents.values()}


# --- Budgets (NSTR-BUD-001 .. NSTR-BUD-005, D-017) -----------------------------------


def _configured_envelope(budgets) -> int:
    return sum(
        p["amount_usd"]
        for p in budgets["profiles"].values()
        if p["type"] in {"fixed", "provider_hard_limit"}
    )


def test_configured_envelope_is_140_under_150_ceiling(budgets):
    envelope = _configured_envelope(budgets)
    ceiling = budgets["monthly_incremental_ceiling_usd"]
    assert envelope == 140
    assert ceiling == 150
    assert envelope < ceiling


def test_role_caps_match_specification(budgets):
    profiles = budgets["profiles"]
    assert profiles["parker"]["amount_usd"] == 70
    assert profiles["ripley"]["amount_usd"] == 25
    assert profiles["dallas"]["amount_usd"] == 25
    assert profiles["chatgpt-plus"]["amount_usd"] == 20


def test_every_budget_profile_referenced_exists(agents, budgets):
    for name, agent in agents.items():
        assert agent["budget_profile"] in budgets["profiles"], name


def test_hard_limit_profiles_name_their_boundary(budgets, agents):
    for profile_name, profile in budgets["profiles"].items():
        if profile["type"] == "provider_hard_limit":
            assert agents[profile_name]["provider"] == profile["provider"]
            assert agents[profile_name]["provider_boundary"] == profile["boundary"]


# --- Lifecycle (NOSTROMO-0001 §14) ------------------------------------------------------


def test_lifecycle_states_match_specification(lifecycle):
    assert lifecycle["states"] == LIFECYCLE_STATES
    assert lifecycle["initial"] in LIFECYCLE_STATES
    assert set(lifecycle["terminal"]) <= set(LIFECYCLE_STATES)


# --- Persona Pack manifest (D-022) -----------------------------------------------------


def test_plugin_personas_match_roster(plugin, agents):
    listed = {Path(p).name.removesuffix(".persona.md") for p in plugin["personas"]}
    assert listed == set(agents)
    assert plugin["pack_instructions"] == "instructions.md"
    assert (ROOT / plugin["pack_instructions"]).exists()


def test_plugin_defaults_do_not_bind_a_model(plugin):
    # Runtime bindings come from the Nostromo launcher, not pack defaults (D-023).
    assert "model" not in plugin.get("defaults", {})


# --- Environment templates (NSTR-PROJ-005, NSTR-MOD-006, NSTR-BUD-007) ---------------


def _assignments(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
    return out


def test_every_agent_has_an_env_template_with_buzz_key(agents):
    for name in agents:
        path = ENV / f"{name}.env.example"
        assert path.exists(), path
        assert "BUZZ_PRIVATE_KEY" in _assignments(path.read_text()), name


def test_ash_template_defines_no_api_key(agents):
    keys = _assignments((ENV / "ash.env.example").read_text())
    assert "OPENAI_API_KEY" not in keys
    assert "CODEX_API_KEY" not in keys


def test_local_agent_templates_define_no_provider_keys():
    for name in LOCAL_AGENTS:
        keys = _assignments((ENV / f"{name}.env.example").read_text())
        forbidden = {k for k in keys if k.endswith("_API_KEY")}
        assert not forbidden, f"{name}: {forbidden}"


def test_cloud_templates_carry_only_their_own_provider_key():
    expected = {
        "ripley": {"OPENAI_API_KEY"},
        "parker": {"OPENAI_API_KEY"},
        "dallas": {"ANTHROPIC_API_KEY"},
    }
    for name, wanted in expected.items():
        keys = {k for k in _assignments((ENV / f"{name}.env.example").read_text()) if k.endswith("_API_KEY")}
        assert keys == wanted, f"{name}: {keys}"


def test_templates_contain_placeholders_only():
    for path in ENV.glob("*.env.example"):
        for key, value in _assignments(path.read_text()).items():
            is_placeholder = (value.startswith("<") and value.endswith(">")) or value.startswith("wss://<")
            assert is_placeholder, f"{path.name}: {key} does not look like a placeholder"


# --- Secret scan over every tracked file (NSTR-SEC-001, plan §18.3) ---------------------


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return [ROOT / p for p in out.decode().split("\0") if p]


def test_no_secret_shaped_values_in_tracked_files():
    findings = []
    for path in _tracked_files():
        if path.suffix in {".png", ".jpg", ".gif", ".lock"} or not path.is_file():
            continue
        text = path.read_text(errors="ignore")
        for label, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append(f"{path.relative_to(ROOT)}: {label}: {match.group(0)[:12]}...")
    assert not findings, "\n".join(findings)
