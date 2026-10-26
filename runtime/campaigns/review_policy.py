"""Decision availability from immutable approval and the current SquadOps cycle record."""
from .core import Refused

DECISIONS = ["approved", "rejected", "returned_for_revision", "needs_owner"]
POLICY_REFUSAL = "proposal revision is unavailable under the approved campaign policy"


def proposal_revisions(campaign, cycle, approved_policy):
    def bound(value):
        return value if type(value) is int and value >= 0 else None

    # SquadOps resolves config with a shallow merge: overrides replace defaults.
    def mapping(value):
        return value if isinstance(value, dict) else {}

    config = {**mapping(cycle.get("applied_defaults")), **mapping(cycle.get("execution_overrides"))}
    block = config.get("campaign_proposal")
    limits = {
        "approved": bound(mapping(approved_policy).get("max_proposal_revisions")),
        "campaign": bound(mapping(campaign.get("policy")).get("max_proposal_revisions")),
        "cycle": bound(block.get("max_revisions")) if isinstance(block, dict) else None,
    }
    runs = cycle.get("runs")
    history_known = isinstance(runs, list) and bool(runs) and all(
        isinstance(run, dict) and run.get("workload_type") and run.get("status") for run in runs)
    # Match SquadOps' restart-stable count: cancelled proposal runs are superseded versions.
    used = sum(run["workload_type"] == "proposal" and run["status"] == "cancelled"
               for run in runs) if history_known else None
    remaining = None
    if None in limits.values():
        reason = "revision_policy_missing"
    elif len(set(limits.values())) != 1:
        reason = "revision_policy_mismatch"
    elif used is None:
        reason = "revision_history_missing"
    else:
        remaining = max(0, limits["approved"] - used)
        reason = "revision_available" if remaining else "revision_allowance_exhausted"
    return {"available": reason == "revision_available", "reason": reason,
            "limits": limits, "used": used, "remaining": remaining}


def decision_contract(packet):
    gate = packet.get("gate", {})
    allowed = list(DECISIONS)
    contract = {"allowed_decisions": allowed}
    if gate.get("gate") == "progress_increment_ruling":
        cycles = [c for c in packet.get("cycles", []) if c.get("cycle_id") == gate.get("cycle")]
        revision = proposal_revisions(packet.get("campaign", {}), cycles[0] if len(cycles) == 1 else {},
                                      packet.get("approved_policy", {}))
        contract["proposal_revisions"] = revision
        if not revision["available"]:
            allowed.remove("returned_for_revision")
    return contract


def validate_decision(packet, result):
    if result.get("decision") not in decision_contract(packet)["allowed_decisions"]:
        raise Refused(POLICY_REFUSAL)
