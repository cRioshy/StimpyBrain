# StimpyBrain

StimpyBrain is a standalone passive observation, memory and descriptive-learning system for PandorickKi. It can poll a small allowlist of local read-only endpoints through an HTTP client that technically supports GET only. It never writes to Pandorick, sends Telegram messages, contacts a broker, creates orders, or enables paper/live trading.

Phase 2 is installed but the Pandorick connection remains disabled by default (`STIMPY_PANDORICK_ENABLED=false`). A separate local reasoning prototype turns a supplied decision/outcome payload into persisted observation, transparent evidence, non-causal reasoning, self-criticism and provisional knowledge. SQLite schema v7 provides persistent Incubation, Pattern Learning and a local Hypothesis foundation. Hypotheses retain supporting, contradicting and neutral cases and use conservative configurable thresholds. These research components have no background scheduler or worker connection. Stimpy remains heuristic, not AI inference or a neural model.

Run the clearly simulated, temporary local demo with:

```powershell
python -m stimpy.demo_reasoning_prototype
```

The local Stimpy API can be started with:

```powershell
python -m stimpy
```

Default Stimpy API: `http://127.0.0.1:8765/api/stimpy/health`. Stop with Ctrl+C. Tests:

```powershell
python -m compileall -q stimpy tests
python -m unittest discover -v
```

Activation requires explicit approval after reviewing [the integration contract](docs/PANDORICK_READ_ONLY_INTEGRATION.md). No secrets belong in `.env.example`, Git, logs or API responses.

See [the reasoning prototype documentation](docs/STIMPY_REASONING_PROTOTYPE.md), [Pattern Learning documentation](docs/STIMPY_PATTERN_LEARNING.md) and [Hypothesis Lab documentation](docs/STIMPY_HYPOTHESIS_LAB.md) for models, rules, persistence and limits.
