"""Role-owned, one-provider-call review worker. No tools, conversation, mentions or retries."""
import argparse
import json
import os
import pwd
import subprocess
import time
import urllib.request
from pathlib import Path

from .auth import NoRedirect
from .cli import call, read_event
from .core import Refused, canonical
from .review import MAX_REQUEST_BYTES, MODELS, attestations, decode, validate

ENDPOINTS = {"ripley": "https://api.openai.com/v1/responses", "dallas": "https://api.anthropic.com/v1/messages"}


def secret(name):
    p = Path.home() / ".config/nostromo/secrets" / name
    if p.is_symlink() or not p.is_file() or p.stat().st_uid != os.getuid() or p.stat().st_mode & 0o077:
        raise Refused("role secret must be a private regular file owned by this role")
    return p.read_text().strip()


def provider(role, body, timeout):
    raw = canonical(body).encode()
    if body.get("model") != MODELS[role] or len(raw) > MAX_REQUEST_BYTES:
        raise Refused("review request violates the fixed model or input bound")
    headers = {"Content-Type": "application/json"}
    if role == "ripley":
        headers["Authorization"] = "Bearer " + secret("openai.key")
    else:
        headers.update({"x-api-key": secret("anthropic.key"), "anthropic-version": "2026-10-21"})
    request = urllib.request.Request(ENDPOINTS[role], data=raw, headers=headers)
    # urllib performs one HTTP request, with redirects disabled and no SDK retry policy.
    with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
        data = response.read(1048577)
    if len(data) > 1048576:
        raise Refused("provider response exceeds its bound")
    return decode(role, json.loads(data))


def publish(job, result):
    env = dict(os.environ)
    env["BUZZ_PRIVATE_KEY"] = secret("buzz.key")
    env["BUZZ_RELAY_URL"] = "wss://nostromo.backspring.xyz"
    config = json.loads(Path("/etc/nostromo/campaign-broker.json").read_text())
    env["BUZZ_AUTH_TAG"] = config["review_auth_tags"][job["role"]]
    destination = job["payload"]["destination"]
    command = ["/opt/nostromo/runtime/bin/buzz", "messages", "send", "--channel", destination["channel"],
               "--reply-to", destination["thread"], "--content", "-"]
    response = subprocess.run(command, input=attestations(job, result), text=True, capture_output=True, env=env, timeout=30)
    if response.returncode:
        raise Refused("signed review publication failed")
    sent = json.loads(response.stdout)
    if sent.get("accepted") is not True:
        raise Refused("signed review publication was not accepted")
    return read_event(sent["event_id"])


def run(role, rpc=call, infer=provider, post=publish, persist=None):
    if role == "ripley":
        rpc({"command": "review-submit", "args": {}})
    job = rpc({"command": "review-claim", "args": {}})
    if job is None:
        return {"idle": True}
    # Everything after a durable claim is single-attempt, including publication/return.
    try:
        remaining = job["deadline"] - time.time()
        if remaining < 30:
            raise Refused("review authorization is about to expire")
        result, usage = infer(role, job["payload"]["body"], min(remaining, 780))
        validate(job["kind"], result, job["payload"]["packet"]["references"])
        if persist:
            persist(job["id"], {"result": result, "usage": usage, "model": MODELS[role], "recorded_at": time.time()})
        proof = post(job, result)
        return rpc({"command": "review-result", "args": {"job": job["id"], "result": result, "usage": usage},
                    "decision_event": proof})
    except Exception:
        rpc({"command": "review-failed", "args": {"job": job["id"]}})
        raise Refused("review failed; reservation retained and no automatic retry") from None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("role", choices=list(MODELS))
    args = p.parse_args()
    if pwd.getpwuid(os.getuid()).pw_name != args.role:
        raise SystemExit("worker must run as its actual role")
    os.umask(0o077)
    state = Path.home() / ".local/state/nostromo-reviews"
    state.mkdir(parents=True, exist_ok=True, mode=0o700)

    def persist(jid, record):
        # Contains no credentials, only recovery evidence. Never replayed as another call.
        target = state / (jid + ".json")
        with target.open("x") as f:
            f.write(canonical(record) + "\n")
            f.flush()
            os.fsync(f.fileno())
    try:
        print(canonical(run(args.role, persist=persist)), flush=True)
    except Exception:
        # Provider exceptions may include echoed request content; never log their bodies.
        print("campaign review worker failed; inspect the retained job and role recovery record", flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
