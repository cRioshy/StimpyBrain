# Architecture

```mermaid
flowchart LR
  subgraph P["PandorickKi — separate repository/process"]
    R["Verified Rick GET API"]
  end
  subgraph S["StimpyBrain — read-only observer"]
    C["GET-only HTTP Client"] --> A[Observation Adapter] --> N[Normalizer]
    N --> J[(Rotating append-only JSONL)]
    N --> DB[(SQLite index v9)]
    DB --> M[Evidence Memory] --> L[Descriptive Learning] --> G[Knowledge Graph]
    DB --> W["Observe-only Workflow Gate"]
    DB & M & L & W & G --> API["Local GET-only Stimpy API"] --> UI["Read-only Hypothesis Controlcenter"]
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

Shitzo S.4 remains manually driven inside Stimpy: `explicit validated tick -> PriceWindow -> frozen FeatureSnapshot -> deterministic traders -> virtual PaperBroker -> ShitzoRepository -> GET-only API/Controlcenter`. `ShitzoLab` owns no thread, timer or network client. There is no concrete provider, Stimpy-worker connection, Evidence bridge or HTTP write edge.

The prototype is deliberately not connected to the worker, HTTP polling, broker, Telegram or any order path. The Hypothesis Controlcenter reads bounded same-origin API projections and has no forms or write calls. Its static assets are served with a restrictive Content Security Policy. Reject/archive commands remain explicit local Python calls. There is no background scheduler or automatic strategy change.
