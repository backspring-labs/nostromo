# Defect draft: Calibration plan does not carry the campaign increment objective

**Provisional owner:** SquadOps campaign calibration/planning. Confirm ownership by tracing the framing prompt and project-PRD selection in SquadOps.
**Status:** Filed as an additional reproduction on [backspring-labs/squad-ops#2619](https://github.com/backspring-labs/squad-ops/issues/2619#issuecomment-6441859437), which already tracks missing calibration inputs/objective-driven framing. Implementation root cause not yet traced in SquadOps.
**Observed:** 2026-10-26, campaign `cmp_29048a00fdb3460c0675529a`.

## Summary

The campaign retained its owner-approved objective for one specific increment (stable ascending raw-string datetime ordering in `GET /runs`), but its calibration framing run produced a generic full-stack MVP plan. The campaign plan gate correctly held the run; no implementation increment began. The campaign later expired and closed with outcome `aborted`.

## Expected behavior

Given an approved campaign objective and acceptance contract, the framing/planning output should either:

1. produce a plan whose implementation task and verification criteria directly cover that objective; or
2. report that the calibration/planning workflow cannot translate the objective and stop before presenting the plan as ready.

For this campaign the plan needed a `GET /runs` raw-string sort task, the A/B/C/D endpoint regression (expected B/A/C/D with stable A-before-C), explicit behavior-preservation criteria, baseline-versus-candidate evidence, and the required evaluator seam table.

## Actual behavior

- The approved campaign objective remained present in the campaign record. Nostromo's launch binding compares the runtime objective and policy with the approved definition and refuses a mismatch (`runtime/campaigns/launch.py`, `bind_campaign`).
- The calibration cycle used the general `fullstack_fastapi_react` configuration and generated a plan for building the group_run MVP. Its plan contains no sorting increment, no A/B/C/D regression, and no baseline-versus-candidate verification.
- The framing artifact's readiness assessment says `GO`, despite the mismatch with the campaign objective.
- Ripley returned `needs_owner`, identifying the mismatch and missing acceptance evidence. The plan gate held, and implementation did not start.
- The cycle record has `prd_ref: null`; the run report identifies the general full-stack profile. This is a clue to investigate, not proof of the cause.

## Evidence

- Campaign: `cmp_29048a00fdb3460c0675529a`.
- Calibration cycle/run: `cyc_b8fe0deebe3e` / `run_1005936f0695`.
- Calibration outcome: framing completed and marked accepted; implementation remained pending and was later cancelled when the campaign ended.
- Artifacts: `art_4a02e6d6c9cc` (`planning_artifact.md`), `art_3c2dfc51d097` (`implementation_plan.yaml`), `art_0fbf8be15c21` (`interface_manifest.yaml`), and `art_968c7fbb0312` (`run_report.md`).
- Ripley review job: `job_cdf0650cd346f87268136aada32c45c6`; Buzz `campaign-job-result` at 2026-10-26 19:36 UTC.
- Final campaign state: `completed`, outcome `aborted`; automation expired at its deadline. No implementation work ran.

## Impact

A campaign can spend calibration and paid-review budget producing a plan for the project's general PRD rather than the owner-approved increment. The readiness score is misleading until an independent review catches the mismatch. In this instance one paid Ripley dispatch was reserved ($0.5632 at the recorded reservation rate), and the requested increment was not attempted.

## Investigation/fix criteria

- Trace how campaign objective/statement, `prd_ref`, accepted baseline, and interface manifest reach the framing/planning task.
- Explain why the generic MVP plan was accepted as a calibration artifact for a one-increment campaign.
- Ensure objective-specific acceptance criteria appear in the generated implementation plan and verification plan, or explicitly halt with a clear incompatibility reason.
- Add a regression scenario with a narrow increment over a project whose baseline PRD is broader; assert the plan addresses the increment and includes its acceptance checks.
- Ensure a generic plan cannot receive `GO` for a campaign whose stated increment is absent.

## Ownership note

The evidence places the first observed divergence in SquadOps-generated framing/planning artifacts, after Nostromo created the campaign with the approved objective intact. The exact SquadOps component and code-level cause remain unconfirmed pending access to that implementation.
