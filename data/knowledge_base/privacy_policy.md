
# Privacy and Information Handling

This document defines synthetic privacy guidance for capstone testing, not an actual Practo privacy policy.

Patients should share only the information necessary to complete an administrative request through an appropriate channel. Appointment references and contact details must not be disclosed to unrelated users or included unnecessarily in model prompts and application logs. Fixed-format contact numbers must be masked before request text is logged or sent to model-facing components, as required by the capstone guardrails. Access to appointment information must be limited to the specific lookup purpose and authorized application component. Requests for information that the system is not authorized to disclose must be refused or routed to an appropriate support channel.
