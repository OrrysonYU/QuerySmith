# Runbook

On elevated failures: identify the request ID, inspect safe events and metrics, verify app DB
readiness, then check data-source and model dependencies without exposing credentials. Cancel hung
jobs and confirm a terminal state. Never disable policy checks to restore service. Backups must be
restored into an isolated database and validated before declaring a drill successful.
