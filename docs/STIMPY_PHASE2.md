# Stimpy Phase 2

Phase 2 adds an opt-in local observer around the Phase-1 workflow. Each successful Pandorick envelope is normalized item by item; one malformed item does not discard its batch. Persistent identity checks cover observation ID, source-scoped event ID, source-type correlation ID and endpoint-scoped content hash.

The worker stores observations, updates evidence memory and records a shadow workflow evaluation. Missing strict workflow fields cause an internal rejection. No result is returned to Pandorick or represented as trade approval. Recovery emits internal unavailable/recovered events. Shutdown stops only Stimpy, atomically records STOPPED and closes resources in the CLI composition root.
