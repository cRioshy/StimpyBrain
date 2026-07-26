# Architecture

```mermaid
flowchart LR
  subgraph P["PandorickKi — separate repository/process"]
    R["Verified Rick GET API"]
  end
  subgraph S["StimpyBrain — read-only observer"]
    C["GET-only HTTP Client"] --> A[Observation Adapter] --> N[Normalizer]
    N --> J[(Rotating append-only JSONL)]
    N --> DB[(SQLite index v2)]
    DB --> M[Evidence Memory] --> L[Descriptive Learning] --> G[Knowledge Graph]
    DB --> W["Observe-only Workflow Gate"]
    DB & M & L & W & G --> API["Local GET-only Stimpy API"]
    WK[Single Worker] --> A
  end
  R -. "disabled by default" .-> C
  W --> I["Internal insight only; zero orders"]
```

There is no edge from Stimpy back to Pandorick. The HTTP client exposes GET only and accepts loopback HTTP base URLs only. Raw observation nodes are not added to the architecture graph.
