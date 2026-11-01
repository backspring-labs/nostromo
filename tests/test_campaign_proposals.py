"""Approval by reply: the owner's one signed word approves the live card, and nothing else does."""
import time

import pytest

from runtime.campaigns.core import Broker, Refused, Store
from runtime.campaigns.decisions import helpers, verifier
from runtime.campaigns.launch_worker import post_card, relay_approvals
from runtime.campaigns.proposals import unqualified_approval

NOW = 1793548800.0
CHANNEL = "60cf6624-62d1-4c37-9522-f6dbf884fd25"
THREAD = "a" * 64
KEYS = {"owner": "0" * 63 + "3", "mother": "0" * 63 + "4", "ripley": "0" * 63 + "1"}
GOAL = {"title": "reading status, tags and ratings", "statement": "Work the next items in docs/goals.md",
        "items": ["reading status", "tags", "ratings"]}


@pytest.fixture
def world(tmp_path, monkeypatch):
    clock = [NOW]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    policy = {"automation_enabled": True, "launch_enabled": True, "decision_channels": [CHANNEL],
              "public_keys": {role: helpers().xonly_pubkey(key) for role, key in KEYS.items()}}
    broker = Broker(Store(tmp_path / "broker.sqlite3"), None, policy, verifier(policy, now=lambda: clock[0]))
    return broker, clock


def rpc(broker, role, command, args=None, **extra):
    return broker.handle(role, {"command": command, "args": args or {}, **extra})


def sign(role, content, tags, created_at):
    return helpers().sign_event(KEYS[role], 9, content, tags, created_at=int(created_at))


def posted_card(broker, clock, goal=GOAL):
    """Ripley proposes; the controller posts the card; the broker verifies it. Returns the proposal and card event."""
    proposal = rpc(broker, "ripley", "propose", {"project": "shelfnote", "goal": goal, "thread": THREAD})["proposal"]
    events = {}

    def publish(job):
        events["card"] = sign("mother", job["content"], [["h", CHANNEL], ["e", THREAD, "", "reply"],
                              ["p", helpers().xonly_pubkey(KEYS["owner"])]], clock[0])
        return events["card"]
    post_card(lambda request: broker.handle("mother", request), publish)
    return proposal, events["card"]


def approval(content="approve", *, reply_to=None, channel=CHANNEL, created_at=NOW + 60, role="owner"):
    tags = [["h", channel], ["e", THREAD, "", "root"]] + ([["e", reply_to, "", "reply"]] if reply_to else [])
    return sign(role, content, tags, created_at)


def test_the_owners_approve_creates_the_allowance_definition_and_launch(world):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    clock[0] = NOW + 120
    result = rpc(broker, "mother", "proposal-approve", {"proposal": proposal}, decision_event=approval(reply_to=card["id"]))
    assert result == {"approved": True, "launch": "launch-" + proposal}
    db = broker.store.db
    assert db.execute("SELECT 1 FROM review_budgets WHERE name=?", (proposal,)).fetchone()
    assert db.execute("SELECT 1 FROM definitions WHERE name=?", (proposal,)).fetchone()
    assert db.execute("SELECT state FROM launch_workflows WHERE id=?", ("launch-" + proposal,)).fetchone()[0] == "queued"


@pytest.mark.parametrize("text,ok", [("approve", True), ("Approve.", True), ("  APPROVE! ", True),
                                     ("approve, but skip ratings", False), ("approved", False), ("ok", False), ("", False)])
def test_only_an_unqualified_approve_counts(text, ok):
    assert unqualified_approval(text) is ok


def test_a_qualified_approval_launches_nothing(world):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    clock[0] = NOW + 120
    with pytest.raises(Refused, match="unqualified"):
        rpc(broker, "mother", "proposal-approve", {"proposal": proposal},
            decision_event=approval("approve, but skip ratings", reply_to=card["id"]))
    assert not broker.store.db.execute("SELECT 1 FROM launch_workflows").fetchone()


@pytest.mark.parametrize("change,match", [
    ("other_channel", "not in the proposal's channel"),
    ("other_thread", "not in the proposal's thread"),
    ("before_card", "within a day"),
    ("after_a_day", "within a day"),
    ("not_owner", "not a genuine owner-signed message"),
])
def test_an_approval_from_elsewhere_or_elsewhen_or_someone_else_is_refused(world, change, match):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    clock[0] = NOW + 2 * 24 * 3600
    event = {
        "other_channel": lambda: approval(channel="other", reply_to=card["id"]),
        "other_thread": lambda: sign("owner", "approve", [["h", CHANNEL], ["e", "b" * 64, "", "root"]], NOW + 60),
        "before_card": lambda: approval(created_at=NOW - 600),
        "after_a_day": lambda: approval(created_at=NOW + 25 * 3600, reply_to=card["id"]),
        "not_owner": lambda: approval(role="ripley", reply_to=card["id"]),
    }[change]()
    with pytest.raises(Refused, match=match):
        rpc(broker, "mother", "proposal-approve", {"proposal": proposal}, decision_event=event)


def test_a_superseded_card_can_no_longer_be_approved(world):
    broker, clock = world
    first, first_card = posted_card(broker, clock)
    clock[0] = NOW + 300
    second, second_card = posted_card(broker, clock, {**GOAL, "items": ["reading status", "tags"]})
    clock[0] = NOW + 400
    with pytest.raises(Refused, match="only the live card"):
        rpc(broker, "mother", "proposal-approve", {"proposal": first}, decision_event=approval(reply_to=first_card["id"]))
    with pytest.raises(Refused, match="no longer live"):
        rpc(broker, "mother", "proposal-approve", {"proposal": second},
            decision_event=approval(reply_to=first_card["id"], created_at=NOW + 350))
    assert rpc(broker, "mother", "proposal-approve", {"proposal": second},
               decision_event=approval(reply_to=second_card["id"], created_at=NOW + 350))["approved"]


def test_one_approval_approves_once(world):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    clock[0] = NOW + 120
    event = approval(reply_to=card["id"])
    rpc(broker, "mother", "proposal-approve", {"proposal": proposal}, decision_event=event)
    assert rpc(broker, "mother", "proposal-approve", {"proposal": proposal}, decision_event=event)["replayed"] is True
    with pytest.raises(Refused, match="already approved"):
        rpc(broker, "mother", "proposal-approve", {"proposal": proposal}, decision_event=approval(created_at=NOW + 90))


def test_only_mothers_controller_posts_cards_or_relays_approvals(world):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    with pytest.raises(Refused, match="Mother's controller"):
        rpc(broker, "ripley", "proposal-approve", {"proposal": proposal}, decision_event=approval(reply_to=card["id"]))
    with pytest.raises(Refused, match="Mother's controller"):
        rpc(broker, "owner", "proposal-card-claim")


def test_a_card_that_differs_from_the_stored_one_is_refused(world):
    broker, clock = world
    proposal = rpc(broker, "ripley", "propose", {"project": "shelfnote", "goal": GOAL, "thread": THREAD})["proposal"]
    with pytest.raises(Refused, match="mismatched or invalid mother message"):
        post_card(lambda request: broker.handle("mother", request),
                  lambda job: sign("mother", job["content"] + " (and more)", [["h", CHANNEL], ["e", THREAD, "", "reply"]], NOW))


def test_the_controller_relays_only_the_owners_approvals(world):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    clock[0] = NOW + 120
    thread = [card, approval("tell me more", reply_to=card["id"]), sign("ripley", "approve", [["h", CHANNEL]], NOW + 70),
              approval(reply_to=card["id"])]
    results = relay_approvals(lambda request: broker.handle("mother", request), lambda channel, t: thread,
                              helpers().xonly_pubkey(KEYS["owner"]))
    assert results == [{"approved": True, "launch": "launch-" + proposal}]
