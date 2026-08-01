# Stimpy reasoning

The deterministic `ReasoningEngine` converts one observation and its Evidence result into reasons, counterarguments, assumptions, missing information, a cautious conclusion, bounded reasoning confidence and uncertainty. Caller confidence remains separate. Every result receives stable reasoning, observation and evidence IDs and is persisted idempotently in SQLite schema v4.

Reasoning explicitly states that one case cannot establish causality. It produces no order, advice or Pandorick response. Historical comparison and multi-observation reasoning remain future work.
