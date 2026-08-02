# Limitations and Boundaries

- All browser workspaces use deterministic synthetic data. They are demonstrations of pipeline behavior, not production users, company results, or evidence of adoption.
- The clean workspace is a comparison sample generated with the same pipeline and a documented synthetic treatment lift. It is included to make the launch path testable; it is not a claim about a real autocomplete release.
- The conversion interval is a normal approximation. Very small samples or extreme rates would require a more conservative interval or exact method.
- The two-metric Holm family is intentionally narrow: additional confirmatory metrics would require an explicit registry change and a new payload contract.
- Guardrail status is descriptive. A real operating plan should define intervention thresholds, exposure duration, and ownership before launch.
- The local CSV panel validates headers and row presence in the browser only. It does not upload, persist, or analyze a user's private file.
- The product is static and credential-free. It does not provide authentication, multi-user workspaces, real-time ingestion, or production data connectors.
- Segment and daily-trend views are diagnostic and can be unstable in small samples. They are not a substitute for the registered primary decision rule.
