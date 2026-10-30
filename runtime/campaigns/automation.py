"""Durable bounded review queue. Mother routes; Ripley judges; Dallas challenges."""
import json
import re
import time
from pathlib import Path

from .core import Refused, canonical, digest, exact, identifier
from .evidence import Evidence
from .review import body, price_basis, reservation_microusd, timestamp, validate, decision_request
from .review_policy import POLICY_REFUSAL, decision_contract, validate_decision

COMMANDS = {"approve-budget", "automation", "advance", "review-claim", "review-result", "review-failed",
            "review-submit", "review-recovery-authorize", "review-recovery-claim", "review-recovery-result",
            "review-recovery-failed", "review-recovery-pending"}

GATE_TYPES = {"interface_manifest", "verification_contract", "control_implementation_plan", "merge_decisions",
              "change_request", "definition_of_done", "test_report", "accepted_tree"}
# Evidence each gate review receives is an explicit contract over evidence keys (evidence_key below).
# A planning run holds several `document` artifacts and only the consolidated plan belongs in a
# plan-gate packet: on the 2026-10-26 plan gate all six documents came to 83 KB against a 64 KB
# request, and the plan itself to 7 KB. SquadOps's planning sequence always ends in
# governance.merge_plan (implementation_plan.yaml, the canonical plan) and governance.review_plan
# (planning_artifact.md, its narrative), so a plan gate missing either holds.
PLANNING_ARTIFACT = "document:governance.review_plan"
GATE_EVIDENCE = {
    "progress_plan_review": {"included": GATE_TYPES | {PLANNING_ARTIFACT},
                             "required": {PLANNING_ARTIFACT, "control_implementation_plan"}},
    "progress_increment_ruling": {"included": GATE_TYPES, "required": set()},
}
CLOSING_EVIDENCE_TYPES = {"definition_of_done", "test_report", "accepted_tree"}


def artifact_metadata(meta):
    """SquadOps's free-form metadata, or nothing when it is absent or not an object."""
    value = meta.get("metadata")
    return value if isinstance(value, dict) else {}


def evidence_key(meta):
    """An artifact's type; for the generic `document` type, also the SquadOps task that produced it.
    A failed emission (SquadOps banks those with emission_status "failed") is never evidence."""
    if artifact_metadata(meta).get("emission_status") == "failed":
        return None
    kind = meta.get("artifact_type")
    if kind == "document":
        return "document:" + str(artifact_metadata(meta).get("producing_task_type"))
    return kind


class Automation:
    def __init__(self, broker, now=None):
        self.b, self.db = broker, broker.store.db
        self.now = time.time() if now is None else now

    def spec(self, cid):
        item = self.b.store.campaign(cid)
        approved, _ = self.b.store.definition(item["definition"])
        return approved["definition"].get("crew", {}).get("automation")

    def budget(self, name):
        row = self.db.execute("SELECT body FROM review_budgets WHERE name=?", (identifier(name),)).fetchone()
        if not row:
            raise Refused("review budget is not owner-approved")
        return json.loads(row[0])

    def validate_spec(self, spec, crew):
        exact(spec, {"budget", "not_after"})
        budget = self.budget(spec["budget"])
        if not self.now < timestamp(spec["not_after"]) <= timestamp(budget["expires_at"]):
            raise Refused("automation needs a future cutoff within the approved budget")
        if type(crew.get("paid_dispatches")) is not int or not 1 <= crew["paid_dispatches"] <= budget["max_dispatches"]:
            raise Refused("automation needs an explicit bounded paid dispatch count")
        if crew.get("require_dallas", True) is not True:
            raise Refused("automated judgments require independent Dallas review")
        if not self.b.policy.get("automation_enabled"):
            raise Refused("bounded review workers are not installed")

    def status(self, cid):
        self.b.store.campaign(cid)
        row = self.db.execute("SELECT * FROM automation WHERE campaign=?", (cid,)).fetchone()
        jobs = [dict(j) for j in self.db.execute(
            "SELECT id,role,kind,state,reserved,claimed,usage,failure_diagnostic FROM review_jobs WHERE campaign=? ORDER BY rowid", (cid,))]
        for job in jobs:
            recovery = self.db.execute("SELECT state,failure,event_id FROM review_recoveries WHERE job=?", (job["id"],)).fetchone()
            job["recovery"] = dict(recovery) if recovery else None
        for job in jobs:
            if job["failure_diagnostic"]:
                job["failure_diagnostic"] = json.loads(job["failure_diagnostic"])
        spec = self.spec(cid)
        total = self.spent(spec["budget"])[0] if spec else 0
        return {"control": dict(row) if row else None, "jobs": jobs,
                "reserved_microusd": sum(j["reserved"] for j in jobs), "shared_budget_reserved_microusd": total,
                "accounting": "Conservative retained reservations, not a provider bill. Ambiguous calls are never refunded or retried."}

    def spent(self, budget):
        total, count = 0, 0
        for j in self.db.execute("SELECT campaign,reserved FROM review_jobs WHERE reserved>0"):
            if self.spec(j["campaign"])["budget"] == budget:
                total += j["reserved"]
                count += 1
        return total, count

    def arm(self, cid):
        spec = self.spec(cid)
        if spec:
            self.validate_spec(spec, self.b.store.definition(self.b.store.campaign(cid)["definition"])[0]["definition"]["crew"])
            policy = self.b.store.definition(self.b.store.campaign(cid)["definition"])[0]["definition"]["policy"]
            deadline = min(self.now + policy["max_elapsed_s"], timestamp(spec["not_after"]))
            self.db.execute("INSERT OR IGNORE INTO automation VALUES(?,?,?,NULL)", (cid, deadline, "active"))
            self.b.store.save()

    def park(self, cid, reason):
        self.db.execute("UPDATE automation SET state='parked',reason=? WHERE campaign=?", (reason, cid))
        self.db.execute("UPDATE review_jobs SET state='cancelled' WHERE campaign=? AND state='queued'", (cid,))
        self.b.store.save()
        return self.stop(cid, "pause", reason)

    def stop(self, cid, command, reason):
        # The stable receipt survives restarts and lost responses. Never invent a new write ID.
        rid = "auto-" + digest({"campaign": cid, "command": command})[:32]
        old = self.db.execute("SELECT state,result FROM receipts WHERE id=?", (rid,)).fetchone()
        if old and old["state"] == "pending":
            log = self.b.read("log", {"campaign": cid})
            applied = next((r for r in log if r.get("idempotency_key") == rid and r.get("outcome") == "applied"), None)
            if applied:
                if command == "abort":
                    # The abort row commits before the route cancels active cycles. A lost
                    # response after that row is NOT proof of cancellation. Replay only this
                    # already-applied abort's exact idempotency key to finish cancellation.
                    progress = Evidence(self.b).handle("progress", {"campaign": cid})
                    terminal = {"completed", "failed", "cancelled"}
                    if any(c.get("status") not in terminal for c in progress["cycles"]):
                        result = self.b.api("control", "POST", f"/api/v1/campaigns/{cid}/abort", {
                            "reason": "Bounded campaign automation deadline reached", "idempotency_key": rid})
                        self.db.execute("UPDATE receipts SET state='done',result=? WHERE id=?", (canonical(result), rid))
                        self.b.store.save()
                        return result
                self.db.execute("UPDATE receipts SET state='done',result=? WHERE id=?", (canonical(applied), rid))
                self.b.store.save()
                return applied
            raise Refused("automatic stop outcome unresolved; owner inspection required")
        current = self.b.read("status", {"campaign": cid})
        if current["state"] == "completed" or command == "pause" and current["state"] in {"paused", "escalated", "launch_blocked"}:
            return {"state": current["state"]}
        # A deadline stop is authorized in every nonterminal state. Do not bind it to a
        # transient state snapshot that can change between this read and the write.
        reason = "Bounded campaign automation " + ("deadline reached" if command == "abort" else "requires owner inspection")
        args = {"campaign": cid, "reason": reason}
        fingerprint = digest({"caller": "mother", "command": command, "args": args})
        if old:
            return json.loads(old["result"])
        self.db.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)", (rid, "mother", fingerprint, "pending", None, self.now))
        self.b.store.save()
        result = self.b.api("control", "POST", f"/api/v1/campaigns/{cid}/{command}", {"reason": reason, "idempotency_key": rid})
        self.db.execute("UPDATE receipts SET state='done',result=? WHERE id=?", (canonical(result), rid))
        self.b.store.save()
        return result

    def queue(self, cid, role, kind, packet, gate=None, parent=None):
        jid = "job_" + digest({"campaign": cid, "kind": kind, "gate": gate, "parent": parent})[:32]
        if self.db.execute("SELECT 1 FROM review_jobs WHERE id=?", (jid,)).fetchone():
            return jid
        persona = Path(self.b.policy["review_personas"][role]).read_text()
        payload = {"packet": packet, "gate": gate, "parent": parent,
                   "body": body(role, kind, packet, persona)}
        item = self.b.store.campaign(cid)
        payload["destination"] = {"channel": item["channel"], "thread": item["thread"]}
        self.db.execute("INSERT INTO review_jobs(id,campaign,role,kind,state,payload) VALUES(?,?,?,?,?,?)",
                        (jid, cid, role, kind, "queued", canonical(payload)))
        self.b.store.save()
        return jid

    def packet(self, cid, gate=None):
        p = self.b.read("packet", {"campaign": cid})
        # The control log and ledger are authoritative. Artifact excerpts are never passed
        # off as full records: selected authoritative documents are included in full.
        packet = {k: p[k] for k in ("campaign", "ledger", "log", "escalations")}
        approved, _ = self.b.store.definition(self.b.store.campaign(cid)["definition"])
        packet["approved_policy"] = approved["definition"]["policy"]
        packet["budget"] = self.status(cid)
        evidence = Evidence(self.b)
        progress = evidence.handle("progress", {"campaign": cid})
        # Closing interpretation needs outcomes and interventions, not every historical
        # planning document. Keep the current gate's full cycle and summarize prior cycles.
        packet["cycles"] = []
        for cycle in progress["cycles"]:
            if gate and cycle["cycle_id"] == gate["cycle"]:
                packet["cycles"].append(cycle)
            else:
                packet["cycles"].append({k: cycle.get(k) for k in
                                         ("cycle_id", "kind", "status", "runs", "cycle_outcome")})
        packet["artifacts"] = []
        if gate is None:
            selected = CLOSING_EVIDENCE_TYPES
            required = set()
        else:
            contract = GATE_EVIDENCE.get(gate.get("gate"))
            if contract is None:
                raise Refused("uncommissioned gate; no evidence contract")
            selected = contract["included"]
            required = contract["required"]
        present = set()
        # A gate's evidence is its own run's; listing other cycles only adds reads that can fail.
        cycles = [c for c in progress["cycles"] if not gate or c["cycle_id"] == gate["cycle"]]
        for cycle in cycles:
            for meta in evidence.listing(f"/api/v1/projects/{identifier(p['campaign']['project_id'])}/cycles/{cycle['cycle_id']}/artifacts"):
                if gate and meta.get("run_id") != gate["run"]:
                    continue
                key = evidence_key(meta)
                if key in selected:
                    try:
                        full = evidence.content(p["campaign"], meta["artifact_id"])
                    except Refused as error:
                        raise Refused(f"evidence hold: {error}") from None
                    packet["artifacts"].append({"artifact_id": meta["artifact_id"], "filename": meta["filename"],
                                                 "sha256": full["sha256"], "content": full["content"], "complete": True})
                    present.add(key)
        missing = required - present
        if missing:
            raise Refused(f"required evidence missing for {gate['gate']}: {', '.join(sorted(missing))}")
        packet["evidence_selection"] = {"included_types": sorted(selected), "required_types": sorted(required),
            "source_files_included": False, "note": "A proposal ruling authorizes work, not acceptance of implemented code. Full source is available through campaignctl artifact. Hold if needed evidence is absent."}
        if gate:
            packet["gate"] = gate
            packet["decision_contract"] = decision_contract(packet)
        packet["references"] = [r["entry_id"] for r in p["log"]] + [a["artifact_id"] for a in packet["artifacts"]]
        return packet

    def current_decision_packet(self, cid, gate):
        campaign = self.b.read("status", {"campaign": cid})
        cycle, _ = Evidence(self.b).cycle(campaign, gate["cycle"])
        approved, _ = self.b.store.definition(self.b.store.campaign(cid)["definition"])
        return {"campaign": campaign, "approved_policy": approved["definition"]["policy"],
                "gate": gate, "cycles": [cycle]}

    def policy_hold(self, cid, jid, reason):
        diagnostic = {"stage": "result_validation", "error": "Refused", "reason_code": "decision_policy_forbidden"}
        self.db.execute("UPDATE review_jobs SET failure_diagnostic=? WHERE id=?", (canonical(diagnostic), jid))
        self.b.store.save()
        self.park(cid, reason)

    def advance(self, cid):
        spec = self.spec(cid)
        if not spec:
            return {"automatic_reviews": "disabled"}
        control = self.db.execute("SELECT * FROM automation WHERE campaign=?", (cid,)).fetchone()
        if not control:
            return {"automatic_reviews": "not started"}
        if control["state"] == "closed":
            return self.status(cid)
        if self.now >= control["deadline"]:
            self.db.execute("UPDATE review_jobs SET state='cancelled' WHERE campaign=? AND state='queued'", (cid,))
            self.db.execute("UPDATE automation SET state='expired',reason='deadline reached' WHERE campaign=?", (cid,))
            self.b.store.save()
            self.stop(cid, "abort", "deadline reached")
            return self.status(cid)
        if control["state"] == "parked":
            self.stop(cid, "pause", control["reason"])
            return self.status(cid)
        if control["state"] != "active":
            return self.status(cid)
        stale = self.db.execute("SELECT id FROM review_jobs WHERE campaign=? AND state='claimed' AND claimed<?",
                                (cid, self.now - 900)).fetchone()
        if stale:
            self.db.execute("UPDATE review_jobs SET state='uncertain' WHERE id=?", (stale[0],))
            self.park(cid, "review worker timed out; reservation retained")
            return self.status(cid)
        p = self.b.read("packet", {"campaign": cid})
        state = p["campaign"]["state"]
        try:
            if state == "completed":
                # One closing interpretation per campaign. No model retry on failure.
                if p.get("analysis"):
                    self.db.execute("UPDATE automation SET state='closed' WHERE campaign=?", (cid,))
                    self.b.store.save()
                else:
                    self.queue(cid, "ripley", "analysis", self.packet(cid))
            elif state in {"paused", "escalated", "launch_blocked"}:
                self.park(cid, "runtime requires an owner decision")
            else:
                gates = Evidence(self.b).handle("progress", {"campaign": cid})["gates"]
                if len(gates) > 1:
                    raise Refused("more than one waiting gate; owner inspection required")
                for gate in gates:
                    if gate["gate"] not in {"progress_plan_review", "progress_increment_ruling"}:
                        raise Refused("uncommissioned gate")
                    # Give SquadOps its no-open-questions automatic approval interval first.
                    if self.now - timestamp(gate["opened_at"]) < 30:
                        continue
                    self.queue(cid, "ripley", "decision", self.packet(cid, gate), gate)
        except Refused as e:
            self.park(cid, str(e))
        return self.status(cid)

    def claim(self, role):
        if role not in {"ripley", "dallas"}:
            raise Refused("only a review role can claim its jobs")
        row = self.db.execute("SELECT * FROM review_jobs WHERE role=? AND state='queued' ORDER BY rowid LIMIT 1", (role,)).fetchone()
        if not row:
            return None
        cid, spec = row["campaign"], self.spec(row["campaign"])
        control = self.db.execute("SELECT * FROM automation WHERE campaign=?", (cid,)).fetchone()
        if not control or control["state"] != "active" or self.now + 900 > control["deadline"]:
            self.park(cid, "insufficient time for a bounded review")
            return None
        current = self.b.read("status", {"campaign": cid})
        if current["state"] in {"paused", "escalated", "launch_blocked", "draft"}:
            self.park(cid, "runtime is held; no new review authorized")
            return None
        if (row["kind"] == "analysis") != (current["state"] == "completed"):
            self.db.execute("UPDATE review_jobs SET state='cancelled' WHERE id=?", (row["id"],))
            self.b.store.save()
            return None
        budget = self.budget(spec["budget"])
        total, count = self.spent(spec["budget"])
        crew = self.b.store.definition(self.b.store.campaign(cid)["definition"])[0]["definition"]["crew"]
        campaign_count = self.db.execute("SELECT count(*) FROM review_jobs WHERE campaign=? AND reserved>0", (cid,)).fetchone()[0]
        # Preserve one complete call for closing analysis until it is claimed.
        # This call reserves for its own request; the closing call kept in hand is not built yet.
        reserve = reservation_microusd(self.now, len(canonical(json.loads(row["payload"])["body"]).encode()))
        closing = 0 if row["kind"] == "analysis" else reservation_microusd(self.now)
        if (self.now >= timestamp(budget["expires_at"])
                or total + reserve + closing > budget["cap_microusd"]
                or count + 1 + bool(closing) > budget["max_dispatches"]
                or campaign_count + 1 + bool(closing) > crew["paid_dispatches"]):
            self.park(cid, "review allowance exhausted; no provider call made")
            return None
        payload = json.loads(row["payload"])
        gate = payload["gate"]
        if gate:
            live = Evidence(self.b).handle("progress", {"campaign": cid})["gates"]
            if gate not in live:
                self.db.execute("UPDATE review_jobs SET state='cancelled' WHERE id=?", (row["id"],))
                self.b.store.save()
                return None
            if row["kind"] == "review" and payload["packet"]["proposed_decision"]["decision"] == "returned_for_revision":
                try:
                    validate_decision(self.current_decision_packet(cid, gate), payload["packet"]["proposed_decision"])
                except Exception:
                    self.db.execute("UPDATE review_jobs SET state='cancelled' WHERE id=?", (row["id"],))
                    self.b.store.save()
                    self.policy_hold(cid, row["id"], "proposed revision authority could not be verified; no Dallas call made")
                    return None
        self.db.execute("UPDATE review_jobs SET state='claimed',claimed=?,reserved=? WHERE id=?",
                        (self.now, reserve, row["id"]))
        self.b.store.save()  # Reservation is durable BEFORE any provider access.
        return {"id": row["id"], "campaign": cid, "role": role, "kind": row["kind"],
                "payload": payload, "deadline": min(control["deadline"], self.now + 840)}

    def result(self, role, args, event):
        exact(args, {"job", "result", "usage"})
        job = self.db.execute("SELECT * FROM review_jobs WHERE id=?", (identifier(args["job"]),)).fetchone()
        if not job or job["role"] != role or job["state"] != "claimed":
            raise Refused("review job is not claimed by this role")
        cid = job["campaign"]
        control = self.db.execute("SELECT * FROM automation WHERE campaign=?", (cid,)).fetchone()
        if control["state"] != "active" or self.now >= control["deadline"] or self.now - job["claimed"] >= 900:
            raise Refused("review arrived after its active authorization window")
        payload = json.loads(job["payload"])
        result = validate(job["kind"], args["result"], payload["packet"]["references"], payload["packet"])
        self.b.verify_event(event, role, "campaign-job-result", {"job": job["id"], "result": result})
        self.db.execute("UPDATE review_jobs SET state='done',result=?,proof=?,usage=? WHERE id=?",
                        (canonical(result), canonical(event), canonical(args["usage"]), job["id"]))
        self.b.store.save()
        if job["kind"] == "analysis":
            # A signed result is the analysis record; the watcher publishes it in Buzz.
            analysis = {"campaign": cid, "analysis": result["notes"], "evidence": result["evidence"], "decision_event": event["id"]}
            self.db.execute("INSERT OR REPLACE INTO analyses VALUES(?,?)", (cid, canonical(analysis)))
            self.db.execute("UPDATE automation SET state='closed' WHERE campaign=?", (cid,))
            self.b.store.save()
        elif job["kind"] == "decision":
            if result["decision"] == "needs_owner":
                self.park(cid, "Ripley requires an owner decision")
            else:
                if result["decision"] == "returned_for_revision":
                    try:
                        validate_decision(self.current_decision_packet(cid, payload["gate"]), result)
                    except Exception:
                        self.policy_hold(cid, job["id"], "proposal revision authority could not be verified; owner inspection required")
                        return {"stored": True, "parked": True}
                packet = {**payload["packet"], "proposed_decision": result,
                          "decision_job": job["id"], "decision_sha256": digest(result),
                          "decision_request": decision_request(cid, payload, result)}
                try:
                    self.queue(cid, "dallas", "review", packet, payload["gate"], job["id"])
                except Refused as e:
                    self.park(cid, str(e))
        elif result["blocking"]:
            self.park(cid, "Dallas has blocking findings; owner inspection required")
        # Successful Dallas review is exposed to Ripley's deterministic submission worker.
        return {"stored": True}

    def authorize_recovery(self, caller, args):
        if caller != "owner":
            raise Refused("only the owner can authorize publication recovery")
        exact(args, {"job"}, {"no_matching_event_verified", "existing_event_id"})
        if set(args) == {"job", "no_matching_event_verified"}:
            if args["no_matching_event_verified"] is not True:
                raise Refused("owner must verify that no matching signed Buzz result is already published")
            event_id = None
        elif set(args) == {"job", "existing_event_id"}:
            event_id = args["existing_event_id"]
            if not isinstance(event_id, str) or not re.fullmatch(r"[0-9a-f]{64}", event_id):
                raise Refused("existing signed result needs its Buzz event ID")
        else:
            raise Refused("choose exactly one recovery mode: verified absence or an existing event ID")
        jid = identifier(args["job"])
        job = self.db.execute("SELECT * FROM review_jobs WHERE id=?", (jid,)).fetchone()
        if not job or job["state"] != "uncertain" or job["reserved"] <= 0 or job["role"] not in {"ripley", "dallas"}:
            raise Refused("job is not an eligible reserved review")
        diagnostic = json.loads(job["failure_diagnostic"] or "{}")
        if diagnostic.get("stage") != "buzz_publication":
            raise Refused("recovery is limited to a failed Buzz publication")
        control = self.db.execute("SELECT * FROM automation WHERE campaign=?", (job["campaign"],)).fetchone()
        recoverable_control = (control and (control["state"] == "parked" and self.now + 180 < control["deadline"]
                               or control["state"] == "expired" and control["reason"] == "deadline reached"))
        if not recoverable_control:
            raise Refused("campaign is not in a recoverable parked window")
        old = self.db.execute("SELECT state,claimed FROM review_recoveries WHERE job=?", (jid,)).fetchone()
        old_event = self.db.execute("SELECT event_id FROM review_recoveries WHERE job=?", (jid,)).fetchone()
        if old_event and old_event["event_id"] and event_id != old_event["event_id"]:
            raise Refused("a Buzz event ID is already recorded; recovery must adopt it without republication")
        if old and (old["state"] in {"queued", "done"}
                    or old["state"] == "claimed" and self.now - old["claimed"] < 900):
            raise Refused("publication recovery is already authorized or completed")
        self.db.execute("INSERT INTO review_recoveries(job,state,authorized,claimed,failure,event_id) VALUES(?, 'queued', ?, NULL, NULL, ?) "
                        "ON CONFLICT(job) DO UPDATE SET state='queued',authorized=excluded.authorized,claimed=NULL,failure=NULL,event_id=excluded.event_id",
                        (jid, self.now, event_id))
        self.b.store.save()
        return {"authorized": True, "job": jid, "provider_calls": 0, "will_publish": event_id is None}

    def claim_recovery(self, role):
        if role not in {"ripley", "dallas"}:
            raise Refused("only the assigned review role can recover its publication")
        row = self.db.execute("SELECT r.job,r.event_id,j.campaign,j.role,j.kind,j.payload FROM review_recoveries r "
                              "JOIN review_jobs j ON j.id=r.job WHERE r.state='queued' AND j.role=? ORDER BY r.authorized LIMIT 1",
                              (role,)).fetchone()
        if not row:
            return None
        control = self.db.execute("SELECT state,deadline,reason FROM automation WHERE campaign=?", (row["campaign"],)).fetchone()
        job_state = self.db.execute("SELECT state FROM review_jobs WHERE id=?", (row["job"],)).fetchone()
        recoverable_control = (control and (control["state"] == "parked" and self.now + 180 < control["deadline"]
                               or control["state"] == "expired" and control["reason"] == "deadline reached"))
        if not recoverable_control or job_state[0] != "uncertain":
            self.db.execute("UPDATE review_recoveries SET state='failed',failure='AuthorizationExpired' WHERE job=?",
                            (row["job"],))
            self.b.store.save()
            return None
        self.db.execute("UPDATE review_recoveries SET state='claimed',claimed=? WHERE job=? AND state='queued'",
                        (self.now, row["job"]))
        self.b.store.save()
        return {"id": row["job"], "campaign": row["campaign"], "role": row["role"], "kind": row["kind"],
                "event_id": row["event_id"],
                "payload": json.loads(row["payload"])}

    def recover_result(self, role, args, event):
        exact(args, {"job", "result", "usage"})
        jid = identifier(args["job"])
        row = self.db.execute("SELECT j.*,c.state AS control_state,c.deadline,c.reason AS control_reason,r.state AS recovery_state "
                              "FROM review_jobs j JOIN automation c ON c.campaign=j.campaign "
                              "JOIN review_recoveries r ON r.job=j.id WHERE j.id=?", (jid,)).fetchone()
        recoverable_control = (row and (row["control_state"] == "parked" and self.now < row["deadline"]
                               or row["control_state"] == "expired" and row["control_reason"] == "deadline reached"))
        if (not row or row["role"] != role or row["state"] != "uncertain" or row["recovery_state"] != "claimed"
                or not recoverable_control):
            raise Refused("publication recovery is not currently authorized for this role")
        if json.loads(row["failure_diagnostic"] or "{}").get("stage") != "buzz_publication":
            raise Refused("job did not fail during Buzz publication")
        payload = json.loads(row["payload"])
        result = validate(row["kind"], args["result"], payload["packet"]["references"], payload["packet"])
        if not isinstance(args["usage"], dict) or len(canonical(args["usage"]).encode()) > 4096:
            raise Refused("saved review usage is invalid")
        self.b.verify_event(event, role, "campaign-job-result", {"job": jid, "result": result},
                            not_before=row["claimed"] - 30)
        self.db.execute("UPDATE review_jobs SET state='done',result=?,proof=?,usage=? WHERE id=?",
                        (canonical(result), canonical(event), canonical(args["usage"]), jid))
        self.db.execute("UPDATE review_recoveries SET state='done',failure=NULL WHERE job=?", (jid,))
        self.b.store.save()
        # Keep the campaign parked. Recovery records the saved result but never resumes work,
        # queues another paid review, or submits a SquadOps gate.
        return {"stored": True, "campaign_control_unchanged": True, "provider_calls": 0}

    def record_recovery_event(self, role, args):
        exact(args, {"job", "event_id"})
        jid = identifier(args["job"])
        if not isinstance(args["event_id"], str) or not re.fullmatch(r"[0-9a-f]{64}", args["event_id"]):
            raise Refused("recovery event ID must be hex64")
        row = self.db.execute("SELECT j.role,r.state,r.event_id FROM review_jobs j "
                              "JOIN review_recoveries r ON r.job=j.id WHERE j.id=?", (jid,)).fetchone()
        if not row or row["role"] != role or row["state"] != "claimed":
            raise Refused("recovery event does not belong to this claimed role job")
        if row["event_id"] and row["event_id"] != args["event_id"]:
            raise Refused("recovery already records a different event ID")
        self.db.execute("UPDATE review_recoveries SET event_id=? WHERE job=?", (args["event_id"], jid))
        self.b.store.save()
        return {"stored": True, "provider_calls": 0}

    def submit(self, caller):
        if caller != "ripley":
            raise Refused("gate submission belongs to Ripley")
        for review in self.db.execute("SELECT * FROM review_jobs WHERE kind='review' AND state='done' ORDER BY rowid").fetchall():
            payload = json.loads(review["payload"])
            if json.loads(review["result"])["blocking"]:
                continue
            decision = self.db.execute("SELECT * FROM review_jobs WHERE id=?", (payload["parent"],)).fetchone()
            cid = review["campaign"]
            control = self.db.execute("SELECT * FROM automation WHERE campaign=?", (cid,)).fetchone()
            if control["state"] != "active" or self.now >= control["deadline"]:
                continue
            current = self.b.read("status", {"campaign": cid})
            if current["state"] in {"paused", "escalated", "launch_blocked", "completed", "draft"}:
                self.park(cid, "runtime moved out of the gate's active authorization")
                continue
            req = payload["packet"]["decision_request"]
            old = self.db.execute("SELECT state FROM receipts WHERE id=?", (req["request_id"],)).fetchone()
            if old:
                if old[0] == "done":
                    self.db.execute("UPDATE review_jobs SET state='submitted' WHERE id=?", (review["id"],))
                    self.b.store.save()
                    continue
                self.park(cid, "gate submission outcome unresolved; no write retry")
                continue
            if payload["gate"] not in Evidence(self.b).handle("progress", {"campaign": cid})["gates"]:
                self.db.execute("UPDATE review_jobs SET state='cancelled' WHERE id=?", (review["id"],))
                self.b.store.save()
                continue
            try:
                result = self.b.handle("ripley", {**req, "decision_event": json.loads(decision["proof"]),
                                                  "review_event": json.loads(review["proof"])})
                self.db.execute("UPDATE review_jobs SET state='submitted' WHERE id=?", (review["id"],))
                self.b.store.save()
                return result
            except Exception as error:
                if isinstance(error, Refused) and str(error) == POLICY_REFUSAL:
                    self.policy_hold(cid, decision["id"], "proposal revision authority changed before gate submission; owner inspection required")
                else:
                    self.park(cid, "gate submission failed; owner inspection required")
                raise
        return None

    def handle(self, caller, command, args, request):
        if command == "review-recovery-authorize":
            return self.authorize_recovery(caller, args)
        if command == "review-recovery-claim":
            exact(args, set())
            return self.claim_recovery(caller)
        if command == "review-recovery-result":
            return self.recover_result(caller, args, request.get("decision_event"))
        if command == "review-recovery-pending":
            return self.record_recovery_event(caller, args)
        if command == "review-recovery-failed":
            exact(args, {"job", "error"})
            jid = identifier(args["job"])
            if not isinstance(args["error"], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,63}", args["error"]):
                raise Refused("recovery failure must contain only an exception class")
            row = self.db.execute("SELECT j.role,r.state FROM review_jobs j JOIN review_recoveries r ON r.job=j.id WHERE j.id=?", (jid,)).fetchone()
            if not row or row["role"] != caller or row["state"] != "claimed":
                raise Refused("recovery failure is not owned by this role")
            self.db.execute("UPDATE review_recoveries SET state='failed',failure=? WHERE job=?", (args["error"], jid))
            self.b.store.save()
            return {"failed": True, "provider_calls": 0}
        if command == "approve-budget":
            if caller != "owner":
                raise Refused("review allowances belong to the owner")
            exact(args, {"name", "cap_microusd", "max_dispatches", "expires_at"})
            identifier(args["name"])
            # A guard against a mistyped approval, not the spending boundary: that is each provider
            # console's hard limit. Raised from the first pilots' $10 / 20 calls on 2026-10-30.
            if type(args["cap_microusd"]) is not int or not 0 < args["cap_microusd"] <= 25000000:
                raise Refused("a review allowance must be at most twenty-five dollars")
            if type(args["max_dispatches"]) is not int or not 1 <= args["max_dispatches"] <= 60:
                raise Refused("a review allowance needs at most sixty calls")
            if not self.now < timestamp(args["expires_at"]):
                raise Refused("review allowance must expire in the future")
            old = self.db.execute("SELECT body FROM review_budgets WHERE name=?", (args["name"],)).fetchone()
            if old and old[0] != canonical(args):
                raise Refused("review allowances are immutable")
            self.db.execute("INSERT OR IGNORE INTO review_budgets VALUES(?,?)", (args["name"], canonical(args)))
            self.b.store.save()
            return {"approved": True, "reservation_per_call_microusd": reservation_microusd(self.now),
                    "price_basis": price_basis(self.now) or "current"}
        if command in {"automation", "advance"}:
            exact(args, {"campaign"})
            if command == "advance" and caller != "mother":
                raise Refused("automatic routing belongs to Mother")
            return self.status(args["campaign"]) if command == "automation" else self.advance(args["campaign"])
        if command == "review-claim":
            exact(args, set())
            return self.claim(caller)
        if command == "review-submit":
            exact(args, set())
            return self.submit(caller)
        if command == "review-result":
            return self.result(caller, args, request.get("decision_event"))
        exact(args, {"job"}, {"diagnostic"})
        job = self.db.execute("SELECT * FROM review_jobs WHERE id=?", (identifier(args["job"]),)).fetchone()
        if not job or job["role"] != caller or job["state"] != "claimed":
            raise Refused("review failure is not owned by this caller")
        diagnostic = args.get("diagnostic")
        if diagnostic is not None:
            exact(diagnostic, {"stage", "error"}, {"http_status", "reason_code"})
            stages = {"preflight", "provider_setup", "provider_http", "provider_transport", "provider_response",
                      "provider_request", "result_validation", "recovery_persist", "buzz_publication",
                      "broker_result_submit"}
            if diagnostic["stage"] not in stages:
                raise Refused("review diagnostic stage is not recognized")
            if not isinstance(diagnostic["error"], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,63}", diagnostic["error"]):
                raise Refused("review diagnostic error class is invalid")
            if "http_status" in diagnostic and (diagnostic["stage"] != "provider_http"
                    or type(diagnostic["http_status"]) is not int or not 100 <= diagnostic["http_status"] <= 599):
                raise Refused("review diagnostic HTTP status is invalid")
            reason_codes = {"result_shape_invalid", "notes_invalid", "evidence_refs_invalid", "decision_invalid",
                            "classification_rationale_missing", "blocking_flag_invalid", "provider_model_mismatch",
                            "provider_incomplete_response", "provider_json_invalid", "provider_response_oversized",
                            "request_bound_violation", "provider_http_error", "review_refused", "decision_policy_forbidden"}
            if "reason_code" in diagnostic and diagnostic["reason_code"] not in reason_codes:
                raise Refused("review diagnostic reason code is invalid")
        serialized = canonical(diagnostic) if diagnostic is not None else None
        self.db.execute("UPDATE review_jobs SET state='uncertain',failure_diagnostic=? WHERE id=?",
                        (serialized, job["id"]))
        reason = ("review decision conflicts with proposal revision policy; owner inspection required"
                  if diagnostic and diagnostic.get("reason_code") == "decision_policy_forbidden" else
                  "provider or worker failure; no automatic retry; reservation retained")
        self.park(job["campaign"], reason)
        return {"parked": True}
