"""Bounded campaign evidence. Vault contents are data, never executable instructions."""
import hashlib
import json

from .core import Refused, exact, identifier

COMMANDS = {"progress", "cycle", "run", "checkpoints", "artifacts", "artifact", "triage"}
MAX_ARTIFACT = 262144


class Evidence:
    def __init__(self, broker):
        self.broker, self.api = broker, broker.api

    def cycle(self, campaign, cid):
        base = f"/api/v1/projects/{identifier(campaign['project_id'])}/cycles/{identifier(cid)}"
        cycle = self.api("read", "GET", base, None)
        if cycle.get("campaign_id") != campaign["campaign_id"] or cycle.get("project_id") != campaign["project_id"]:
            raise Refused("cycle is not part of this campaign and project")
        return cycle, base

    def run(self, cycle, base, rid):
        run = self.api("read", "GET", f"{base}/runs/{identifier(rid)}", None)
        if run.get("cycle_id") != cycle["cycle_id"] or run.get("run_id") != rid:
            raise Refused("run is not part of this cycle")
        return run

    def listing(self, path):
        items = []
        for offset in range(0, 2000, 100):
            page = json.loads(self.api.request("read", "GET", path, None, page=(offset, 100)))
            if not isinstance(page, list):
                raise Refused("evidence list unreadable")
            items.extend(page)
            if len(page) < 100:
                return items
        raise Refused("evidence list exceeds bounded pagination; no completeness inferred")

    def content(self, campaign, aid):
        aid = identifier(aid)
        meta = self.api("read", "GET", f"/api/v1/artifacts/{aid}", None)
        if meta.get("artifact_id") != aid or meta.get("project_id") != campaign["project_id"]:
            raise Refused("artifact is not part of this project")
        # Some accepted-tree member files were inherited from earlier cycles. They may only
        # be read through an accepted-tree manifest, not guessed by global artifact id.
        cycle, base = self.cycle(campaign, meta.get("cycle_id"))
        if meta.get("run_id"):
            self.run(cycle, base, meta["run_id"])
        if type(meta.get("size_bytes")) is not int or not 0 <= meta["size_bytes"] <= MAX_ARTIFACT:
            raise Refused("artifact exceeds the full-content limit; inspect outside the review worker")
        raw = self.api.request("read", "GET", f"/api/v1/artifacts/{aid}/download", None, limit=MAX_ARTIFACT)
        sha = hashlib.sha256(raw).hexdigest()
        if len(raw) != meta["size_bytes"] or sha != meta.get("content_hash"):
            raise Refused("artifact bytes do not match vault metadata")
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise Refused("artifact is binary; no text interpretation supplied") from None
        return {"metadata": meta, "content": content, "sha256": sha, "complete": True}

    def handle(self, command, args):
        optional = {"cycle", "run"} if command == "artifacts" else set()
        required = {"campaign"} | ({"cycle"} if command in {"cycle", "run", "checkpoints"} else set())
        if command in {"run", "checkpoints"}:
            required.add("run")
        if command == "artifact":
            required.add("artifact")
        exact(args, required, optional)
        self.broker.store.campaign(args["campaign"])
        campaign = self.broker.read("status", {"campaign": args["campaign"]})
        if command == "triage":
            from .automation import Automation
            progress = self.handle("progress", {"campaign": args["campaign"]})
            automation = Automation(self.broker).status(args["campaign"])
            ledger = self.broker.read("ledger", {"campaign": args["campaign"]})
            control_log = self.broker.read("log", {"campaign": args["campaign"]})
            findings = []
            for job in automation["jobs"]:
                if job["state"] != "uncertain":
                    continue
                diagnostic = job.get("failure_diagnostic")
                if not diagnostic:
                    findings.append({"job": job["id"], "classification": "failure_detail_unavailable",
                                     "detail": "This worker version did not persist a safe diagnostic. The review response cannot be reconstructed; do not retry this job."})
                elif diagnostic["stage"] == "result_validation":
                    findings.append({"job": job["id"], "classification": diagnostic.get("reason_code", "result_validation_failed"),
                                     "detail": "The provider returned a response, but the local review contract rejected it. No decision was committed; do not retry this job."})
                elif diagnostic["stage"] == "provider_http" and diagnostic.get("http_status") == 429:
                    findings.append({"job": job["id"], "classification": "provider_rate_limited",
                                     "detail": "The provider returned HTTP 429. No automatic retry was attempted."})
                elif diagnostic["stage"] == "provider_http":
                    findings.append({"job": job["id"], "classification": "provider_http_error",
                                     "detail": "The provider returned the recorded HTTP status. No automatic retry was attempted."})
                else:
                    findings.append({"job": job["id"], "classification": "worker_stage_failed",
                                     "detail": "See the bounded diagnostic fields for the failing stage and error class. No automatic retry was attempted."})
            return {
                "mode": "read_only_no_model_calls",
                "campaign": {k: campaign.get(k) for k in ("campaign_id", "project_id", "state", "outcome", "accepted")},
                "cycles": [{"cycle_id": c.get("cycle_id"), "kind": c.get("kind"), "status": c.get("status"),
                            "outcome": c.get("cycle_outcome", {}).get("verdict"),
                            "runs": [{"run_id": r.get("run_id"), "type": r.get("workload_type"),
                                      "status": r.get("status"), "finished_at": r.get("finished_at")}
                                     for r in c.get("runs", [])]} for c in progress["cycles"]],
                "gates": progress["gates"],
                "ledger": ledger,
                "review_jobs": [{k: j.get(k) for k in ("id", "role", "kind", "state", "reserved", "claimed", "failure_diagnostic")}
                                for j in automation["jobs"]],
                "reserved_microusd": automation["reserved_microusd"],
                "shared_budget_reserved_microusd": automation["shared_budget_reserved_microusd"],
                "findings": findings,
                "control_log": [{k: e.get(k) for k in ("seq", "operation", "outcome", "reason", "committed_at")}
                                for e in control_log[-12:]],
                "limitations": ["This report does not call a model.",
                                "Missing failure diagnostics cannot be recovered from the provider reservation.",
                                "This report contains metadata and references only; inspect artifacts separately when needed."],
            }
        if command == "artifact":
            return self.content(campaign, args["artifact"])
        if command == "progress":
            log = self.broker.read("log", {"campaign": args["campaign"]})
            ids = sorted({row["binding"]["cycle_id"] for row in log
                          if row.get("outcome") == "applied" and row.get("binding", {}).get("cycle_id")})
            if len(ids) > 50:
                raise Refused("campaign cycle count exceeds the evidence limit")
            cycles = [self.cycle(campaign, cid)[0] for cid in ids]
            return {"campaign": campaign, "cycles": cycles, "gates": waiting_gates(cycles),
                    "current_task": None,
                    "task_visibility": "Current task is not exposed by this read principal; checkpoints show completed work only."}
        if command == "artifacts" and "cycle" not in args:
            if "run" in args:
                raise Refused("run evidence requires its cycle")
            raise Refused("artifact listing requires a campaign cycle")
        cycle, base = self.cycle(campaign, args["cycle"])
        if command == "cycle":
            return cycle
        if "run" in args:
            run = self.run(cycle, base, args["run"])
            base += "/runs/" + args["run"]
        if command == "run":
            return run
        if command == "checkpoints":
            return self.api("read", "GET", base + "/checkpoints", None)
        return self.listing(base + "/artifacts")


def waiting_gates(cycles):
    gates = []
    for cycle in cycles:
        runs = [r for r in cycle.get("runs", []) if r["status"] != "cancelled"]
        if not runs:
            continue
        last = max(runs, key=lambda r: r["run_number"])
        if last["status"] != "completed" or not last.get("finished_at"):
            continue
        gate = next((w.get("gate") for w in cycle.get("applied_defaults", {}).get("workload_sequence", [])
                     if w.get("type") == last.get("workload_type")), None)
        if gate and not any(d.get("gate_name") == gate for d in last.get("gate_decisions", [])):
            gates.append({"cycle": cycle["cycle_id"], "run": last["run_id"], "gate": gate,
                          "opened_at": last["finished_at"]})
    return gates
