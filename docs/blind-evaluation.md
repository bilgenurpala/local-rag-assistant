# Blind Evaluation

This is the one-time validation run performed after the original development
evaluation and after the configuration was frozen. The ten questions in
`prototypes/blind_evaluation_run.py` had not been used to choose the model,
threshold, prompt, Top-K value, or corpus wording.

## Method

- Five questions are answerable from the knowledge base.
- Five questions are deliberately unsupported and require the exact fallback.
- Answerable questions use frozen minimum keyword checks.
- Unsupported questions pass only when the answer body is the exact fallback.
- Source lines are excluded from fallback classification.
- Complete questions, answers, scores, latency, and automatic decisions are
  preserved in `blind-evaluation-results.json`.

## Result

| Group | Passed | Total |
|---|---:|---:|
| Answerable | 4 | 5 |
| Unsupported | 3 | 5 |
| Overall | 7 | 10 |

The initial console summary printed `4/10` because the validator compared the
fallback plus its appended source line against the fallback string. The stored
answers show that cases 6-8 returned the correct fallback. The validator was
corrected to classify the answer body separately; no model output, question,
threshold, prompt, or corpus text was changed in response.

## Failure analysis

1. **Internet-after-setup question:** retrieval returned a broadly relevant
   offline paragraph instead of the troubleshooting paragraph that explains
   later downloads and catalog refreshes. The model then made an absolute claim.
2. **Catalog-license question:** the answer admitted that the license was not in
   context but did not use the required exact fallback.
3. **Kubernetes question:** the model generated generic deployment instructions
   from outside the supplied context. This is the most severe failure.

The blind result confirms the limitation already seen in the development set:
semantic similarity plus an instruction-only grounding rule does not reliably
separate related context from answering evidence. The result remains frozen as
validation evidence and was not used for another tuning cycle.
