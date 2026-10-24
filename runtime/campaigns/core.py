"""Caller-bounded campaign operations. Runtime records remain authoritative in SquadOps."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path


class Refused(Exception):
    """An explicit policy, evidence or state refusal, safe to show the caller."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", value):
        raise Refused("invalid identifier")
    return value


def exact(data, required, optional=()):
    if not isinstance(data, dict) or set(data) - set(required) - set(optional) or set(required) - set(data):
        raise Refused("missing or unexpected request fields")


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS definitions(name TEXT PRIMARY KEY, body TEXT, sha TEXT);
            CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY, definition TEXT,
                channel TEXT, thread TEXT, owner TEXT);
            CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, caller TEXT, hash TEXT,
                state TEXT, result TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, fingerprint TEXT,
                status TEXT, failures INTEGER DEFAULT 0, report TEXT);
            CREATE TABLE IF NOT EXISTS analyses(campaign TEXT PRIMARY KEY, body TEXT);
            CREATE TABLE IF NOT EXISTS launches(definition TEXT PRIMARY KEY, request TEXT UNIQUE, campaign TEXT);
        """)

    def definition(self, name):
        row = self.db.execute("SELECT * FROM definitions WHERE name=?", (identifier(name),)).fetchone()
        if row is None:
            raise Refused("definition is not owner-approved")
        return json.loads(row["body"]), row["sha"]

    def campaign(self, cid):
        row = self.db.execute("SELECT * FROM campaigns WHERE id=?", (identifier(cid),)).fetchone()
        if row is None:
            raise Refused("campaign is not registered with this broker")
        return dict(row)

    def save(self):
        self.db.commit()


READS = {"status", "log", "ledger", "package", "escalations", "lease"}
OPERATIONS = {"create", "start", "pause", "resume", "abort", "materialize", "lease-take", "lease-give"}
GATES = {"plan", "increment"}
ROLES = {"mother", "ripley", "dallas", "parker", "brett", "ash", "lambert", "owner", "watcher"}


class Broker:
    def __init__(self, store, api, policy, verify_event, window=None):
        self.store, self.api, self.policy, self.verify_event = store, api, policy, verify_event
        self.window = window

    def handle(self, caller, request):
        if caller not in ROLES:
            raise Refused("caller is not admitted")
        exact(request, {"command", "args"}, {"request_id", "decision_event", "review_event"})
        command, args = request["command"], request["args"]
        if not isinstance(args, dict):
            raise Refused("args must be an object")
        if command == "tracked":
            exact(args, set())
            return [dict(row) for row in self.store.db.execute("SELECT * FROM campaigns ORDER BY id")]
        if command == "open-window":
            if caller not in {"mother", "watcher"} or self.window is None:
                raise Refused("window coordination is unavailable to this caller")
            exact(args, {"campaign"})
            cid = identifier(args["campaign"])
            self.store.campaign(cid)
            campaign = self.api("read", "GET", f"/api/v1/campaigns/{cid}", None)
            if campaign["state"] != "awaiting_ruling":
                raise Refused("local inference window requires an open increment gate")
            lease = self.api("read", "GET", f"/api/v1/campaigns/{cid}/lease", None)
            if not lease or not lease.get("supervisor_holds"):
                import uuid
                self.api("control", "POST", f"/api/v1/campaigns/{cid}/lease", {
                    "reason": "crew evidence window at the open increment gate", "idempotency_key": str(uuid.uuid4()),
                    "expires_in_s": min(campaign["policy"]["lease_expiry_s"], 600),
                })
                lease = self.api("read", "GET", f"/api/v1/campaigns/{cid}/lease", None)
            if not lease or not lease.get("supervisor_holds") or lease.get("held_by") != self.policy["control_principal"]:
                raise Refused("the broker does not hold a live box lease")
            self.window.open(lease["expires_at"])
            return {"window": "open", "lease": lease}
        if command == "analysis":
            if caller != "ripley":
                raise Refused("closing analysis belongs to Ripley")
            exact(args, {"campaign", "analysis", "evidence"})
            self.store.campaign(args["campaign"])
            if not isinstance(args["analysis"], str) or not args["analysis"].strip() or not isinstance(args["evidence"], list):
                raise Refused("analysis needs text and evidence references")
            self.verify_event(request.get("decision_event"), "ripley", "campaign-analysis", args)
            current = self.read("status", {"campaign": args["campaign"]})
            if current["state"] != "completed":
                raise Refused("closing analysis requires a closed campaign")
            body = {**args, "decision_event": request["decision_event"]["id"]}
            self.store.db.execute("INSERT OR REPLACE INTO analyses VALUES(?,?)", (args["campaign"], canonical(body)))
            self.store.save()
            return {"stored_for_buzz_report": True, "sha256": digest(body)}
        if command in READS or command == "packet":
            return self.read(command, args)
        if command == "approve-definition":
            if caller != "owner":
                self.verify_event(request.get("decision_event"), "owner", "campaign-definition", args)
            return self.approve(args)
        if command in OPERATIONS:
            if caller != "mother":
                raise Refused("campaign operations belong to Mother")
        elif command in GATES:
            if caller != "ripley":
                raise Refused("gate decisions belong to Ripley")
        else:
            raise Refused("unknown command; no raw API or CLI pass-through exists")
        rid = identifier(request.get("request_id"))
        fingerprint = digest({"caller": caller, "command": command, "args": args})
        old = self.store.db.execute("SELECT * FROM receipts WHERE id=?", (rid,)).fetchone()
        if old:
            if old["caller"] != caller or old["hash"] != fingerprint:
                raise Refused("request id already binds different content")
            if old["state"] == "done":
                return {"replayed": True, "result": json.loads(old["result"])}
            raise Refused("previous attempt is unresolved; inspect SquadOps before any further action")
        if command in GATES:
            expected = {"command": command, "args": args, "request_id": rid}
            self.verify_event(request.get("decision_event"), "ripley", "campaign-decision", expected)
        # Construct and validate before reserving an action. A validation refusal has no side effect.
        principal, method, path, body, after = self.operation(command, args, rid, request)
        self.store.db.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)",
                             (rid, caller, fingerprint, "pending", None, time.time(),))
        if command == "create":
            # One owner approval buys one campaign, including an ambiguous creation attempt.
            self.store.db.execute("INSERT INTO launches VALUES(?,?,?)",
                                  (args["definition"], rid, body["campaign_id"]))
        self.store.save()
        try:
            if self.window is not None and (command == "start" or command in GATES or command == "lease-give"):
                self.window.close()
                if command in GATES:
                    lease = self.api("read", "GET", f"/api/v1/campaigns/{args['campaign']}/lease", None)
                    if lease and lease.get("supervisor_holds"):
                        if lease.get("held_by") != self.policy["control_principal"]:
                            raise Refused("another actor holds the box lease")
                        self.api("control", "POST", f"/api/v1/campaigns/{args['campaign']}/lease/release", {
                            "reason": "local harnesses stopped before Ripley's gate submission",
                            "idempotency_key": rid + "-lease-release",
                        })
            result = self.api(principal, method, path, body)
            if after:
                after(result)
            self.store.db.execute("UPDATE receipts SET state='done', result=? WHERE id=?",
                                  (canonical(result), rid))
            self.store.save()
            return {"replayed": False, "result": result}
        except Exception:
            # A transport failure may follow a committed action. Never repeat an ambiguous write.
            self.store.save()
            raise

    def approve(self, args):
        exact(args, {"name", "definition", "channel", "thread"})
        name = identifier(args["name"])
        identifier(args["channel"])
        identifier(args["thread"])
        definition = args["definition"]
        exact(definition, {"project_id", "objective", "policy"}, {"scenario_suite", "crew"})
        identifier(definition["project_id"])
        objective, policy = definition["objective"], definition["policy"]
        if not isinstance(objective, dict) or not isinstance(policy, dict):
            raise Refused("definition must carry objective and policy")
        if not objective.get("allowed_scope") or not objective.get("target_accepted_increments"):
            raise Refused("objective needs explicit scope and increment target")
        for field in ("max_cycles", "max_elapsed_s", "budget_tokens"):
            if type(policy.get(field)) is not int or policy[field] < 1:
                raise Refused(f"policy.{field} needs a positive bound")
        crew = definition.get("crew", {})
        exact(crew, set(), {"require_dallas", "paid_dispatches"})
        if type(crew.get("require_dallas", True)) is not bool:
            raise Refused("require_dallas must be boolean")
        # Version one never automatically dispatches metered roles. Owner can request them in Buzz.
        if crew.get("paid_dispatches", 0) != 0:
            raise Refused("automatic paid dispatch is not commissioned")
        stored = {**args, "definition": definition}
        sha = digest(definition)
        previous = self.store.db.execute("SELECT body FROM definitions WHERE name=?", (name,)).fetchone()
        if previous and previous["body"] != canonical(stored):
            raise Refused("approved definitions are immutable; approve a new name")
        self.store.db.execute("INSERT OR IGNORE INTO definitions VALUES(?,?,?)",
                             (name, canonical(stored), sha))
        self.store.save()
        return {"name": name, "sha256": sha, "approved": True}

    def read(self, command, args):
        exact(args, {"campaign"})
        cid = identifier(args["campaign"])
        base = f"/api/v1/campaigns/{cid}"
        if command == "packet":
            result = {"campaign": self.api("read", "GET", base, None)}
            for part in ("ledger", "escalations", "log"):
                result[part] = self.api("read", "GET", f"{base}/{part}", None)
            row = self.store.db.execute("SELECT body FROM analyses WHERE campaign=?", (cid,)).fetchone()
            result["analysis"] = json.loads(row["body"]) if row else None
            try:
                item = self.store.campaign(cid)
                definition, _ = self.store.definition(item["definition"])
                result["crew_policy"] = definition["definition"].get("crew", {})
            except Refused:
                result["crew_policy"] = {"paid_dispatches": 0}
            return result
        return self.api("read", "GET", base + ("" if command == "status" else f"/{command}"), None)

    def operation(self, command, args, rid, request):
        if command == "create":
            exact(args, {"definition", "reason"})
            approved, sha = self.store.definition(args["definition"])
            if self.store.db.execute("SELECT 1 FROM launches WHERE definition=?", (args["definition"],)).fetchone():
                raise Refused("definition already reserved for one campaign; a new campaign needs fresh owner approval")
            spec = approved["definition"]
            cid = "cmp_" + hashlib.sha256(rid.encode()).hexdigest()[:24]
            body = {k: v for k, v in spec.items() if k != "crew"}
            body.update(campaign_id=cid, reason=args["reason"], idempotency_key=rid,
                        definition={"path": "buzz-approved:" + args["definition"], "sha256": sha})

            def remember(result):
                actual = result["campaign"]["campaign_id"]
                if actual != cid:
                    raise Refused("API returned an unexpected campaign identity")
                self.store.db.execute("INSERT OR IGNORE INTO campaigns VALUES(?,?,?,?,?)",
                                      (cid, args["definition"], approved["channel"], approved["thread"], "mother"))
            return "control", "POST", "/api/v1/campaigns", body, remember
        cid = identifier(args.get("campaign"))
        record = self.store.campaign(cid)
        approved, _ = self.store.definition(record["definition"])
        campaign = self.api("read", "GET", f"/api/v1/campaigns/{cid}", None)
        if command in GATES:
            return self.gate(command, args, rid, request, campaign, approved)
        required = {"campaign", "reason"}
        if command == "lease-take":
            required.add("expires_in_s")
        exact(args, required)
        body = {"reason": args["reason"], "idempotency_key": rid, "expected_state": campaign["state"]}
        if not isinstance(args["reason"], str) or not args["reason"].strip():
            raise Refused("reason is required")
        if command == "resume":
            # The API also enforces this against the durable control log. Never send an action.
            if campaign["state"] != "paused":
                raise Refused("only the supervisor's own pause may be resumed")
        suffix = {"materialize": "package", "lease-take": "lease", "lease-give": "lease/release"}.get(command, command)
        if command == "lease-take":
            if type(args["expires_in_s"]) is not int or args["expires_in_s"] < 1:
                raise Refused("lease duration must be a positive integer")
            body["expires_in_s"] = args["expires_in_s"]
        if command == "materialize":
            body = None
        return "control", "POST", f"/api/v1/campaigns/{cid}/{suffix}", body, None

    def gate(self, command, args, rid, request, campaign, approved):
        required = {"campaign", "cycle", "run", "decision", "notes"}
        if command == "increment":
            required.add("binding")
        exact(args, required, {"classification", "classification_rationale"})
        for key in ("cycle", "run"):
            identifier(args[key])
        if args["decision"] not in {"approved", "approved_with_refinements", "rejected", "returned_for_revision"}:
            raise Refused("unsupported gate decision")
        if not isinstance(args["notes"], str) or not args["notes"].strip():
            raise Refused("a gate decision needs substantive notes")
        project = identifier(campaign["project_id"])
        base = f"/api/v1/projects/{project}/cycles/{args['cycle']}"
        cycle = self.api("read", "GET", base, None)
        if cycle.get("campaign_id") != args["campaign"]:
            raise Refused("cycle is not part of the named campaign")
        run = self.api("read", "GET", f"{base}/runs/{args['run']}", None)
        if run.get("cycle_id") != args["cycle"]:
            raise Refused("run is not part of the named cycle")
        gate_name = "progress_increment_ruling" if command == "increment" else "progress_plan_review"
        if any(g.get("gate_name") == gate_name for g in run.get("gate_decisions", [])):
            raise Refused("gate already has a decision")
        if approved["definition"].get("crew", {}).get("require_dallas", True):
            self.verify_event(request.get("review_event"), "dallas", "campaign-review",
                              {"campaign": args["campaign"], "cycle": args["cycle"], "run": args["run"],
                               "decision_sha256": digest({"command": command, "args": args}), "blocking": False})
        body = {"decision": args["decision"], "notes": args["notes"], "decided_by_kind": "agent"}
        sources = ["Decision event: " + str(request["decision_event"].get("id", "test-fixture"))]
        if request.get("review_event"):
            sources.append("Review event: " + str(request["review_event"].get("id", "test-fixture")))
        body["notes"] += "\n\n" + "\n".join(sources)
        if command == "increment":
            body.update(binding=args["binding"], idempotency_key=rid)
            for key in ("classification", "classification_rationale"):
                if key in args:
                    body[key] = args[key]
        return "review", "POST", f"{base}/runs/{args['run']}/gates/{gate_name}", body, None
