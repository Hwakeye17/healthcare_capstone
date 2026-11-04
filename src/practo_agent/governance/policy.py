"""Application-layer governance: least-autonomy tool permissions and risk.

The appointment lookup tool (``check_appointment_status``) reads synthetic
healthcare appointment records, so only the Lookup Agent may use it. The
policy is enforced in code at two points rather than by prompt wording alone:

1. Wiring time: agent and crew construction rejects any agent or task that
   is assigned a tool its role is not permitted to use.
2. Call time: a CrewAI ``before_tool_call`` hook blocks a tool call from any
   agent whose role is not permitted for that tool, so a mis-wired agent
   assembled outside the project factories still cannot execute it.

Both checks are default-deny: a tool or role absent from the policy is
refused.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

from crewai.hooks import (
    get_before_tool_call_hooks,
    register_before_tool_call_hook,
)

from practo_agent.observability import log_event


RETRIEVAL_AGENT_ROLE = "Practo Knowledge Retrieval Specialist"
LOOKUP_AGENT_ROLE = "Practo Appointment Lookup Specialist"
COMPOSER_AGENT_ROLE = "Practo Support Response Composer"

KNOWLEDGE_BASE_TOOL = "search_practo_knowledge_base"
APPOINTMENT_LOOKUP_TOOL = "check_appointment_status"

# Tool name -> agent roles permitted to receive and call the tool.
TOOL_PERMISSIONS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        KNOWLEDGE_BASE_TOOL: frozenset({RETRIEVAL_AGENT_ROLE}),
        APPOINTMENT_LOOKUP_TOOL: frozenset({LOOKUP_AGENT_ROLE}),
    }
)


class ToolPermissionError(PermissionError):
    """Raised when a tool is wired to an agent that may not use it."""


def is_tool_permitted(agent_role: str | None, tool_name: str | None) -> bool:
    """Return whether the role may use the tool; unknown values are denied."""

    if not agent_role or not tool_name:
        return False
    return agent_role in TOOL_PERMISSIONS.get(tool_name, frozenset())


def authorize_agent_tools(agent_role: str, tools: Iterable[Any]) -> None:
    """Reject the assignment if any tool is not permitted for the role."""

    denied = sorted(
        {
            str(getattr(tool, "name", tool))
            for tool in tools
            if not is_tool_permitted(agent_role, getattr(tool, "name", None))
        }
    )
    if denied:
        raise ToolPermissionError(
            f"Governance policy denies tool(s) {denied} for agent role "
            f"{agent_role!r}."
        )


def enforce_crew_tool_permissions(crew: Any) -> None:
    """Validate every agent's tools and every task-level tool override."""

    for agent in crew.agents:
        authorize_agent_tools(agent.role, agent.tools or [])

    for task in crew.tasks:
        task_tools = getattr(task, "tools", None) or []
        if not task_tools:
            continue
        agent = getattr(task, "agent", None)
        authorize_agent_tools(getattr(agent, "role", ""), task_tools)


_LOGGABLE_ROLES = frozenset(
    {RETRIEVAL_AGENT_ROLE, LOOKUP_AGENT_ROLE, COMPOSER_AGENT_ROLE}
)


def tool_call_guard(context: Any) -> bool | None:
    """CrewAI ``before_tool_call`` hook: ``False`` blocks the call."""

    agent_role = getattr(getattr(context, "agent", None), "role", None)
    tool_name = getattr(context, "tool_name", None)

    if is_tool_permitted(agent_role, tool_name):
        return None

    fields: dict[str, object] = {
        "agent_role": (
            agent_role if agent_role in _LOGGABLE_ROLES else "unknown"
        ),
    }
    if tool_name in TOOL_PERMISSIONS:
        fields["tool_name"] = tool_name
    log_event("tool_call_blocked", **fields)
    return False


def install_tool_call_guard() -> None:
    """Register the call-time guard once for this process."""

    if tool_call_guard not in get_before_tool_call_hooks():
        register_before_tool_call_hook(tool_call_guard)


class RiskLevel(str, Enum):
    """Course risk scheme for AI systems."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}


@dataclass(frozen=True)
class RiskClassification:
    """A risk level with its justification."""

    subject: str
    level: RiskLevel
    justification: str


COMPONENT_RISK_CLASSIFICATIONS: tuple[RiskClassification, ...] = (
    RiskClassification(
        subject=f"Knowledge-base retrieval ({KNOWLEDGE_BASE_TOOL})",
        level=RiskLevel.MEDIUM,
        justification=(
            "Answers patient-facing customer-support questions from "
            "project-authored policy documents. It reads no personal or "
            "appointment data, but an unsupported or wrong policy answer "
            "about fees, cancellations, or emergencies could mislead a "
            "patient, so it is guarded by calibrated abstention and an "
            "output groundedness check."
        ),
    ),
    RiskClassification(
        subject=f"Appointment lookup ({APPOINTMENT_LOOKUP_TOOL})",
        level=RiskLevel.HIGH,
        justification=(
            "Reads individual healthcare appointment records (medical "
            "specialty, status, fee, follow-up flag). Even though the "
            "dataset is synthetic, the tool models access to medical data, "
            "so it is read-only, restricted to the Lookup Agent, and its "
            "identifiers are excluded from logs."
        ),
    ),
)

SYSTEM_RISK_CLASSIFICATION = RiskClassification(
    subject="Practo healthcare support agent",
    level=RiskLevel.HIGH,
    justification=(
        "Under the Low/Medium/High scheme (Low: summarization or "
        "transcription; Medium: code generation or customer-support "
        "tickets; High: medical data, hiring, or financial decisions), the "
        "system is High risk. Although most traffic is customer-support "
        "policy questions, it looks up patient appointment records tied to "
        "a medical specialty and answers questions near clinical topics "
        "such as prescriptions, lab results, and emergencies, where an "
        "unsupported answer could cause harm. The highest-risk capability "
        "sets the system level, which is why it is governed by "
        "least-autonomy tool permissions, input guardrails, grounded "
        "abstention, independent review, per-request budgets, and "
        "privacy-safe logging; it must not diagnose or recommend treatment."
    ),
)


def highest_risk_level(
    classifications: Iterable[RiskClassification],
) -> RiskLevel:
    """Return the highest level among the given classifications."""

    levels = [item.level for item in classifications]
    if not levels:
        raise ValueError("At least one risk classification is required.")
    return max(levels, key=_RISK_ORDER.__getitem__)

