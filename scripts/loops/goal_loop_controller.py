#!/usr/bin/env python3
"""Durable state helpers for Athanor lfg-goal loops."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CYCLE_STATES = {
    "aborted",
    "bootstrapping",
    "cycle_n_complete",
    "cycle_n_in_progress",
    "goal_complete",
    "scope_change_pending",
}
CYCLE_PHASES = {
    "lfg_done_seen",
    "not_started",
    "receipt_validated",
    "tier1_checked",
    "tier2_checked",
    "tier3_pending",
    "tier3_ratified",
}
TERMINAL_CYCLE_STATES = {"aborted", "goal_complete"}
VALIDATOR_STATUSES = {
    "all_valid",
    "completed_with_residuals",
    "invalid_steps_present",
    "not_yet_run",
}
EVAL_STATUSES = {"fail", "missing", "not_applicable", "pass"}
TIER3_USER_RESPONSES = {"abort", "continue", "yes"}
DECISION_STATUSES = {"concern", "escalated", "failure", "pass", "skipped"}
ASSESSMENT_KINDS = {"baseline", "delta", "final"}
ROUTES_BY_CYCLE_PHASE = {
    "not_started": "resume_cycle_from_start",
    "lfg_done_seen": "validate_receipt",
    "receipt_validated": "run_tier1_check",
    "tier1_checked": "run_tier2_judges",
    "tier2_checked": "prompt_tier3_user",
    "tier3_pending": "prompt_tier3_user",
    "tier3_ratified": "start_next_cycle",
}
EVIDENCE_REQUIRED_ACTIONS = {
    "validate_receipt",
    "run_tier1_check",
    "run_tier2_judges",
    "prompt_tier3_user",
    "start_next_cycle",
}
DELIVERY_LOOP_ACTIONS = {
    "bootstrap_goal",
    "resume_cycle_from_start",
    "run_lfg_cycle",
    "start_next_cycle",
}

REQUIRED_FIELDS = {
    "schema_version",
    "goal_id",
    "cycle_state",
    "cycle_phase",
    "current_cycle",
    "max_iterations",
    "no_progress_threshold",
    "last_receipt_path",
    "last_validator_status",
    "tier2_last_verdict",
    "aborted_reason",
    "no_progress_count",
    "stop_reason",
    "updated_at",
}
LEGACY_OPTIONAL_FIELDS = {"schema_version", "cycle_phase"}
GOAL_ID_RE = re.compile(r"^[0-9a-f]{8}$")
_UNCHANGED = object()


class LoopStateError(ValueError):
    """Raised when durable loop state is malformed or contradictory."""


def _require_object(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise LoopStateError("state root must be an object")
    return data


def _require_int(value: Any, field_name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LoopStateError(f"{field_name} must be an integer")
    if minimum is not None and value < minimum:
        raise LoopStateError(f"{field_name} must be >= {minimum}")
    return value


def _require_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise LoopStateError(f"{field_name} must be a non-empty string or null")
    return value


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise LoopStateError(f"{field_name} must be a non-empty string")
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise LoopStateError(f"{field_name} must be a boolean")
    return value


def _require_number(value: Any, field_name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LoopStateError(f"{field_name} must be a number")
    return value


def _require_string_list(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LoopStateError(f"{field_name} must be a list of strings")
    return tuple(value)


@dataclass(frozen=True)
class LoopState:
    """Validated durable lfg-goal loop state."""

    schema_version: int
    goal_id: str
    cycle_state: str
    cycle_phase: str | None
    current_cycle: int
    max_iterations: int
    no_progress_threshold: int
    last_receipt_path: str | None
    last_validator_status: str
    tier2_last_verdict: dict[str, Any] | None
    aborted_reason: str | None
    no_progress_count: int
    stop_reason: str | None
    updated_at: str
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, raw_data: Any) -> "LoopState":
        data = dict(_require_object(raw_data))
        warnings: list[str] = []

        legacy_missing_schema = "schema_version" not in data
        if legacy_missing_schema:
            warnings.append("legacy_missing_schema_version")
            data["schema_version"] = 1
        elif data.get("schema_version") != 1:
            raise LoopStateError("schema_version must be 1")

        if "cycle_phase" not in data and legacy_missing_schema:
            warnings.append("legacy_missing_phase")
            data["cycle_phase"] = None

        missing = sorted(REQUIRED_FIELDS - set(data))
        if missing:
            raise LoopStateError(f"missing required fields: {missing}")

        goal_id = _require_string(data["goal_id"], "goal_id")
        if not GOAL_ID_RE.match(goal_id):
            raise LoopStateError("goal_id must be 8 lowercase hex characters")

        cycle_state = _require_string(data["cycle_state"], "cycle_state")
        if cycle_state not in CYCLE_STATES:
            raise LoopStateError(f"unsupported cycle_state: {cycle_state}")

        cycle_phase = data["cycle_phase"]
        if cycle_phase is not None:
            cycle_phase = _require_string(cycle_phase, "cycle_phase")
            if cycle_phase not in CYCLE_PHASES:
                raise LoopStateError(f"unsupported cycle_phase: {cycle_phase}")

        if cycle_state == "cycle_n_in_progress" and cycle_phase is None and not warnings:
            raise LoopStateError("cycle_phase is required for cycle_n_in_progress")
        if cycle_state != "cycle_n_in_progress" and cycle_phase is not None:
            raise LoopStateError("cycle_phase must be null outside cycle_n_in_progress")

        max_iterations = _require_int(data["max_iterations"], "max_iterations", minimum=1)
        current_cycle = _require_int(data["current_cycle"], "current_cycle", minimum=0)
        if current_cycle > max_iterations:
            raise LoopStateError("current_cycle must be <= max_iterations")

        no_progress_threshold = _require_int(
            data["no_progress_threshold"], "no_progress_threshold", minimum=1
        )
        no_progress_count = _require_int(
            data["no_progress_count"], "no_progress_count", minimum=0
        )
        if no_progress_count > no_progress_threshold:
            raise LoopStateError("no_progress_count must be <= no_progress_threshold")

        last_validator_status = _require_string(
            data["last_validator_status"], "last_validator_status"
        )
        if last_validator_status not in VALIDATOR_STATUSES:
            raise LoopStateError(
                f"unsupported last_validator_status: {last_validator_status}"
            )

        tier2_last_verdict = data["tier2_last_verdict"]
        if tier2_last_verdict is not None and not isinstance(tier2_last_verdict, dict):
            raise LoopStateError("tier2_last_verdict must be an object or null")

        return cls(
            schema_version=1,
            goal_id=goal_id,
            cycle_state=cycle_state,
            cycle_phase=cycle_phase,
            current_cycle=current_cycle,
            max_iterations=max_iterations,
            no_progress_threshold=no_progress_threshold,
            last_receipt_path=_require_optional_string(
                data["last_receipt_path"], "last_receipt_path"
            ),
            last_validator_status=last_validator_status,
            tier2_last_verdict=tier2_last_verdict,
            aborted_reason=_require_optional_string(
                data["aborted_reason"], "aborted_reason"
            ),
            no_progress_count=no_progress_count,
            stop_reason=_require_optional_string(data["stop_reason"], "stop_reason"),
            updated_at=_require_string(data["updated_at"], "updated_at"),
            warnings=tuple(warnings),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "goal_id": self.goal_id,
            "cycle_state": self.cycle_state,
            "cycle_phase": self.cycle_phase,
            "current_cycle": self.current_cycle,
            "max_iterations": self.max_iterations,
            "no_progress_threshold": self.no_progress_threshold,
            "last_receipt_path": self.last_receipt_path,
            "last_validator_status": self.last_validator_status,
            "tier2_last_verdict": self.tier2_last_verdict,
            "aborted_reason": self.aborted_reason,
            "no_progress_count": self.no_progress_count,
            "stop_reason": self.stop_reason,
            "updated_at": self.updated_at,
        }


def is_terminal_state(state: LoopState) -> bool:
    return state.cycle_state in TERMINAL_CYCLE_STATES


@dataclass(frozen=True)
class AssessmentDimension:
    """One assessed dimension used for target/floor/regression decisions."""

    score: int | float
    target: int | float | None
    floor: int | float | None
    target_met: bool
    regressed: bool

    @classmethod
    def from_dict(cls, raw_data: Any, field_name: str) -> "AssessmentDimension":
        data = _require_object(raw_data)
        target = data.get("target")
        floor = data.get("floor")
        return cls(
            score=_require_number(data.get("score"), f"{field_name}.score"),
            target=(
                None
                if target is None
                else _require_number(target, f"{field_name}.target")
            ),
            floor=(
                None if floor is None else _require_number(floor, f"{field_name}.floor")
            ),
            target_met=_require_bool(
                data.get("target_met"), f"{field_name}.target_met"
            ),
            regressed=_require_bool(data.get("regressed"), f"{field_name}.regressed"),
        )

    def needs_work(self) -> bool:
        below_floor = self.floor is not None and self.score < self.floor
        return not self.target_met or self.regressed or below_floor

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "target": self.target,
            "floor": self.floor,
            "target_met": self.target_met,
            "regressed": self.regressed,
        }


@dataclass(frozen=True)
class AssessmentEvidence:
    """Structured assessment evidence consumed by the adaptive goal controller."""

    kind: str
    report_path: str
    overall_score: int | float
    min_dimension_score: int | float
    target_met: bool
    priority_plan_items: tuple[str, ...]
    dimensions: dict[str, AssessmentDimension]

    @classmethod
    def from_dict(cls, raw_data: Any) -> "AssessmentEvidence":
        data = _require_object(raw_data)
        kind = _require_string(data.get("kind"), "assessment.kind")
        if kind not in ASSESSMENT_KINDS:
            raise LoopStateError(f"unsupported assessment.kind: {kind}")

        dimensions_raw = data.get("dimensions")
        if not isinstance(dimensions_raw, dict) or not dimensions_raw:
            raise LoopStateError("assessment.dimensions must be a non-empty object")
        dimensions: dict[str, AssessmentDimension] = {}
        for name, dimension_data in dimensions_raw.items():
            if not isinstance(name, str) or not name:
                raise LoopStateError("assessment dimension names must be non-empty strings")
            dimensions[name] = AssessmentDimension.from_dict(
                dimension_data,
                f"assessment.dimensions.{name}",
            )

        return cls(
            kind=kind,
            report_path=_require_string(
                data.get("report_path"), "assessment.report_path"
            ),
            overall_score=_require_number(
                data.get("overall_score"), "assessment.overall_score"
            ),
            min_dimension_score=_require_number(
                data.get("min_dimension_score"), "assessment.min_dimension_score"
            ),
            target_met=_require_bool(data.get("target_met"), "assessment.target_met"),
            priority_plan_items=_require_string_list(
                data.get("priority_plan_items", []),
                "assessment.priority_plan_items",
            ),
            dimensions=dimensions,
        )

    def target_dimensions(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, _dimension in sorted(
                (
                    (name, dimension)
                    for name, dimension in self.dimensions.items()
                    if dimension.needs_work()
                ),
                key=lambda item: (item[1].score, item[0]),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "report_path": self.report_path,
            "overall_score": self.overall_score,
            "min_dimension_score": self.min_dimension_score,
            "target_met": self.target_met,
            "priority_plan_items": list(self.priority_plan_items),
            "dimensions": {
                name: dimension.to_dict()
                for name, dimension in self.dimensions.items()
            },
        }


def _score_target_from_dict(raw_data: Any) -> dict[str, Any]:
    data = _require_object(raw_data)
    target = {
        "overall_score": _require_number(
            data.get("overall_score"), "score_target.overall_score"
        ),
        "min_dimension_score": _require_number(
            data.get("min_dimension_score"), "score_target.min_dimension_score"
        ),
    }
    # NOTE: `completion_gates_required` was removed (v0.24.x correctness batch).
    # It was parsed/validated/echoed but never read — the tier1/tier2 completion
    # gate fires UNCONDITIONALLY (the documented always-apply 3-tier invariant).
    # Wiring it would have broken that invariant, so the inert flag was deleted
    # rather than honored. Any leftover key in input is simply ignored here.
    return target


@dataclass(frozen=True)
class EvidenceSummary:
    """Narrow evidence input consumed by the durable loop controller."""

    eval_status: str
    validator_status: str | None = None
    tier1_passed: bool | None = None
    tier2_goal_met: bool | None = None
    tier3_user_response: str | None = None
    progress_made: bool | None = None
    references: tuple[str, ...] = field(default_factory=tuple)
    score_target: dict[str, Any] | None = None
    assessment: AssessmentEvidence | None = None

    @classmethod
    def from_dict(cls, raw_data: Any) -> "EvidenceSummary":
        data = _require_object(raw_data)
        eval_status = data.get("eval_status", "not_applicable")
        if not isinstance(eval_status, str) or eval_status not in EVAL_STATUSES:
            raise LoopStateError(f"unsupported eval_status: {eval_status}")

        validator_status = data.get("validator_status")
        if validator_status is not None:
            validator_status = _require_string(validator_status, "validator_status")
            if validator_status not in VALIDATOR_STATUSES:
                raise LoopStateError(f"unsupported validator_status: {validator_status}")

        tier3_user_response = data.get("tier3_user_response")
        if tier3_user_response is not None:
            tier3_user_response = _require_string(
                tier3_user_response, "tier3_user_response"
            )
            if tier3_user_response not in TIER3_USER_RESPONSES:
                raise LoopStateError(
                    f"unsupported tier3_user_response: {tier3_user_response}"
                )

        references = data.get("references", [])
        if not isinstance(references, list) or not all(
            isinstance(item, str) for item in references
        ):
            raise LoopStateError("references must be a list of strings")

        progress_made = data.get("progress_made")
        if progress_made is not None and not isinstance(progress_made, bool):
            raise LoopStateError("progress_made must be a boolean or null")

        tier1_passed = data.get("tier1_passed")
        if tier1_passed is not None and not isinstance(tier1_passed, bool):
            raise LoopStateError("tier1_passed must be a boolean or null")

        tier2_goal_met = data.get("tier2_goal_met")
        if tier2_goal_met is not None and not isinstance(tier2_goal_met, bool):
            raise LoopStateError("tier2_goal_met must be a boolean or null")

        score_target = data.get("score_target")
        if score_target is not None:
            score_target = _score_target_from_dict(score_target)

        assessment = data.get("assessment")
        if assessment is not None:
            assessment = AssessmentEvidence.from_dict(assessment)

        return cls(
            eval_status=eval_status,
            validator_status=validator_status,
            tier1_passed=tier1_passed,
            tier2_goal_met=tier2_goal_met,
            tier3_user_response=tier3_user_response,
            progress_made=progress_made,
            references=tuple(references),
            score_target=score_target,
            assessment=assessment,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "eval_status": self.eval_status,
            "validator_status": self.validator_status,
            "tier1_passed": self.tier1_passed,
            "tier2_goal_met": self.tier2_goal_met,
            "tier3_user_response": self.tier3_user_response,
            "progress_made": self.progress_made,
            "references": list(self.references),
            "score_target": self.score_target,
            "assessment": (
                None if self.assessment is None else self.assessment.to_dict()
            ),
        }


@dataclass(frozen=True)
class LoopDecision:
    """A normalized durable-loop decision."""

    schema_version: int
    goal_id: str
    action: str
    status: str
    reason: str
    next_cycle_state: str
    next_cycle_phase: str | None
    references: tuple[str, ...] = field(default_factory=tuple)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "goal_id": self.goal_id,
            "action": self.action,
            "status": self.status,
            "reason": self.reason,
            "next_cycle_state": self.next_cycle_state,
            "next_cycle_phase": self.next_cycle_phase,
            "references": list(self.references),
            "evidence": self.evidence,
        }


def _decision(
    state: LoopState,
    evidence: EvidenceSummary,
    *,
    action: str,
    status: str,
    reason: str,
    next_cycle_state: Any = _UNCHANGED,
    next_cycle_phase: Any = _UNCHANGED,
    extra_evidence: dict[str, Any] | None = None,
) -> LoopDecision:
    if status not in DECISION_STATUSES:
        raise LoopStateError(f"unsupported decision status: {status}")
    decision_evidence = {
        "cycle_state": state.cycle_state,
        "cycle_phase": state.cycle_phase,
        "current_cycle": state.current_cycle,
        "max_iterations": state.max_iterations,
        "no_progress_count": state.no_progress_count,
        "no_progress_threshold": state.no_progress_threshold,
        "progress_made": evidence.progress_made,
        "eval_status": evidence.eval_status,
    }
    if state.warnings:
        decision_evidence["state_warnings"] = list(state.warnings)
    if evidence.score_target is not None:
        decision_evidence["score_target"] = evidence.score_target
    if evidence.assessment is not None:
        decision_evidence["assessment"] = evidence.assessment.to_dict()
    if extra_evidence:
        decision_evidence.update(extra_evidence)
    return LoopDecision(
        schema_version=1,
        goal_id=state.goal_id,
        action=action,
        status=status,
        reason=reason,
        next_cycle_state=state.cycle_state
        if next_cycle_state is _UNCHANGED
        else next_cycle_state,
        next_cycle_phase=state.cycle_phase
        if next_cycle_phase is _UNCHANGED
        else next_cycle_phase,
        references=evidence.references,
        evidence=decision_evidence,
    )


def _route_for_state(state: LoopState) -> tuple[str, str, str]:
    if (
        state.cycle_state == "cycle_n_in_progress"
        and "legacy_missing_phase" in state.warnings
    ):
        return (
            "resume_cycle_from_start",
            "concern",
            (
                "state.json missing cycle_phase field; using coarse-grained resume "
                "from cycle start"
            ),
        )
    if state.cycle_state == "bootstrapping":
        return "bootstrap_goal", "pass", "resume goal bootstrap"
    if state.cycle_state == "cycle_n_complete":
        return "start_next_cycle", "pass", "cycle complete; start next cycle"
    if state.cycle_state == "scope_change_pending":
        return (
            "resume_scope_change_review",
            "pass",
            "resume scope-change review",
        )
    if state.cycle_state == "cycle_n_in_progress" and state.cycle_phase in ROUTES_BY_CYCLE_PHASE:
        action = ROUTES_BY_CYCLE_PHASE[state.cycle_phase]
        return action, "pass", f"resume from cycle_phase {state.cycle_phase}"
    raise LoopStateError("could not route loop state")


def _adaptive_target_evidence(assessment: AssessmentEvidence) -> dict[str, Any]:
    return {
        "target_dimensions": list(assessment.target_dimensions()),
        "priority_plan_items": list(assessment.priority_plan_items),
    }


def _assessment_contradictions(
    assessment: AssessmentEvidence,
    score_target: dict[str, Any],
) -> tuple[str, ...]:
    target_failures: list[str] = []
    computed_min_dimension_score = min(
        dimension.score for dimension in assessment.dimensions.values()
    )
    min_dimension_score_mismatch: str | None = None
    if assessment.overall_score < score_target["overall_score"]:
        target_failures.append("overall_score_below_target")
    if assessment.min_dimension_score != computed_min_dimension_score:
        claimed = f"{assessment.min_dimension_score:g}"
        computed = f"{computed_min_dimension_score:g}"
        min_dimension_score_mismatch = (
            f"min_dimension_score_mismatch:claimed={claimed},computed={computed}"
        )
        target_failures.append(min_dimension_score_mismatch)
    if computed_min_dimension_score < score_target["min_dimension_score"]:
        target_failures.append("min_dimension_score_below_target")
    for name, dimension in assessment.dimensions.items():
        if not dimension.target_met:
            target_failures.append(f"dimension_target_not_met:{name}")
        if dimension.floor is not None and dimension.score < dimension.floor:
            target_failures.append(f"dimension_below_floor:{name}")
        if dimension.regressed:
            target_failures.append(f"dimension_regressed:{name}")

    if min_dimension_score_mismatch is not None and not assessment.target_met:
        return (min_dimension_score_mismatch,)
    if assessment.target_met and target_failures:
        return tuple(target_failures)
    if not assessment.target_met and not target_failures:
        return ("target_met_false_but_scores_satisfy_target",)
    return ()


def _max_iterations_decision(state: LoopState, evidence: EvidenceSummary) -> LoopDecision:
    return _decision(
        state,
        evidence,
        action="stop_max_iterations",
        status="failure",
        reason=f"max iterations reached: {state.current_cycle}/{state.max_iterations}",
        next_cycle_state="aborted",
        next_cycle_phase=None,
        extra_evidence={"stop_reason": "stop_max_iterations"},
    )


def _counts_as_no_progress(evidence: EvidenceSummary) -> bool:
    """A cycle is no-progress unless evidence explicitly reports progress_made=True.

    ``progress_made=None`` (evidence silent on progress) counts as no-progress: a cycle
    with no positive progress signal is, honestly, no progress.
    """
    return evidence.progress_made is not True


def _no_progress_stop_if_tripped(
    state: LoopState,
    evidence: EvidenceSummary,
) -> LoopDecision | None:
    """Shared no-progress accounting.

    The single accounting site for the ``progress_made is False`` path and for emitted
    blocks (eval-fail / invalid-receipt). Returns a terminal ``stop_no_progress`` decision
    when the incremented count reaches ``no_progress_threshold``; otherwise ``None`` (the
    caller emits its own action and ``apply_decision`` advances ``no_progress_count``).
    """
    if not _counts_as_no_progress(evidence):
        return None
    next_no_progress_count = state.no_progress_count + 1
    if next_no_progress_count < state.no_progress_threshold:
        return None
    return _decision(
        state,
        evidence,
        action="stop_no_progress",
        status="failure",
        reason=(
            "no progress threshold reached: "
            f"{next_no_progress_count}/{state.no_progress_threshold}"
        ),
        next_cycle_state="aborted",
        next_cycle_phase=None,
        extra_evidence={
            "stop_reason": "stop_no_progress",
            "next_no_progress_count": next_no_progress_count,
        },
    )


def _bounded_block_decision(
    state: LoopState,
    evidence: EvidenceSummary,
    *,
    action: str,
    status: str,
    reason: str,
    extra_evidence: dict[str, Any],
) -> LoopDecision:
    """Emit a block action while folding it into no-progress / max-iter bounding.

    A block does NOT advance ``current_cycle`` / ``cycle_state`` / ``cycle_phase``; the
    only state it moves is ``no_progress_count``. The terminators are checked first:
      * the no-progress budget (primary): if this block would reach the threshold, return
        ``stop_no_progress`` (terminal ``aborted``) instead of the block;
      * the max-iter cap (secondary safety net): a block on the final allowed cycle
        returns ``stop_max_iterations``.
    A non-tripping block carries the incremented ``no_progress_count`` so ``apply_decision``
    persists it for the block action.
    """
    if state.current_cycle >= state.max_iterations:
        return _max_iterations_decision(state, evidence)

    no_progress_stop = _no_progress_stop_if_tripped(state, evidence)
    if no_progress_stop is not None:
        return no_progress_stop

    block_extra = dict(extra_evidence)
    if _counts_as_no_progress(evidence):
        block_extra["no_progress_count"] = state.no_progress_count + 1
    return _decision(
        state,
        evidence,
        action=action,
        status=status,
        reason=reason,
        extra_evidence=block_extra,
    )


def _failed_eval_decision(state: LoopState, evidence: EvidenceSummary) -> LoopDecision:
    blocked_action = "run_lfg_cycle"
    if evidence.score_target is None:
        try:
            blocked_action = _route_for_state(state)[0]
        except LoopStateError:
            blocked_action = "unknown"
    return _bounded_block_decision(
        state,
        evidence,
        action="block_failed_eval",
        status="failure",
        reason="eval evidence failed; refusing to advance loop",
        extra_evidence={"blocked_action": blocked_action},
    )


def _invalid_receipt_decision(
    state: LoopState,
    evidence: EvidenceSummary,
) -> LoopDecision | None:
    if evidence.validator_status != "invalid_steps_present":
        return None

    try:
        blocked_action = _route_for_state(state)[0]
    except LoopStateError:
        blocked_action = "unknown"
    if evidence.score_target is not None and state.cycle_state == "cycle_n_complete":
        blocked_action = "run_delta_assess"

    return _bounded_block_decision(
        state,
        evidence,
        action="run_scope_drift",
        status="escalated",
        reason="invalid receipt evidence blocks loop advancement",
        extra_evidence={
            "blocked_action": blocked_action,
            "validator_status": evidence.validator_status,
            "state_validator_status": state.last_validator_status,
        },
    )


def _decide_adaptive_goal(
    state: LoopState,
    evidence: EvidenceSummary,
) -> LoopDecision | None:
    if evidence.score_target is None:
        return None

    if state.cycle_state == "bootstrapping":
        if evidence.assessment is None:
            return _decision(
                state,
                evidence,
                action="run_baseline_assess",
                status="pass",
                reason="score target requires baseline assessment before delivery loop",
            )
        if evidence.assessment.kind != "baseline":
            return _decision(
                state,
                evidence,
                action="require_assessment_evidence",
                status="escalated",
                reason="bootstrapping requires baseline assessment evidence",
                extra_evidence={"expected_assessment_kind": "baseline"},
            )
        return _decision(
            state,
            evidence,
            action="run_lfg_cycle",
            status="pass",
            reason="baseline assessment captured; start first delivery loop",
            next_cycle_state="cycle_n_in_progress",
            next_cycle_phase="not_started",
            extra_evidence=_adaptive_target_evidence(evidence.assessment),
        )

    if state.cycle_state != "cycle_n_complete":
        return None

    validator_status = evidence.validator_status or state.last_validator_status

    if validator_status == "invalid_steps_present":
        return _bounded_block_decision(
            state,
            evidence,
            action="run_scope_drift",
            status="escalated",
            reason="invalid receipt blocks adaptive assessment routing",
            extra_evidence={
                "blocked_action": "run_delta_assess",
                "validator_status": validator_status,
                "state_validator_status": state.last_validator_status,
            },
        )

    if validator_status not in {"all_valid", "completed_with_residuals"}:
        return _decision(
            state,
            evidence,
            action="require_receipt_validation",
            status="escalated",
            reason="cycle receipt must be valid before assessment routing",
            extra_evidence={
                "blocked_action": "run_delta_assess",
                "validator_status": validator_status,
                "state_validator_status": state.last_validator_status,
            },
        )

    if evidence.assessment is None:
        return _decision(
            state,
            evidence,
            action="run_delta_assess",
            status="pass",
            reason="valid cycle receipt requires delta assessment before next loop",
            extra_evidence={"blocked_action": "run_lfg_cycle"},
        )

    if evidence.assessment.kind not in {"delta", "final"}:
        return _decision(
            state,
            evidence,
            action="require_assessment_evidence",
            status="escalated",
            reason="completed cycle requires delta or final assessment evidence",
            extra_evidence={"expected_assessment_kind": "delta|final"},
        )

    assessment_contradictions = _assessment_contradictions(
        evidence.assessment,
        evidence.score_target,
    )
    if assessment_contradictions:
        return _decision(
            state,
            evidence,
            action="require_assessment_evidence",
            status="escalated",
            reason="assessment target contradiction blocks completion prompt",
            extra_evidence={
                "assessment_contradictions": list(assessment_contradictions),
            },
        )

    if (
        evidence.assessment.kind == "final"
        and evidence.assessment.target_met
        and evidence.tier1_passed is True
        and evidence.tier2_goal_met is True
    ):
        return _decision(
            state,
            evidence,
            action="prompt_tier3_user",
            status="pass",
            reason="final assessment met score target and completion gates",
            next_cycle_state="cycle_n_in_progress",
            next_cycle_phase="tier3_pending",
        )

    if state.current_cycle >= state.max_iterations:
        return _max_iterations_decision(state, evidence)

    return _decision(
        state,
        evidence,
        action="run_lfg_cycle",
        status="pass",
        reason="assessment target not met; run next delivery/fix loop",
        next_cycle_state="cycle_n_in_progress",
        next_cycle_phase="not_started",
        extra_evidence=_adaptive_target_evidence(evidence.assessment),
    )


def decide_next_action(state: LoopState, evidence: EvidenceSummary) -> LoopDecision:
    """Return the next durable-loop decision without writing state."""
    if is_terminal_state(state):
        return _decision(
            state,
            evidence,
            action="refuse_terminal_state",
            status="skipped",
            reason=f"terminal state refuses re-entry: {state.cycle_state}",
        )

    if evidence.eval_status == "fail":
        return _failed_eval_decision(state, evidence)

    invalid_receipt_decision = _invalid_receipt_decision(state, evidence)
    if invalid_receipt_decision is not None:
        return invalid_receipt_decision

    if evidence.progress_made is False:
        no_progress_stop = _no_progress_stop_if_tripped(state, evidence)
        if no_progress_stop is not None:
            return no_progress_stop

    adaptive_decision = _decide_adaptive_goal(state, evidence)
    if adaptive_decision is not None:
        return adaptive_decision

    action, status, reason = _route_for_state(state)
    if state.current_cycle >= state.max_iterations and action in DELIVERY_LOOP_ACTIONS:
        return _max_iterations_decision(state, evidence)
    if evidence.eval_status == "missing" and action in EVIDENCE_REQUIRED_ACTIONS:
        return _decision(
            state,
            evidence,
            action="require_eval_evidence",
            status="escalated",
            reason=f"eval evidence missing for {action}",
            extra_evidence={"blocked_action": action},
        )
    return _decision(state, evidence, action=action, status=status, reason=reason)


BLOCK_NO_OP_ACTIONS = {
    "refuse_terminal_state",
    "block_failed_eval",
    "require_eval_evidence",
    "require_assessment_evidence",
    "require_receipt_validation",
    "run_scope_drift",
}


def apply_decision(state: LoopState, decision: LoopDecision) -> LoopState:
    """Return state after applying a controller decision."""
    if decision.action in BLOCK_NO_OP_ACTIONS:
        # A block "stays put and surfaces the failure": it must NOT advance
        # current_cycle / cycle_state / cycle_phase. The only state it may move is
        # no_progress_count, when the decision carries the folded-in increment.
        block_no_progress_count = decision.evidence.get("no_progress_count")
        if (
            isinstance(block_no_progress_count, int)
            and not isinstance(block_no_progress_count, bool)
            and block_no_progress_count != state.no_progress_count
        ):
            data = state.to_dict()
            data["no_progress_count"] = min(
                state.no_progress_threshold,
                block_no_progress_count,
            )
            return LoopState.from_dict(data)
        return state

    data = state.to_dict()
    if decision.action in {"stop_max_iterations", "stop_no_progress"}:
        data["cycle_state"] = "aborted"
        data["cycle_phase"] = None
        data["aborted_reason"] = decision.reason
        data["stop_reason"] = decision.action
        if decision.action == "stop_no_progress":
            data["no_progress_count"] = min(
                state.no_progress_threshold,
                state.no_progress_count + 1,
            )
        return LoopState.from_dict(data)

    if decision.action in {"start_next_cycle", "run_lfg_cycle"}:
        data["cycle_state"] = "cycle_n_in_progress"
        data["cycle_phase"] = "not_started"
        data["current_cycle"] = state.current_cycle + 1
        data["last_validator_status"] = "not_yet_run"
        data["tier2_last_verdict"] = None

    if (
        decision.action == "prompt_tier3_user"
        and decision.next_cycle_state == "cycle_n_in_progress"
        and decision.next_cycle_phase == "tier3_pending"
    ):
        data["cycle_state"] = "cycle_n_in_progress"
        data["cycle_phase"] = "tier3_pending"

    if decision.evidence.get("progress_made") is True:
        data["no_progress_count"] = 0
    elif decision.evidence.get("progress_made") is False:
        data["no_progress_count"] = min(
            state.no_progress_threshold,
            state.no_progress_count + 1,
        )
    return LoopState.from_dict(data)


def load_loop_state(path: Path | str) -> LoopState:
    state_path = Path(path)
    try:
        parsed = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoopStateError(f"malformed state JSON: {exc.msg}") from exc
    except OSError as exc:
        raise LoopStateError(f"could not read state file: {state_path}") from exc
    return LoopState.from_dict(parsed)


def write_loop_state_atomic(path: Path | str, state: LoopState) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_name(f"{state_path.name}.tmp")
    temp_path.write_text(
        json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(state_path)
