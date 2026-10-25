#!/usr/bin/env python3
"""Owner-only, post-cycle validation of two shared TensorFold lanes. Never changes the server."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

GIB = 2**30


def key_from_registry(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise ValueError("key registry must be owner-only")
    matches = [line.partition(":")[2].strip() for line in path.read_text().splitlines()
               if line.partition(":")[0].strip() == "squadops"]
    if len(matches) != 1 or not matches[0] or any(c.isspace() for c in matches[0]):
        raise ValueError("expected one squadops label; key values withheld")
    return matches[0]


def memory():
    values = {key: int(value.split()[0])*1024 for line in Path("/proc/meminfo").read_text().splitlines()
              for key, _, value in [line.partition(":")] if key in {"MemAvailable", "SwapTotal", "SwapFree"}}
    return values["MemAvailable"], values["SwapTotal"]-values["SwapFree"]


def overlaps(results):
    return all(r["first_token_s"] is not None for r in results) and max(r["first_token_s"] for r in results) < min(r["finished_s"] for r in results)


class Probe:
    def __init__(self, key, model, floor=20*GIB):
        self.key, self.model, self.floor = key, model, floor
        self.abort = threading.Event()
        self.min_available, self.initial_swap = memory()
        self.max_swap = self.initial_swap
        self.origin = time.monotonic()

    def request(self, path, body):
        return urllib.request.Request("http://127.0.0.1:8090"+path, data=json.dumps(body).encode(),
                                      headers={"Content-Type": "application/json", "Authorization": "Bearer "+self.key})

    def prompt(self, target):
        rows = max(1, target//18)
        for _ in range(5):
            text = "\n".join(f"Record {i:06d}: service alpha records vector checksum {i*17} and preserves the original observation." for i in range(rows))
            messages = [{"role": "user", "content": text+"\nWrite 100 numbered observations about these records, at least 15 words each. Do not stop early."}]
            body = {"model": self.model, "messages": messages, "chat_template_kwargs": {"enable_thinking": False}}
            with urllib.request.urlopen(self.request("/tokenize", body), timeout=60) as response:
                tokens = json.loads(response.read(4*1024*1024))["count"]
            if target*0.95 <= tokens <= target*1.02:
                return messages, tokens
            rows = max(1, int(rows*target/tokens))
        raise ValueError("could not construct the requested long-context probe")

    def generate(self, messages, seed, barrier=None):
        body = {"model": self.model, "messages": messages, "max_tokens": 1024, "temperature": 0,
                "seed": seed, "chat_template_kwargs": {"enable_thinking": False},
                "stream": True, "stream_options": {"include_usage": True}}
        if barrier:
            barrier.wait(timeout=10)
        started = time.monotonic()-self.origin
        first, parts, usage, finished = None, [], None, None
        with urllib.request.urlopen(self.request("/v1/chat/completions", body), timeout=180) as response:
            for line in response:
                if self.abort.is_set():
                    raise ValueError("memory reserve violated; cancelling probe")
                if not line.startswith(b"data: "):
                    continue
                raw = line[6:].strip()
                if raw == b"[DONE]":
                    finished = time.monotonic()-self.origin
                    break
                event = json.loads(raw)
                if event.get("error"):
                    raise ValueError("TensorFold emitted a stream error")
                if event.get("usage"):
                    usage = event["usage"]
                for choice in event.get("choices", []):
                    delta = choice.get("delta", {})
                    text = delta.get("content") or ""
                    if text:
                        first = first if first is not None else time.monotonic()-self.origin
                        parts.append(text)
        if first is None or finished is None or not usage:
            raise ValueError("incomplete generation or missing usage")
        return {"started_s": started, "first_token_s": first, "finished_s": finished,
                "ttft_s": first-started, "elapsed_s": finished-started,
                "sha256": hashlib.sha256("".join(parts).encode()).hexdigest(), "usage": usage}

    def monitor(self, done):
        while not done.wait(0.2):
            available, swap = memory()
            self.min_available = min(self.min_available, available)
            self.max_swap = max(self.max_swap, swap)
            if available < self.floor or swap-self.initial_swap > 64*1024*1024:
                self.abort.set()

    def run(self):
        done = threading.Event()
        monitor = threading.Thread(target=self.monitor, args=(done,), daemon=True)
        monitor.start()
        try:
            prompts = [self.prompt(48000), self.prompt(32000)]
            solo = [self.generate(messages, 901+i) for i, (messages, _) in enumerate(prompts)]
            barrier = threading.Barrier(2)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(self.generate, messages, 901+i, barrier) for i, (messages, _) in enumerate(prompts)]
                paired = [future.result(timeout=240) for future in futures]
            if self.abort.is_set() or not overlaps(paired):
                raise ValueError("two long-context generations did not overlap safely")
            if [x["sha256"] for x in solo] != [x["sha256"] for x in paired]:
                raise ValueError("paired output differs from same-seed solo output")
            return {"passed": True, "model": self.model, "prompt_tokens": [n for _, n in prompts],
                    "solo": solo, "parallel": paired, "overlap_verified": True,
                    "min_available_gib": self.min_available/GIB,
                    "swap_growth_mib": (self.max_swap-self.initial_swap)/1024**2}
        finally:
            done.set(); monitor.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="qwen3.8-27b-tf-nvfp4")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        with urllib.request.urlopen("http://127.0.0.1:8001/health/host", timeout=15) as response:
            host = json.load(response)
        if host.get("box", {}).get("quiet") is not True:
            raise ValueError("runtime box is not quiet")
        # The switch helper also checks every campaign/run and holds its host lock before restart.
        held = subprocess.run(["docker", "exec", "squadops-postgres", "psql", "-U", "squadops", "-d", "squadops", "-At", "-c",
            "select (select count(*) from cycle_runs where status in ('running','queued','paused')) + (select count(*) from campaigns where state <> 'completed')"],
            capture_output=True, text=True, check=True, timeout=15)
        if held.stdout.strip() != "0":
            raise ValueError("an open run or campaign still holds the validation window")
        command = json.loads(subprocess.check_output(["docker", "inspect", "-f", "{{json .Args}}", "squadops-tensorfold"],text=True))
        index = command.index("--parallel")
        if command[index+1] != "2":
            raise ValueError("candidate server is not configured with exactly two lanes")
        probe = Probe(key_from_registry(args.key_file), args.model)
        if probe.min_available < probe.floor:
            raise ValueError("memory reserve unavailable before probe")
        result = probe.run()
        result["server_args"] = command
    except Exception as error:
        result = {"passed": False, "error": type(error).__name__ + ": " + str(error)[:180]}
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(result,indent=2)+"\n"); path.chmod(0o600)
    print(json.dumps({k:v for k,v in result.items() if k not in {"server_args","solo","parallel"}}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
