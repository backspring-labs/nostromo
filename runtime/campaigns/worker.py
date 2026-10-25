"""Role-owned, one-provider-call review worker. No tools, conversation, mentions or retries."""
import argparse
import json
import os
import pwd
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .auth import NoRedirect
from .cli import call, read_event
from .core import Refused, canonical
from .review import MAX_REQUEST_BYTES, MODELS, attestations, decode, refusal_code, validate

ENDPOINTS = {"ripley": "https://api.openai.com/v1/responses", "dallas": "https://api.anthropic.com/v1/messages"}


class WorkerFailure(Refused):
    """A failure with safe diagnostic metadata; never contains request or response text."""

    def __init__(self, stage, error_type, status=None, reason_code=None, failure_report_type=None):
        self.stage = stage
        self.error_type = error_type
        self.status = status
        self.reason_code = reason_code
        self.failure_report_type = failure_report_type
        super().__init__("review failed; reservation retained and no automatic retry")

    def diagnostic(self):
        fields = ["stage=" + self.stage, "error=" + self.error_type]
        if self.status is not None:
            fields.append("http_status=" + str(self.status))
        if self.reason_code is not None:
            fields.append("reason_code=" + self.reason_code)
        if self.failure_report_type is not None:
            fields.append("failure_report_error=" + self.failure_report_type)
        return " ".join(fields)

    def record(self):
        result = {"stage": self.stage, "error": self.error_type}
        if self.status is not None:
            result["http_status"] = self.status
        if self.reason_code is not None:
            result["reason_code"] = self.reason_code
        return result


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
    try:
        if role == "ripley":
            headers["Authorization"] = "Bearer " + secret("openai.key")
        else:
            headers.update({"x-api-key": secret("anthropic.key"), "anthropic-version": "2026-10-21"})
    except Exception as error:
        raise WorkerFailure("provider_setup", type(error).__name__, reason_code=refusal_code(error)
                            if isinstance(error, Refused) else None) from None

    request = urllib.request.Request(ENDPOINTS[role], data=raw, headers=headers)
    # urllib performs one HTTP request, with redirects disabled and no SDK retry policy.
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
            data = response.read(1048577)
    except urllib.error.HTTPError as error:
        raise WorkerFailure("provider_http", type(error).__name__, status=error.code,
                            reason_code="provider_http_error") from None
    except Exception as error:
        # Do not log exception text: URL and transport exceptions may contain sensitive data.
        raise WorkerFailure("provider_transport", type(error).__name__) from None
    try:
        if len(data) > 1048576:
            raise Refused("provider response exceeds its bound")
        return decode(role, json.loads(data))
    except Exception as error:
        raise WorkerFailure("provider_response", type(error).__name__,
                            reason_code=refusal_code(error) if isinstance(error, Refused)
                            else "provider_json_invalid" if isinstance(error, json.JSONDecodeError)
                            else None) from None


def publish(job, result):
    env = dict(os.environ)
    env["BUZZ_PRIVATE_KEY"] = secret("buzz.key")
    env["BUZZ_RELAY_URL"] = "wss://nostromo.backspring.xyz"
    config = json.loads(Path("/etc/nostromo/campaign-broker.json").read_text())
    env["BUZZ_AUTH_TAG"] = config["review_auth_tags"][job["role"]]
    destination = job["payload"]["destination"]
    command = ["/opt/nostromo/runtime/bin/buzz", "messages", "send", "--channel", destination["channel"],
               "--reply-to", destination["thread"], "--content", "-"]
    response = subprocess.run(command, input=attestations(job, result), text=True, capture_output=True, env=env, timeout=120)
    if response.returncode:
        raise Refused("signed review publication failed")
    sent = json.loads(response.stdout)
    if sent.get("accepted") is not True:
        raise Refused("signed review publication was not accepted")
    return read_event(sent["event_id"])


def run(role, rpc=call, infer=provider, post=publish, persist=None):
    recovery = rpc({"command": "review-recovery-claim", "args": {}})
    if recovery is not None:
        return recover(role, recovery, rpc=rpc, post=post)
    if role == "ripley":
        rpc({"command": "review-submit", "args": {}})
    job = rpc({"command": "review-claim", "args": {}})
    if job is None:
        return {"idle": True}
    # Everything after a durable claim is single-attempt, including publication/return.
    stage = "preflight"
    try:
        remaining = job["deadline"] - time.time()
        if remaining < 30:
            raise Refused("review authorization is about to expire")
        stage = "provider_request"
        result, usage = infer(role, job["payload"]["body"], min(remaining, 780))
        stage = "result_validation"
        validate(job["kind"], result, job["payload"]["packet"]["references"])
        if persist:
            stage = "recovery_persist"
            persist(job["id"], {"result": result, "usage": usage, "model": MODELS[role], "recorded_at": time.time()})
        stage = "buzz_publication"
        proof = post(job, result)
        stage = "broker_result_submit"
        return rpc({"command": "review-result", "args": {"job": job["id"], "result": result, "usage": usage},
                    "decision_event": proof})
    except Exception as error:
        if isinstance(error, WorkerFailure):
            failure = error
        else:
            failure = WorkerFailure(stage, type(error).__name__,
                                    reason_code=refusal_code(error) if isinstance(error, Refused) else None)
        try:
            rpc({"command": "review-failed", "args": {"job": job["id"], "diagnostic": failure.record()}})
        except Exception as report_error:
            failure = WorkerFailure(failure.stage, failure.error_type, failure.status,
                                    failure.reason_code, type(report_error).__name__)
        raise failure from None


def recover(role, job, rpc=call, post=publish):
    """Publish a previously validated response only after an explicit owner authorization."""
    if job.get("role") != role:
        raise Refused("recovery job belongs to a different role")
    path = Path.home() / ".local/state/nostromo-reviews" / (job["id"] + ".json")
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
            raise Refused("private recovery record is unavailable")
        record = json.loads(path.read_text())
        if record.get("model") != MODELS[role] or not isinstance(record.get("result"), dict) or not isinstance(record.get("usage"), dict):
            raise Refused("recovery record does not match the pinned review")
        validate(job["kind"], record["result"], job["payload"]["packet"]["references"])
        proof = read_event(job["event_id"]) if job.get("event_id") else post(job, record["result"])
        return rpc({"command": "review-recovery-result", "args": {
            "job": job["id"], "result": record["result"], "usage": record["usage"]}, "decision_event": proof})
    except Exception as error:
        try:
            rpc({"command": "review-recovery-failed", "args": {"job": job["id"], "error": type(error).__name__}})
        except Exception:
            pass
        raise WorkerFailure("recovery_publication", type(error).__name__) from None


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
    except WorkerFailure as error:
        # Log only a stage, exception class and optional HTTP status, never exception text.
        print("campaign review worker failed; reservation retained; no automatic retry; "
              + error.diagnostic(), flush=True)
        raise SystemExit(1) from None
    except Exception as error:
        # Failures before a job is claimed have no review reservation to reconcile.
        print("campaign review worker failed before a claimed job; error="
              + type(error).__name__, flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
