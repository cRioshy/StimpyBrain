# Stimpy Hypothesis Lab foundation

Phase D.1 lets Stimpy persist a bounded research statement and question without treating either as truth. A Hypothesis is not a signal, `SUPPORTED` is not proof, Confidence is not a price probability, and correlation is not causation.

## Local workflow

`HypothesisEngine.create_hypothesis()` creates a stable exact-content identity after whitespace/case normalization for identity only. Similar wording is not silently merged. Text and required-data lists are bounded; secret-like assignments are rejected. The service is available locally from `build_app()["hypothesis_engine"]` and has no HTTP write route.

`add_evidence()` accepts `SUPPORTING`, `CONTRADICTING` or `NEUTRAL` evidence with finite strength and quality in `[0,1]`. Every item references existing Observations. One Evidence item represents exactly one correlation origin; it may contain multiple derived Observations only when they share that origin. The correlation identity forms an independence key, so derivations and overlapping groups cannot inflate the case count. Evidence is append-only and contradictions remain stored.

`evaluate_hypothesis()` persists an idempotent snapshot for the exact Evidence set and configured rules. Evidence Ratio measures the relative weighted support among decisive cases. Confidence separately combines consistency, mean quality, independent-case count and source diversity, then applies a status cap.

## Default thresholds

- 1-24 independent cases: `INVESTIGATING`.
- At least 25 cases and support ratio at least 0.70: `PROVISIONAL`.
- At least 25 cases and support ratio at most 0.30: `CONTRADICTED`.
- At least 100 cases, support ratio at least 0.70, mean quality at least 0.60 and at least two sources: potentially `SUPPORTED`.

Three positive cases can therefore never become `SUPPORTED`. Even supported evaluations retain uncertainty and explicitly state that they are descriptive, non-causal and non-predictive.

## Deliberate limits

D.1 does not implement Hypothesis-specific Reasoning, Self Critic, incubation, rejection/archive commands, Inspiration, Mining/Social/On-Chain adapters or Knowledge Graph promotion. Those require separate reviewed phases. No component writes to Pandorick, creates orders, contacts a broker or sends Telegram messages.
