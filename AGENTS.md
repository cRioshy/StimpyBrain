# Project handover rules

Before changing this project, read `docs/CURRENT_SYSTEM_STATE.md`, `docs/SESSION_HANDOVER.md`, `docs/ARCHITECTURE.md`, `docs/KNOWN_PROBLEMS.md`, and `docs/NEXT_STEPS.md`, then verify them against the actual code.

Never trust chat history alone. Never delete stored observations, history, learning data, tokens, or configuration. Never activate live trading, broker access, order creation, Telegram, or writes to Pandorick. Keep changes small and tested. After every completed task update `docs/SESSION_HANDOVER.md`; update system state for architecture changes, known problems for remaining defects, and next steps for completed/new work.

Pandorick is a separate repository. Never commit or push StimpyBrain to `cRioshy/Pando`. The Pandorick adapter must use the local GET-only client, remain disabled by default, and use only endpoints verified in `docs/PANDORICK_READ_ONLY_INTEGRATION.md`. Do not invent missing endpoints or add a write fallback.
