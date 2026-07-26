# StimpyBrain

Standalone, passive observation and descriptive-learning service. Phase 1 accepts only explicitly supplied, allowlisted Pandorick event copies. It never submits orders, calls a broker, sends Telegram messages, or modifies Pandorick.

Run tests:

```powershell
python -m unittest discover -v
```

The Pandorick connection is intentionally not active. Integration must later be a one-way, read-only event adapter.
