"""Decision cards: the owner answers a campaign's escalation from Buzz (plain-language campaigns, phase 3).

When Ripley's ruling at an increment gate is needs_owner, the automation parks the campaign and
stores a decision card. Mother's deterministic controller posts the card in the campaign's thread,
mentioning the owner, and the broker verifies the posted card says exactly the stored one. The
owner's signed reply to that card is the decision:
- "approve": the campaign is resumed from the supervisor's own pause, the proposal at the gate is
  ruled approved as the owner's decision (decided_by_kind "human"), with Ripley's notes as the build
  guidance and the provenance as their last line, and the automation is re-activated;
- "abort": the campaign is aborted with the owner's reason.

As with approval by reply, only a reply to the card's own event counts: Mother holds her own Buzz
key, so a reply tagged only to the thread can't say which card the owner read. Each step is
idempotent and recorded, so a retry after a failure part-way continues rather than repeats.
SquadOps order (its answer of 2026-11-01): resume first, then rule, then re-activate.
"""
import json
import re
import time

from .core import Refused, canonical, digest, exact, identifier

COMMANDS = {"decision-cards", "decision-card-claim", "decision-card-posted", "decision-answer"}
CARD_ATTEMPTS = 3
CARD_LEASE_S = 180
ANSWERS = {"approve", "abort"}


def answer_of(text):
    """A bare "approve" or "abort", forgiving case, surrounding space and closing punctuation."""
    word = re.sub(r"[.!\s]+$", "", str(text or "").strip()).lower()
    return word if word in ANSWERS else None


def card_view(notes):
    """Ripley's view as the card shows it: one line, at most 600 characters. The owner approves
    exactly this, and exactly this becomes the build guidance; nothing past it is sent."""
    view = " ".join(str(notes).split())
    return view if len(view) <= 600 else view[:597].rstrip() + "..."


def card_text(product, version, view, can_approve):
    from .drafting import shown
    lines = [f"**{shown(product)}: Ripley needs your decision on proposal v{version} for the next increment.**",
             "", f"Her view: {shown(view)}", ""]
    if can_approve:
        lines.append("Reply **approve** to this card to go ahead with it (her notes go to the build plan), "
                     "or **abort** to stop the campaign.")
    else:
        lines.append("Reply **abort** to this card to stop the campaign.")
    lines.append("Anything else goes to Mother as conversation.")
    return "@jladd " + "\n".join(lines)


class DecisionCards:
    def __init__(self, broker, now=None):
        self.b, self.db = broker, broker.store.db
        self.now = time.time() if now is None else now

    def create(self, cid, payload, result):
        """Called when Ripley's ruling is needs_owner. Stores the card; the controller posts it."""
        from .review import decision_request
        from .watch import product
        gate = payload.get("gate") or {}
        item = self.b.store.campaign(cid)
        request, version = None, "?"
        if gate.get("gate") == "progress_increment_ruling":
            try:
                request = decision_request(cid, payload, {**result, "decision": "approved"})
                version = request["args"]["binding"]["version"]
            except Exception:
                request = None
        cid_row = identifier(cid)
        card = "card_" + digest({"campaign": cid_row, "gate": gate})[:32]
        project = (payload["packet"].get("campaign") or {}).get("project_id")
        view = card_view(result["notes"])
        body = {"campaign": cid_row, "gate": gate, "request": request, "view": view, "channel": item["channel"],
                "content": card_text(product(project) + " campaign", version, view, request is not None)}
        self.db.execute("INSERT OR IGNORE INTO decision_cards(id,campaign,thread,state,body,created) VALUES(?,?,?,?,?,?)",
                        (card, cid_row, item["thread"], "drafted", canonical(body), self.now))
        self.b.store.save()
        return card

    def handle(self, caller, command, args, request):
        if command == "decision-cards":
            exact(args, set(), {"state"})
            rows = self.db.execute("SELECT id,campaign,thread,state,card_event,posted,outcome,body FROM decision_cards "
                                   "ORDER BY created").fetchall()
            return [{**{k: r[k] for k in ("id", "campaign", "thread", "state", "card_event", "posted", "outcome")},
                     "channel": json.loads(r["body"])["channel"]}
                    for r in rows if "state" not in args or r["state"] == args["state"]]
        if caller != "mother":
            raise Refused("posting decision cards and relaying answers is Mother's controller's")
        if command == "decision-card-claim":
            exact(args, set())
            return self.claim()
        exact(args, {"card"})
        if command == "decision-card-posted":
            return self.posted(args["card"], request.get("decision_event"))
        return self.answer(args["card"], request.get("decision_event"))

    def row(self, card):
        row = self.db.execute("SELECT * FROM decision_cards WHERE id=?", (identifier(card),)).fetchone()
        if row is None:
            raise Refused("no such decision card")
        return row

    def claim(self):
        for row in self.db.execute("SELECT * FROM decision_cards WHERE state='drafted' ORDER BY created").fetchall():
            if row["claimed"] and self.now - row["claimed"] < CARD_LEASE_S:
                continue
            if row["attempts"] >= CARD_ATTEMPTS:
                self.db.execute("UPDATE decision_cards SET state='failed' WHERE id=?", (row["id"],))
                self.b.store.save()
                continue
            self.db.execute("UPDATE decision_cards SET claimed=?,attempts=attempts+1 WHERE id=?", (self.now, row["id"]))
            self.b.store.save()
            body = json.loads(row["body"])
            return {"id": row["id"], "phase": "decision", "channel": body["channel"], "thread": row["thread"],
                    "content": body["content"], "mention_owner": True}
        return None

    def posted(self, card, event):
        row = self.row(card)
        if row["state"] != "drafted":
            raise Refused("this decision card is not awaiting publication")
        body = json.loads(row["body"])
        eid = self.b.verify_event.rendered(event, "mother", body["content"], body["channel"], row["thread"], row["created"])
        try:
            # Posted when the broker recorded it, by its own clock (as for proposal cards).
            self.db.execute("UPDATE decision_cards SET state='posted',card_event=?,posted=? WHERE id=?",
                            (eid, self.now, row["id"]))
        except Exception:
            raise Refused("this card message already belongs to another decision card") from None
        self.b.store.save()
        return {"posted": True, "card_event": eid}

    def answer(self, card, event):
        row = self.row(card)
        if row["state"] in {"approved", "aborted", "stale", "failed"}:
            if (event or {}).get("id") == row["answer_event"]:
                return {"decided": row["state"], "replayed": True}
            raise Refused("this decision card has already been answered")
        if row["state"] not in {"posted", "answered"}:
            raise Refused("this decision card is not live")
        body = json.loads(row["body"])
        if row["state"] == "answered":
            # A retry after a failure part-way: continue with the recorded answer, never a new one.
            if (event or {}).get("id") != row["answer_event"]:
                raise Refused("this decision card's recorded answer is still being applied")
            word = row["outcome"]
        else:
            eid = self.b.verify_event.authentic(event, "owner")
            tags = event["tags"]
            if [t[1] for t in tags if len(t) >= 2 and t[0] == "h"] != [body["channel"]]:
                raise Refused("the answer is not in the campaign's channel")
            if row["card_event"] not in {t[1] for t in tags if len(t) >= 2 and t[0] == "e"}:
                raise Refused("the answer must reply to the decision card itself")
            if not row["posted"] <= event["created_at"] <= self.now + 30:
                raise Refused("the answer was not given after the card was posted")
            word = answer_of(event["content"])
            if word is None:
                raise Refused("only a bare \"approve\" or \"abort\" answers a decision card")
            if word == "approve" and body["request"] is None:
                raise Refused("this card offers only abort")
            if self.db.execute("SELECT 1 FROM decision_cards WHERE answer_event=?", (eid,)).fetchone():
                raise Refused("this reply already answered another card")
            self.db.execute("UPDATE decision_cards SET state='answered',answer_event=?,outcome=? WHERE id=?",
                            (eid, word, row["id"]))
            self.b.store.save()
        return self.apply(row["id"], body, word, (event or {}).get("id"))

    def apply(self, card, body, word, eid):
        cid = body["campaign"]
        key = "owner-" + digest({"card": card, "answer": word})[:32]
        if word == "abort":
            current = self.b.read("status", {"campaign": cid})
            if current["state"] != "completed":
                self.b.api("control", "POST", f"/api/v1/campaigns/{cid}/abort",
                           {"reason": "Owner: aborted, by signed reply to Ripley's decision card in Buzz.",
                            "idempotency_key": key})
            self.db.execute("UPDATE automation SET state='closed',reason='owner aborted' WHERE campaign=?", (cid,))
            return self.done(card, "aborted")
        args = body["request"]["args"]
        current = self.b.read("status", {"campaign": cid})
        # Before any write: the proposal the card shows must still be the one waiting at the gate.
        # SquadOps would refuse a stale binding, but only after the resume had already happened.
        rows = [r for r in self.b.read("ledger", {"campaign": cid}) or []
                if r.get("cycle_id") == args["cycle"] and r.get("run_id") == args["run"] and not r.get("ruling")]
        live = [{k: r.get(k) for k in ("proposal_id", "version", "content_hash", "baseline_tree")} for r in rows]
        if current["state"] not in {"paused", "awaiting_ruling"} or live != [args["binding"]]:
            return self.done(card, "stale")
        if current["state"] == "paused":
            # The supervisor's own pause: resume without an action, back to awaiting_ruling.
            self.b.api("control", "POST", f"/api/v1/campaigns/{cid}/resume",
                       {"reason": "Owner approved the proposal at the gate, by signed reply in Buzz.",
                        "idempotency_key": key + "-resume", "expected_state": "paused"})
            current = self.b.read("status", {"campaign": cid})
        if current["state"] != "awaiting_ruling":
            # Resumed but not at the gate any more: hold it again (a new pause episode) and stop.
            from .automation import Automation
            self.done(card, "failed")
            Automation(self.b, now=self.now).park(cid, f"the campaign was {current['state']} after the resume, not "
                                                      "waiting for this ruling; owner inspection required")
            return {"decided": "failed"}
        project = identifier(self.b.read("status", {"campaign": cid})["project_id"])
        path = (f"/api/v1/projects/{project}/cycles/{identifier(args['cycle'])}/runs/{identifier(args['run'])}"
                "/gates/progress_increment_ruling")
        # Ripley's notes first, and about the build: SquadOps shows approval notes to the framing run.
        notes = body["view"] + f"\n\nApproved by the owner in Buzz, event {eid}."
        try:
            self.b.api("review", "POST", path, {"decision": "approved", "notes": notes, "decided_by_kind": "human",
                                                "binding": args["binding"], "idempotency_key": key + "-rule"})
        except Refused as error:
            if not re.search(r"\(HTTP 4\d\d\)", str(error)):
                raise  # transport or server trouble: the recorded answer is retried
            # A definitive refusal: hold the campaign again (a new pause episode) instead of retrying.
            from .automation import Automation
            self.done(card, "failed")
            Automation(self.b, now=self.now).park(cid, "SquadOps refused the owner's ruling; owner inspection required")
            return {"decided": "failed"}
        from .automation import CARD_HOLD
        # Lift only the hold this card answers.
        self.db.execute("UPDATE automation SET state='active',reason=NULL WHERE campaign=? AND state='parked' AND reason=?",
                        (cid, CARD_HOLD))
        return self.done(card, "approved")

    def done(self, card, state):
        self.db.execute("UPDATE decision_cards SET state=? WHERE id=?", (state, card))
        self.b.store.save()
        return {"decided": state}
