# Defect draft: Plan-review packet omits the consolidated planning artifact

**Owner:** Nostromo campaign automation.
**Status:** Filed as [backspring-labs/nostromo#11](https://github.com/backspring-labs/nostromo/issues/11). Confirmed packet-selection gap in the version deployed on Spark for this campaign; assess severity and intended artifact contract.
**Observed:** 2026-10-26, campaign `cmp_29048a00fdb3460c0675529a`.

## Summary

Nostromo's bounded review packet selects artifacts by type but omits the canonical consolidated `planning_artifact.md` (`artifact_type: document`). For a `progress_plan_review` decision, the packet currently includes `interface_manifest`, `verification_contract`, `control_implementation_plan`, and `merge_decisions`, but not the consolidated planning artifact, test strategy, or run report.

## Expected behavior

Ripley should receive the complete authoritative planning evidence needed to judge the plan gate, or the review contract should explicitly define a smaller sufficient evidence set and reject a gate when that evidence is incomplete. If the consolidated planning artifact is part of the proposal, it should be included intact and referenceable in the review packet.

## Actual behavior

`runtime/campaigns/automation.py` builds `packet()` from a fixed `selected` artifact-type set. For gate reviews it selects `interface_manifest`, `verification_contract`, `control_implementation_plan`, `merge_decisions`, `change_request`, `definition_of_done`, `test_report`, and `accepted_tree`; it does not select the `document` type or identify `planning_artifact.md` by filename/metadata. The campaign's actual `planning_artifact.md` has artifact ID `art_4a02e6d6c9cc` and is therefore absent from that selected packet.

The checked-in file hash and Spark's installed `/usr/local/lib/nostromo/campaigns/automation.py` hash both equal `e996d77f4b7300e22d1cb6f74af4e3c602331e63ae64fedbcb79c39e81f53595`, confirming that this selector was deployed during the campaign review. That installed pathname now resolves through the root-owned `/usr/local/lib/nostromo` links into the live release at `/opt/nostromo/current`.

The reviewer did receive the campaign objective and the implementation plan, and correctly held this campaign because the objective was missing from that plan. The packet gap did **not** cause SquadOps to generate the generic plan. Whether it affected the breadth of Ripley's assessment in this campaign is unproven; it creates a review-completeness risk when required proposal details appear only in the consolidated document.

## Evidence

- Code: `runtime/campaigns/automation.py`, `Automation.packet`, especially the `selected` set and artifact filtering loop.
- Campaign: `cmp_29048a00fdb3460c0675529a`; plan gate on `cyc_b8fe0deebe3e` / `run_1005936f0695`.
- Omitted artifact: `art_4a02e6d6c9cc`, filename `planning_artifact.md`, type `document`.
- Included plan artifact: `art_3c2dfc51d097`, filename `implementation_plan.yaml`, type `control_implementation_plan`.
- Ripley review job: `job_cdf0650cd346f87268136aada32c45c6`.

## Impact

The bounded reviewer may make a plan-gate decision without seeing the consolidated plan and its readiness/open-item analysis. A required criterion present only in that document may be treated as absent; conversely, conflicting statements between the consolidated plan and implementation plan may go unnoticed.

## Fix criteria

- Include the canonical consolidated planning artifact in `progress_plan_review` packets, selected by stable artifact type/metadata rather than a fragile filename alone.
- Preserve the complete artifact bytes/hash and include its artifact ID in the packet's allowed evidence references.
- Add coverage proving the plan-review packet contains the consolidated planning artifact, while non-plan gates continue to receive only their intended evidence.
- Keep the bounded request-size limit; if complete required evidence does not fit, park with an explicit evidence-size hold instead of silently omitting a required document.
