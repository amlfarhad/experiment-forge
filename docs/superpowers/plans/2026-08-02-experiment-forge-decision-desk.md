# Experiment Forge Decision Desk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a static, credential-free Experiment Forge Decision Desk backed by reproducibly generated Python/DuckDB artifacts and a tested browser workflow.

**Architecture:** Keep Python, SQL, DuckDB, and statistical modules authoritative. Add a deterministic artifact builder that generates clean and intentionally flawed experiment payloads, then serve those JSON payloads through an accessible static browser app with local-only CSV schema validation.

**Tech Stack:** Python 3.12+, DuckDB, pandas, SciPy, statsmodels, Plotly (existing report path), vanilla HTML/CSS/JavaScript, pytest, Playwright, Vercel static deployment.

---

### Task 1: Add explicit sample-data profiles and decision evidence

**Files:**
- Modify: `data_generation/synthetic_product.py`
- Modify: `analysis/experiment_readout.py`
- Modify: `config/experiments.yml`
- Test: `tests/test_web_artifacts.py`

- [ ] Add `quality_profile` and `experiment_name` parameters with defaults that preserve the current flawed `checkout_progress_indicator` behavior; clean mode must skip duplicate assignments, null events, pre-assignment events, and negative revenue injection.
- [ ] Add policy fields for practical lift and alpha without changing existing test call sites.
- [ ] Extend the analysis payload with a four-state decision, practical threshold, continuous-metric evidence, and Holm-adjusted confirmatory evidence calculated from `int_user_experiment_metrics`.
- [ ] Add tests that assert the default sample remains flawed, clean mode contains no critical source failures, and decision fields serialize deterministically.

### Task 2: Build the browser artifact contract and CLI

**Files:**
- Create: `web_artifacts.py`
- Modify: `forge.py`
- Create: `tests/test_web_build.py`

- [ ] Implement a payload builder that runs generation, warehouse build, quality audit, analysis, and DuckDB queries for summary, guardrails, segments, daily trend, metric definitions, lineage, and limitations.
- [ ] Generate both sample workspaces into a temporary or ignored build area, write `web/data/catalog.json` and `web/data/experiments/*.json`, and include a generation manifest with seed, row counts, artifact paths, and source hashes.
- [ ] Add `forge.py web-build --workspace . --output web/data` with deterministic defaults and a clear completion message.
- [ ] Test clean-output reproducibility and direct agreement with `analysis.json`/DuckDB values.

### Task 3: Implement the static Decision Desk

**Files:**
- Create: `web/index.html`
- Create: `web/styles.css`
- Create: `web/app.js`
- Create: `web/data/catalog.json`
- Create: `web/data/experiments/*.json`

- [ ] Build the responsive shell with workspace cards, decision banner, primary metric comparison, confidence interval visualization, quality checks, guardrails, segments, time trend, methodology, and local CSV validator.
- [ ] Add semantic labels, keyboard navigation, focus states, reduced-motion CSS, loading/empty/error states, and compact mobile layouts.
- [ ] Render all numbers from the selected payload; do not hard-code analytical values in JavaScript.
- [ ] Add workspace switching and query-string deep links so the flawed experiment can be opened directly.

### Task 4: Add browser regression coverage and product documentation

**Files:**
- Create: `tests/browser/test_decision_desk.py`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Create: `docs/data_lineage.md`
- Create: `docs/methodology.md`
- Create: `docs/limitations.md`
- Modify: `.gitignore`

- [ ] Add Playwright coverage for landing, clean workspace, flawed workspace, method drawer, CSV validation errors, and screenshots.
- [ ] Document one-command setup, build, local serving, deployment, data schema, lineage, statistical decisions, limitations, and synthetic-data boundaries.
- [ ] Keep generated DuckDB and temporary raw sample builds ignored while committing small browser JSON artifacts.

### Task 5: Verify, deploy, and publish

**Files:**
- Modify: `vercel.json`
- Modify: `.github/workflows/tests.yml`

- [ ] Run the complete Python suite, web-build, and browser suite with fresh output.
- [ ] Start a clean static server, capture screenshots, and inspect console/network failures.
- [ ] Deploy the static `web/` product to Vercel, open the deployed URL in a clean browser, and repeat the critical path.
- [ ] Commit the implementation, push `main` to the configured GitHub origin, and report the verified repository and deployment URLs plus any remaining limitations.
