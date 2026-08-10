# StimpyBrain

StimpyBrain is a standalone passive observation, memory and descriptive-learning system for PandorickKi. It never writes to Pandorick, sends Telegram messages, contacts a real broker or creates real orders. The disabled Shitzo S.4 laboratory adds explicit tick-by-tick orchestration and GET-only projections to its virtual broker and deterministic traders, but still has no live provider, scheduler or automatic activity.

Phase 2 is installed but the Pandorick connection remains disabled by default (`STIMPY_PANDORICK_ENABLED=false`). A separate local reasoning prototype turns a supplied decision/outcome payload into persisted observation, transparent evidence, non-causal reasoning, self-criticism and provisional knowledge. SQLite schema v9 provides persistent Incubation, Pattern Learning and a local Hypothesis Lab. Hypotheses retain supporting, contradicting and neutral cases, use conservative thresholds, receive immutable analysis and criticism, and may be explicitly incubated, rejected or archived. Lifecycle decisions require a reason and create an immutable audit event. These research components have no background scheduler or worker connection. Stimpy remains heuristic, not AI inference or a neural model.

Run the clearly simulated, temporary local demo with:

```powershell
python -m stimpy.demo_reasoning_prototype
```

The local Stimpy API can be started with:

```powershell
python -m stimpy
```

Default Stimpy API: `http://127.0.0.1:8765/api/stimpy/health`. The local read-only Hypothesis Controlcenter is available at `http://127.0.0.1:8765/controlcenter`. Stop with Ctrl+C. Tests:

```powershell
python -m compileall -q stimpy tests
python -m unittest discover -v
```

Activation requires explicit approval after reviewing [the integration contract](docs/PANDORICK_READ_ONLY_INTEGRATION.md). No secrets belong in `.env.example`, Git, logs or API responses.

See [the reasoning prototype documentation](docs/STIMPY_REASONING_PROTOTYPE.md), [Hypothesis Lab documentation](docs/STIMPY_HYPOTHESIS_LAB.md), [Lifecycle documentation](docs/STIMPY_HYPOTHESIS_LIFECYCLE.md) and [Controlcenter documentation](docs/STIMPY_HYPOTHESIS_CONTROLCENTER.md) for models, rules, persistence and limits.

See [Shitzo Lab](docs/SHITZO_LAB.md) for the isolated paper-research foundation and its non-negotiable no-order boundary.
