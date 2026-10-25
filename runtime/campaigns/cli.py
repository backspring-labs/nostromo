"""Role-side client. Buzz signing keys stay in the role; OIDC keys never reach this client."""
import argparse
import base64
import hashlib
import json
import os
import re
import socket
import sys
import urllib.request
import uuid
from pathlib import Path

from .core import Refused, canonical
from .decisions import helpers


def call(request, path="/run/nostromo-campaigns/control.sock"):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(90)
        sock.connect(path)
        sock.sendall(canonical(request).encode() + b"\n")
        with sock.makefile("rb") as stream:
            raw = stream.readline(2097153)
        if len(raw) > 2097152 or not raw.endswith(b"\n"):
            raise Refused("broker response is incomplete or too large")
    result = json.loads(raw)
    if not result.get("ok"):
        raise Refused(result.get("error", "broker refused request"))
    return result["result"]


def read_event(eid, relay="https://nostromo.backspring.xyz"):
    if not re.fullmatch(r"[0-9a-f]{64}", eid):
        raise Refused("decision event id must be hex64")
    key_file = Path.home() / ".config/nostromo/secrets/buzz.key"
    if key_file.is_symlink() or key_file.stat().st_mode & 0o077:
        raise Refused("Buzz key must be owner-only")
    payload = canonical([{"ids": [eid], "limit": 1}]).encode()
    url = relay.rstrip("/") + "/query"
    auth = helpers().sign_event(key_file.read_text().strip(), 27235, "", [
        ["u", url], ["method", "POST"], ["payload", hashlib.sha256(payload).hexdigest()],
        ["nonce", str(uuid.uuid4())],
    ])
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json",
        "Authorization": "Nostr " + base64.b64encode(canonical(auth).encode()).decode()})
    with urllib.request.urlopen(request, timeout=15) as response:
        events = json.loads(response.read(524288))
    if not isinstance(events, list) or len(events) != 1 or events[0].get("id") != eid:
        raise Refused("decision event was not returned by the relay")
    return events[0]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", help="Read: status/log/ledger/package/escalations/packet/tracked/progress/cycle/run/checkpoints/artifacts/artifact/automation/triage; Mother: create/start/pause/resume/abort/materialize/lease-take/lease-give/open-window/advance; Ripley: plan/increment/analysis; owner: approve-definition/approve-budget/restore-shared")
    p.add_argument("--args", default="-", help="JSON file; - reads stdin")
    p.add_argument("--request-id", help="stable retry identity for a write")
    p.add_argument("--decision", help="signed Buzz decision event id")
    p.add_argument("--review", help="signed Dallas review event id")
    p.add_argument("--explain", action="store_true", help="print the exact decision/review lines to publish, without acting")
    p.add_argument("--socket", default="/run/nostromo-campaigns/control.sock")
    args = p.parse_args()
    try:
        body = json.loads(sys.stdin.read() if args.args == "-" else Path(args.args).read_text())
        request = {"command": args.command, "args": body}
        if args.request_id:
            request["request_id"] = args.request_id
        if args.explain:
            from .core import digest
            if args.command == "approve-definition":
                print("campaign-definition: " + canonical(body))
            elif args.command == "analysis":
                print("campaign-analysis: " + canonical(body))
            else:
                if not args.request_id:
                    raise Refused("gate decisions need a stable --request-id")
                print("campaign-decision: " + canonical(request))
                review = {"campaign": body["campaign"], "cycle": body["cycle"], "run": body["run"],
                          "decision_sha256": digest({"command": args.command, "args": body}), "blocking": False}
                print("campaign-review: " + canonical(review))
            return 0
        if args.decision:
            request["decision_event"] = read_event(args.decision)
        if args.review:
            request["review_event"] = read_event(args.review)
        print(canonical(call(request, args.socket)))
        return 0
    except (Refused, OSError, ValueError, KeyError) as e:
        print(canonical({"ok": False, "error": str(e) if isinstance(e, Refused) else "client input or connection failed"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
