"""Authorization and live-caller-shaped gate paths, with an external API fixture."""
import copy
import json
import sqlite3
import time
from types import SimpleNamespace

import pytest

from runtime.campaigns.core import Broker, Refused, Store, canonical, digest
from runtime.campaigns.decisions import helpers, verifier
from runtime.campaigns.watch import Watcher, report


def test_large_closing_record_keeps_runtime_references_and_bounded_buzz_content():
    packet = {"campaign": {"campaign_id": "cmp_test", "project_id": "group_run", "state": "completed"},
              "ledger": {"large": "x" * 100000}}
    body = report(packet, {"artifact_digest": "fixture"})
    assert len(body.encode()) < 20000
    assert "SHA-256" in body and "campaignctl status" in body
    assert "Pending" in body and "cmp_test" in body


DEFINITION = {
    "project_id": "group_run",
    "objective": {"statement": "commission one local calibration", "allowed_scope": ["backend/**", "frontend/**"],
                  "measurement": "one calibration closes", "target_accepted_increments": 1},
    "policy": {"max_cycles": 1, "max_elapsed_s": 3600, "budget_tokens": 1000000},
    "crew": {"require_dallas": True, "paid_dispatches": 0},
}


class World:
    def __init__(self):
        self.calls = []
        self.campaign = {"campaign_id": "cmp_test", "project_id": "group_run", "state": "awaiting_ruling",
                         "policy": {"lease_expiry_s": 600}}

    def __call__(self, principal, method, path, body):
        self.calls.append((principal, method, path, copy.deepcopy(body)))
        if path == "/api/v1/campaigns" and method == "POST":
            return {"campaign": {**self.campaign, "campaign_id": body["campaign_id"]}}
        if path.endswith("/gates/progress_plan_review") or path.endswith("/gates/progress_increment_ruling"):
            return {"run_id": "run_test", "gate_decisions": [body]}
        if path.endswith("/runs/run_test"):
            return {"run_id": "run_test", "cycle_id": "cyc_test", "gate_decisions": []}
        if path.endswith("/cycles/cyc_test"):
            return {"cycle_id": "cyc_test", "campaign_id": "cmp_test"}
        return copy.deepcopy(self.campaign)


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / "broker.sqlite3")
    api = World()
    proofs = []

    def verify(event, signer, prefix, expected):
        if event != {"signed_by": signer, "payload": expected}:
            raise Refused("wrong decision")
        proofs.append((signer, prefix, expected))

    broker = Broker(store, api, {}, verify)
    broker.handle("owner", {"command": "approve-definition", "args": {
        "name": "calibration-1", "definition": copy.deepcopy(DEFINITION), "channel": "channel", "thread": "thread"}})
    store.db.execute("INSERT INTO campaigns VALUES(?,?,?,?,?)", ("cmp_test", "calibration-1", "channel", "thread", "mother"))
    store.save()
    return broker, api, proofs


def request(command, **args):
    return {"command": command, "args": args, "request_id": "request-1"}


@pytest.mark.parametrize("caller,command", [("ripley", "start"), ("dallas", "start"), ("brett", "pause"),
    ("mother", "plan"), ("mother", "increment"), ("parker", "increment"), ("watcher", "abort")])
def test_wrong_role_never_reaches_an_api_write(setup, caller, command):
    broker, api, _ = setup
    with pytest.raises(Refused):
        broker.handle(caller, request(command, campaign="cmp_test", reason="test"))
    assert not any(call[1] == "POST" for call in api.calls)


def test_unapproved_definition_cannot_be_created(setup):
    broker, api, _ = setup
    with pytest.raises(Refused, match="not owner-approved"):
        broker.handle("mother", request("create", definition="unapproved", reason="test"))
    assert api.calls == []


def test_owner_approval_is_immutable_and_does_not_expand_a_running_envelope(setup):
    broker, _, _ = setup
    args = {"name": "calibration-1", "definition": copy.deepcopy(DEFINITION), "channel": "channel", "thread": "thread"}
    args["definition"]["policy"]["budget_tokens"] *= 2
    with pytest.raises(Refused, match="immutable"):
        broker.handle("owner", {"command": "approve-definition", "args": args})


def test_mother_creates_from_approved_bytes_and_replays_without_a_second_api_write(setup):
    broker, api, _ = setup
    req = request("create", definition="calibration-1", reason="commission")
    first = broker.handle("mother", req)
    second = broker.handle("mother", req)
    assert first["result"] == second["result"]
    assert second["replayed"] is True
    assert len(api.calls) == 1
    principal, _, _, body = api.calls[0]
    assert principal == "control"
    assert body["policy"] == DEFINITION["policy"]
    assert "crew" not in body
    assert body["definition"]["sha256"] == digest(DEFINITION)
    with pytest.raises(Refused, match="different content"):
        broker.handle("mother", request("create", definition="calibration-1", reason="changed"))


def gate_request(command="plan"):
    args = {"campaign": "cmp_test", "cycle": "cyc_test", "run": "run_test", "decision": "approved", "notes": "The PRD answers this question."}
    if command == "increment":
        args["binding"] = {"proposal_id": "prop_test", "version": 1, "content_hash": "a" * 64, "accepted_tree": "tree_test"}
    req = request(command, **args)
    req["decision_event"] = {"signed_by": "ripley", "payload": copy.deepcopy(req)}
    req["review_event"] = {"signed_by": "dallas", "payload": {"campaign": "cmp_test", "cycle": "cyc_test", "run": "run_test",
        "decision_sha256": digest({"command": command, "args": args}), "blocking": False}}
    return req


@pytest.mark.parametrize("command", ["plan", "increment"])
def test_ripley_submits_the_bound_gate_as_an_agent_after_independent_review(setup, command):
    broker, api, proofs = setup
    broker.handle("ripley", gate_request(command))
    principal, method, path, body = api.calls[-1]
    assert principal == "review" and method == "POST"
    assert path.endswith("/gates/progress_" + ("plan_review" if command == "plan" else "increment_ruling"))
    assert body["decided_by_kind"] == "agent"
    assert [p[0] for p in proofs] == ["ripley", "dallas"]
    assert ("idempotency_key" in body) == (command == "increment")


def test_gate_quiesces_local_roles_before_releasing_lease_and_submitting(setup):
    broker, api, _ = setup
    sequence = []
    original = broker.api
    def with_lease(principal, method, path, body):
        sequence.append((method, path))
        if path.endswith("/lease"):
            return {"supervisor_holds": True, "held_by": "operations-subject"}
        if path.endswith("/lease/release"):
            return {"released": True}
        return original(principal, method, path, body)
    broker.api = with_lease
    broker.policy["control_principal"] = "operations-subject"
    broker.window = SimpleNamespace(close=lambda: sequence.append(("LOCAL", "stopped")))
    broker.handle("ripley", gate_request("increment"))
    stop = sequence.index(("LOCAL", "stopped"))
    release = next(i for i, item in enumerate(sequence) if item[1].endswith("lease/release"))
    gate = next(i for i, item in enumerate(sequence) if "/gates/" in item[1])
    assert stop < release < gate


def test_failed_quiescence_prevents_gate_write_and_leaves_receipt_unresolved(setup):
    broker, api, _ = setup
    def fail():
        raise Refused("local stop failed")
    broker.window = SimpleNamespace(close=fail)
    with pytest.raises(Refused, match="local stop failed"):
        broker.handle("ripley", gate_request())
    assert not any(c[1] == "POST" for c in api.calls)
    with pytest.raises(Refused, match="unresolved"):
        broker.handle("ripley", gate_request())


@pytest.mark.parametrize("change", ["notes", "run", "review"])
def test_changed_gate_or_unrelated_review_cannot_be_used(setup, change):
    broker, api, _ = setup
    req = gate_request()
    if change == "review":
        req["review_event"]["payload"]["blocking"] = True
    else:
        req["args"][change] = "different"
    with pytest.raises(Refused):
        broker.handle("ripley", req)
    assert not any(c[1] == "POST" for c in api.calls)


def test_cycle_membership_is_checked_before_a_gate_write(setup, monkeypatch):
    broker, api, _ = setup
    original = api.__class__.__call__
    def changed(self, principal, method, path, body):
        result = original(self, principal, method, path, body)
        if path.endswith("/cycles/cyc_test"):
            result["campaign_id"] = "cmp_elsewhere"
        return result
    monkeypatch.setattr(World, "__call__", changed)
    with pytest.raises(Refused, match="not part"):
        broker.handle("ripley", gate_request())
    assert not any(c[1] == "POST" for c in api.calls)


def test_unresolved_transport_write_is_not_repeated(setup):
    broker, api, _ = setup
    def broken(*args):
        if args[1] == "POST":
            raise OSError("connection lost after submission")
        return api(*args)
    broker.api = broken
    req = request("start", campaign="cmp_test", reason="test")
    with pytest.raises(OSError):
        broker.handle("mother", req)
    with pytest.raises(Refused, match="unresolved"):
        broker.handle("mother", req)


@pytest.mark.parametrize("command,args", [("raw", {}), ("start", {"campaign": "../admin", "reason": "x"}),
    ("resume", {"campaign": "cmp_test", "reason": "x", "action": "repair"}),
    ("abort", {"campaign": "cmp_test", "reason": "x", "url": "http://elsewhere"})])
def test_no_passthrough_or_owner_override(setup, command, args):
    broker, api, _ = setup
    with pytest.raises(Refused):
        broker.handle("mother", request(command, **args))
    assert not any(c[1] == "POST" for c in api.calls)


def test_real_bip340_decision_and_tampering_controls():
    crypto = helpers()
    key = "0" * 63 + "1"
    policy = {"public_keys": {"ripley": crypto.xonly_pubkey(key)}, "decision_channels": ["channel"], "decision_ttl_s": 60}
    payload = {"command": "plan", "args": {"decision": "approved"}, "request_id": "one"}
    event = crypto.sign_event(key, 9, "campaign-decision: " + canonical(payload), [["h", "channel"]], created_at=100)
    verify = verifier(policy, now=lambda: 110)
    assert verify(event, "ripley", "campaign-decision", payload) == event["id"]
    for field, value in (("content", event["content"] + "x"), ("created_at", 1), ("tags", [["h", "other"]]), ("sig", "0" * 128)):
        changed = {**event, field: value}
        with pytest.raises(Refused):
            verify(changed, "ripley", "campaign-decision", payload)


def test_watcher_posts_once_and_survives_restart_without_paid_dispatch():
    db = sqlite3.connect(":memory:")
    notices, posts, requests = [], [], []
    item = {"id": "cmp_test", "channel": "channel", "thread": "thread"}
    packet = {"campaign": {"campaign_id": "cmp_test", "project_id": "group_run", "state": "completed", "outcome": "exhausted"}, "ledger": [], "escalations": []}
    def rpc(req):
        requests.append(req)
        return [item] if req["command"] == "tracked" else {"identity": "pkg_test"} if req["command"] == "package" else packet
    def post(cid, text):
        posts.append((cid, text))
        return "30023:pubkey:closing-cmp_test"
    for _ in range(2):
        Watcher(db, rpc, lambda item, text: notices.append(text), post).poll()
    assert len(posts) == len(notices) == 1
    assert "Crew analysis" in posts[0][1] and "Pending" in posts[0][1]
    assert not any("@" in n for n in notices)
    assert {r["command"] for r in requests} == {"tracked", "packet", "package"}


def test_watcher_calls_an_unreadable_source_unreadable_once():
    db = sqlite3.connect(":memory:")
    notices = []
    def rpc(req):
        if req["command"] == "tracked":
            return [{"id": "cmp_test"}]
        raise OSError("unavailable")
    watcher = Watcher(db, rpc, lambda item, text: notices.append(text), lambda *_: None)
    for _ in range(4):
        watcher.poll()
    assert len(notices) == 1 and "UNREADABLE" in notices[0]
