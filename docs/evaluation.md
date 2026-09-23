# Evaluation

`eval/datasets/questions.json` contains 60 normal questions and `adversarial.json` contains 15
security cases. `EvalRunner` accepts an explicit async application adapter, records every case, and
writes JSON and Markdown reports. Metrics are computed from records: execution success,
first-attempt success, self-heal recovery, unsafe-query rejection, semantic match, and attempts.
Regression checks protect unsafe-query rejection and semantic match by default.

Example once a configured adapter exists:

```bash
python -m eval.runner --adapter your_module:build_eval_adapter --output eval/runs/2026-09-20
```

No live baseline exists in this repository because no provider credential or PostgreSQL runtime was
available during the current execution. The nightly workflow runs only when evaluation secrets are
configured; this prevents fabricated reports.
