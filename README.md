# StimpyBrain

StimpyBrain is a standalone passive observation, memory and descriptive-learning system for PandorickKi. It can poll a small allowlist of local read-only endpoints through an HTTP client that technically supports GET only. It never writes to Pandorick, sends Telegram messages, contacts a broker, creates orders, or enables paper/live trading.

Phase 2 is installed but the Pandorick connection remains disabled by default (`STIMPY_PANDORICK_ENABLED=false`). A separate local reasoning prototype now turns a supplied decision/outcome payload into persisted observation, transparent evidence, non-causal reasoning, self-criticism and provisional knowledge. It is heuristic—not AI inference or a neural model—and is not connected to the worker or Pandorick.

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

See [the reasoning prototype documentation](docs/STIMPY_REASONING_PROTOTYPE.md) for models, rules, persistence and limits.
