"""Deterministic safe terminal responses for Stage 10."""

from __future__ import annotations

from backend.app.agent.answer_models import FinalResponse
from backend.app.agent.state import AgentState


def build_terminal_response(state: AgentState) -> FinalResponse:
    """Build the user-safe terminal response from the Evidence Judge reason."""

    if state["route"] != "insufficient_evidence":
        raise ValueError("Terminal response requires the insufficient_evidence route.")
    if state["insufficient_reason"] == "missing_information":
        return FinalResponse(
            status="needs_more_information",
            answer="当前问题缺少作出可靠护理判断所需的信息。请补充产品、材质、洗标或型号等与问题相关的信息。",
            sources=[],
        )
    if state["insufficient_reason"] == "retrieval_problem":
        return FinalResponse(
            status="insufficient_evidence",
            answer="当前官方知识库中的证据不足，无法可靠回答这个问题。",
            sources=[],
        )
    raise ValueError("Terminal response requires a valid insufficient_reason.")
