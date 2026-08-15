# Stimpy Hypothesis Controlcenter

Phase D.4 adds a local browser view at `http://127.0.0.1:8765/controlcenter`. It shows a status summary, searchable/filterable Hypothesis list, Confidence, uncertainty, Evidence Ratio, independent case count, Reasoning, counterarguments, missing information, alternatives, Self Critic, Evidence, incubation and lifecycle history. It refreshes from the existing API every 15 seconds and also has a manual refresh button.

The view is responsive without fixed page widths and uses only packaged HTML, CSS and JavaScript. Persisted text is inserted with DOM text nodes rather than HTML interpretation. Assets are same-origin and served with a restrictive Content Security Policy, `nosniff` and `no-store` headers.

The Controlcenter is strictly read-only: it contains no reject/archive buttons, submits no forms and makes only GET requests. POST, PUT, PATCH and DELETE still return 405. It must remain on loopback because Stimpy has no API authentication. It is not hosted externally and adds no Pandorick write, broker, order, Telegram, automatic decision or Knowledge promotion path.
