"""Fixed evaluation set for grounded AI assistance (Phase 8 item 9).

`cases.py` holds the immutable case list; `test_ai_grounding_eval.py` runs
every case offline (no network, no provider) against the validators, so the
grounding/omission/hallucination contract is enforced on every gate run.
`backend/scripts/eval_ai_grounding.py` replays a live subset against the
configured provider and writes a human-reviewable report (latency +
grounding outcomes) to `backend/data/validation_reports/`.
"""
