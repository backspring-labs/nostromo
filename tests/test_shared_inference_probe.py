"""A concurrency probe must distinguish queued work from overlapping generation and reject partial streams."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("shared_probe", ROOT/"infrastructure/spark/bin/probe-shared-inference.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_overlap_requires_both_streams_to_emit_before_either_finishes():
    assert probe.overlaps([{"first_token_s": 1, "finished_s": 5}, {"first_token_s": 2, "finished_s": 6}])
    assert not probe.overlaps([{"first_token_s": 1, "finished_s": 2}, {"first_token_s": 3, "finished_s": 6}])
    assert not probe.overlaps([{"first_token_s": None, "finished_s": 5}, {"first_token_s": 2, "finished_s": 6}])


def test_registry_reader_does_not_confuse_crew_keys_with_squad_key(tmp_path):
    key = tmp_path/"keys"
    key.write_text("nostromo-mother: mother-fixture\nsquadops: squad-fixture\nnostromo-brett: brett-fixture\n")
    key.chmod(0o600)
    assert probe.key_from_registry(key) == "squad-fixture"
    key.write_text("squadops: a\nsquadops: b")
    with pytest.raises(ValueError, match="values withheld"):
        probe.key_from_registry(key)
    key.chmod(0o644)
    with pytest.raises(ValueError, match="owner-only"):
        probe.key_from_registry(key)


@pytest.mark.parametrize("failure", [None, "error", "missing_done", "missing_usage"])
def test_stream_checks_completion_and_usage_without_exposing_prompts(monkeypatch, failure):
    monkeypatch.setattr(probe, "memory", lambda: (30*probe.GIB, 0))
    events = [{"choices": [{"delta": {"content": "hello"}}]}]
    if failure != "missing_usage":
        events.append({"choices": [], "usage": {"completion_tokens": 1}})
    if failure == "error":
        events.append({"error": {"message": "fixture"}})
    lines = [b"data: "+json.dumps(x).encode()+b"\n" for x in events]
    if failure != "missing_done":
        lines.append(b"data: [DONE]\n")
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __iter__(self): return iter(lines)
    monkeypatch.setattr(probe.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    client = probe.Probe("fixture-only", "model")
    if failure:
        with pytest.raises(ValueError):
            client.generate([], 123)
    else:
        result = client.generate([], 123)
        assert result["sha256"] and result["usage"]["completion_tokens"] == 1
        assert "hello" not in json.dumps(result)


def test_memory_floor_violation_cancels_work(monkeypatch):
    monkeypatch.setattr(probe, "memory", lambda: (30*probe.GIB, 0))
    client = probe.Probe("fixture-only", "model")
    monkeypatch.setattr(probe, "memory", lambda: (19*probe.GIB, 0))
    class Done:
        n = 0
        def wait(self, *args):
            self.n += 1
            return self.n > 1
    client.monitor(Done())
    assert client.abort.is_set()
