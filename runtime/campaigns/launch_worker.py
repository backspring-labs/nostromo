"""Mother-owned no-model launch timer and durable signed-message outbox."""
import argparse
import base64
import fcntl
import hashlib
import json
import os
import pwd
import tempfile
import urllib.request
import uuid
from pathlib import Path

from .auth import NoRedirect
from .cli import call, read_event
from .core import Refused, canonical, digest
from .decisions import helpers
from .worker import secret

RELAY = "https://nostromo.backspring.xyz"


def submit_event(event, key, auth_tag):
    """One POST of a persisted kind-9 event. Replays retain the same event ID."""
    payload = canonical(event).encode()
    url = RELAY + "/events"
    auth = helpers().sign_event(key, 27235, "", [["u", url], ["method", "POST"],
        ["payload", hashlib.sha256(payload).hexdigest()], ["nonce", str(uuid.uuid4())]])
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json",
        "Authorization": "Nostr " + base64.b64encode(canonical(auth).encode()).decode(),
        "x-auth-tag": canonical(auth_tag)})
    # Buzz stored kind-9 events deduplicate by event ID. This is not a moderation command.
    with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise Refused("launch publication response exceeds its bound")
    result = json.loads(raw)
    if result.get("accepted") is not True or result.get("event_id") != event["id"]:
        raise Refused("relay did not confirm the exact launch event")


class Publisher:
    def __init__(self, state, key, auth_tag, submit=submit_event, lookup=read_event):
        self.state, self.key, self.auth_tag = Path(state), key, auth_tag
        self.submit, self.lookup = submit, lookup
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.state.is_symlink() or self.state.stat().st_uid != os.getuid() or self.state.stat().st_mode & 0o077:
            raise Refused("launch outbox must be private and role-owned")
        if not isinstance(auth_tag, list) or not auth_tag or auth_tag[0] != "auth":
            raise Refused("Mother's existing Buzz membership tag is required")

    def __call__(self, job):
        # Serialize timer/manual invocations so a single outbox key never gets two events.
        descriptor = os.open(self.state / ".publisher.lock", os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            root = self.lookup(job["thread"])
            if (root.get("id") != job["thread"] or root.get("kind") != 9 or
                    [t[1] for t in root.get("tags", []) if len(t) >= 2 and t[0] == "h"] != [job["channel"]] or
                    any(len(t) >= 4 and t[0] == "e" and t[3] in {"root", "reply"} for t in root.get("tags", []))):
                raise Refused("approved campaign destination is not a top-level channel post")
            target = self.state / (digest({"launch": job["id"], "phase": job["phase"]}) + ".json")
            tags = [["h", job["channel"]], ["e", job["thread"], "", "reply"], self.auth_tag]
            if target.exists() or target.is_symlink():
                if target.is_symlink() or not target.is_file() or target.stat().st_uid != os.getuid() or target.stat().st_mode & 0o077:
                    raise Refused("saved launch event must be a private role-owned file")
                if target.stat().st_size > 65536:
                    raise Refused("saved launch event exceeds its bound")
                event = json.loads(target.read_text())
                eid = hashlib.sha256(canonical([0, event["pubkey"], event["created_at"],
                    event["kind"], event["tags"], event["content"]]).encode()).hexdigest()
                if (event.get("kind") != 9 or event.get("content") != job["content"] or event.get("tags") != tags or
                        event.get("pubkey") != helpers().xonly_pubkey(self.key) or event.get("id") != eid or
                        not helpers().schnorr_verify(bytes.fromhex(eid), event["pubkey"], event["sig"])):
                    raise Refused("saved launch event does not match this intent and phase")
                try:
                    return self.lookup(event["id"])
                except Exception:
                    pass  # Re-submit only this exact durable kind-9 event, never re-sign it.
            else:
                event = helpers().sign_event(self.key, 9, job["content"], tags)
                with tempfile.NamedTemporaryFile("w", dir=self.state, prefix=".launch-", delete=False) as temp:
                    temp.write(canonical(event) + "\n")
                    temp.flush()
                    os.fsync(temp.fileno())
                    temporary = Path(temp.name)
                os.replace(temporary, target)
                directory = os.open(self.state, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            self.submit(event, self.key, self.auth_tag)
            return self.lookup(event["id"])


def run(rpc=call, publish=None):
    states = rpc({"command": "launch-advance", "args": {}})
    job = rpc({"command": "launch-notice-claim", "args": {}})
    if job is None:
        return {"launches": states, "notice": "idle"}
    try:
        event = publish(job)
        return rpc({"command": "launch-notice-result", "args": {"launch": job["id"], "phase": job["phase"]},
                    "decision_event": event})
    except Exception as error:
        try:
            rpc({"command": "launch-notice-failed", "args": {
                "launch": job["id"], "phase": job["phase"], "error": type(error).__name__}})
        except Exception:
            pass
        # Never print exception bodies, HTTP responses, credentials, or model text.
        raise Refused("launch notice failed; inspect launch-status; error=" + type(error).__name__) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default="/var/lib/nostromo-campaign-launch")
    args = parser.parse_args()
    if pwd.getpwuid(os.getuid()).pw_name != "mother":
        raise SystemExit("launch worker must run as Mother")
    os.umask(0o077)
    try:
        config = json.loads(Path("/etc/nostromo/campaign-broker.json").read_text())
        publisher = Publisher(args.state, secret("buzz.key"), json.loads(config["watcher_auth_tag"]))
        print(canonical(run(publish=publisher)), flush=True)
    except Refused as error:
        print(canonical({"error": str(error)}), flush=True)
        raise SystemExit(1) from None
    except Exception as error:
        print(canonical({"error": type(error).__name__}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
