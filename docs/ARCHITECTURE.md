# Architecture

```mermaid
flowchart LR
  subgraph P["PandorickKi — separate repository/process"]
    R["Verified Rick GET API"]
  end
  subgraph S["StimpyBrain — read-only observer"]
    C["GET-only HTTP Client"] --> A[Observation Adapter] --> N[Normalizer]
    N --> J[(Rotating append-only JSONL)]
    N --> DB[(SQLite index v7)]
    DB --> M[Evidence Memory] --> L[Descriptive Learning] --> G[Knowledge Graph]
    DB --> W["Observe-only Workflow Gate"]
    DB & M & L & W & G --> API["Local GET-only Stimpy API"]
    WK[Single Worker] --> A
    subgraph RP["Isolated local reasoning prototype"]
      PO["Local payload"] --> O[Observer] --> PM["Memory facade"]
      PM --> E["Persisted Evidence"] --> RE["Persisted non-causal reasoning"] --> SC["Persisted Self Critic"] --> KG["Provisional Knowledge Store"]
      RE --> IC["Explicit Incubation"] --> RE2["Stored second reasoning comparison"]
      E --> PL["Explicit Pattern Learning"]
      PL --> HE["Explicit Hypothesis Foundation"]
    end
    PM --> J
    PM --> DB
    KG --> DB
    PL --> DB
    HE --> DB
  end
  R -. "disabled by default" .-> C
  W --> I["Internal insight only; zero orders"]
```

There is no edge from Stimpy back to Pandorick. The HTTP client exposes GET only and accepts loopback HTTP base URLs only. Raw observation nodes are not added to the architecture graph.

The prototype is deliberately not connected to the worker, HTTP polling, broker, Telegram or any order path. Evidence, Reasoning and Critic records are immutable-by-ID SQLite projections linked to observations. Incubation persists both reasoning identities and comparison deltas. Pattern Learning links independent Observation/Evidence cases. The Hypothesis Lab stores bounded research questions, append-only supporting/contradicting/neutral evidence, idempotent evaluations, Hypothesis-specific Reasoning/Critic records and evidence-gated incubation. These services advance only through explicit calls; there is no background scheduler or automatic strategy change.
