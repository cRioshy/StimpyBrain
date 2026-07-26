# Known problems

- Pandorick integration is deliberately absent; its stable event schema and transport need agreement before implementation.
- The API is an in-process read-only facade, not an authenticated network service.
- SQLite observation schema is initial phase-1 creation and needs explicit versioned migrations before later schema changes.
- Pattern learning is descriptive aggregation only; outcome-link quality depends on shared correlation IDs.
- The prediction node is deterministic scaffolding, not a trained or validated model.
