"""Drafting a campaign from a plain-language goal: the registry and presets build the definition."""
import json
import time

import pytest

from runtime.campaigns.core import Broker, Refused, Store
from runtime.campaigns.decisions import verifier
from runtime.campaigns.drafting import PRESETS, draft, render_card

NOW = 1793548800.0  # 2026-11-01 16:00 UTC, 11:00 am ET
THREAD = "a" * 64


GOALS_COMMIT = "ae9ad47" + "0" * 33
GOALS_FILE = {"path": "docs/goals.md", "commit": GOALS_COMMIT, "content": "# Goals\n\n1. Readers can find a book.\n"}


def squadops(principal, method, path, body, *, query=None):
    """SquadOps' read of the product's managed clone, at its integrated commit. Like the real client,
    it refuses a query smuggled into the path."""
    assert (principal, method, body) == ("read", "GET", None) and "?" not in path
    if path == "/api/v1/projects/prj-shelfnote/source-file" and query == {"path": "docs/goals.md"}:
        return dict(GOALS_FILE)
    raise RuntimeError("404")


@pytest.fixture
def broker(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: NOW)
    policy = {"automation_enabled": True, "decision_channels": ["60cf6624-62d1-4c37-9522-f6dbf884fd25"], "public_keys": {}}
    return Broker(Store(tmp_path / "broker.sqlite3"), squadops, policy, verifier(policy, now=lambda: NOW))


GOAL = {"title": "reading status, tags and ratings", "statement": "Work the next items in docs/goals.md",
        "items": ["reading status", "tags", "ratings"]}


def test_a_goal_becomes_a_valid_definition_from_the_registry(broker):
    result = draft(broker, {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT}, NOW)
    definition = result["approval"]["definition"]
    assert definition["project_id"] == "prj-shelfnote"
    # Criterion files sit beside the product's tests (squad-ops #2859); a root one is out of scope.
    assert definition["objective"]["allowed_scope"] == ["backend/**", "tests/**"]
    assert definition["objective"]["target_accepted_increments"] == 3, "the size follows the goal"
    assert definition["policy"]["calibration_profile"] == "campaign-increment-source"
    assert definition["crew"]["paid_dispatches"] == 16 == result["allowance"]["max_dispatches"]
    assert result["allowance"]["cap_microusd"] <= 25000000
    assert result["approval"]["thread"] == THREAD
    assert broker.store.db.execute("SELECT count(*) FROM definitions").fetchone()[0] == 0, "stores nothing"


@pytest.mark.parametrize("size", sorted(PRESETS))
def test_every_preset_fits_the_allowance_ceiling(broker, size):
    goal = {**GOAL, "items": [f"item {n}" for n in range(12)]}
    result = draft(broker, {"project": "shelfnote", "goal": goal, "thread": THREAD, "goals_commit": GOALS_COMMIT, "size": size}, NOW)
    increments, hours = PRESETS[size]
    assert result["approval"]["definition"]["objective"]["target_accepted_increments"] == increments
    assert result["allowance"]["cap_microusd"] <= 25000000 and result["allowance"]["max_dispatches"] <= 60
    assert result["approval"]["definition"]["policy"]["max_elapsed_s"] == hours * 3600


def test_the_card_reads_as_a_proposal_without_ids(broker):
    goal = {**GOAL, "items": ["a", "b", "c", "d"]}
    card = draft(broker, {"project": "shelfnote", "goal": goal, "thread": THREAD, "goals_commit": GOALS_COMMIT, "size": "small"}, NOW)["card"]
    assert card.startswith("**ShelfNote campaign 1: reading status, tags and ratings**")
    assert "Reply **approve** to this card to launch" in card and "Left for a later campaign:** d." in card
    assert "crew-shelfnote" not in card and THREAD not in card and "{" not in card
    assert "Approve it by 11:00 am ET, Mon Nov 2" in card
    assert "- **Accepted when:** its own tests pass on the product's runner" in card


def test_names_never_collide_with_an_earlier_definition_or_allowance(broker):
    first = draft(broker, {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT}, NOW)["approval"]["name"]
    broker.store.db.execute("INSERT INTO review_budgets VALUES(?,?)", (first, "{}"))
    broker.store.save()
    second = draft(broker, {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT}, NOW)["approval"]["name"]
    assert first == "crew-shelfnote-20261101-1" and second == "crew-shelfnote-20261101-2"


@pytest.mark.parametrize("args,match", [
    ({"project": "nonesuch", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT}, "not in the project registry"),
    ({"project": "../crew/manifest", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT}, "registry name"),
    ({"project": "shelfnote", "goal": {"title": "", "statement": "x"}, "thread": THREAD, "goals_commit": GOALS_COMMIT}, "title is required"),
    ({"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT, "size": "huge"}, "small, medium or large"),
    ({"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT, "hours": 12}, "between 1 and 8"),
])
def test_bad_requests_are_refused_in_words(broker, args, match):
    with pytest.raises(Refused, match=match):
        draft(broker, args, NOW)


def test_only_mother_ripley_or_the_owner_can_draft(broker):
    request = {"command": "draft", "args": {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT}}
    assert "card" in broker.handle("mother", request)
    with pytest.raises(Refused, match="belongs to Mother, Ripley or the owner"):
        broker.handle("parker", request)


def test_the_goals_are_read_live_and_the_card_says_which_commit(broker):
    assert rpc_goals(broker) == GOALS_FILE
    card = draft(broker, {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT}, NOW)["card"]
    assert "- **Goals:** from docs/goals.md at ae9ad47." in card


def test_unreadable_goals_refuse_the_draft_with_no_fallback(broker, monkeypatch):
    # 2026-11-01: every draft rebuilt the list from older campaigns, and a stale list launched.
    def down(*args, **kwargs):
        raise RuntimeError("404")
    monkeypatch.setattr(broker, "api", down)
    with pytest.raises(Refused, match="couldn't read ShelfNote's goals .* never draft from an older list"):
        draft(broker, {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT}, NOW)


def test_goals_that_changed_since_they_were_read_refuse_the_draft(broker):
    with pytest.raises(Refused, match="has changed since it was read"):
        draft(broker, {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": "b" * 40}, NOW)


def test_a_malformed_goals_answer_is_unreadable(broker, monkeypatch):
    monkeypatch.setattr(broker, "api", lambda *a, **k: {"path": "docs/goals.md", "content": "x"})  # no commit
    with pytest.raises(Refused, match="couldn't read"):
        rpc_goals(broker)


def rpc_goals(broker):
    return broker.handle("ripley", {"command": "goals", "args": {"project": "shelfnote"}})


def test_the_crew_can_read_which_squadops_revision_is_live(broker):
    from types import SimpleNamespace
    broker.api = SimpleNamespace(agents=lambda: [
        {"agent_id": "neo", "revision": "1068c094", "deployed_revision": "1068c094", "revision_matches_deploy": True},
        {"agent_id": "nat", "revision": "1068c094", "deployed_revision": "1068c094", "revision_matches_deploy": True}])
    result = broker.handle("ripley", {"command": "squadops-deploy", "args": {}})
    assert result["revision"] == "1068c094" and result["all_match_deploy"] is True
    assert "runtime-API-only change isn't visible" in result["covers"]
