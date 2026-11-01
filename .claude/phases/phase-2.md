# Phase 2: evaluation
Spec: docs/cadrage.md section 3, data/scenarios/README.md, configs/gates.yaml, dvc.yaml, ADR 0003 and 0005.

1. `data/scenarios/scenarios_v1.jsonl`: about 80 scenarios across the 7 categories, in French as real users would ask.
2. `evaluation/run.py` and `evaluation/gates.py` wired to dvc.yaml. All metrics, per category, repeated per params.yaml, mean and spread. Deterministic checks first; LLM judge only where needed, validated against hand labels on a sample.
3. MLflow: params, metrics, prompt version, model id, scenario hash, seed. Compare groq-large vs groq-small and prompt v1 vs v2 (plus Ollama if available).
4. After a real run, fill null thresholds in gates.yaml from the baseline with the stated margins and document the source of each.
5. Enable the pull_request trigger in `.github/workflows/eval-gate.yml`.
6. `docs/evaluation.md`: tables, charts in reports/, at least 3 analysed failure cases.
