"""InvestigationReport: the structure the agent must hand to `propose_disposition` (design doc section 5).

The Gateway's tool schema (`src/tools/schema.py`) declares the same object loosely (three required keys) so the
model can see the shape; this model is the strict version the agent enforces on itself before the call leaves.
A test in `tests/test_report_and_guard.py` checks that every property here is also declared on the Gateway side.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Disposition = Literal["CLOSE_FP", "ESCALATE", "DRAFT_STOR"]
Verdict = Literal["ruled_out", "supported", "undetermined"]

EVIDENCE_SOURCES = {
    "get_alert",
    "get_order_events",
    "reconstruct_book",
    "compute_discriminators",
    "get_trader_profile",
    "get_trader_alert_history",
    "get_market_events",
    "get_instrument_stats",
    "get_procedures",
    "recall_memory",
    "memory",
}


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^E\d+$", description="E1, E2, ...")
    source: str = Field(description="the tool the fact came from, without the surv___ prefix")
    fact: str = Field(min_length=8, description="one verifiable statement, with the number it rests on")

    @field_validator("source")
    @classmethod
    def _known_source(cls, v: str) -> str:
        v = v.removeprefix("surv___")
        if v not in EVIDENCE_SOURCES:
            raise ValueError(f"source must be one of {sorted(EVIDENCE_SOURCES)}")
        return v


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation: str = Field(min_length=3)
    ruled_out_by: list[str] = Field(default_factory=list, description="evidence ids")
    verdict: Verdict

    @model_validator(mode="before")
    @classmethod
    def _accept_ruled_out(cls, data: Any) -> Any:
        """The model wrote `ruled_out` for `ruled_out_by` in 24 of 167 v3 sessions (132 explanations), sometimes
        alone and sometimes next to an empty `ruled_out_by` (seen on Runtime v13), and each slip cost a full report
        rewrite (+8.6 s, +32k tokens). The slip is folded into the declared name here; the field is always emitted
        as `ruled_out_by`, which is what the Gateway schema declares. Every other unknown key is still refused."""
        if isinstance(data, dict) and "ruled_out" in data:
            data = dict(data)
            legacy = data.pop("ruled_out")
            if not data.get("ruled_out_by"):
                data["ruled_out_by"] = legacy
        return data

    @field_validator("ruled_out_by", mode="before")
    @classmethod
    def _one_id_is_a_list(cls, v: object) -> object:
        if v is None:
            return []
        return [v] if isinstance(v, str) else v

    @model_validator(mode="after")
    def _ruled_out_needs_evidence(self) -> Explanation:
        if self.verdict == "ruled_out" and not self.ruled_out_by:
            raise ValueError(f"explanation {self.explanation!r} is ruled_out but cites no evidence")
        return self


class InvestigationReport(BaseModel):
    """What the agent proposes, and why, in a form a Level-2 reviewer can check line by line."""

    model_config = ConfigDict(extra="forbid")

    alert_id: str
    scenario: str
    summary: str = Field(min_length=40, description="one paragraph an L2 can read in 30 seconds")
    evidence: list[Evidence] = Field(min_length=3)
    indicators_matched: list[str] = Field(default_factory=list)
    indicators_not_matched: list[str] = Field(default_factory=list)
    legitimate_explanations_considered: list[Explanation] = Field(min_length=1)
    proposed_disposition: Disposition
    confidence: float = Field(ge=0.0, le=1.0)
    what_would_change_my_mind: str = Field(min_length=10)
    memory_used: list[str] = Field(default_factory=list)
    window_used: str = Field(
        min_length=5, description="the detector window covered, and whether a longer frame was considered"
    )
    tool_calls: list[str] = Field(
        default_factory=list, description="filled in by the agent from its own trace, not by the model"
    )

    @model_validator(mode="after")
    def _consistent(self) -> InvestigationReport:
        ids = {e.id for e in self.evidence}
        if len(ids) != len(self.evidence):
            raise ValueError("evidence ids must be unique")
        for ex in self.legitimate_explanations_considered:
            unknown = [r for r in ex.ruled_out_by if r not in ids]
            if unknown:
                raise ValueError(f"explanation {ex.explanation!r} cites unknown evidence ids {unknown}")
        if self.proposed_disposition == "CLOSE_FP":
            supported = [ex.explanation for ex in self.legitimate_explanations_considered if ex.verdict == "supported"]
            if not supported:
                raise ValueError(
                    "CLOSE_FP needs at least one legitimate explanation with verdict 'supported' "
                    "(closure standard: a legitimate explanation that accounts for the pattern)"
                )
        if self.proposed_disposition in ("ESCALATE", "DRAFT_STOR"):
            if any(ex.verdict == "supported" for ex in self.legitimate_explanations_considered):
                raise ValueError(
                    f"{self.proposed_disposition} with a legitimate explanation marked 'supported' is inconsistent; "
                    "mark it undetermined and say why it does not account for the pattern, or propose CLOSE_FP"
                )
        return self

    def for_gateway(self) -> dict:
        """The `report` argument of `propose_disposition` (the Gateway schema does not carry the two fields the
        tool takes separately)."""
        d = self.model_dump()
        d.pop("proposed_disposition")
        d.pop("confidence")
        return d
