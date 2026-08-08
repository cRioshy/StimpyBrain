# Stimpy Hypothesis Lifecycle

Phase D.3 adds explicit local `reject()` and `archive()` commands. Both require a bounded reason, record an actor and create an immutable `HypothesisLifecycleEvent`. The event insert and Hypothesis status change are one SQLite transaction. Identical repeated commands are idempotent; a repeated terminal decision with different audit content fails closed.

`REJECTED` and `ARCHIVED` are terminal for Evidence, evaluation, Reasoning and incubation reactivation. A rejected Hypothesis may subsequently be archived, preserving both events. An archived Hypothesis cannot be reopened or rejected. This prevents later evaluation from silently replacing a reviewed decision.

SQLite schema v9 stores events in `hypothesis_lifecycle_events`. `GET /api/stimpy/hypotheses/{id}/lifecycle` exposes a bounded audit projection. Reject/archive are deliberately absent from HTTP and are available only through `build_app()["hypothesis_lifecycle"]`. There is no scheduler, automatic rejection, Pandorick write, broker, order, Telegram, strategy mutation or Knowledge promotion.
