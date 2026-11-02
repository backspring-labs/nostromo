"""No-model observer. Publishes transitions and factual closing posts in Buzz, never gate verdicts."""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import time
from pathlib import Path

from .cli import call
from .core import digest


def publication_result(command, stdout):
    # notes set deliberately prints durable references, even with the CLI's global JSON format.
    if command[:2] == ["notes", "set"]:
        fields = dict(line.split(None, 1) for line in stdout.splitlines() if len(line.split(None, 1)) == 2)
        name = command[command.index("--name")+1]
        if (not re.fullmatch(r"[0-9a-f]{64}", fields.get("event_id", "")) or
                fields.get("slug") != name or
                not re.fullmatch(r"30023:[0-9a-f]{64}:"+re.escape(name), fields.get("coordinate", ""))):
            raise RuntimeError("Buzz note publication references unreadable")
        return fields
    result = json.loads(stdout)
    if result.get("accepted") is not True:
        raise RuntimeError("Buzz message was not accepted")
    return result


ET = "America/New_York"
ROOT = Path(__file__).resolve().parents[2]
# Plain words for what a campaign is doing. A state not listed reads as its own name, spaced.
DOING = {
    "at_proposal": "the squad is proposing the next increment",
    "executing": "the squad is building the approved increment",
    "awaiting_ruling": "a proposal is waiting for a ruling",
    "escalated": "it has escalated and is waiting for you",
    "paused": "it is paused",
    "launch_blocked": "it is waiting to launch its next cycle; SquadOps retries on its own",
}
OUTCOMES = {"aborted": "it was aborted", "exhausted": "it reached one of its limits",
            "succeeded": "it reached its target", "success": "it reached its target", "failure": "it failed"}
# launch_blocked is not the owner's move: SquadOps retries it, and escalates if it never launches.
YOURS = {"escalated", "paused"}
FINISHED_JOBS = {"done", "submitted", "cancelled", "failed", "uncertain"}
# Bump whenever fingerprint() changes. On the first poll under a new format the watcher adopts the new
# fingerprints silently instead of announcing every campaign: on 2026-11-01, changing the format
# without this re-posted eleven closed campaigns into their threads.
FINGERPRINT_FORMAT = 3


def product(project_id):
    """A product's readable name: its registry entry if there is one, else from its project ID."""
    slug = str(project_id or "").removeprefix("prj-")
    entry = ROOT / "campaigns" / "projects" / (slug + ".yaml")
    try:
        for line in entry.read_text().splitlines():
            if line.startswith("display_name:"):
                return line.split(":", 1)[1].strip().strip("'\"")
    except OSError:
        pass
    return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-") if part) or "This"


def when(iso):
    """A runtime timestamp in ET, for people."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:
        moment = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(ZoneInfo(ET))
    except ValueError:
        return None
    return moment.strftime("%-I:%M %p ET, %b %-d").replace("AM", "am").replace("PM", "pm")


def rows(packet):
    ledger = packet.get("ledger")
    return [row for row in ledger if isinstance(row, dict)] if isinstance(ledger, list) else []


def accepted(packet):
    # SquadOps' outcome is a record ({"verdict": "accepted", ...}); a bare string is the older shape.
    # On 2026-11-01 reading only the string counted an accepted increment as none.
    def verdict(outcome):
        return outcome.get("verdict") if isinstance(outcome, dict) else outcome
    return sum(1 for row in rows(packet) if str(verdict(row.get("outcome")) or "").startswith("accept"))


# The squad's steps inside a cycle, as a person would say them.
STEPS = {"proposal": "proposing", "framing": "planning how to build", "implementation": "building",
         "verification": "verifying", "qa": "testing", "repair": "repairing", "retry": "retrying"}


def items(packet):
    """The objective's increments in order, from the draft's "In order: a; b; c"."""
    statement = str((packet["campaign"].get("objective") or {}).get("statement") or "")
    _, found, tail = statement.rpartition("In order: ")
    return [i.strip().rstrip(".") for i in tail.split(";") if i.strip()] if found else []


def step(packet):
    """The squad's current step: the campaign's most recently started run, as (type, status)."""
    cycles = [c for c in ((packet.get("progress") or {}).get("cycles") or []) if isinstance(c, dict)]
    runs = [r for c in cycles for r in (c.get("runs") or []) if isinstance(r, dict)]
    if not runs:
        return None
    run = max(runs, key=lambda r: (r.get("started_at") or "", r.get("run_number") or 0))
    return run.get("workload_type"), run.get("status")


def doing(packet):
    """What the squad is doing now, naming the increment when the objective lists them."""
    if packet["campaign"]["state"] == "repairing":
        # Campaign 4's repair post read word for word like the build before it.
        names, n = items(packet), accepted(packet)
        subject = names[n] if n < len(names) else "the increment"
        return f"the first build of {subject} didn't pass its checks; the squad is repairing it"
    current = step(packet)
    if not current or current[0] not in STEPS:
        return None
    kind, status = current
    names = items(packet)
    n = accepted(packet)
    if kind == "proposal":
        subject = f"the next increment ({names[n]})" if n < len(names) else "the next increment"
    else:
        subject = names[n] if n < len(names) else "the approved increment"
    if status in {"completed", "succeeded"}:
        return f"the squad finished {STEPS[kind]} {subject}"
    if status in {"failed", "cancelled"}:
        return f"the squad's {kind} run for {subject} {status}"
    return f"the squad is {STEPS[kind]} {subject}"


def progress(packet):
    target = (packet["campaign"].get("objective") or {}).get("target_accepted_increments")
    text = f"{accepted(packet)} of {target} increments accepted" if target else f"{accepted(packet)} increments accepted"
    automation = packet.get("automation")
    if automation:
        used = sum(1 for job in automation.get("jobs") or [] if job.get("reserved"))
        limit = (packet.get("crew_policy") or {}).get("paid_dispatches")
        text += f"; {used} of {limit} reviews used" if limit else f"; {used} reviews used"
    return text + "."


def next_actor(packet):
    """Whose move it is: the squad, Ripley, Dallas, the owner, or nobody."""
    campaign, automation = packet["campaign"], packet.get("automation") or {}
    control = automation.get("control") or {}
    if campaign["state"] == "completed":
        if packet.get("analysis"):
            return "nobody; it has closed"
        pending = [job for job in automation.get("jobs") or []
                   if job.get("kind") == "analysis" and job.get("state") not in FINISHED_JOBS]
        return "Ripley, for the closing analysis" if pending else "nobody; it has closed, with no closing analysis to come"
    if control.get("state") == "parked" or campaign["state"] in YOURS:
        return "you"
    if campaign["state"] == "awaiting_ruling":
        pending = [job for job in automation.get("jobs") or [] if job.get("state") not in FINISHED_JOBS]
        return pending[-1]["role"].title() if pending else "Ripley"
    return "the squad"


def notice(packet, label):
    """One readable post: the campaign and what happened, where it stands, and whose move it is."""
    campaign = packet["campaign"]
    control = (packet.get("automation") or {}).get("control") or {}
    if campaign["state"] == "completed":
        what = "closed. " + OUTCOMES.get(campaign.get("outcome"), f"Its outcome is {campaign.get('outcome')}").capitalize()
    elif control.get("state") == "parked":
        what = "paused for you. " + str(control.get("reason") or "It needs a decision").rstrip(".")
    else:
        what = (doing(packet) if campaign["state"] not in {"awaiting_ruling", "escalated", "paused", "launch_blocked"}
                else None) or DOING.get(campaign["state"], str(campaign["state"]).replace("_", " "))
    who = next_actor(packet)
    if campaign["state"] != "completed" and running_out(packet):
        from .drafting import et
        deadline = packet["automation"]["control"]["deadline"]
        what += f". It stops at its cutoff, {et(deadline)}, in under half an hour, if it isn't answered"
    return f"{label}: {what}. {progress(packet)} Next: {who}.", who == "you"


WARN_BEFORE_CUTOFF_S = 1800


def running_out(packet, now=None):
    """A held campaign within half an hour of its cutoff: the owner's last chance to answer. On
    2026-11-01 campaign 4 sat held for 1h44m and was stopped by its cutoff with no warning."""
    import time
    control = (packet.get("automation") or {}).get("control") or {}
    deadline = control.get("deadline")
    held = control.get("state") == "parked" or packet["campaign"]["state"] in YOURS
    now = time.time() if now is None else now
    return bool(held and isinstance(deadline, (int, float)) and 0 < deadline - now <= WARN_BEFORE_CUTOFF_S)


def fingerprint(packet):
    """Only what a person would want a new post for. Review jobs being queued or claimed are not news."""
    campaign, automation = packet["campaign"], packet.get("automation") or {}
    control = automation.get("control") or {}
    return digest({"state": campaign["state"], "outcome": campaign.get("outcome"),
                   "control": [control.get("state"), control.get("reason")], "accepted": accepted(packet),
                   "rulings": sum(1 for row in rows(packet) if row.get("ruling")),
                   "escalations": len(packet.get("escalations") or []), "analysis": bool(packet.get("analysis")),
                   "step": step(packet), "running_out": running_out(packet)})


def report(packet, package, label):
    """The closing record, for people. The full SquadOps records stay with the broker."""
    campaign = packet["campaign"]
    objective = campaign.get("objective") or {}
    started, closed = when(campaign.get("created_at")), when(campaign.get("updated_at"))
    lines = [f"# {label}: closed", "",
             f"**Outcome:** {OUTCOMES.get(campaign.get('outcome'), str(campaign.get('outcome')))}.",
             f"**Goal:** {objective.get('statement') or 'not stated'}."]
    if started and closed:
        lines.append(f"**Ran:** {started} to {closed}.")
    aborts = [entry for entry in packet.get("log") or [] if isinstance(entry, dict) and entry.get("operation") == "abort"]
    if aborts and aborts[-1].get("reason"):
        lines.append(f"**Why it was stopped:** {str(aborts[-1]['reason']).rstrip('.')}.")
    lines += [f"**Progress:** {progress(packet)}", "", "## Rulings", ""]
    rulings = [row for row in rows(packet) if row.get("ruling")]
    for number, row in enumerate(rulings, 1):
        ruling = row["ruling"]
        reason = (str(ruling.get("reason") or "").splitlines() or [""])[0].split(". ")[0].rstrip(".")
        lines.append(f"{number}. {str(ruling.get('decision', '')).replace('_', ' ').capitalize()}. {reason}.")
    if not rulings:
        lines.append("No proposal was ruled on.")
    analysis = packet.get("analysis")
    lines += ["", "## Ripley's closing analysis", "",
              analysis["analysis"] if analysis else "Pending. Ripley's analysis will be added here when it is done."]
    lines += ["", "The full SquadOps records (campaign, ledger, package) are kept by the broker."]
    return "\n".join(lines) + "\n"


def labels(packets):
    """'ShelfNote campaign 2': the product, and the campaign's order among that product's campaigns."""
    by_product = {}
    for cid, packet in packets.items():
        by_product.setdefault(packet["campaign"].get("project_id"), []).append(
            (packet["campaign"].get("created_at") or "", cid))
    names = {}
    for project, rows in by_product.items():
        for number, (_created, cid) in enumerate(sorted(rows), 1):
            names[cid] = f"{product(project)} campaign {number}"
    return names


class Watcher:
    def __init__(self, db, rpc, publish, publish_report):
        self.db, self.rpc, self.publish, self.publish_report = db, rpc, publish, publish_report
        db.execute("CREATE TABLE IF NOT EXISTS watched(id TEXT PRIMARY KEY, fingerprint TEXT, failures INTEGER, report TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS watcher_meta(key TEXT PRIMARY KEY, value TEXT)")
        row = db.execute("SELECT value FROM watcher_meta WHERE key='fingerprint_format'").fetchone()
        has_history = db.execute("SELECT count(*) FROM watched").fetchone()[0] > 0
        # Old history under another format: adopt silently. A fresh watcher announces as before.
        self.adopting = has_history and (row is None or row[0] != str(FINGERPRINT_FORMAT))
        db.commit()

    def poll(self):
        tracked = self.rpc({"command": "tracked", "args": {}})
        packets, unread = {}, {}
        for item in tracked:
            try:
                packets[item["id"]] = self.rpc({"command": "packet", "args": {"campaign": item["id"]}})
                if packets[item["id"]]["campaign"]["state"] != "completed":
                    # The squad's step inside a cycle (framing, building, ...). Optional: a failed read
                    # only means a coarser post.
                    try:
                        packets[item["id"]]["progress"] = self.rpc({"command": "progress", "args": {"campaign": item["id"]}})
                    except Exception:
                        pass
            except Exception as error:
                unread[item["id"]] = error
        names = labels(packets)
        for item in tracked:
            cid = item["id"]
            old = self.db.execute("SELECT fingerprint,failures,report FROM watched WHERE id=?", (cid,)).fetchone()
            previous, failures, posted = old if old else (None, 0, None)
            try:
                if cid in unread:
                    raise unread[cid]
                packet = packets[cid]
                campaign = packet["campaign"]
                if campaign["state"] == "awaiting_ruling":
                    self.rpc({"command": "open-window", "args": {"campaign": cid}})
                current = fingerprint(packet)
                if self.adopting:
                    self.db.execute("INSERT OR REPLACE INTO watched VALUES(?,?,?,?)", (cid, current, 0, posted))
                    self.db.commit()
                    continue
                if campaign["state"] == "completed" and (not posted or current != previous):
                    package = self.rpc({"command": "package", "args": {"campaign": cid}})
                    # Stable NIP-23 name makes a retry update the same post after a crash.
                    posted = self.publish_report(cid, report(packet, package, names[cid]), names[cid])
                if current != previous:
                    text, yours = notice(packet, names[cid])
                    if yours:
                        text = "@jladd " + text
                    if posted and campaign["state"] == "completed":
                        text += " The closing record is in this channel's notes."
                    self.publish(item, text, yours)
                self.db.execute("INSERT OR REPLACE INTO watched VALUES(?,?,?,?)", (cid, current, 0, posted))
            except Exception:
                failures += 1
                if failures == 3:
                    self.publish(item, "@jladd I couldn't read this campaign's state three times in a row, so nothing is "
                                       "assumed about whether it is still working. Next: you.", True)
                self.db.execute("INSERT OR REPLACE INTO watched VALUES(?,?,?,?)", (cid, previous, failures, posted))
            self.db.commit()
        if self.adopting:
            self.db.execute("INSERT OR REPLACE INTO watcher_meta VALUES('fingerprint_format',?)", (str(FINGERPRINT_FORMAT),))
            self.db.commit()
            self.adopting = False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", default="/var/lib/nostromo-campaign-watch/watch.sqlite3")
    # Every minute: the owner watches the thread, and a poll is cheap and calls no model.
    p.add_argument("--interval", type=int, default=60)
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    if args.interval < 30:
        p.error("interval must be at least 30 seconds")
    env = dict(os.environ)
    env["BUZZ_RELAY_URL"] = "wss://nostromo.backspring.xyz"
    env["BUZZ_PRIVATE_KEY"] = (Path.home()/".config/nostromo/secrets/buzz.key").read_text().strip()
    config = json.loads(Path("/etc/nostromo/campaign-broker.json").read_text())
    env["BUZZ_AUTH_TAG"] = config["watcher_auth_tag"]
    buzz = "/opt/nostromo/runtime/bin/buzz"

    def run(command, content):
        result = subprocess.run([buzz, *command, "--content", "-"], input=content,
                                text=True, capture_output=True, env=env, timeout=30)
        if result.returncode:
            raise RuntimeError("Buzz publication failed")
        return publication_result(command, result.stdout)

    owner = config["public_keys"]["owner"]

    def publish(item, text, mention_owner=False):
        # Never a crew mention: every named agent would start a paid turn. The owner is mentioned only
        # when it is the owner's move, which starts no turn and makes Desktop notify them.
        command = ["messages", "send", "--channel", item["channel"], "--reply-to", item["thread"]]
        if mention_owner:
            command += ["--mention", owner]
        return run(command, text)

    def publish_report(cid, text, label):
        name = "closing-" + cid
        result = run(["notes", "set", "--name", name, "--title", label + ": closing record"], text)
        expected = "30023:" + helpers_pubkey(env["BUZZ_PRIVATE_KEY"]) + ":" + name
        if result["coordinate"] != expected:
            raise RuntimeError("Buzz note was published under an unexpected coordinate")
        return expected

    db = sqlite3.connect(args.state)
    watcher = Watcher(db, call, publish, publish_report)
    while True:
        try:
            watcher.poll()
        except Exception:
            print("campaign watcher: source unavailable; retrying at the next scheduled observation", flush=True)
        if args.once:
            break
        time.sleep(args.interval)


def helpers_pubkey(key):
    from .decisions import helpers
    return helpers().xonly_pubkey(key)


if __name__ == "__main__":
    main()
