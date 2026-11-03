# Retrieval Evaluation

## Objective

Compare fixed-size-with-overlap and sentence-based chunking for the
project-authored healthcare policy knowledge base. The experiment evaluates
document-level retrieval, not the correctness or safety of generated answers.

## Method

Both collections use the same 12 documents, the local
`sentence-transformers/all-MiniLM-L6-v2` embedding model, cosine distance,
top-k of 2, 25 labeled in-scope queries, and expected-source labels. Retrieved
chunks are mapped to source IDs and deduplicated before precision and recall
are calculated. The per-query arithmetic and retrieved IDs are in
[`../../evaluation/results/retrieval_comparison.md`](../../evaluation/results/retrieval_comparison.md);
the complete machine-readable results are in
[`../../evaluation/results/retrieval_results.json`](../../evaluation/results/retrieval_results.json).

## Results

| Strategy | Collection | Chunks | Queries | Macro precision | Macro recall |
|---|---|---:|---:|---:|---:|
| Fixed-size with overlap | `practo_fixed_size` | 33 | 25 | 0.7400 | 0.9600 |
| Sentence-based with overlap | `practo_sentence` | 24 | 25 | 0.8200 | 1.0000 |

Sentence-based chunking retrieved the labeled source for all 25 queries and
had higher macro precision than fixed-size (0.8200 versus 0.7400). Fixed-size
missed the labeled source for one query and had macro recall 0.9600. Sentence-
based is the selected default for this labeled query set; the results are not
evidence of general superiority.

## Abstention Calibration

The selected sentence-based collection was calibrated on 25 in-scope and two
out-of-scope queries. Candidate thresholds include observed distances and
midpoints between adjacent observations. The selection rule requires zero
false acceptances, maximizes in-scope recall, and uses the midpoint between
the nearest class boundaries when the measured classes are fully separable.

| Observed group | Best-distance boundary | Query ID |
|---|---:|---|
| Maximum in-scope distance | 0.6452579498 | RAG-023 |
| Minimum out-of-scope distance | 0.7499952912 | ABS-004 |

The selected threshold is **0.6976266205310822**, the midpoint between these
boundaries. On this 27-query calibration set, it produced 25 true positives,
0 false positives, 2 true negatives, and 0 false negatives (precision
1.0000, recall 1.0000, false acceptance rate 0.0000). The configured
comparison is inclusive: evidence is accepted when its best distance is less
than or equal to this value.

The calibration set is small and the threshold is provisional. Cosine
similarity is not a probability or a proof of entailment; passing the
threshold does not by itself guarantee that a generated answer is grounded.
The separate groundedness validation remains necessary.

## Reproduction

Run these commands from the repository root after the local embedding model
is available:

```powershell
python .\dataset.py --count 240 --seed 42
python .\scripts\validate_knowledge_base.py
python .\scripts\build_vectorstores.py
python .\scripts\evaluate_retrieval.py
python .\scripts\calibrate_abstention.py
```

Changing the knowledge base, chunking parameters, model, selected collection,
or top-k requires rebuilding the collections and rerunning both evaluations.
