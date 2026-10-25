"""Deferred changes never run on a live campaign; failed candidates restore the original recipe."""
import contextlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("deferred_shared", ROOT/"infrastructure/spark/bin/apply-shared-inference.py")
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


@pytest.mark.parametrize("state", ["calibrating", "paused", "escalated", "completed"])
def test_waits_for_explicit_campaign_completion_and_installed_contract(state):
    def rpc(request):
        return {"contract": 1} if request["command"] == "shared-ready" else {"state": state}
    assert job.ready(rpc, "cmp_probe") is (state == "completed")
    assert job.ready(lambda request: {}, "cmp_probe") is False


@pytest.fixture
def engine(tmp_path):
    calls = []
    locked = []
    @contextlib.contextmanager
    def lock():
        locked.append(True)
        try: yield
        finally: locked.pop()
    def switch(record, recipe, timeout):
        assert locked
        calls.append(str(recipe))
    return SimpleNamespace(switch_lock=lock, box_work=lambda: [], Record=lambda p: None,
                           RECORDS=tmp_path, to_tensorfold=switch, record_deploy=lambda *args: True), calls


def test_busy_box_never_restarts_an_engine(engine):
    api, calls = engine
    api.box_work = lambda: ["another run"]
    with pytest.raises(ValueError, match="holds"):
        job.execute(api, "candidate", "baseline", lambda: {}, lambda: None)
    assert calls == []


def test_failed_validation_restores_original_recipe_and_shared_serial_crew(engine):
    api, calls = engine
    restored = []
    result = job.execute(api, "candidate", "baseline", lambda: {"passed": False}, lambda: restored.append(True))
    assert calls == ["candidate", "baseline"]
    assert restored == [True] and result["parallel_validated"] is False


def test_success_restores_crew_only_after_passed_probe_and_deploy_record(engine):
    api, calls = engine
    order = []
    api.record_deploy = lambda *args: order.append("record") or True
    result = job.execute(api, "candidate", "baseline", lambda: order.append("probe") or {"passed": True},
                         lambda: order.append("crew") or {"window": "shared"})
    assert calls == ["candidate"] and order == ["probe", "record", "crew"]
    assert result == {"parallel_validated": True, "crew": {"window": "shared"}}


def test_failed_baseline_restoration_keeps_crew_stopped(engine):
    api, calls = engine
    original = api.to_tensorfold
    restored = []
    def switch(record, recipe, timeout):
        original(record, recipe, timeout)
        if recipe == "baseline":
            raise ValueError("baseline restoration failed")
    api.to_tensorfold = switch
    with pytest.raises(ValueError, match="baseline restoration failed"):
        job.execute(api, "candidate", "baseline", lambda: {"passed": False}, lambda: restored.append(True))
    assert calls == ["candidate", "baseline"] and restored == []
