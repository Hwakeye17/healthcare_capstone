# Application-Layer Governance and Risk Classification

## 1. Principle of Least Autonomy

The Practo support assistant separates policy retrieval, appointment record
lookup, and final response composition across three CrewAI specialist roles.
Because `check_appointment_status` reads individual appointment records, it is
governed under the principle of least autonomy: only the Lookup Agent
(`Practo Appointment Lookup Specialist`) may receive or invoke it.

| Agent role | `search_practo_knowledge_base` | `check_appointment_status` |
|---|---:|---:|
| `Practo Knowledge Retrieval Specialist` | Permitted | Denied |
| `Practo Appointment Lookup Specialist` | Denied | Permitted |
| `Practo Support Response Composer` | Denied | Denied |

The policy is defined as an immutable default-deny mapping (`TOOL_PERMISSIONS`)
in `src/practo_agent/governance/policy.py`. Any unknown agent role or unknown
tool name is denied.

## 2. Two-Stage Enforcement Guard

Rather than relying on prompt instructions alone, tool permissions are enforced
in Python at both wiring time and tool-invocation time. During agent and crew
construction (`create_specialist_agents` and `create_practo_crew`),
`authorize_agent_tools` and `enforce_crew_tool_permissions` inspect every
agent's `tools` list and every task's `tools` override and raise
`ToolPermissionError` before execution if `check_appointment_status` (or any
other tool) is attached to an unauthorized role. In addition,
`install_tool_call_guard` registers `tool_call_guard` as a CrewAI
`before_tool_call` hook so that even if an agent or task is constructed outside
the project factories with `check_appointment_status` attached, any runtime
attempt by a non-Lookup agent to call the tool is intercepted before
`check_appointment_status` executes, returns `False` to abort the tool call,
and records a privacy-safe `tool_call_blocked` event in the JSONL audit log
without exposing the requested record ID.

## 3. Risk Classification

Under the course Low/Medium/High risk scheme (**Low**: summarization or
transcription; **Medium**: code generation or customer-support tickets;
**High**: medical data, hiring decisions, or financial data), the system and
its tool capabilities are classified as follows:

| Subject | Risk level | Justification |
|---|---|---|
| Knowledge-base retrieval (`search_practo_knowledge_base`) | Medium | Answers patient-facing customer-support questions from project-authored policy documents. It reads no personal or appointment data, but an unsupported or wrong policy answer about fees, cancellations, or emergencies could mislead a patient, so it is guarded by calibrated abstention and an output groundedness check. |
| Appointment lookup (`check_appointment_status`) | High | Reads individual healthcare appointment records (medical specialty, status, fee, follow-up flag). Even though the dataset is synthetic, the tool models access to medical data, so it is read-only, restricted to the Lookup Agent, and its identifiers are excluded from logs. |
| Practo healthcare support agent (overall system) | High | Under the Low/Medium/High scheme (Low: summarization or transcription; Medium: code generation or customer-support tickets; High: medical data, hiring, or financial decisions), the system is High risk. Although most traffic is customer-support policy questions, it looks up patient appointment records tied to a medical specialty and answers questions near clinical topics such as prescriptions, lab results, and emergencies, where an unsupported answer could cause harm. The highest-risk capability sets the system level, which is why it is governed by least-autonomy tool permissions, input guardrails, grounded abstention, independent review, per-request budgets, and privacy-safe logging; it must not diagnose or recommend treatment. |

`highest_risk_level(COMPONENT_RISK_CLASSIFICATIONS)` computes the overall
level from the component classifications and confirms that the system level
matches its highest-risk capability (`RiskLevel.HIGH`).

## 4. Four-Layer Governance Alignment

- **Application layer:** Default-deny tool permission table, wiring-time
  validation (`authorize_agent_tools`, `enforce_crew_tool_permissions`),
  call-time CrewAI hook (`tool_call_guard`), and `allow_delegation=False` on
  every specialist agent.
- **Input/Output guardrail layer:** Fixed-format contact-number masking and
  prompt-injection rejection before routing, calibrated retrieval abstention,
  output groundedness verification, and two-agent AutoGen review.
- **Runtime layer:** Per-request input token, cumulative token, and estimated
  cost caps enforced by `RuntimeBudget` before routing and before each model
  call (see [`docs/runtime_budget_design.md`](../runtime_budget_design.md)).
- **Observability layer:** Allowlisted JSONL events (`workflow_routed`,
  `tool_completed`, `tool_call_blocked`, `request_completed`) correlated by
  trace ID without logging raw queries, contact numbers, or appointment IDs.

## 5. Offline Demonstration and Tests

Run the offline governance demonstration:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_governance.py
```

The script verifies:

1. Permitted access: the Lookup Agent invokes `check_appointment_status` on an
   appointment query and logs `tool_completed`.
2. Prohibited wiring: attaching `check_appointment_status` to the Retrieval
   Agent or Response Composer raises `ToolPermissionError`.
3. Prohibited runtime call: a Response Composer deliberately constructed
   outside the project factories with `lookup_appointment` attached attempts to
   call `check_appointment_status` during `Crew.kickoff()`; the `before_tool_call`
   hook blocks execution before the lookup function runs and logs
   `tool_call_blocked`.

The demonstration writes `evaluation/results/governance_demo.json`.

Run the unit tests:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m pytest tests/unit/test_governance.py -v
```

## 6. Limitations

- Role-based tool checks rely on the agent's configured `role` string matching
  the canonical role constants in `practo_agent.governance.policy`.
- Process-local Python hooks protect CrewAI tool execution within the
  application process; in a multi-service production deployment, appointment
  data access would also be enforced by service authentication and database
  access controls.

