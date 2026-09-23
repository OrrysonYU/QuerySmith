# Troubleshooting

- Readiness fails: validate configuration and app DB connectivity.
- Queries time out: inspect cost and indexes; do not raise limits before measuring.
- Policy blocks SQL: treat as terminal and inspect the rule; never auto-repair around it.
- LLM output is malformed: one bounded re-prompt, then fail safely.
