"""Exercise real signed role handoffs and failure boundaries without provider/network calls."""
import copy
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from runtime.campaigns.automation import Automation
from runtime.campaigns.core import Broker, Refused, Store, canonical
from runtime.campaigns.decisions import helpers, verifier
from runtime.campaigns.evidence import Evidence, waiting_gates
from runtime.campaigns.review import RESERVATION_MICROUSD, attestations, body, decode, timestamp
from runtime.campaigns.worker import WorkerFailure, provider, run
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
def world(tmp_path, monkeypatch, request):
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
            "policy": {"max_cycles": 2, "max_elapsed_s": 7200, "budget_tokens": 1000000,
                       "max_proposal_revisions": getattr(request, "param", 0)},
            "crew": {"paid_dispatches": 8, "require_dallas": True,
                     "automation": {"budget": "pilot", "not_after": "2026-10-25T03:00:00Z"}}}
    broker.approve({"name": "pilot-test", "definition": spec, "channel": "channel", "thread": "thread"})
    api.campaign["policy"] = copy.deepcopy(spec["policy"])
    api.cycle["execution_overrides"] = {"campaign_proposal": {"max_revisions": spec["policy"]["max_proposal_revisions"]}}
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
RETURNED = {**DECISION, "decision": "returned_for_revision", "notes": "Acceptance evidence needs clarification before implementation.",
            "classification_rationale": "The proposal omits an objective acceptance condition."}


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
    with pytest.raises(WorkerFailure) as caught: run("ripley", request, infer, post)
    expected_stage = {"provider": "provider_request", "publication": "buzz_publication",
                      "return_lost": "broker_result_submit"}[fault]
    assert caught.value.diagnostic() == f"stage={expected_stage} error={'TimeoutError' if fault == 'provider' else 'OSError'}"
    assert all(text not in caught.value.diagnostic() for text in
               ("unknown outcome", "publication response lost", "broker result lost"))
    run("ripley", request, infer, post)
    assert len(calls) == 1
    assert store.db.execute("SELECT reserved,state FROM review_jobs").fetchone()[0] == RESERVATION_MICROUSD
    status = rpc(broker, "mother", "automation", {"campaign": "cmp_test"})
    assert status["control"]["state"] == "parked"
    assert status["jobs"][0]["failure_diagnostic"]["stage"] == expected_stage


def test_validation_failure_is_stored_for_read_only_triage(world):
    broker, api, _ = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    calls = []

    def invalid_result(*args):
        calls.append(args)
        return {**DECISION, "evidence": ["not-in-approved-packet"]}, {"output_tokens": 100}

    def ripley_rpc(request):
        return broker.handle("ripley", request)

    with pytest.raises(WorkerFailure) as caught:
        run("ripley", ripley_rpc, invalid_result)
    assert caught.value.diagnostic() == "stage=result_validation error=Refused reason_code=evidence_refs_invalid"
    triage = rpc(broker, "mother", "triage", {"campaign": "cmp_test"})
    assert triage["mode"] == "read_only_no_model_calls"
    assert triage["findings"][0]["classification"] == "evidence_refs_invalid"
    assert triage["review_jobs"][0]["failure_diagnostic"] == {
        "stage": "result_validation", "error": "Refused", "reason_code": "evidence_refs_invalid"}
    assert "not-in-approved-packet" not in json.dumps(triage)
    assert len(calls) == 1
    assert api.posts and api.posts[-1][1].endswith("/pause")


def test_provider_http_failure_logs_status_without_provider_body(monkeypatch):
    from urllib.error import HTTPError

    class FailedOpener:
        def open(self, request, timeout):
            raise HTTPError(request.full_url, 401, "denied TOP_SECRET", {}, None)

    monkeypatch.setattr("runtime.campaigns.worker.secret", lambda name: "TOP_SECRET")
    monkeypatch.setattr("runtime.campaigns.worker.urllib.request.build_opener", lambda redirect: FailedOpener())
    with pytest.raises(WorkerFailure) as caught:
        provider("ripley", {"model": "gpt-5.6-sol"}, 1)
    assert caught.value.diagnostic() == "stage=provider_http error=HTTPError http_status=401 reason_code=provider_http_error"
    assert "TOP_SECRET" not in caught.value.diagnostic()


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


def test_recovery_keeps_accepted_event_across_read_failure_without_republishing(world, tmp_path, monkeypatch):
    from runtime.campaigns import worker
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    job = rpc(broker, "ripley", "review-claim")
    rpc(broker, "ripley", "review-failed", {"job": job["id"], "diagnostic": {
        "stage": "buzz_publication", "error": "TimeoutExpired"}})
    store.db.execute("UPDATE automation SET state='expired',reason='deadline reached',deadline=?", (NOW - 1,))
    store.save()
    api.campaign["state"] = "completed"
    original_posts = copy.deepcopy(api.posts)
    state = tmp_path / ".local/state/nostromo-reviews"
    state.mkdir(parents=True)
    record = state / (job["id"] + ".json")
    record.write_text(canonical({"model": "gpt-5.6-sol", "result": DECISION, "usage": {"output_tokens": 100}}))
    record.chmod(0o600)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    event = proof(job, DECISION)
    sent = []
    def send(*args):
        sent.append(args)
        return event["id"]
    monkeypatch.setattr(worker, "send_message", send)
    def unavailable(eid):
        raise OSError("relay read unavailable")
    monkeypatch.setattr(worker, "read_event", unavailable)
    request = lambda req: broker.handle("ripley", req)
    infer = lambda *args: pytest.fail("recovery must never call a provider")
    authorize = {"job": job["id"], "no_matching_event_verified": True}
    with pytest.raises(Refused, match="owner"):
        rpc(broker, "mother", "review-recovery-authorize", authorize)
    rpc(broker, "owner", "review-recovery-authorize", authorize)
    with pytest.raises(WorkerFailure):
        worker.run("ripley", rpc=request, infer=infer)
    saved = rpc(broker, "owner", "automation", {"campaign": "cmp_test"})["jobs"][0]
    assert saved["recovery"] == {"state": "failed", "failure": "OSError", "event_id": event["id"]}
    assert json.loads(record.read_text())["pending_event_id"] == event["id"]
    with pytest.raises(Refused, match="without republication"):
        rpc(broker, "owner", "review-recovery-authorize", authorize)
    rpc(broker, "owner", "review-recovery-authorize", {"job": job["id"], "existing_event_id": event["id"]})
    monkeypatch.setattr(worker, "read_event", lambda eid: event)
    result = worker.run("ripley", rpc=request, infer=infer)
    assert result == {"stored": True, "campaign_control_unchanged": True, "provider_calls": 0}
    assert len(sent) == 1
    assert api.posts == original_posts
    assert store.db.execute("SELECT state FROM automation").fetchone()[0] == "expired"
    assert store.db.execute("SELECT count(*) FROM review_jobs").fetchone()[0] == 1
    assert store.db.execute("SELECT state,reserved FROM review_jobs").fetchone()[:] == ("done", RESERVATION_MICROUSD)


@pytest.mark.parametrize("stage", ["provider_request", "result_validation", "recovery_persist"])
def test_publication_recovery_refuses_other_failure_stages(world, stage):
    broker, _, _ = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    job = rpc(broker, "ripley", "review-claim")
    rpc(broker, "ripley", "review-failed", {"job": job["id"], "diagnostic": {"stage": stage, "error": "Refused"}})
    with pytest.raises(Refused, match="failed Buzz publication"):
        rpc(broker, "owner", "review-recovery-authorize", {"job": job["id"], "no_matching_event_verified": True})


@pytest.mark.parametrize("category,expected", [(None, None), ("network_error", "BuzzNetworkError"),
                                              ("auth_error", "BuzzAuthError"), ("relay_error", "BuzzRelayError")])
def test_buzz_publisher_bounds_threads_and_keeps_failure_diagnostics_safe(monkeypatch, category, expected):
    from runtime.campaigns import worker
    original_read = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda path, *a, **kw:
        json.dumps({"review_auth_tags": {"ripley": "fixture"}})
        if str(path) == "/etc/nostromo/campaign-broker.json" else original_read(path, *a, **kw))
    monkeypatch.setattr(worker, "secret", lambda name: "fixture-key")
    monkeypatch.setenv("TOKIO_WORKER_THREADS", "99")
    monkeypatch.setattr(worker, "attestations", lambda job, result: "fixture review")
    calls = []
    def command(argv, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(returncode=2 if category else 0,
                               stdout=json.dumps({"accepted": True, "event_id": "a" * 64}),
                               stderr=json.dumps({"error": category, "message": "TOP_SECRET"}))
    monkeypatch.setattr(worker.subprocess, "run", command)
    job = {"role": "ripley", "payload": {"destination": {"channel": "channel", "thread": "thread"}}}
    if category:
        with pytest.raises(WorkerFailure) as caught:
            worker.send_message(job, {})
        assert caught.value.error_type == expected
        assert "TOP_SECRET" not in caught.value.diagnostic()
    else:
        assert worker.send_message(job, {}) == "a" * 64
    assert calls[0]["env"]["TOKIO_WORKER_THREADS"] == "2"
    assert calls[0]["input"] == "fixture review"


def test_zero_revision_packet_and_provider_schema_offer_an_owner_hold(world):
    broker, _, _ = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    job = rpc(broker, "ripley", "review-claim")
    contract = job["payload"]["packet"]["decision_contract"]
    assert contract["proposal_revisions"] == {
        "available": False, "reason": "revision_allowance_exhausted",
        "limits": {"approved": 0, "campaign": 0, "cycle": 0}, "used": 0, "remaining": 0}
    shape = job["payload"]["body"]["text"]["format"]["schema"]
    assert shape["properties"]["decision"]["enum"] == ["approved", "rejected", "needs_owner"]
    assert json.loads(job["payload"]["body"]["input"])["packet"]["decision_contract"] == contract
    result = {**RETURNED, "decision": "needs_owner"}
    finish(broker, job, result)
    control = rpc(broker, "mother", "automation", {"campaign": "cmp_test"})
    assert control["control"]["state"] == "parked" and len(control["jobs"]) == 1


def test_retained_zero_revision_failure_stops_before_dallas_or_gate_write(world):
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    calls, publications = [], []
    def infer(*args):
        calls.append(args)
        return RETURNED, {"output_tokens": 100}
    def post(*args):
        publications.append(args)
        raise AssertionError("policy-forbidden decision must not be published")
    with pytest.raises(WorkerFailure) as caught:
        run("ripley", lambda req: broker.handle("ripley", req), infer, post)
    assert caught.value.reason_code == "decision_policy_forbidden"
    run("ripley", lambda req: broker.handle("ripley", req), infer, post)
    assert len(calls) == 1 and publications == []
    assert store.db.execute("SELECT count(*) FROM review_jobs WHERE role='dallas'").fetchone()[0] == 0
    assert store.db.execute("SELECT sum(reserved) FROM review_jobs").fetchone()[0] == RESERVATION_MICROUSD
    assert all("/gates/" not in p[1] for p in api.posts)
    assert rpc(broker, "mother", "triage", {"campaign": "cmp_test"})["findings"][0]["classification"] == "decision_policy_forbidden"


def test_broker_refuses_forbidden_signed_result_without_trusting_worker_validation(world):
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    job = rpc(broker, "ripley", "review-claim")
    event = helpers().sign_event(KEYS["ripley"], 9, "campaign-job-result: " + canonical({"job": job["id"], "result": RETURNED}),
                                 [["h", "channel"]], created_at=int(NOW))
    with pytest.raises(Refused, match="proposal revision is unavailable"):
        finish(broker, job, RETURNED, event)
    assert store.db.execute("SELECT count(*) FROM review_jobs").fetchone()[0] == 1
    assert api.posts == []


def test_read_only_triage_diagnoses_the_retained_pre_fix_ruling_without_replay(world):
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    job = rpc(broker, "ripley", "review-claim")
    # The old worker accepted this judgment before policy checks existed.
    payload = copy.deepcopy(job["payload"])
    payload["packet"].pop("decision_contract")
    payload["packet"].pop("approved_policy")
    store.db.execute("UPDATE review_jobs SET state='done',result=?,payload=? WHERE id=?",
                     (canonical(RETURNED), canonical(payload), job["id"]))
    store.save()
    report = rpc(broker, "mother", "triage", {"campaign": "cmp_test"})
    finding = report["findings"][0]
    assert finding["classification"] == "decision_policy_forbidden"
    assert finding["proposal_revisions"]["remaining"] == 0
    assert finding["proposal_revisions"]["reason"] == "revision_allowance_exhausted"
    assert api.posts == [] and store.db.execute("SELECT count(*) FROM review_jobs").fetchone()[0] == 1
    assert RETURNED["notes"] not in canonical(report)


@pytest.mark.parametrize("world", [1], indirect=True)
def test_positive_revision_allowance_keeps_independent_review_and_exact_ruling(world):
    broker, api, _ = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    ripley = rpc(broker, "ripley", "review-claim")
    assert "returned_for_revision" in ripley["payload"]["body"]["text"]["format"]["schema"]["properties"]["decision"]["enum"]
    finish(broker, ripley, RETURNED)
    dallas = rpc(broker, "dallas", "review-claim")
    assert dallas["payload"]["packet"]["proposed_decision"] == RETURNED
    assert api.posts == []
    finish(broker, dallas, REVIEW)
    rpc(broker, "ripley", "review-submit")
    assert len(api.posts) == 1 and api.posts[0][2]["decision"] == "returned_for_revision"
    assert broker.store.definition("pilot-test")[0]["definition"]["policy"]["max_proposal_revisions"] == 1


@pytest.mark.parametrize("world", [1], indirect=True)
@pytest.mark.parametrize("when", ["before_result", "before_dallas", "before_submit"])
def test_live_revision_exhaustion_cannot_spend_dallas_or_submit_stale_ruling(world, when):
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    ripley = rpc(broker, "ripley", "review-claim")
    superseded = {"run_id": "run_old", "workload_type": "proposal", "status": "cancelled", "run_number": 0}
    if when == "before_result":
        api.cycle["runs"].append(superseded)
    finish(broker, ripley, RETURNED)
    if when == "before_dallas":
        api.cycle["runs"].append(superseded)
    dallas = rpc(broker, "dallas", "review-claim")
    if when == "before_submit":
        finish(broker, dallas, REVIEW)
        api.cycle["runs"].append(superseded)
        with pytest.raises(Refused, match="proposal revision is unavailable"):
            rpc(broker, "ripley", "review-submit")
    else:
        assert dallas is None
        assert store.db.execute("SELECT coalesce(sum(reserved),0) FROM review_jobs WHERE role='dallas'").fetchone()[0] == 0
    assert all("/gates/" not in p[1] for p in api.posts)
    assert rpc(broker, "mother", "automation", {"campaign": "cmp_test"})["control"]["state"] == "parked"
    assert rpc(broker, "mother", "triage", {"campaign": "cmp_test"})["findings"][0]["classification"] == "decision_policy_forbidden"


@pytest.mark.parametrize("world", [1], indirect=True)
def test_unreadable_live_revision_authority_retains_signed_result_and_parks(world, monkeypatch):
    broker, api, store = world
    rpc(broker, "mother", "advance", {"campaign": "cmp_test"})
    ripley = rpc(broker, "ripley", "review-claim")
    def unavailable(*args):
        raise OSError("unreadable runtime; do not log transport details")
    monkeypatch.setattr(Automation, "current_decision_packet", unavailable)
    finish(broker, ripley, RETURNED)
    result = store.db.execute("SELECT state,result,proof FROM review_jobs WHERE id=?", (ripley["id"],)).fetchone()
    assert result["state"] == "done" and json.loads(result["result"]) == RETURNED and result["proof"]
    assert rpc(broker, "dallas", "review-claim") is None
    assert rpc(broker, "mother", "triage", {"campaign": "cmp_test"})["findings"][0]["classification"] == "decision_policy_forbidden"
    assert len(api.posts) == 1 and api.posts[0][1].endswith("/pause")
