# Stimpy incubation

Phase B simulates an incubation effect without pretending that waiting itself creates knowledge. A task stores an initial observation and reasoning, enters `INCUBATING`, becomes `READY` only through an explicit due-task call, and can be resolved only with new persisted observations, Evidence and a final Reasoning result.

## States

`NEW`, `INCUBATING`, `READY`, `RESOLVED`, `FAILED`, `CANCELLED`.

The service does not use a durable `RUNNING` state. A failed attempt returns to `READY` until the configured retry limit is reached, then becomes `FAILED`. Cancellation and successful reactivation are idempotent. Restarting Stimpy does not lose tasks because every transition is stored in SQLite schema v5.

## Comparison

Resolution preserves both reasoning IDs and records Evidence-score delta, separate Reasoning-confidence delta, initial/final decisions, direction change and both conclusions. Incubation time alone never raises confidence. At least one different stored observation with persisted Evidence is mandatory.

## Safety

There is no automatic scheduler, worker integration, Pandorick callback, order, broker, Telegram or model mutation. The API exposes only `GET /api/stimpy/incubation`; state transitions are internal explicit service calls.
