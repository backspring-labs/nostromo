"""Durable create/announce/start workflow; only Mother may request or execute it."""
import hashlib
import json
import re
import time

from .core import Refused, canonical, digest, exact, identifier
from .review import timestamp

COMMANDS = {"launch", "launches", "launch-status", "launch-advance", "launch-notice-claim",
            "launch-notice-result", "launch-notice-failed"}
LAUNCH_SECONDS = 600
NOTICE_LEASE_SECONDS = 180
NOTICE_ATTEMPTS = 3


class Launches:
    def __init__(self, broker, now=None):
        self.b, self.db = broker, broker.store.db
        self.now = time.time() if now is None else now

    def row(self, wid):
        row = self.db.execute("SELECT * FROM launch_workflows WHERE id=?", (identifier(wid),)).fetchone()
        if row is None:
            raise Refused("launch intent is not registered")
        return row

    def status(self, wid):
        row = self.row(wid)
        keys = ("id", "definition", "campaign", "channel", "thread", "create_request", "start_request",
                "state", "created", "deadline", "notice_phase", "notice_attempts", "notice_event",
                "announcement_event", "completion_event", "delivery_error")
        return {**{key: row[key] for key in keys},
                "diagnostic": json.loads(row["diagnostic"]) if row["diagnostic"] else None}

    def submit(self, args, rid):
        exact(args, {"definition", "reason"})
        rid = identifier(rid)
        if not isinstance(args["reason"], str) or not 1 <= len(args["reason"].strip()) <= 2000:
            raise Refused("launch needs a substantive bounded reason")
        fingerprint = digest(args)
        old = self.db.execute("SELECT fingerprint FROM launch_workflows WHERE id=?", (rid,)).fetchone()
        if old:
            if old[0] != fingerprint:
                raise Refused("launch request id already binds different content")
            return self.status(rid)
        if not self.b.policy.get("launch_enabled"):
            raise Refused("durable launch worker is not commissioned")
        approved, sha = self.b.store.definition(args["definition"])
        if approved["channel"] not in self.b.policy.get("decision_channels", []):
            raise Refused("launch destination is not an admitted campaign channel")
        if not re.fullmatch(r"[0-9a-f]{64}", approved["thread"]):
            raise Refused("launch needs an approved Buzz root event ID")
        if self.db.execute("SELECT 1 FROM launches WHERE definition=?", (args["definition"],)).fetchone():
            raise Refused("definition already reserved for a campaign")
        if self.db.execute("SELECT 1 FROM launch_workflows WHERE definition=? OR (channel=? AND thread=?)",
                           (args["definition"], approved["channel"], approved["thread"])).fetchone():
            raise Refused("definition or thread already belongs to another launch intent")
        if self.db.execute("SELECT 1 FROM campaigns WHERE channel=? AND thread=?",
                           (approved["channel"], approved["thread"])).fetchone():
            raise Refused("a new launch needs its own campaign thread")
        deadline = self.now + LAUNCH_SECONDS
        crew = approved["definition"].get("crew", {})
        if crew.get("automation"):
            from .automation import Automation
            Automation(self.b).validate_spec(crew["automation"], crew)
            deadline = min(deadline, timestamp(crew["automation"]["not_after"]))
        if deadline <= self.now + NOTICE_LEASE_SECONDS:
            raise Refused("insufficient approved time to complete launch")
        create_id = "launch-create-" + digest(rid)[:32]
        start_id = "launch-start-" + digest(rid)[:32]
        if self.db.execute("SELECT 1 FROM receipts WHERE id IN (?,?)", (create_id, start_id)).fetchone():
            raise Refused("derived launch operation IDs are already in use")
        cid = "cmp_" + hashlib.sha256(create_id.encode()).hexdigest()[:24]
        body = {**args, "definition_sha256": sha}
        self.db.execute("INSERT INTO launch_workflows(id,definition,fingerprint,body,campaign,channel,thread,"
                        "create_request,start_request,state,created,deadline) VALUES(?,?,?,?,?,?,?,?,?,'queued',?,?)",
                        (rid, args["definition"], fingerprint, canonical(body), cid, approved["channel"],
                         approved["thread"], create_id, start_id, self.now, deadline))
        self.b.store.save()  # A killed model/client can now leave; the timer owns continuation.
        return self.status(rid)

    def block(self, row, step, error):
        reason = str(error) if isinstance(error, Refused) else "operation outcome unresolved; inspect runtime evidence"
        diagnostic = {"step": step, "error": type(error).__name__, "reason": reason[:400]}
        if row["diagnostic"]:
            diagnostic["previous"] = json.loads(row["diagnostic"])
        self.db.execute("UPDATE launch_workflows SET state='blocked',diagnostic=?,notice_phase=NULL,"
                        "notice_claimed=NULL,notice_attempts=0,notice_event=NULL WHERE id=?",
                        (canonical(diagnostic), row["id"]))
        self.b.store.save()

    def bind_campaign(self, row, campaign):
        approved, _ = self.b.store.definition(row["definition"])
        expected = approved["definition"]
        # The API renders omitted optional fields as null; no other approval changes are allowed.
        objective = {"work_class": None, **expected["objective"]}
        policy = {"stack": None, **expected["policy"]}
        if (campaign.get("campaign_id") != row["campaign"] or
                campaign.get("project_id") != expected["project_id"] or
                {"work_class": None, **campaign.get("objective", {})} != objective or
                {"stack": None, **campaign.get("policy", {})} != policy):
            raise Refused("runtime campaign does not match the approved launch")
        existing = self.db.execute("SELECT * FROM campaigns WHERE id=?", (row["campaign"],)).fetchone()
        binding = (row["campaign"], row["definition"], row["channel"], row["thread"], "mother")
        if existing and tuple(existing) != binding:
            raise Refused("runtime campaign has a different local thread binding")
        self.db.execute("INSERT OR IGNORE INTO campaigns VALUES(?,?,?,?,?)", binding)

    def reconcile(self, row, command):
        """Read-only after a crash/ambiguous write. Never POST the operation again."""
        rid = row["create_request" if command == "create" else "start_request"]
        receipt = self.db.execute("SELECT * FROM receipts WHERE id=?", (rid,)).fetchone()
        if not receipt:
            # The process died after persisting the step, before reserving the API request.
            return False
        args = {"reason": json.loads(row["body"])["reason"],
                **({"definition": row["definition"]} if command == "create" else {"campaign": row["campaign"]})}
        if receipt["caller"] != "mother" or receipt["hash"] != digest({"caller": "mother", "command": command, "args": args}):
            raise Refused("launch receipt binds different content")
        if receipt["state"] == "done":
            if command == "create":
                self.bind_campaign(row, json.loads(receipt["result"])["campaign"])
            return True
        base = "/api/v1/campaigns/" + row["campaign"]
        campaign = self.b.api("read", "GET", base, None)
        log = self.b.api("read", "GET", base + "/control-log", None)
        matches = [e for e in log if e.get("operation") == command and
                   e.get("idempotency_key") == rid and e.get("outcome") == "applied"]
        if len(matches) != 1:
            raise Refused("launch write is unresolved in the runtime control log")
        if command == "create":
            approved, sha = self.b.store.definition(row["definition"])
            if matches[0].get("binding", {}).get("definition") != {
                    "path": "buzz-approved:" + row["definition"], "sha256": sha}:
                raise Refused("runtime creation does not bind the approved definition digest")
            # Suite pinning happens after the create transaction. Its commit alone cannot prove
            # that a lost create response completed pinning; leave that ambiguity with the owner.
            if approved["definition"].get("scenario_suite"):
                raise Refused("ambiguous creation needs owner verification of the scenario suite pin")
        self.bind_campaign(row, campaign)
        if command == "start" and campaign.get("state") == "draft":
            raise Refused("start receipt conflicts with the runtime draft state")
        result = {"campaign": campaign, "entry": matches[0], "reconciled": True}
        self.db.execute("UPDATE receipts SET state='done',result=? WHERE id=?", (canonical(result), rid))
        self.b.store.save()
        return True

    def advance(self):
        # At most one create/start operation per tick; cutoff/review routing has its own timer.
        rows = self.db.execute("SELECT * FROM launch_workflows WHERE state NOT IN ('started','blocked') ORDER BY created").fetchall()
        advanced = False
        for row in rows:
            state = row["state"]
            if self.now >= row["deadline"]:
                # A committed start remains a success even if its response was lost near cutoff.
                if state == "starting":
                    try:
                        if self.reconcile(row, "start"):
                            self.db.execute("UPDATE launch_workflows SET state='started' WHERE id=?", (row["id"],))
                            self.b.store.save()
                            continue
                    except Exception:
                        pass
                self.block(row, state, Refused("launch deadline reached; no further create/start is authorized"))
                continue
            if state not in {"queued", "creating", "announced", "starting"}:
                continue
            if advanced:
                continue
            advanced = True
            command = "create" if state in {"queued", "creating"} else "start"
            pending, complete = ("creating", "created") if command == "create" else ("starting", "started")
            try:
                if state == pending and self.reconcile(row, command):
                    self.db.execute("UPDATE launch_workflows SET state=? WHERE id=?", (complete, row["id"]))
                    self.b.store.save()
                    continue
                # No reserved receipt means no API attempt happened; the original key is safe.
                self.db.execute("UPDATE launch_workflows SET state=? WHERE id=?", (pending, row["id"]))
                self.b.store.save()
                args = {"reason": json.loads(row["body"])["reason"],
                        **({"definition": row["definition"]} if command == "create" else {"campaign": row["campaign"]})}
                result = self.b.handle("mother", {"command": command, "args": args,
                                                 "request_id": row["create_request" if command == "create" else "start_request"]})
                if command == "create":
                    self.bind_campaign(row, result["result"]["campaign"])
                self.db.execute("UPDATE launch_workflows SET state=?,diagnostic=NULL WHERE id=?", (complete, row["id"]))
                self.b.store.save()
            except Exception as error:
                rid = row["create_request" if command == "create" else "start_request"]
                receipt = self.db.execute("SELECT state FROM receipts WHERE id=?", (rid,)).fetchone()
                if not receipt:
                    self.block(row, command, error)
                else:
                    # Stay pending and retry only reads on later ticks, bounded by deadline.
                    diagnostic = {"step": command, "error": type(error).__name__,
                                  "reason": str(error)[:400] if isinstance(error, Refused) else
                                  "write outcome pending read-only reconciliation"}
                    self.db.execute("UPDATE launch_workflows SET diagnostic=? WHERE id=?", (canonical(diagnostic), row["id"]))
                    self.b.store.save()
        return [self.status(row["id"]) for row in rows]

    def notice(self, row):
        if row["state"] in {"created", "announcing"}:
            phase = "announcement"
            text = f"{row['campaign']}: created; starting the owner-approved campaign."
        elif row["state"] == "started" and not row["completion_event"]:
            phase = "result"
            text = f"{row['campaign']}: start accepted. The campaign watcher will report runtime progress here."
        elif row["state"] == "blocked" and not row["completion_event"]:
            phase = "failure"
            text = f"{row['campaign']}: launch incomplete; owner inspection required. " + row["diagnostic"]
        else:
            return None
        body = json.loads(row["body"])
        payload = {"launch": row["id"], "phase": phase, "campaign": row["campaign"],
                   "definition": row["definition"], "definition_sha256": body["definition_sha256"],
                   "channel": row["channel"], "thread": row["thread"],
                   "create_request": row["create_request"], "start_request": row["start_request"]}
        if phase == "failure":
            payload["diagnostic"] = json.loads(row["diagnostic"])
        return {"id": row["id"], "phase": phase, "channel": row["channel"], "thread": row["thread"],
                "payload": payload, "content": text + "\nDefinition: " + row["definition"] +
                "\nCreate request: " + row["create_request"] + "\nStart request: " + row["start_request"] +
                "\ncampaign-launch: " + canonical(payload)}

    def claim_notice(self):
        for row in self.db.execute("SELECT * FROM launch_workflows ORDER BY created").fetchall():
            job = self.notice(row)
            if not job:
                continue
            same = row["notice_phase"] == job["phase"]
            attempts = row["notice_attempts"] if same else 0
            if same and row["notice_claimed"] and self.now - row["notice_claimed"] < NOTICE_LEASE_SECONDS:
                continue
            if attempts >= NOTICE_ATTEMPTS:
                if job["phase"] == "announcement":
                    self.block(row, "announcement", Refused("signed launch announcement could not be verified"))
                continue
            state = "announcing" if job["phase"] == "announcement" else row["state"]
            self.db.execute("UPDATE launch_workflows SET state=?,notice_phase=?,notice_attempts=?,notice_claimed=?,"
                            "delivery_error=NULL WHERE id=?", (state, job["phase"], attempts + 1, self.now, row["id"]))
            self.b.store.save()
            return job
        return None

    def published(self, args, event):
        exact(args, {"launch", "phase"})
        row = self.row(args["launch"])
        job = self.notice(row)
        if not job or args["phase"] != job["phase"] or row["notice_phase"] != job["phase"] or row["notice_claimed"] is None:
            raise Refused("launch notice is not claimed for this phase")
        self.b.verify_event(event, "mother", "campaign-launch", job["payload"])
        tags = event["tags"]
        roots = [t[1] for t in tags if len(t) >= 4 and t[0] == "e" and t[3] == "root"]
        replies = [t[1] for t in tags if len(t) >= 4 and t[0] == "e" and t[3] == "reply"]
        if ([t[1] for t in tags if len(t) >= 2 and t[0] == "h"] != [row["channel"]] or
                (roots != [row["thread"]] if roots else replies != [row["thread"]])):
            raise Refused("launch notice is outside the approved campaign thread")
        if job["phase"] == "announcement":
            self.db.execute("UPDATE launch_workflows SET state='announced',announcement_event=?,notice_event=?,"
                            "notice_claimed=NULL,delivery_error=NULL WHERE id=?", (event["id"], event["id"], row["id"]))
        else:
            self.db.execute("UPDATE launch_workflows SET completion_event=?,notice_event=?,notice_claimed=NULL,"
                            "delivery_error=NULL WHERE id=?", (event["id"], event["id"], row["id"]))
        self.b.store.save()
        return self.status(row["id"])

    def handle(self, caller, command, args, request):
        if command == "launches":
            exact(args, set())
            return [self.status(r[0]) for r in self.db.execute("SELECT id FROM launch_workflows ORDER BY created")]
        if command == "launch-status":
            exact(args, {"launch"})
            return self.status(args["launch"])
        if caller != "mother":
            raise Refused("durable campaign launches belong to Mother")
        if command == "launch":
            return self.submit(args, request.get("request_id"))
        if command in {"launch-advance", "launch-notice-claim"}:
            exact(args, set())
            return self.advance() if command == "launch-advance" else self.claim_notice()
        if command == "launch-notice-result":
            return self.published(args, request.get("decision_event"))
        exact(args, {"launch", "phase", "error"})
        row = self.row(args["launch"])
        if row["notice_phase"] != args["phase"] or row["notice_claimed"] is None:
            raise Refused("launch notice failure is not claimed")
        if not isinstance(args["error"], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,63}", args["error"]):
            raise Refused("launch notice failure must be an exception class")
        self.db.execute("UPDATE launch_workflows SET notice_claimed=NULL,delivery_error=? WHERE id=?", (args["error"], row["id"]))
        self.b.store.save()
        return self.status(row["id"])
