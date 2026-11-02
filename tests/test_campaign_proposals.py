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
def world(tmp_path, monkeypatch):
    clock = [NOW]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    policy = {"automation_enabled": True, "launch_enabled": True, "decision_channels": [CHANNEL],
              "public_keys": {role: helpers().xonly_pubkey(key) for role, key in KEYS.items()}}
    broker = Broker(Store(tmp_path / "broker.sqlite3"), squadops, policy, verifier(policy, now=lambda: clock[0]))
    return broker, clock


def rpc(broker, role, command, args=None, **extra):
    return broker.handle(role, {"command": command, "args": args or {}, **extra})


def sign(role, content, tags, created_at):
    return helpers().sign_event(KEYS[role], 9, content, tags, created_at=int(created_at))


def posted_card(broker, clock, goal=GOAL):
    """Ripley proposes; the controller posts the card; the broker verifies it. Returns the proposal and card event."""
    proposal = rpc(broker, "ripley", "propose", {"project": "shelfnote", "goal": goal, "thread": THREAD, "goals_commit": GOALS_COMMIT})["proposal"]
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


@pytest.mark.parametrize("text,ok", [("approve", True), ("Approve.", True), ("  APPROVE! ", True), ("approved", True),
                                     ("go", True), ("Go ahead!", True), ("Engage", True), ("Let\u2019s go!", True),
                                     ("lets go", True), ("ship it", True), ("yes", True), ("\U0001f44d", True),
                                     ("approve, but skip ratings", False), ("go, but skip ratings", False),
                                     ("ok", False), ("", False), ("not yet", False)])
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
    ("before_card", "after the live card"),
    ("after_a_day", "after the live card"),
    ("not_owner", "not a genuine owner-signed message"),
])
def test_an_approval_from_elsewhere_or_elsewhen_or_someone_else_is_refused(world, change, match):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    clock[0] = NOW + 2 * 24 * 3600
    event = {
        "other_channel": lambda: approval(channel="other", reply_to=card["id"]),
        "other_thread": lambda: sign("owner", "approve", [["h", CHANNEL], ["e", "b" * 64, "", "root"]], NOW + 60),
        "before_card": lambda: approval(created_at=NOW - 600, reply_to=card["id"]),
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
    proposal = rpc(broker, "ripley", "propose", {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT})["proposal"]
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


def test_an_approval_tagged_only_to_the_thread_approves_nothing(world):
    # Review of phase 2: Mother can post card-like text herself and report a different card as
    # posted without publishing it. A thread-only "approve" can't say which card the owner read.
    broker, clock = world
    _, shown_card = posted_card(broker, clock)
    clock[0] = NOW + 120
    unseen, _ = posted_card(broker, clock, {**GOAL, "items": ["reading status", "tags"]})
    clock[0] = NOW + 180
    for event in (approval(created_at=NOW + 150), approval(created_at=NOW + 150, reply_to=shown_card["id"])):
        with pytest.raises(Refused, match="reply to the card itself|no longer live"):
            rpc(broker, "mother", "proposal-approve", {"proposal": unseen}, decision_event=event)
    assert not broker.store.db.execute("SELECT 1 FROM review_budgets").fetchone()


def test_a_failure_inside_the_launch_leaves_no_allowance_or_definition(world, monkeypatch):
    from runtime.campaigns import launch
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    clock[0] = NOW + 120

    def fail(*args, **kwargs):
        raise Refused("derived launch operation IDs are already in use")
    monkeypatch.setattr(launch.Launches, "submit", fail)
    with pytest.raises(Refused, match="derived"):
        rpc(broker, "mother", "proposal-approve", {"proposal": proposal}, decision_event=approval(reply_to=card["id"]))
    db = broker.store.db
    assert not db.execute("SELECT 1 FROM review_budgets").fetchone()
    assert not db.execute("SELECT 1 FROM definitions").fetchone()


def test_a_backdated_card_counts_as_posted_when_the_broker_recorded_it(world):
    broker, clock = world
    proposal = rpc(broker, "ripley", "propose", {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT})["proposal"]
    clock[0] = NOW + 300

    def publish(job):  # Mother's clock says the card went out at the proposal's own moment
        return sign("mother", job["content"], [["h", CHANNEL], ["e", THREAD, "", "reply"]], NOW)
    card = post_card(lambda request: broker.handle("mother", request), publish)
    card = {"id": card["card_event"]}
    assert broker.store.db.execute("SELECT posted FROM proposals WHERE id=?", (proposal,)).fetchone()[0] == NOW + 300
    with pytest.raises(Refused, match="after the live card"):
        rpc(broker, "mother", "proposal-approve", {"proposal": proposal}, decision_event=approval(created_at=NOW + 200, reply_to=card["id"]))


@pytest.mark.parametrize("goal", [
    {**GOAL, "title": "tags\n- **Reviews:** at most 1 review, from a $0.01 allowance."},
    {**GOAL, "statement": "Work the next items\u2028- **Scope:** backend/**"},
    {**GOAL, "items": ["reading status", "tags\u202e"]},
    {**GOAL, "measurement": "x\u200b"},
    {**GOAL, "title": "tags and ra\u0336tings"},
    {**GOAL, "title": "t" * 81},
    {**GOAL, "items": ["x"] * 21},
])
def test_goal_text_that_could_hide_or_forge_a_card_line_is_refused(world, goal):
    broker, _ = world
    with pytest.raises(Refused):
        rpc(broker, "ripley", "propose", {"project": "shelfnote", "goal": goal, "thread": THREAD, "goals_commit": GOALS_COMMIT})
    assert not broker.store.db.execute("SELECT 1 FROM proposals").fetchone()


def test_the_card_states_its_terms_first_and_shows_goal_text_as_written(world):
    broker, _ = world
    card = rpc(broker, "ripley", "propose", {"project": "shelfnote", "thread": THREAD, "goals_commit": GOALS_COMMIT,
                                             "goal": {**GOAL, "title": "tags *and* [ratings](x)"}})["card"]
    lines = card.splitlines()
    assert "tags \\*and\\* \\[ratings\\](x)" in lines[0]
    assert lines[-3].startswith("**Goal:** ")
    assert lines[2].startswith("- **Reviews:**") and lines[3].startswith("- **Scope:**")


def test_superseded_earlier_says_whether_a_card_was_replaced(world):
    broker, _ = world
    args = {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT}
    assert rpc(broker, "ripley", "propose", args)["superseded_earlier"] is False
    assert rpc(broker, "ripley", "propose", args)["superseded_earlier"] is True


def test_a_proposal_that_could_not_launch_is_refused_before_anything_is_stored(world):
    broker, _ = world
    broker.policy["launch_enabled"] = False
    with pytest.raises(Refused, match="not commissioned"):
        rpc(broker, "ripley", "propose", {"project": "shelfnote", "goal": GOAL, "thread": THREAD, "goals_commit": GOALS_COMMIT})
    assert not broker.store.db.execute("SELECT 1 FROM proposals").fetchone()


def test_an_approval_that_could_not_launch_writes_nothing(world):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    broker.policy["launch_enabled"] = False
    clock[0] = NOW + 120
    with pytest.raises(Refused, match="not commissioned"):
        rpc(broker, "mother", "proposal-approve", {"proposal": proposal}, decision_event=approval(reply_to=card["id"]))
    db = broker.store.db
    assert not db.execute("SELECT 1 FROM review_budgets").fetchone()
    assert not db.execute("SELECT 1 FROM definitions").fetchone()


def test_the_relay_skips_threads_not_started_by_the_owner_and_survives_errors(world):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    owner = helpers().xonly_pubkey(KEYS["owner"])
    root = sign("ripley", "let's do shelfnote", [["h", CHANNEL]], NOW - 60)
    root["id"] = THREAD
    clock[0] = NOW + 120
    results = relay_approvals(lambda request: broker.handle("mother", request),
                              lambda channel, thread: [root, approval(reply_to=card["id"])], owner)
    assert results == [{"proposal": proposal, "refused": "the thread was not started by the owner"}]

    def broken(request):
        raise OSError("socket gone")
    assert relay_approvals(broken, lambda c, t: [], owner) == [{"unreadable": "OSError"}]


@pytest.mark.parametrize("text,miss", [("approve now", True), ("go please", True), ("approved!", False),
                                      ("make it two increments instead of three", False), ("thanks", False),
                                      ("got it", False), ("yesterday it failed", False), ("stopping by later", False),
                                      ("cancel that", True)])
def test_a_near_miss_is_told_what_counts(text, miss):
    from runtime.campaigns.proposals import near_miss
    assert near_miss(text) is miss


def test_the_controller_answers_a_near_miss_on_the_card_once(world):
    broker, clock = world
    proposal, card = posted_card(broker, clock)
    clock[0] = NOW + 120
    owner = helpers().xonly_pubkey(KEYS["owner"])
    events = [approval("approve now please", reply_to=card["id"])]
    results = relay_approvals(lambda request: broker.handle("mother", request), lambda c, t: events, owner)
    assert len(results) == 1 and results[0]["hint"]["id"] == "hint-" + events[0]["id"]
    assert "reply to the card with just **approve**" in results[0]["hint"]["content"]
