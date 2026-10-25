#!/usr/bin/env python3
"""One-shot owner job: wait for the named campaign, validate two lanes, then restore local crew.

Run as the Spark owner. No root privileges, paid model calls, campaign decisions, retries, or
credential rewrites. A failed candidate is restored to the unchanged one-lane TensorFold recipe.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def ready(rpc, campaign):
    capability = rpc({"command": "shared-ready", "args": {}})
    if capability.get("contract") != 1:
        return False
    status = rpc({"command": "status", "args": {"campaign": campaign}})
    return status.get("state") == "completed"


def atomic_state(path, **state):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"updated_at": time.time(), **state}, indent=2)+"\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def load_engine(checkout):
    spec = importlib.util.spec_from_file_location("nostromo_engine_switch", checkout/"scripts/dev/ops/engine_switch.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def execute(engine, candidate, baseline, run_probe, restore_crew):
    """Keep the host engine lock across switch, validation, and any rollback."""
    with engine.switch_lock():
        if engine.box_work():
            raise ValueError("other campaign/run work still holds the Spark")
        record = engine.Record(engine.RECORDS/"nostromo-shared-inference.jsonl")
        try:
            engine.to_tensorfold(record, candidate, 600)
            result = run_probe()
            if result.get("passed") is not True:
                raise ValueError("two-lane validation failed")
            if engine.record_deploy(record, "nostromo shared inference --parallel 2") is not True:
                raise ValueError("candidate deploy record failed")
        except Exception:
            engine.to_tensorfold(record, baseline, 600)
            if engine.record_deploy(record, "nostromo shared inference restored one lane") is not True:
                raise ValueError("one-lane restored but its deploy record failed") from None
            return {"parallel_validated": False, "fallback": "original one-lane TensorFold recipe",
                    "crew": restore_crew()}
        return {"parallel_validated": True, "crew": restore_crew()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--squadops-checkout", required=True, type=Path)
    parser.add_argument("--nostromo-checkout", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    state = args.state_dir/"state.json"
    if state.exists() and json.loads(state.read_text()).get("phase") not in {"waiting", None}:
        raise SystemExit("Prior attempt exists; inspect its result before any further action")
    sys.path.insert(0, "/usr/local/lib/nostromo")
    from campaigns.cli import call
    deadline = time.monotonic()+24*3600
    while True:
        try:
            admitted = ready(call, args.campaign)
        except Exception:
            admitted = False  # Unreadable or old broker is never treated as completion.
        if admitted:
            break
        atomic_state(state, phase="waiting", campaign=args.campaign,
                     reason="waiting for installed sharing contract and the named campaign to complete")
        if time.monotonic() >= deadline:
            raise SystemExit("Deferred window expired without verified completion; no engine change made")
        time.sleep(30)
    atomic_state(state, phase="validating", campaign=args.campaign)
    engine = load_engine(args.squadops_checkout)
    baseline = args.squadops_checkout/"infra/tensorfold/recipes/qwen27b-nvfp4.yaml"
    candidate = args.squadops_checkout/"infra/tensorfold/recipes/candidates/qwen27b-nvfp4-parallel2.yaml"
    output = args.state_dir/"probe.json"
    def probe():
        command = [sys.executable, str(args.nostromo_checkout/"infrastructure/spark/bin/probe-shared-inference.py"),
                   "--key-file", str(engine.KEY_FILE), "--output", str(output)]
        subprocess.run(command, check=False, timeout=1200, stdout=subprocess.DEVNULL)
        return json.loads(output.read_text())
    try:
        restored = execute(engine, candidate, baseline, probe,
                           lambda: call({"command": "restore-shared", "args": {"campaign": args.campaign}}))
        atomic_state(state, phase="complete" if restored["parallel_validated"] else "complete_with_fallback",
                     campaign=args.campaign, result=restored, validation=str(output),
                     note="Mother/Brett restored under shared-use policy; result identifies parallel or serial service")
    except Exception as error:
        atomic_state(state, phase="blocked", campaign=args.campaign,
                     error=type(error).__name__, note="inspect engine record and probe; no automatic retry")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
