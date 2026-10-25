"""Exercise real signed role handoffs and failure boundaries without provider/network calls."""
import copy
import hashlib
import json
import time

import pytest

from runtime.campaigns.automation import Automation
from runtime.campaigns.core import Broker, Refused, Store, canonical
from runtime.campaigns.decisions import helpers, verifier
from runtime.campaigns.evidence import Evidence, waiting_gates
from runtime.campaigns.review import RESERVATION_MICROUSD, attestations, body, decode, timestamp
from runtime.campaigns.worker import run
from runtime.campaigns.usage import observed

NOW = timestamp("2026-10-25T00:00:00Z")
KEYS = {"ripley": "0" * 63 + "1", "dallas": "0" * 63 + "2"}


class Runtime:
    def __init__(self):
        self.posts = []
        self.campaign = {"campaign_id": "cmp_test", "project_id": "group_run", "state": "awaiting_ruling"}
        self.log = [{"entry_id": "ctl_launched", "operation": "mark_launched", "outcome": "applied",
                     "binding": {"cycle_id": "cyc_test"}}]
        self.ledger = [{"cycle_id": "cyc_test", "run_id": "run_test", "proposal_id": "prop_test", "version": 1,
                        "content_hash": "a" * 64, "baseline_tree": "b" * 64, "ruling": None}]
        self.cycle = {"cycle_id": "cyc_test", "project_id": "group_run", "campaign_id": "cmp_test",
                      "status": "gate_awaiting",
                      "applied_defaults": {"workload_sequence": [{"type": "proposal", "gate": "progress_increment_ruling"}]},
                      "runs": [{"run_id": "run_test", "cycle_id": "cyc_test", "run_number": 1, "status": "completed",
                                "finished_at": "2026-10-24T23:00:00Z", "workload_type": "proposal", "gate_decisions": []}]}
        self.raw = b'{"proposal_id":"prop_test"}'
        self.meta = {"artifact_id": "art_test", "project_id": "group_run", "cycle_id": "cyc_test", "run_id": "run_test",
                     "artifact_type": "change_request", "filename": "change_request.yaml", "size_bytes": len(self.raw),
                     "content_hash": hashlib.sha256(self.raw).hexdigest()}

    def __call__(self, principal, method, path, payload):
        if method == "POST":
            self.posts.append((principal, path, copy.deepcopy(payload)))
            if "/gates/" in path:
                self.cycle["runs"][0]["gate_decisions"].append({"gate_name": "progress_increment_ruling", **payload})
                self.campaign["state"] = "executing"
            elif path.endswith("/pause") or path.endswith("/abort"):
                self.campaign["state"] = "completed" if path.endswith("/abort") else "paused"
                if path.endswith("/abort"):
                    self.cycle["status"] = "cancelled"
                self.log.append({"entry_id": "ctl_stop", "operation": path.rsplit("/", 1)[-1], "outcome": "applied",
                                 "binding": {}, "idempotency_key": payload["idempotency_key"], "prior_state": "awaiting_ruling"})
            return {"campaign": copy.deepcopy(self.campaign)}
        if path.endswith("/control-log"): return copy.deepcopy(self.log)
        if path.endswith("/ledger"): return copy.deepcopy(self.ledger)
        if path.endswith("/escalations"): return []
        if path.endswith("/cycles/cyc_test"): return copy.deepcopy(self.cycle)
        if path.endswith("/runs/run_test"): return copy.deepcopy(self.cycle["runs"][0])
        if path.endswith("/artifacts/art_test"): return copy.deepcopy(self.meta)
        if path.endswith("/lease"): return None
        if path == "/api/v1/campaigns/cmp_test": return copy.deepcopy(self.campaign)
        raise AssertionError(path)

    def request(self, principal, method, path, payload, **kwargs):
        if path.endswith("/download"): return self.raw
        assert path.endswith("/artifacts")
        return json.dumps([self.meta] if kwargs["page"][0] == 0 else []).encode()


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: NOW)
    policy = {"automation_enabled": True, "review_personas": {}, "decision_channels": ["channel"],
              "public_keys": {r: helpers().xonly_pubkey(k) for r, k in KEYS.items()}}
    for role in KEYS:
        path = tmp_path / (role + ".md"); path.write_text(role + " role")
        policy["review_personas"][role] = str(path)
    api = Runtime()
    store = Store(tmp_path / "broker.sqlite3")
    broker = Broker(store, api, policy, verifier(policy, now=lambda: time.time()))
    broker.handle("owner", {"command": "approve-budget", "args": {"name": "pilot", "cap_microusd": 5000000,
                  "max_dispatches": 8, "expires_at": "2026-10-26T12:00:00Z"}})
    spec = {"project_id": "group_run", "objective": {"allowed_scope": ["backend/**", "frontend/**"], "target_accepted_increments": 1},
            "policy": {"max_cycles": 2, "max_elapsed_s": 7200, "budget_tokens": 1000000},
            "crew": {"paid_dispatches": 8, "require_dallas": True,
                     "automation": {"budget": "pilot", "not_after": "2026-10-25T03:00:00Z"}}}
    broker.approve({"name": "pilot-test", "definition": spec, "channel": "channel", "thread": "thread"})
    store.db.execute("INSERT INTO campaigns VALUES(?,?,?,?,?)", ("cmp_test", "pilot-test", "channel", "thread", "mother"))
    store.save()
    Automation(broker).arm("cmp_test")
    return broker, api, store


def rpc(broker, role, command, args=None, **kwargs):
    return broker.handle(role, {"command": command, "args": {} if args is None else args, **kwargs})


def proof(job, result, key=None):
    return helpers().sign_event(key or KEYS[job["role"]], 9, attestations(job, result), [["h", "channel"]], created_at=int(NOW))


def finish(broker, job, result, event=None):
    return rpc(broker, job["role"], "review-result", {"job": job["id"], "result": result, "usage": {"output_tokens": 100}},
               decision_event=event or proof(job, result))


DECISION = {"decision": "approved", "notes": "Proposal fits the bounded feature and acceptance source.",
            "classification_rationale": "", "evidence": ["art_test", "ctl_launched"]}
REVIEW = {"blocking": False, "notes": "No blocking findings after independent seam review.", "evidence": ["art_test"]}


def test_signed_independent_handoff_submits_once_after_restart(world):
    broker, api, store = world
    for _ in range(2): rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    assert store.db.execute("SELECT count(*) FROM review_jobs").fetchone()[0] == 1
    job = rpc(broker, "ripley", "review-claim")
    assert rpc(broker, "ripley", "review-claim") is None
    assert store.db.execute("SELECT reserved FROM review_jobs").fetchone()[0] == RESERVATION_MICROUSD
    finish(broker, job, DECISION)
    assert api.posts == []
    dallas = rpc(broker, "dallas", "review-claim")
    assert dallas["payload"]["packet"]["decision_request"]["args"]["binding"]["baseline_tree"] == "b" * 64
    finish(broker, dallas, REVIEW)
    assert api.posts == []
    restarted = Broker(Store(store.db.execute("PRAGMA database_list").fetchone()[2]), api, broker.policy, broker.verify_event)
    rpc(restarted, "ripley", "review-submit")
    rpc(restarted, "ripley", "review-submit")
    assert len(api.posts) == 1
    principal, path, payload = api.posts[0]
    assert principal == "review" and path.endswith("/gates/progress_increment_ruling")
    assert payload["decided_by_kind"] == "agent"
    assert "Decision event:" in payload["notes"] and "Review event:" in payload["notes"]


@pytest.mark.parametrize("fault", ["budget", "calls", "expired_price", "near_deadline"])
def test_allowance_failures_cannot_claim_a_paid_call(world, fault, monkeypatch):
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    if fault in {"budget", "calls"}:
        row = json.loads(store.db.execute("SELECT body FROM review_budgets").fetchone()[0])
        row["cap_microusd" if fault == "budget" else "max_dispatches"] = RESERVATION_MICROUSD if fault == "budget" else 1
        store.db.execute("UPDATE review_budgets SET body=?", (canonical(row),))
    else:
        monkeypatch.setattr(time, "time", lambda: timestamp("2026-11-02T00:00:00Z") if fault == "expired_price" else NOW + 6400)
    assert rpc(broker, "ripley", "review-claim") is None
    assert store.db.execute("SELECT sum(reserved) FROM review_jobs").fetchone()[0] == 0
    assert all("/gates/" not in p[1] for p in api.posts)


@pytest.mark.parametrize("fault", ["provider", "publication", "return_lost"])
def test_worker_failure_never_repeats_provider_call(world, fault):
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    calls = []
    def infer(*args):
        calls.append(args)
        if fault == "provider": raise TimeoutError("unknown outcome")
        return DECISION, {"output_tokens": 100}
    def post(job, result):
        if fault == "publication": raise OSError("publication response lost")
        return proof(job, result)
    def request(req):
        if fault == "return_lost" and req["command"] == "review-result": raise OSError("broker result lost")
        return broker.handle("ripley", req)
    with pytest.raises(Refused): run("ripley", request, infer, post)
    run("ripley", request, infer, post)
    assert len(calls) == 1
    assert store.db.execute("SELECT reserved,state FROM review_jobs").fetchone()[0] == RESERVATION_MICROUSD
    assert rpc(broker, "mother", "automation", {"campaign": "cmp_test"})["control"]["state"] == "parked"


def test_dallas_objection_parks_without_gate_or_revision_loop(world):
    broker, api, _ = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    finish(broker, rpc(broker, "ripley", "review-claim"), DECISION)
    finish(broker, rpc(broker, "dallas", "review-claim"), {**REVIEW, "blocking": True})
    for _ in range(2): rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    rpc(broker, "ripley", "review-submit")
    assert len(api.posts) == 1 and api.posts[0][1].endswith("/pause")


def test_stale_gate_is_cancelled_before_spend(world):
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    api.cycle["runs"][0]["gate_decisions"] = [{"gate_name": "progress_increment_ruling"}]
    assert rpc(broker, "ripley", "review-claim") is None
    assert store.db.execute("SELECT state,reserved FROM review_jobs").fetchone()[0] == "cancelled"


def test_owner_pause_between_queue_and_claim_prevents_paid_dispatch(world):
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    api.campaign["state"] = "paused"
    assert rpc(broker, "ripley", "review-claim") is None
    assert store.db.execute("SELECT reserved FROM review_jobs").fetchone()[0] == 0


def test_forged_role_and_unknown_evidence_are_refused(world):
    broker, api, _ = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    job = rpc(broker, "ripley", "review-claim")
    with pytest.raises(Refused): finish(broker, job, DECISION, proof(job, DECISION, KEYS["dallas"]))
    with pytest.raises(Refused): finish(broker, job, {**DECISION, "evidence": ["art_invented"]})
    assert api.posts == []


def test_deadline_survives_restart_and_reconciles_lost_abort_response(world, monkeypatch):
    broker, api, store = world
    deadline = store.db.execute("SELECT deadline FROM automation").fetchone()[0]
    monkeypatch.setattr(time, "time", lambda: deadline + 1)
    original = api.__call__
    class Lost:
        def __call__(self, *args):
            result = original(*args)
            if args[1] == "POST": raise OSError("lost after commit")
            return result
    broker.api = Lost()
    with pytest.raises(OSError): rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    broker.api = api
    for _ in range(2): rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    assert len(api.posts) == 1 and api.posts[0][1].endswith("/abort")
    assert store.db.execute("SELECT deadline FROM automation").fetchone()[0] == deadline


def test_closing_analysis_is_separate_signed_buzz_report_input(world):
    broker, api, _ = world
    api.campaign["state"] = "completed"
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    job = rpc(broker, "ripley", "review-claim")
    assert job["kind"] == "analysis"
    finish(broker, job, {"notes": "Completed with known source visibility limits; recommend an attended UI check.", "evidence": ["ctl_launched"]})
    packet = rpc(broker, "mother", "packet", {"campaign": "cmp_test"})
    assert packet["analysis"]["decision_event"]
    assert packet["automation"]["control"]["state"] == "closed"


def test_abort_row_alone_does_not_prove_cycle_cancellation(world, monkeypatch):
    broker, api, store = world
    monkeypatch.setattr(time, "time", lambda: NOW + 7201)
    original = api.__call__
    class Partial:
        def __call__(self, *args):
            result = original(*args)
            if args[1] == "POST":
                api.cycle["status"] = "running"
                raise OSError("abort committed but cancellation failed")
            return result
    broker.api = Partial()
    with pytest.raises(OSError): rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    broker.api = api
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    assert len(api.posts) == 2
    assert api.posts[0][2] == api.posts[1][2]
    assert api.cycle["status"] == "cancelled"


def test_budget_is_shared_across_campaigns_and_never_refunded(world):
    broker, _, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    job = rpc(broker, "ripley", "review-claim")
    rpc(broker, "ripley", "review-failed", {"job": job["id"]})
    # Another campaign naming the same owner allowance sees the first one's reservation.
    store.db.execute("INSERT INTO campaigns VALUES(?,?,?,?,?)", ("cmp_second", "pilot-test", "channel", "thread", "mother"))
    store.save()
    assert Automation(broker).status("cmp_second")["shared_budget_reserved_microusd"] == RESERVATION_MICROUSD


def test_worker_response_lost_after_broker_commit_does_not_repeat_call(world):
    broker, _, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    calls = []
    def infer(*args): calls.append(1); return DECISION, {}
    def request(req):
        result = broker.handle("ripley", req)
        if req["command"] == "review-result": raise OSError("lost after durable signed result")
        return result
    with pytest.raises(Refused): run("ripley", request, infer, proof)
    run("ripley", request, infer, proof)
    assert len(calls) == 1
    assert store.db.execute("SELECT count(*) FROM review_jobs WHERE kind='review'").fetchone()[0] == 1


@pytest.mark.parametrize("fault", ["project", "cycle", "hash", "size", "binary"])
def test_artifact_membership_and_bytes_are_verified(world, fault):
    broker, api, _ = world
    if fault == "project": api.meta["project_id"] = "other"
    if fault == "cycle": api.cycle["campaign_id"] = "cmp_other"
    if fault == "hash": api.meta["content_hash"] = "0" * 64
    if fault == "size": api.meta["size_bytes"] = 1000000
    if fault == "binary":
        api.raw = b'\xff'; api.meta.update(size_bytes=1, content_hash=hashlib.sha256(api.raw).hexdigest())
    with pytest.raises(Refused): rpc(broker, "mother", "artifact", {"campaign": "cmp_test", "artifact": "art_test"})


def test_progress_discloses_task_visibility_and_uses_latest_run_number(world):
    broker, api, _ = world
    api.cycle["runs"].insert(0, {**api.cycle["runs"][0], "run_id": "run_later", "run_number": 2, "status": "running"})
    result = rpc(broker, "mother", "progress", {"campaign": "cmp_test"})
    assert result["gates"] == [] and result["current_task"] is None
    assert "completed work only" in result["task_visibility"]


def test_evidence_pagination_never_infers_completeness_from_a_full_page(world):
    broker, api, _ = world
    calls = []
    def pages(*args, **kwargs):
        calls.append(kwargs["page"])
        return json.dumps([api.meta] * 100).encode()
    api.request = pages
    with pytest.raises(Refused, match="pagination"):
        Evidence(broker).listing("/api/v1/projects/group_run/cycles/cyc_test/artifacts")
    assert len(calls) == 20


@pytest.mark.parametrize("role", ["mother", "brett", "dallas"])
def test_routing_and_submission_authority_cannot_be_swapped(world, role):
    broker, _, _ = world
    command = "review-submit" if role != "mother" else "review-claim"
    if role == "dallas": command = "advance"
    with pytest.raises(Refused): rpc(broker, role, command, {"campaign": "cmp_test"} if command == "advance" else {})


def test_single_call_requests_have_no_tools_and_fail_on_oversized_evidence():
    for role, kind in [("ripley", "decision"), ("dallas", "review")]:
        request = body(role, kind, {"references": ["art_test"]}, "persona")
        assert "tools" not in request
        assert request.get("max_tokens", request.get("max_output_tokens")) == 8192
        with pytest.raises(Refused, match="complete evidence"):
            body(role, kind, {"content": "x" * 70000}, "persona")


@pytest.mark.parametrize("role,response", [("ripley", {"model": "gpt-5.6-sol", "status": "incomplete"}),
                                          ("dallas", {"model": "claude-opus-5-5", "stop_reason": "max_tokens"}),
                                          ("ripley", {"model": "different", "status": "completed"})])
def test_incomplete_or_wrong_model_provider_response_is_not_a_verdict(role, response):
    with pytest.raises(Refused): decode(role, response)


def test_review_usage_preserves_cache_and_reasoning_accounting():
    c = observed({"model": "claude-opus-5-5", "usage": {"input_tokens": 100, "cache_read_input_tokens": 200,
                  "cache_creation_input_tokens": 50, "cache_creation": {"ephemeral_1h_input_tokens": 20},
                  "output_tokens": 80, "output_tokens_details": {"thinking_tokens": 40}}})
    assert (c["input"], c["cached"], c["write5"], c["write1h"], c["output"], c["reasoning"]) == (350, 200, 30, 20, 80, 40)
    c = observed({"model": "gpt-5.6-sol", "usage": {"input_tokens": 300, "input_tokens_details": {"cached_tokens": 200},
                  "output_tokens": 80, "output_tokens_details": {"reasoning_tokens": 40}}})
    assert (c["input"], c["cached"], c["output"], c["reasoning"]) == (300, 200, 80, 40)
