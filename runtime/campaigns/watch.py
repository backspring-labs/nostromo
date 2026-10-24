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
from .core import canonical, digest


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


def notice(campaign):
    state = campaign["state"]
    if state == "completed":
        return "Campaign closed; evidence ready for analysis."
    if state in {"awaiting_ruling", "escalated", "paused", "launch_blocked"}:
        return "Action required; inspect the current evidence packet. No review has been dispatched automatically."
    return "Campaign state changed."


def report(packet, package):
    campaign = packet["campaign"]
    # Reporting stored values is deliberately separate from a crew interpretation of those values.
    analysis = packet.get("analysis")
    interpretation = (analysis["analysis"] + "\n\nEvidence: " + canonical(analysis["evidence"]) +
                      "\n\nRipley decision event: " + analysis["decision_event"]) if analysis else (
                      "Pending. This factual record is not an app-quality verdict. "
                      "A reviewer must add what improved, failures, interventions, unknowns, actual crew cost, "
                      "and recommendations, with evidence references. No automatic paid review was dispatched.")
    records = {"campaign": campaign, "ledger": packet["ledger"], "package": package}
    raw = json.dumps(records, indent=2, ensure_ascii=False)
    evidence = ("```json\n" + raw + "\n```" if len(raw.encode()) <= 18000 else
                "The runtime records exceed the Buzz excerpt limit. Retrieve them with "
                "`campaignctl status`, `ledger`, and `package` using this campaign ID.\n\n"
                "Canonical combined record SHA-256: `" + digest(records) + "`.\n\n"
                "Record sizes in bytes: " + canonical({k: len(canonical(v).encode()) for k, v in records.items()}))
    return (f"# Campaign closing record: {campaign['campaign_id']}\n\n"
            f"Project: `{campaign['project_id']}`\n\n"
            f"Stored state: `{campaign['state']}`; stored outcome: `{campaign.get('outcome')}`.\n\n"
            "## SquadOps records\n\n"
            + evidence + "\n\n"
            "## Crew analysis\n\n" + interpretation + "\n")


class Watcher:
    def __init__(self, db, rpc, publish, publish_report):
        self.db, self.rpc, self.publish, self.publish_report = db, rpc, publish, publish_report
        db.execute("CREATE TABLE IF NOT EXISTS watched(id TEXT PRIMARY KEY, fingerprint TEXT, failures INTEGER, report TEXT)")
        db.commit()

    def poll(self):
        tracked = self.rpc({"command": "tracked", "args": {}})
        for item in tracked:
            cid = item["id"]
            old = self.db.execute("SELECT fingerprint,failures,report FROM watched WHERE id=?", (cid,)).fetchone()
            previous, failures, posted = old if old else (None, 0, None)
            try:
                packet = self.rpc({"command": "packet", "args": {"campaign": cid}})
                campaign = packet["campaign"]
                if campaign["state"] == "awaiting_ruling":
                    self.rpc({"command": "open-window", "args": {"campaign": cid}})
                fingerprint = digest({"state": campaign["state"], "outcome": campaign.get("outcome"),
                                      "escalations": packet["escalations"], "ledger": packet["ledger"],
                                      "analysis": packet.get("analysis")})
                if campaign["state"] == "completed" and (not posted or fingerprint != previous):
                    package = self.rpc({"command": "package", "args": {"campaign": cid}})
                    # Stable NIP-23 name makes a retry update the same post after a crash.
                    posted = self.publish_report(cid, report(packet, package))
                if fingerprint != previous:
                    text = f"{cid}: {campaign['state']}. {notice(campaign)}"
                    if posted:
                        text += " Closing record: " + posted
                    self.publish(item, text)
                self.db.execute("INSERT OR REPLACE INTO watched VALUES(?,?,?,?)", (cid, fingerprint, 0, posted))
            except Exception:
                failures += 1
                if failures == 3:
                    self.publish(item, f"{cid}: UNREADABLE after three failed readings. No success or idleness inferred; owner inspection required.")
                self.db.execute("INSERT OR REPLACE INTO watched VALUES(?,?,?,?)", (cid, previous, failures, posted))
            self.db.commit()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", default="/var/lib/nostromo-campaign-watch/watch.sqlite3")
    p.add_argument("--interval", type=int, default=300)
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

    def publish(item, text):
        # No @mentions: every named agent would start a paid turn. Humans can inspect the thread.
        return run(["messages", "send", "--channel", item["channel"], "--reply-to", item["thread"]], text)

    def publish_report(cid, text):
        name = "closing-" + cid
        result = run(["notes", "set", "--name", name, "--title", "Campaign closing record " + cid], text)
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
