"""The campaign controller's posts: plain English, whose move it is, the owner mentioned only on theirs."""
import sqlite3

from runtime.campaigns.watch import Watcher, fingerprint, labels, notice, report

BASE = {"campaign_id": "cmp_a", "project_id": "prj-shelfnote", "created_at": "2026-11-01T15:45:32Z",
        "updated_at": "2026-11-01T16:52:51Z", "objective": {"target_accepted_increments": 3,
        "statement": "work the goals.md backlog"}}


def packet(state, outcome=None, control=None, jobs=(), ledger=(), analysis=None):
    return {"campaign": {**BASE, "state": state, "outcome": outcome}, "ledger": list(ledger), "escalations": [],
            "crew_policy": {"paid_dispatches": 16}, "analysis": analysis,
            "automation": {"control": control or {"state": "active"}, "jobs": list(jobs)}}


def test_a_working_campaign_says_what_the_squad_is_doing_and_whose_move_it_is():
    text, yours = notice(packet("at_proposal"), "ShelfNote campaign 1")
    assert text == ("ShelfNote campaign 1: the squad is proposing the next increment. "
                    "0 of 3 increments accepted; 0 of 16 reviews used. Next: the squad.")
    assert yours is False and "cmp_" not in text and "{" not in text


def test_a_ruling_in_progress_names_the_reviewer_whose_turn_it_is():
    jobs = [{"role": "ripley", "state": "done", "reserved": 1}, {"role": "dallas", "state": "queued", "reserved": 0}]
    text, _ = notice(packet("awaiting_ruling", jobs=jobs), "ShelfNote campaign 1")
    assert text.endswith("1 of 16 reviews used. Next: Dallas.")


def test_a_pause_for_the_owner_is_marked_as_the_owners_move():
    text, yours = notice(packet("paused", control={"state": "parked", "reason": "Ripley requires an owner decision"}),
                         "ShelfNote campaign 1")
    assert text.startswith("ShelfNote campaign 1: paused for you. Ripley requires an owner decision.")
    assert text.endswith("Next: you.") and yours is True


def test_a_closed_campaign_waits_for_ripleys_analysis_then_for_nobody():
    analysing = packet("completed", "aborted", jobs=[{"role": "ripley", "kind": "analysis", "state": "queued"}])
    text, _ = notice(analysing, "ShelfNote campaign 1")
    assert "closed. It was aborted." in text and text.endswith("Next: Ripley, for the closing analysis.")
    text, _ = notice(packet("completed", "aborted"), "ShelfNote campaign 1")
    assert text.endswith("Next: nobody; it has closed, with no closing analysis to come.")
    text, _ = notice(packet("completed", "aborted", analysis={"analysis": "Done."}), "ShelfNote campaign 1")
    assert text.endswith("Next: nobody; it has closed.")


def test_review_jobs_changing_state_is_not_news():
    queued = packet("awaiting_ruling", jobs=[{"role": "ripley", "state": "queued"}])
    claimed = packet("awaiting_ruling", jobs=[{"role": "ripley", "state": "claimed"}])
    assert fingerprint(queued) == fingerprint(claimed)
    assert fingerprint(queued) != fingerprint(packet("paused", control={"state": "parked", "reason": "x"}))


def test_campaigns_are_numbered_per_product_in_start_order():
    a = packet("completed"); b = packet("at_proposal")
    b["campaign"] = {**b["campaign"], "campaign_id": "cmp_b", "created_at": "2026-11-02T10:00:00Z"}
    other = packet("at_proposal"); other["campaign"] = {**other["campaign"], "project_id": "group_run"}
    names = labels({"cmp_a": a, "cmp_b": b, "cmp_c": other})
    assert names == {"cmp_a": "ShelfNote campaign 1", "cmp_b": "ShelfNote campaign 2", "cmp_c": "Group Run campaign 1"}


def test_the_closing_record_reads_as_a_summary_not_a_dump():
    ledger = [{"ruling": {"decision": "returned_for_revision", "reason": "Revise the acceptance source first. More."}}]
    text = report(packet("completed", "aborted", ledger=ledger), {"identity": "pkg"}, "ShelfNote campaign 1")
    assert text.startswith("# ShelfNote campaign 1: closed")
    assert "**Ran:** 10:45 am ET, Nov 1 to 11:52 am ET, Nov 1." in text
    assert "1. Returned for revision. Revise the acceptance source first." in text
    assert "```json" not in text and "{" not in text


def test_the_owner_is_mentioned_only_on_their_move():
    db = sqlite3.connect(":memory:")
    posts = []
    states = iter([packet("at_proposal"), packet("paused", control={"state": "parked", "reason": "Ripley requires an owner decision"})])
    current = {}
    def rpc(request):
        if request["command"] == "tracked":
            current["p"] = next(states)
            return [{"id": "cmp_a", "channel": "c", "thread": "t"}]
        return current["p"]
    watcher = Watcher(db, rpc, lambda item, text, yours: posts.append((text, yours)), lambda *_: None)
    watcher.poll(); watcher.poll()
    assert [yours for _, yours in posts] == [False, True]
    assert not posts[0][0].startswith("@") and posts[1][0].startswith("@jladd ")


def test_the_closing_record_says_why_a_campaign_was_stopped():
    p = packet("completed", "aborted")
    p["log"] = [{"operation": "abort", "reason": "Owner decision: the scope excluded the criterion files."}]
    assert "**Why it was stopped:** Owner decision: the scope excluded the criterion files." in report(p, {}, "ShelfNote campaign 1")


def test_a_registered_product_keeps_its_own_spelling():
    from runtime.campaigns.watch import product
    assert product("prj-shelfnote") == "ShelfNote" and product("group_run") == "Group Run"


def test_a_new_fingerprint_format_is_adopted_silently_not_announced():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE watched(id TEXT PRIMARY KEY, fingerprint TEXT, failures INTEGER, report TEXT)")
    db.execute("INSERT INTO watched VALUES('cmp_a','old-format-fingerprint',0,'30023:x:closing-cmp_a')")
    db.commit()
    posts, notes = [], []
    rpc = lambda r: [{"id": "cmp_a", "channel": "c", "thread": "t"}] if r["command"] == "tracked" else packet("completed", "aborted")
    Watcher(db, rpc, lambda item, text, yours: posts.append(text), lambda *a: notes.append(a)).poll()
    assert posts == [] and notes == []
    Watcher(db, rpc, lambda item, text, yours: posts.append(text), lambda *a: notes.append(a)).poll()
    assert posts == [] and notes == [], "nothing changed since adoption, so still nothing to say"


def test_a_fresh_watcher_still_announces():
    db = sqlite3.connect(":memory:")
    posts = []
    rpc = lambda r: [{"id": "cmp_a", "channel": "c", "thread": "t"}] if r["command"] == "tracked" else packet("at_proposal")
    Watcher(db, rpc, lambda item, text, yours: posts.append(text), lambda *a: None).poll()
    assert len(posts) == 1


def test_a_refused_launch_is_the_squads_wait_not_the_owners_move():
    # SquadOps retries launch_blocked on its own and escalates if it never launches.
    text, yours = notice(packet("launch_blocked"), "ShelfNote campaign 1")
    assert "retries on its own" in text and text.endswith("Next: the squad.") and yours is False


SHELF = {**BASE, "objective": {"target_accepted_increments": 3,
                               "statement": "Find, track and organise a shelf. In order: Search; Reading status; Tags"}}


def stepped(kind, status, ledger=()):
    p = packet("building", ledger=ledger)
    p["campaign"] = {**SHELF, "state": "building", "outcome": None}
    p["progress"] = {"cycles": [{"runs": [{"workload_type": "proposal", "status": "completed", "started_at": "2026-11-02T02:23:35Z"},
                                          {"workload_type": kind, "status": status, "started_at": "2026-11-02T02:39:26Z"}]}]}
    return p


def test_an_accepted_increment_counts_when_squadops_reports_its_outcome_as_a_record():
    # 2026-11-01: the ledger's outcome is {"verdict": "accepted", ...}; reading only a string counted none.
    row = {"cycle_id": "c1", "run_id": "r1", "ruling": {"decision": "approved"},
           "outcome": {"action": "propose", "ending": "assessed", "verdict": "accepted"}}
    text, _ = notice(packet("building", ledger=[row]), "ShelfNote campaign 4")
    assert "1 of 3 increments accepted" in text


def test_the_squads_step_is_named_with_its_increment():
    text, _ = notice(stepped("implementation", "running"), "ShelfNote campaign 4")
    assert text.startswith("ShelfNote campaign 4: the squad is building Search.")
    text, _ = notice(stepped("framing", "completed"), "ShelfNote campaign 4")
    assert "the squad finished planning how to build Search" in text


def test_a_new_step_is_news():
    assert fingerprint(stepped("framing", "running")) != fingerprint(stepped("implementation", "running"))


def test_a_held_campaign_warns_half_an_hour_before_its_cutoff(monkeypatch):
    import time
    held = packet("paused", control={"state": "parked", "reason": "evidence_size_hold: too big", "deadline": 1793596763.0})
    monkeypatch.setattr(time, "time", lambda: 1793596763.0 - 3600)
    early = fingerprint(held)
    assert "cutoff" not in notice(held, "ShelfNote campaign 4")[0]
    monkeypatch.setattr(time, "time", lambda: 1793596763.0 - 1500)
    assert fingerprint(held) != early, "crossing into the last half hour is news"
    text, yours = notice(held, "ShelfNote campaign 4")
    assert "It stops at its cutoff, 12:19 am ET, Mon Nov 2, in under half an hour" in text and yours
