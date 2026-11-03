# Retrieval Strategy Comparison Report

Both chunking strategies were evaluated against the same 25 in-scope queries, using document-level relevance labels and deduplicated source documents.

- Embedding model: sentence-transformers/all-MiniLM-L6-v2
- Similarity metric: cosine
- Top-k: 2

## Fixed-size-with-overlap

| Query | Expected source(s) | Retrieved source(s) | TP | FP | FN | Precision arithmetic | Recall arithmetic |
|---|---|---|---:|---:|---:|---|---|
| RAG-001 | appointment_booking | second_opinions, appointment_booking | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-002 | cancellation_rescheduling | cancellation_rescheduling | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-003 | fee_structure | second_opinions, fee_structure | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-004 | insurance_claims | insurance_claims, second_opinions | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-005 | prescription_refills | prescription_refills | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-006 | lab_turnaround | lab_turnaround | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-007 | telemedicine | telemedicine | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-008 | emergency_visits | emergency_visits | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-009 | privacy_policy | privacy_policy, insurance_claims | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-010 | follow_up_discounts | follow_up_discounts, second_opinions | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-011 | second_opinions | second_opinions, prescription_refills | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-012 | home_visits | home_visits | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-013 | appointment_booking | appointment_booking, second_opinions | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-014 | appointment_booking | appointment_booking, cancellation_rescheduling | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-015 | cancellation_rescheduling | cancellation_rescheduling, appointment_booking | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-016 | cancellation_rescheduling | cancellation_rescheduling | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-017 | fee_structure | follow_up_discounts, second_opinions | 0 | 2 | 1 | 0/2 = 0.0000 | 0/1 = 0.0000 |
| RAG-018 | insurance_claims | insurance_claims | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-019 | prescription_refills | prescription_refills | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-020 | lab_turnaround | lab_turnaround | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-021 | telemedicine | telemedicine | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-022 | emergency_visits | emergency_visits, telemedicine | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-023 | privacy_policy | privacy_policy | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-024 | follow_up_discounts | follow_up_discounts | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-025 | home_visits | home_visits, second_opinions | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |

Macro precision: **0.7400** (mean over 25 queries).
Macro recall: **0.9600** (mean over 25 queries).

## Sentence-based

| Query | Expected source(s) | Retrieved source(s) | TP | FP | FN | Precision arithmetic | Recall arithmetic |
|---|---|---|---:|---:|---:|---|---|
| RAG-001 | appointment_booking | second_opinions, appointment_booking | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-002 | cancellation_rescheduling | cancellation_rescheduling | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-003 | fee_structure | fee_structure, follow_up_discounts | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-004 | insurance_claims | insurance_claims, second_opinions | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-005 | prescription_refills | prescription_refills | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-006 | lab_turnaround | lab_turnaround | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-007 | telemedicine | telemedicine | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-008 | emergency_visits | emergency_visits | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-009 | privacy_policy | second_opinions, privacy_policy | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-010 | follow_up_discounts | follow_up_discounts | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-011 | second_opinions | second_opinions | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-012 | home_visits | home_visits | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-013 | appointment_booking | appointment_booking | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-014 | appointment_booking | appointment_booking, cancellation_rescheduling | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-015 | cancellation_rescheduling | cancellation_rescheduling, appointment_booking | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-016 | cancellation_rescheduling | cancellation_rescheduling, fee_structure | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-017 | fee_structure | fee_structure, follow_up_discounts | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-018 | insurance_claims | insurance_claims | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-019 | prescription_refills | prescription_refills | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-020 | lab_turnaround | lab_turnaround | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-021 | telemedicine | telemedicine | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-022 | emergency_visits | emergency_visits, telemedicine | 1 | 1 | 0 | 1/2 = 0.5000 | 1/1 = 1.0000 |
| RAG-023 | privacy_policy | privacy_policy | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-024 | follow_up_discounts | follow_up_discounts | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |
| RAG-025 | home_visits | home_visits | 1 | 0 | 0 | 1/1 = 1.0000 | 1/1 = 1.0000 |

Macro precision: **0.8200** (mean over 25 queries).
Macro recall: **1.0000** (mean over 25 queries).

## Recommendation

Select **sentence** chunking: recall is prioritized to reduce missed policy sources; it has macro recall 1.0000 and macro precision 0.8200. The sentence-based minus fixed-size precision difference is +0.0800; this recommendation is limited to this 25-query labeled evaluation.
