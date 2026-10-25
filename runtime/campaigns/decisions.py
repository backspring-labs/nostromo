"""Verify Buzz decisions using the crew's existing BIP-340 helper and pinned public keys."""
import hashlib
import importlib.util
import json
import time
from pathlib import Path

from .core import Refused, canonical


def helpers():
    # Installed beside this module; in the checkout reuse the existing helper without a copy.
    path = Path(__file__).with_name("nostr_keys.py")
    if not path.exists():
        path = Path(__file__).resolve().parents[2] / "infrastructure/buzz/bin/nostr_keys.py"
    spec = importlib.util.spec_from_file_location("nostromo_nostr_keys", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verifier(policy, now=time.time):
    crypto = helpers()

    def verify(event, signer, prefix, expected, not_before=None):
        try:
            if not isinstance(event, dict) or event["kind"] != 9:
                raise ValueError()
            age = now() - event["created_at"]
            if age < -30 or age > policy.get("decision_ttl_s", 1800) and not_before is None:
                raise ValueError()
            if not_before is not None and event["created_at"] < not_before:
                raise ValueError()
            if event["pubkey"] != policy["public_keys"][signer]:
                raise ValueError()
            channels = [tag[1] for tag in event["tags"] if len(tag) == 2 and tag[0] == "h"]
            if len(channels) != 1 or channels[0] not in policy["decision_channels"]:
                raise ValueError()
            # The full message may introduce the decision, but exactly one fixed decision line binds it.
            lines = [line[len(prefix) + 2:] for line in event["content"].splitlines()
                     if line.startswith(prefix + ": ")]
            if len(lines) != 1 or json.loads(lines[0]) != expected:
                raise ValueError()
            raw = json.dumps([0, event["pubkey"], event["created_at"], event["kind"],
                              event["tags"], event["content"]], separators=(",", ":"), ensure_ascii=False)
            eid = hashlib.sha256(raw.encode()).hexdigest()
            if event["id"] != eid or not crypto.schnorr_verify(bytes.fromhex(eid), event["pubkey"], event["sig"]):
                raise ValueError()
            return eid
        except (KeyError, TypeError, ValueError, IndexError, OverflowError):
            raise Refused(f"missing, stale, mismatched or invalid {signer} {prefix} event") from None
    return verify
