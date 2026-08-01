# Stimpy reasoning prototype

## Purpose and boundaries

This is a small, deterministic foundation for observation memory, evidence, reasoning, self-criticism and later incubation. It is not AI inference, a neural architecture, a probability model or an autonomous learning loop. It has no market connection and cannot write to Pandorick, create orders, contact a broker or send Telegram messages.

## Flow

`Decision payload -> Observer -> Observation -> Memory -> EvidenceEngine -> ReasoningEngine -> SelfCritic -> KnowledgeGraph -> PrototypeResult`

`StimpyPrototypeService.process(mapping)` is the public orchestration method. The prototype is deliberately absent from `stimpy/app.py` and the production worker, so importing or starting Stimpy does not run it.

## Models

- `Observation`: existing frozen model, compatibly extended with optional `decision`, `confidence`, `outcome` and `profit`. Prototype observations require the full quartet, UTC-aware time, known enums, finite profit and confidence in `[0, 1]`.
- `EvidenceResult`: raw heuristic score, normalized score, structured supporting/contradicting evidence, count and timestamp.
- `ReasoningResult`: evidence score, reasons, counterarguments, non-causal conclusion, separate reasoning confidence, uncertainty and timestamp.
- `CriticResult`: hypothesis-only issues, severity and suggestions.
- `KnowledgeEntry`: stable ID, observation link, evidence and criticism, status and schema version.
- `PrototypeResult`: complete serializable processing result.
- `IncubationRequest` and `IncubationPort`: future interface only.

## Persistence

No parallel `memory.py` file store or `knowledge.json` exists. `Memory` is a facade in the existing `memory_service.py`, backed by `ObservationStore`. Every accepted observation is appended as one complete UTF-8 JSONL line with flush/fsync and indexed in SQLite. Duplicate observation IDs return `False`. Recent observations are reconstructed as typed objects.

SQLite schema v4 retains the nullable prototype columns and adds idempotent `evidence_results`, `reasoning_results` and `critic_results` tables. Knowledge rows link to stable reasoning and critic IDs. Existing generic Phase-2 observations remain valid. Inserts use stable identities and do not silently overwrite prior analysis.

## Evidence and reasoning

Default Evidence rules are centrally configured in `EvidenceRules`: confidence above `0.8` adds 2, positive profit adds 3, `WIN` adds 2, `LOSS` subtracts 3, and high confidence combined with `LOSS` subtracts another 2. `UNKNOWN` adds nothing. Normalization only maps the configured score range to `[0, 1]`; it is not a win probability.

Reasoning carries supporting factors forward, always states that one observation cannot establish causality, adds low-evidence and possible confidence-overweighting counterarguments where relevant, and exposes assumptions, missing information and uncertainty. Conclusions are observational and never orders or advice.

Self Critic checks possible high-confidence miscalibration, large negative profit, profit/outcome inconsistency and non-final outcomes. Its wording remains hypothetical. A single knowledge entry can only be `OBSERVED` or `PROVISIONAL`; `SUPPORTED` requires a future independent multi-observation design.

## Demo and tests

Run `python -m stimpy.demo_reasoning_prototype`. It uses a temporary data directory, a fixed simulated BTCUSDT record and no network. Run the full suite with `python -m unittest discover -s tests -v`.

## Next steps

Implement incubation persistence and explicit scheduling first. Then design independent-evidence aggregation, contradiction handling and offline calibration. None of these should create a Pandorick feedback edge or automatic code/model mutation.
