"""Durable launch fault cases through the real broker/worker, without model or network calls."""
import copy
import base64
import hashlib
import json

import pytest

from runtime.campaigns.core import Broker, Refused, Store
from runtime.campaigns.decisions import helpers, verifier
from runtime.campaigns.launch import LAUNCH_SECONDS, NOTICE_LEASE_SECONDS
from runtime.campaigns.launch_worker import Publisher, run, submit_event

CHANNEL = "60cf6624-62d1-4c37-9522-f6dbf884fd25"
THREAD = "a" * 64
KEY = "0" * 63 + "1"
DEFINITION = {"project_id": "group_run",
              "objective": {"statement": "one bounded increment", "allowed_scope": ["backend/**"],
                            "measurement": "actual verification", "target_accepted_increments": 1},
              "policy": {"max_cycles": 2, "max_elapsed_s": 3600, "budget_tokens": 1000000},
              "crew": {"inference_mode": "shared", "require_dallas": True, "paid_dispatches": 0}}


class Crash(BaseException):
    pass


class Runtime:
    def __init__(self):
        self.campaigns, self.logs, self.writes = {}, {}, []
        self.fault = None

    def __call__(self, principal, method, path, body):
        if method == "POST":
            self.writes.append((principal, path, copy.deepcopy(body)))
            command = "create" if path == "/api/v1/campaigns" else path.rsplit("/", 1)[-1]
            if self.fault == "before_" + command:
                raise OSError("lost before runtime commit")
            if command == "create":
                cid = body["campaign_id"]
                assert cid not in self.campaigns, "duplicate create reached runtime"
                self.campaigns[cid] = {k: copy.deepcopy(body[k]) for k in ("campaign_id", "project_id", "objective", "policy")}
                self.campaigns[cid]["objective"].setdefault("work_class", None)
                self.campaigns[cid]["policy"].setdefault("stack", None)
                self.campaigns[cid]["state"] = "draft"
                self.logs[cid] = []
            elif command == "start":
                cid = path.split("/")[-2]
                assert self.campaigns[cid]["state"] == "draft", "duplicate start reached runtime"
                self.campaigns[cid]["state"] = "calibrating"
            else:
                raise AssertionError(path)
            entry = {"operation": command, "idempotency_key": body["idempotency_key"], "outcome": "applied",
                     "binding": {"definition": body["definition"]} if command == "create" else {}}
            self.logs[cid].append(entry)
            if self.fault == "after_" + command:
                raise OSError("lost response after runtime commit")
            return {"campaign": copy.deepcopy(self.campaigns[cid]), "entry": entry}
        cid = path.split("/")[4]
        if cid not in self.campaigns:
            raise Refused("SquadOps refused the operation (HTTP 404); inspect its control log")
        if path.endswith("/control-log"):
            return copy.deepcopy(self.logs[cid])
        return copy.deepcopy(self.campaigns[cid])


@pytest.fixture
def world(tmp_path, monkeypatch):
    clock = [1792983600.0]
    monkeypatch.setattr("time.time", lambda: clock[0])
    api = Runtime()
    policy = {"launch_enabled": True, "decision_channels": [CHANNEL],
              "public_keys": {"mother": helpers().xonly_pubkey(KEY)}}
    database = tmp_path / "broker.sqlite3"
    def restart():
        return Broker(Store(database), api, policy, verifier(policy, now=lambda: clock[0]))
    broker = restart()
    broker.approve({"name": "pilot", "definition": copy.deepcopy(DEFINITION), "channel": CHANNEL, "thread": THREAD})
    return broker, api, clock, restart


def rpc(broker, role, command, args=None, **extra):
    return broker.handle(role, {"command": command, "args": args or {}, **extra})


def queue(broker):
    return rpc(broker, "mother", "launch", {"definition": "pilot", "reason": "owner-approved pilot"}, request_id="pilot-launch")


def proof(job, thread=THREAD):
    return helpers().sign_event(KEY, 9, job["content"], [["h", CHANNEL], ["e", thread, "", "reply"]])


def tick(broker, publish=proof):
    return run(rpc=lambda request: broker.handle("mother", request), publish=publish)


def status(broker):
    return rpc(broker, "owner", "launch-status", {"launch": "pilot-launch"})


def test_one_intent_finishes_after_model_exits_and_broker_restarts(world):
    broker, api, _, restart = world
    accepted = queue(broker)
    assert accepted["state"] == "queued" and api.writes == []
    assert queue(broker) == accepted
    tick(restart())  # Independent timer; no model continuation after accepting the intent.
    assert status(broker)["state"] == "announced"
    tick(restart())
    result = status(broker)
    assert result["state"] == "started" and result["completion_event"]
    assert len(api.writes) == 2
    assert [x[1].rsplit("/", 1)[-1] for x in api.writes] == ["campaigns", "start"]
    assert api.writes[0][2]["idempotency_key"] == result["create_request"]
    assert api.writes[1][2]["idempotency_key"] == result["start_request"]
    assert api.writes[0][2]["policy"] == DEFINITION["policy"]
    assert api.writes[0][2]["objective"] == DEFINITION["objective"]
    assert broker.store.db.execute("SELECT count(*) FROM review_jobs").fetchone()[0] == 0
    assert queue(broker)["state"] == "started"
    tick(restart())
    assert len(api.writes) == 2


@pytest.mark.parametrize("command", ["create", "start"])
def test_lost_committed_response_reconciles_without_repeating_control_write(world, command):
    broker, api, _, restart = world
    queue(broker)
    if command == "start":
        tick(broker)
    api.fault = "after_" + command
    tick(broker)
    assert status(broker)["state"] == ("creating" if command == "create" else "starting")
    api.fault = None
    tick(restart())
    if command == "create":
        tick(restart())
    assert status(broker)["state"] == "started"
    assert len(api.writes) == 2
    assert sum(x[1] == "/api/v1/campaigns" for x in api.writes) == 1


def test_crash_before_receipt_reservation_continues_with_original_request_id(world):
    broker, api, _, restart = world
    queued = queue(broker)
    original = broker.handle
    def interrupted(caller, request):
        if request["command"] == "create":
            raise Crash()
        return original(caller, request)
    broker.handle = interrupted
    with pytest.raises(Crash):
        tick(broker)
    assert api.writes == []
    resumed = restart()
    tick(resumed)
    tick(resumed)
    assert status(resumed)["state"] == "started"
    assert api.writes[0][2]["idempotency_key"] == queued["create_request"]


def test_unknown_create_outcome_never_gets_reposted_and_expires_visibly(world):
    broker, api, clock, restart = world
    queue(broker)
    api.fault = "before_create"
    tick(broker)
    api.fault = None
    for _ in range(2):
        tick(restart())
    assert len(api.writes) == 1 and status(broker)["state"] == "creating"
    clock[0] += LAUNCH_SECONDS + 1
    notices = []
    tick(restart(), lambda job: notices.append(job) or proof(job))
    assert status(broker)["state"] == "blocked"
    assert notices[0]["phase"] == "failure"
    assert "launch incomplete" in notices[0]["content"]
    assert status(broker)["completion_event"]
    assert len(api.writes) == 1


def test_deadline_between_announcement_and_start_prevents_late_launch(world):
    broker, api, clock, restart = world
    queue(broker)
    tick(broker)
    clock[0] += LAUNCH_SECONDS + 1
    tick(restart())
    assert status(broker)["state"] == "blocked"
    assert status(broker)["completion_event"]
    assert len(api.writes) == 1
    assert list(api.campaigns.values())[0]["state"] == "draft"


def test_signed_outbox_survives_crash_after_delivery_without_duplicate_notice(world, tmp_path):
    broker, api, clock, restart = world
    queue(broker)
    events = {THREAD: {"id": THREAD, "kind": 9, "tags": [["h", CHANNEL]]}}
    submissions = []
    crashing = [True]
    def submit(event, key, auth_tag):
        submissions.append(copy.deepcopy(event))
        events[event["id"]] = event
        if crashing[0]:
            raise Crash()
    publisher = Publisher(tmp_path / "outbox", KEY, ["auth", "fixture"], submit=submit, lookup=events.__getitem__)
    with pytest.raises(Crash):
        tick(broker, publisher)
    assert len(submissions) == 1
    assert status(broker)["state"] == "announcing"
    clock[0] += NOTICE_LEASE_SECONDS + 1
    crashing[0] = False
    resumed = restart()
    publisher = Publisher(tmp_path / "outbox", KEY, ["auth", "fixture"], submit=submit, lookup=events.__getitem__)
    tick(resumed, publisher)
    assert status(resumed)["state"] == "announced"
    assert len(submissions) == 1  # The persisted event was read back; no new event was signed/sent.
    tick(resumed, publisher)
    assert status(resumed)["state"] == "started" and len(submissions) == 2
    assert submissions[0]["id"] != submissions[1]["id"]  # Announcement and final receipt.
    assert all(path.stat().st_mode & 0o077 == 0 for path in (tmp_path / "outbox").glob("*.json"))


def test_ambiguous_notice_resubmits_exact_event_id_if_not_yet_readable(world, tmp_path):
    broker, _, _, _ = world
    queue(broker)
    events = {THREAD: {"id": THREAD, "kind": 9, "tags": [["h", CHANNEL]]}}
    sent = []
    fail = [True]
    def submit(event, key, tag):
        sent.append(event)
        if fail[0]:
            raise OSError("lost response; never log a secret-shaped response")
        events[event["id"]] = event
    publisher = Publisher(tmp_path / "outbox", KEY, ["auth", "fixture"], submit=submit, lookup=events.__getitem__)
    with pytest.raises(Refused, match="notice failed"):
        tick(broker, publisher)
    fail[0] = False
    tick(broker, publisher)
    assert len(sent) == 2 and sent[0] == sent[1]
    assert status(broker)["state"] == "announced"


@pytest.mark.parametrize("role", ["owner", "ripley", "dallas", "brett", "watcher"])
def test_other_roles_cannot_submit_or_advance_launches(world, role):
    broker, api, _, _ = world
    with pytest.raises(Refused, match="belong to Mother"):
        rpc(broker, role, "launch", {"definition": "pilot", "reason": "attempt"}, request_id="probe")
    with pytest.raises(Refused, match="belong to Mother"):
        rpc(broker, role, "launch-advance")
    assert api.writes == []


def test_launch_reserves_definition_and_refuses_manual_bypass(world):
    broker, api, _, _ = world
    queued = queue(broker)
    with pytest.raises(Refused, match="another launch"):
        rpc(broker, "mother", "launch", {"definition": "pilot", "reason": "second"}, request_id="second")
    with pytest.raises(Refused, match="different content"):
        rpc(broker, "mother", "launch", {"definition": "pilot", "reason": "changed"}, request_id="pilot-launch")
    with pytest.raises(Refused, match="durable launch"):
        rpc(broker, "mother", "create", {"definition": "pilot", "reason": "bypass"}, request_id="bypass")
    rpc(broker, "mother", "launch-advance")
    with pytest.raises(Refused, match="durable launch"):
        rpc(broker, "mother", "start", {"campaign": queued["campaign"], "reason": "owner-approved pilot"},
            request_id=queued["start_request"])
    assert len(api.writes) == 1


def test_wrong_thread_signed_notice_cannot_unlock_start(world):
    broker, api, _, _ = world
    queue(broker)
    rpc(broker, "mother", "launch-advance")
    job = rpc(broker, "mother", "launch-notice-claim")
    with pytest.raises(Refused, match="approved campaign thread"):
        rpc(broker, "mother", "launch-notice-result", {"launch": job["id"], "phase": job["phase"]},
            decision_event=proof(job, thread="b" * 64))
    rpc(broker, "mother", "launch-advance")
    assert len(api.writes) == 1


def test_reused_campaign_thread_cannot_accept_new_launch(world):
    broker, api, _, _ = world
    broker.store.db.execute("INSERT INTO campaigns VALUES('cmp_old','old',?,?,'mother')", (CHANNEL, THREAD))
    broker.store.save()
    with pytest.raises(Refused, match="own campaign thread"):
        queue(broker)
    assert api.writes == []


def test_failed_notices_are_bounded_and_never_allow_start(world):
    broker, api, _, _ = world
    queue(broker)
    def unavailable(job):
        raise OSError("unavailable")
    for _ in range(3):
        with pytest.raises(Refused):
            tick(broker, unavailable)
    tick(broker)  # Records the exhausted announcement attempt as an incomplete launch.
    tick(broker)  # Posts the failure notice instead of starting.
    assert status(broker)["state"] == "blocked" and status(broker)["completion_event"]
    assert len(api.writes) == 1


def test_missing_worker_commissioning_cannot_silently_queue(world):
    broker, api, _, _ = world
    broker.policy["launch_enabled"] = False
    with pytest.raises(Refused, match="not commissioned"):
        queue(broker)
    assert api.writes == []


def test_expired_queued_intent_never_creates_a_campaign(world):
    broker, api, clock, restart = world
    queue(broker)
    clock[0] += LAUNCH_SECONDS + 1
    tick(restart())
    assert status(broker)["state"] == "blocked" and status(broker)["completion_event"]
    assert api.writes == []


def test_pending_start_requires_exact_control_log_and_approved_policy(world):
    broker, api, clock, restart = world
    queued = queue(broker)
    tick(broker)
    api.fault = "after_start"
    tick(broker)
    api.fault = None
    api.logs[queued["campaign"]][-1]["idempotency_key"] = "unrelated"
    resumed = restart()
    tick(resumed)
    assert status(resumed)["state"] == "starting"
    api.logs[queued["campaign"]][-1]["idempotency_key"] = queued["start_request"]
    api.campaigns[queued["campaign"]]["policy"]["budget_tokens"] += 1
    tick(resumed)
    assert status(resumed)["state"] == "starting"
    clock[0] += LAUNCH_SECONDS + 1
    tick(resumed)
    assert status(resumed)["state"] == "blocked" and len(api.writes) == 2


def test_launch_keeps_paid_allowance_and_original_automation_cutoff(world):
    broker, api, clock, restart = world
    broker.policy["automation_enabled"] = True
    rpc(broker, "owner", "approve-budget", {"name": "shared", "cap_microusd": 5000000,
        "max_dispatches": 8, "expires_at": "2026-10-26T12:00:00Z"})
    spec = copy.deepcopy(DEFINITION)
    spec["crew"].update(paid_dispatches=3, automation={"budget": "shared", "not_after": "2026-10-26T06:00:00Z"})
    broker.approve({"name": "paid", "definition": spec, "channel": CHANNEL, "thread": THREAD})
    accepted = rpc(broker, "mother", "launch", {"definition": "paid", "reason": "existing allowance"}, request_id="paid-launch")
    tick(broker)
    tick(broker)
    cid = accepted["campaign"]
    control = rpc(broker, "mother", "automation", {"campaign": cid})["control"]
    assert control["deadline"] == clock[0] + DEFINITION["policy"]["max_elapsed_s"]
    assert broker.store.definition("paid")[0]["definition"]["crew"]["paid_dispatches"] == 3
    assert broker.store.db.execute("SELECT count(*) FROM review_jobs").fetchone()[0] == 0
    clock[0] += 100
    tick(restart())
    assert rpc(broker, "mother", "automation", {"campaign": cid})["control"]["deadline"] == control["deadline"]
    assert len(api.writes) == 2


def test_outbox_refuses_wrong_root_and_tampered_event(world, tmp_path):
    broker, api, _, _ = world
    queue(broker)
    events = {THREAD: {"id": THREAD, "kind": 9, "tags": [["h", "wrong-channel"]]}}
    sent = []
    def unavailable(event, key, tag):
        sent.append(event)
        raise OSError("no acknowledgment")
    publisher = Publisher(tmp_path / "outbox", KEY, ["auth", "fixture"], submit=unavailable, lookup=events.__getitem__)
    with pytest.raises(Refused, match="notice failed"):
        tick(broker, publisher)
    assert sent == []
    events[THREAD]["tags"] = [["h", CHANNEL]]
    with pytest.raises(Refused, match="notice failed"):
        tick(broker, publisher)
    target = next((tmp_path / "outbox").glob("*.json"))
    saved = json.loads(target.read_text())
    saved["content"] = "tampered"
    target.write_text(json.dumps(saved))
    with pytest.raises(Refused, match="notice failed"):
        tick(broker, publisher)
    assert len(sent) == 1 and len(api.writes) == 1


def test_ambiguous_create_cannot_claim_scenario_pin_from_create_transaction(world):
    broker, api, _, _ = world
    spec = copy.deepcopy(DEFINITION)
    spec["scenario_suite"] = "b" * 64
    broker.approve({"name": "suite", "definition": spec, "channel": CHANNEL, "thread": THREAD})
    rpc(broker, "mother", "launch", {"definition": "suite", "reason": "approved suite"}, request_id="suite-launch")
    api.fault = "after_create"
    tick(broker)
    api.fault = None
    tick(broker)
    state = rpc(broker, "owner", "launch-status", {"launch": "suite-launch"})
    assert state["state"] == "creating" and "scenario suite pin" in state["diagnostic"]["reason"]
    assert len(api.writes) == 1


def test_http_publication_binds_auth_to_exact_event_and_requires_exact_receipt(monkeypatch):
    event = proof({"content": "launch receipt"})
    acknowledgment = {"accepted": True, "event_id": event["id"]}
    requests = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, bound):
            assert bound == 65537
            return json.dumps(acknowledgment).encode()
    class Opener:
        def open(self, request, timeout):
            assert timeout == 20
            requests.append(request)
            return Response()
    monkeypatch.setattr("urllib.request.build_opener", lambda handler: Opener())
    submit_event(event, KEY, ["auth", "fixture"])
    request = requests[0]
    assert request.full_url == "https://nostromo.backspring.xyz/events"
    assert json.loads(request.data) == event
    assert json.loads(request.get_header("X-auth-tag")) == ["auth", "fixture"]
    auth = json.loads(base64.b64decode(request.get_header("Authorization").split(" ", 1)[1]))
    assert auth["kind"] == 27235 and auth["pubkey"] == event["pubkey"]
    assert ["u", request.full_url] in auth["tags"] and ["method", "POST"] in auth["tags"]
    assert ["payload", hashlib.sha256(request.data).hexdigest()] in auth["tags"]
    assert helpers().schnorr_verify(bytes.fromhex(auth["id"]), auth["pubkey"], auth["sig"])
    acknowledgment["event_id"] = "wrong"
    with pytest.raises(Refused, match="exact launch event"):
        submit_event(event, KEY, ["auth", "fixture"])
