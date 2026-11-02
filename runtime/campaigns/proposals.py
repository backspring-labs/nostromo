"""Proposals and approval by reply (docs/specs/plain-language-campaigns.md, phase 2).

Ripley proposes a campaign from a plain-language goal (`propose`, which drafts and stores it). Mother's
deterministic controller posts the card in the request's thread, mentioning the owner. The broker
verifies the posted card is exactly the stored one. The controller then watches the thread, and
relays any owner reply. The broker approves only an owner-signed reply that:
- says only "approve";
- replies to its live card's own event, after the card was recorded, by its approve-by time.

A reply tagged only to the thread is not enough. Mother holds her own Buzz key, so she could post a
card-like message herself and report a different card as posted without publishing it. Only the
event the owner actually replied to binds the approval to what they read (review, 2026-11-01).

The approval creates the card's allowance, approves its definition and queues the launch. One
signed word does all of it, and the owner never handles an ID or a definition.
"""
import json
import re
import time

from .core import Refused, canonical, exact, identifier

COMMANDS = {"propose", "proposals", "proposal-card-claim", "proposal-card-posted", "proposal-approve"}
LIVE = ("drafted", "posted")
CARD_ATTEMPTS = 3
CARD_LEASE_S = 180
APPROVAL_WINDOW_S = 24 * 3600


# The owner's go-words (2026-11-02: "approved" was turned away in silence). Each must be the whole
# reply; anything more ("go, but skip export") is not an approval.
GO_WORDS = {"approve", "approved", "go", "go ahead", "engage", "let's go", "lets go", "launch", "ship it",
            "yes", "\U0001f44d"}
STOP_WORDS = {"abort", "stop", "cancel"}


def bare(text):
    """A reply as a word: case, surrounding space, closing punctuation and curly apostrophes forgiven."""
    word = str(text or "").strip().lower().replace("\u2019", "'")
    return " ".join(re.sub(r"[.!\s]+$", "", word).split())


def unqualified_approval(text):
    """Only a bare go-word approves."""
    return bare(text) in GO_WORDS


def near_miss(text):
    """A short reply that starts like an answer but isn't one ("approve now", "go please"): worth
    telling the owner what counts, rather than ignoring it in silence."""
    word = bare(text)
    if not word or len(word) > 60 or word in GO_WORDS or word in STOP_WORDS:
        return False
    return any(word.startswith(w) for w in GO_WORDS | STOP_WORDS if w != "\U0001f44d")


class Proposals:
    def __init__(self, broker, now=None):
        self.b, self.db = broker, broker.store.db
        self.now = time.time() if now is None else now

    def handle(self, caller, command, args, request):
        if command == "propose":
            if caller not in {"ripley", "mother"}:
                raise Refused("proposing a campaign belongs to Ripley or Mother")
            return self.propose(args)
        if command == "proposals":
            exact(args, set(), {"state"})
            rows = self.db.execute("SELECT id,thread,state,card_event,posted,launch,body FROM proposals ORDER BY created").fetchall()
            return [{**{k: r[k] for k in ("id", "thread", "state", "card_event", "posted", "launch")},
                     "channel": json.loads(r["body"])["approval"]["channel"]}
                    for r in rows if "state" not in args or r["state"] == args["state"]]
        if caller != "mother":
            raise Refused("posting cards and relaying approvals is Mother's controller's")
        if command == "proposal-card-claim":
            exact(args, set())
            return self.claim()
        if command == "proposal-card-posted":
            exact(args, {"proposal"})
            return self.posted(args["proposal"], request.get("decision_event"))
        exact(args, {"proposal"})
        return self.approve(args["proposal"], request.get("decision_event"))

    def row(self, pid):
        row = self.db.execute("SELECT * FROM proposals WHERE id=?", (identifier(pid),)).fetchone()
        if row is None:
            raise Refused("no such proposal")
        return row

    def approve_by(self, body):
        """The card's stated approve-by time: the cutoff less the hours it may run."""
        from .review import timestamp
        definition = body["approval"]["definition"]
        return timestamp(definition["crew"]["automation"]["not_after"]) - definition["policy"]["max_elapsed_s"]

    def propose(self, args):
        from .drafting import draft
        from .launch import Launches
        drafted = draft(self.b, args, self.now)
        name, thread = drafted["approval"]["name"], drafted["approval"]["thread"]
        # Fail now, not at the owner's approval: the thread must be free for a new launch.
        Launches(self.b, now=self.now).preflight(name, drafted["approval"])
        superseded = self.db.execute("SELECT count(*) FROM proposals WHERE thread=? AND state IN ('drafted','posted')",
                                     (thread,)).fetchone()[0]
        # One live card per thread: a new proposal supersedes the earlier one, which can no longer be approved.
        self.db.execute("UPDATE proposals SET state='superseded' WHERE thread=? AND state IN ('drafted','posted')", (thread,))
        owner = "@jladd "  # it is the owner's move: the card asks for their reply
        body = {**drafted, "content": owner + drafted["card"]}
        self.db.execute("INSERT INTO proposals(id,thread,state,body,created) VALUES(?,?,'drafted',?,?)",
                        (name, thread, canonical(body), self.now))
        self.b.store.save()
        return {"proposal": name, "card": drafted["card"], "superseded_earlier": bool(superseded)}

    def claim(self):
        for row in self.db.execute("SELECT * FROM proposals WHERE state='drafted' ORDER BY created").fetchall():
            if row["claimed"] and self.now - row["claimed"] < CARD_LEASE_S:
                continue
            if row["attempts"] >= CARD_ATTEMPTS:
                self.db.execute("UPDATE proposals SET state='failed' WHERE id=?", (row["id"],))
                self.b.store.save()
                continue
            self.db.execute("UPDATE proposals SET claimed=?,attempts=attempts+1 WHERE id=?", (self.now, row["id"]))
            self.b.store.save()
            body = json.loads(row["body"])
            return {"id": row["id"], "phase": "card", "channel": body["approval"]["channel"], "thread": row["thread"],
                    "content": body["content"], "mention_owner": True}
        return None

    def posted(self, pid, event):
        """Render and verify the card: Mother's signed message says exactly the stored card, in the thread."""
        row = self.row(pid)
        if row["state"] != "drafted":
            raise Refused("this proposal's card is not awaiting publication")
        body = json.loads(row["body"])
        eid = self.b.verify_event.rendered(event, "mother", body["content"], body["approval"]["channel"],
                                           row["thread"], row["created"])
        try:
            # Posted when the broker recorded it, by the broker's clock: the card's own timestamp is
            # Mother's to choose and could be backdated (review B1, 2026-11-01).
            self.db.execute("UPDATE proposals SET state='posted',card_event=?,posted=? WHERE id=?",
                            (eid, self.now, row["id"]))
        except Exception:
            raise Refused("this card message already belongs to another proposal") from None
        self.b.store.save()
        return {"posted": True, "card_event": eid}

    def approve(self, pid, event):
        """The owner's signed "approve", relayed by the controller, which can't forge it."""
        row = self.row(pid)
        if row["state"] == "approved":
            if (event or {}).get("id") == row["approval_event"]:
                return {"approved": True, "launch": row["launch"], "replayed": True}
            raise Refused("this proposal is already approved")
        if row["state"] != "posted":
            raise Refused("only the live card can be approved; it has been superseded or was never posted")
        body = json.loads(row["body"])
        channel = body["approval"]["channel"]
        eid = self.b.verify_event.authentic(event, "owner")
        tags = event["tags"]
        if [t[1] for t in tags if len(t) >= 2 and t[0] == "h"] != [channel]:
            raise Refused("the approval is not in the proposal's channel")
        referenced = {t[1] for t in tags if len(t) >= 2 and t[0] == "e"}
        if row["thread"] not in referenced and row["card_event"] not in referenced:
            raise Refused("the approval is not in the proposal's thread")
        # A reply that names some other card (a superseded one, say) approves nothing.
        cards = {r[0] for r in self.db.execute("SELECT card_event FROM proposals WHERE thread=? AND card_event IS NOT NULL",
                                               (row["thread"],))}
        if (referenced & cards) - {row["card_event"]}:
            raise Refused("the approval answers a card that is no longer live")
        if row["card_event"] not in referenced:
            raise Refused("the approval must reply to the card itself, not only to the thread")
        # After the live card was recorded, with no slack: an "approve" written before a replacement
        # card existed approves nothing, so it can't be carried over to a card the owner never saw.
        latest = min(self.now + 30, row["posted"] + APPROVAL_WINDOW_S, self.approve_by(body))
        if not row["posted"] <= event["created_at"] <= latest:
            raise Refused("the approval was not given after the live card and by its approve-by time")
        if not unqualified_approval(event["content"]):
            raise Refused("only an unqualified \"approve\" approves; anything more needs a question or a revised card")
        if self.db.execute("SELECT 1 FROM proposals WHERE approval_event=?", (eid,)).fetchone():
            raise Refused("this reply already approved another proposal")
        # The owner's one word: the allowance, the definition, and the launch, in that order. Every
        # launch precondition is checked before anything is written, so an approval can't stop half
        # way with a definition and allowance approved and no launch.
        from .automation import Automation
        from .launch import Launches
        allowance = body["allowance"]
        Automation(self.b, now=self.now).validate_allowance(allowance)
        Launches(self.b, now=self.now).preflight(row["id"], body["approval"])
        rid = "launch-" + row["id"]
        # One transaction: the allowance, the definition and the launch are all written, or none is.
        with self.b.store.one_transaction():
            stored = self.db.execute("SELECT body FROM review_budgets WHERE name=?", (allowance["name"],)).fetchone()
            if stored and stored[0] != canonical(allowance):
                raise Refused("an allowance of this name already exists with other terms")
            self.db.execute("INSERT OR IGNORE INTO review_budgets VALUES(?,?)", (allowance["name"], canonical(allowance)))
            self.b.approve(body["approval"])
            # The reason names no event, so a retry after a crash binds the same launch request.
            Launches(self.b, now=self.now).submit(
                {"definition": row["id"], "reason": "The owner approved this campaign's card by signed reply."}, rid)
            self.db.execute("UPDATE proposals SET state='approved',approval_event=?,launch=? WHERE id=?",
                            (eid, rid, row["id"]))
        return {"approved": True, "launch": rid}
