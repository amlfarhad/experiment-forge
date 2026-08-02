(() => {
  "use strict";

  const state = { catalog: null, payload: null };
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const schemas = {
    raw_experiment_assignments: ["assignment_id", "experiment_name", "user_id", "variant", "assigned_at"],
    raw_events: ["event_id", "session_id", "user_id", "event_name", "event_at", "source"],
    raw_orders: ["order_id", "user_id", "session_id", "order_at", "revenue", "currency"],
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function number(value, digits = 0) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return "—";
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(parsed);
  }

  function pct(value, digits = 1) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? `${(parsed * 100).toFixed(digits)}%` : "—";
  }

  function signedPct(value, digits = 1) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return "—";
    return `${parsed >= 0 ? "+" : ""}${(parsed * 100).toFixed(digits)}%`;
  }

  function money(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? `$${parsed.toFixed(2)}` : "—";
  }

  function decisionLabel(decision) {
    return {
      launch: "launch",
      stop: "stop",
      continue: "continue",
      investigate: "investigate",
    }[decision] || "review";
  }

  function decisionDescription(decision) {
    return {
      launch: "The evidence clears the quality, statistical, and practical gates.",
      stop: "The treatment shows a statistically supported practical harm.",
      continue: "The signal is useful, but the evidence is not yet a launch or stop call.",
      investigate: "Critical data-quality failures make the observed effect unsafe to act on.",
    }[decision] || "Review the evidence before making a product call.";
  }

  function showView(name) {
    $("#loading-state").hidden = name !== "loading";
    $("#error-state").hidden = name !== "error";
    $("#landing-view").hidden = name !== "landing";
    $("#workspace-view").hidden = name !== "workspace";
  }

  async function fetchJson(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) throw new Error(`Could not load ${path} (${response.status})`);
    return response.json();
  }

  function renderLanding() {
    const grid = $("#workspace-grid");
    if (!state.catalog?.experiments?.length) {
      grid.innerHTML = `<div class="empty-box">No sample workspaces are available yet. Run <code>python3 forge.py web-build</code> to create the artifact catalog.</div>`;
      showView("landing");
      return;
    }
    grid.innerHTML = state.catalog.experiments.map((item) => `
      <button class="workspace-card" type="button" data-workspace="${escapeHtml(item.id)}">
        <span class="card-topline">
          <span class="sample-tag">${escapeHtml(item.sample_profile)} sample · ${escapeHtml(item.quality_status)}</span>
          <span class="decision-chip" data-decision="${escapeHtml(item.decision)}">${escapeHtml(decisionLabel(item.decision))}</span>
        </span>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.takeaway)}</p>
        <span class="card-bottom">
          <span class="card-stat"><strong class="card-stat-value">${number(item.assigned_users)}</strong><span class="card-stat-label">canonical users</span></span>
          <span class="card-stat"><strong class="card-stat-value">${signedPct(item.relative_lift)}</strong><span class="card-stat-label">primary lift</span></span>
          <span class="card-arrow" aria-hidden="true">↗</span>
        </span>
      </button>
    `).join("");
    $$("[data-workspace]", grid).forEach((card) => card.addEventListener("click", () => openWorkspace(card.dataset.workspace)));
    showView("landing");
  }

  function renderWorkspaceOptions(selectedId) {
    const select = $("#workspace-select");
    select.innerHTML = state.catalog.experiments.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title)}</option>`).join("");
    select.value = selectedId;
    select.onchange = () => openWorkspace(select.value);
  }

  function renderEffectChart(analysis) {
    const lowerValue = Math.min(Number(analysis.ci_lower), 0);
    const upperValue = Math.max(Number(analysis.ci_upper), 0);
    const padding = Math.max((upperValue - lowerValue) * 0.12, 0.01);
    const lower = lowerValue - padding;
    const upper = upperValue + padding;
    const x = (value) => 24 + ((Number(value) - lower) / (upper - lower)) * 572;
    const zero = x(0);
    const point = x(analysis.absolute_lift);
    const ciLeft = x(analysis.ci_lower);
    const ciRight = x(analysis.ci_upper);
    const effectColor = Number(analysis.absolute_lift) >= 0 ? "#71951e" : "#c1543d";
    return `
      <svg viewBox="0 0 620 118" role="img" aria-label="Treatment minus control conversion-rate difference is ${escapeHtml(signedPct(analysis.absolute_lift, 2))}, with a 95 percent interval from ${escapeHtml(signedPct(analysis.ci_lower, 2))} to ${escapeHtml(signedPct(analysis.ci_upper, 2))}">
        <line x1="24" y1="53" x2="596" y2="53" stroke="#d7d2c4" stroke-width="2" />
        <line x1="${zero}" y1="25" x2="${zero}" y2="82" stroke="#101416" stroke-width="1" stroke-dasharray="3 4" />
        <line x1="${ciLeft}" y1="53" x2="${ciRight}" y2="53" stroke="${effectColor}" stroke-width="5" stroke-linecap="round" />
        <line x1="${ciLeft}" y1="43" x2="${ciLeft}" y2="63" stroke="${effectColor}" stroke-width="2" />
        <line x1="${ciRight}" y1="43" x2="${ciRight}" y2="63" stroke="${effectColor}" stroke-width="2" />
        <circle cx="${point}" cy="53" r="8" fill="${effectColor}" stroke="#fffdf6" stroke-width="3" />
        <text x="${zero}" y="102" fill="#70756e" font-size="10" text-anchor="middle">0 effect</text>
        <text x="${point}" y="25" fill="#101416" font-size="10" font-weight="700" text-anchor="middle">${escapeHtml(signedPct(analysis.absolute_lift, 2))}</text>
      </svg>
    `;
  }

  function formatGuardrailValue(key, value) {
    if (key.includes("rate")) return pct(value, 2);
    if (key.includes("duration")) return `${number(value, 0)} sec`;
    return number(value, key.includes("ticket") ? 3 : 2);
  }

  function guardrailLabel(key) {
    return {
      sessions_per_user: "Sessions per user",
      support_tickets_per_user: "Support tickets / user",
      avg_session_duration_seconds: "Average session duration",
      negative_revenue_user_rate: "Users with negative revenue",
    }[key] || key.replaceAll("_", " ");
  }

  function renderComparison(analysis) {
    const rows = [
      ["Conversion rate", pct(analysis.control.conversion_rate), pct(analysis.treatment.conversion_rate)],
      ["Conversions", number(analysis.control.conversions), number(analysis.treatment.conversions)],
      ["Assigned users", number(analysis.control.assigned_users), number(analysis.treatment.assigned_users)],
      ["Revenue / user", money(analysis.control.revenue_per_user), money(analysis.treatment.revenue_per_user)],
    ];
    return rows.map(([label, control, treatment], index) => `
      <tr>
        <td>${index === 0 ? `<span class="variant-label">${escapeHtml(label)}</span>` : escapeHtml(label)}</td>
        <td class="${index === 0 ? "metric-big" : ""}">${escapeHtml(control)}</td>
        <td class="${index === 0 ? "metric-big" : ""}">${escapeHtml(treatment)}</td>
      </tr>
    `).join("");
  }

  function renderQuality(quality) {
    const summary = quality.summary;
    const checks = quality.checks || [];
    return `
      <div class="quality-summary">
        <span class="quality-pill ${summary.status}">overall <strong>${escapeHtml(summary.status)}</strong></span>
        <span class="quality-pill pass">pass <strong>${number(summary.passed)}</strong></span>
        <span class="quality-pill warn">warn <strong>${number(summary.warnings)}</strong></span>
        <span class="quality-pill fail">fail <strong>${number(summary.failed)}</strong></span>
      </div>
      <div class="check-list">
        ${checks.map((check) => `
          <div class="check-row">
            <span class="check-signal ${escapeHtml(check.status)}" aria-label="${escapeHtml(check.status)}"></span>
            <span class="check-name">${escapeHtml(check.name.replaceAll("_", " "))}</span>
            <span class="check-observed">${escapeHtml(number(check.observed, Number(check.observed) < 1 ? 4 : 0))}<span>threshold ${escapeHtml(number(check.threshold, Number(check.threshold) < 1 ? 4 : 0))}</span></span>
            <span class="check-detail">${escapeHtml(check.detail)}</span>
          </div>
        `).join("")}
      </div>
    `;
  }

  function renderGuardrails(payload) {
    const byVariant = Object.fromEntries((payload.guardrails || []).map((row) => [row.variant, row]));
    const keys = payload.experiment.guardrails?.length ? payload.experiment.guardrails : ["sessions_per_user", "support_tickets_per_user", "avg_session_duration_seconds"];
    return keys.map((key) => {
      const control = Number(byVariant.control?.[key] ?? 0);
      const treatment = Number(byVariant.treatment?.[key] ?? 0);
      const harmful = key.includes("support") || key.includes("negative") ? treatment > control * 1.1 : treatment < control * 0.98;
      const delta = control ? treatment / control - 1 : 0;
      return `
        <article class="guardrail-card">
          <div class="guardrail-top"><h3>${escapeHtml(guardrailLabel(key))}</h3><span class="guardrail-status ${harmful ? "watch" : ""}">${harmful ? "watch" : "clear"}</span></div>
          <div class="guardrail-values">
            <div class="guardrail-value"><span>control</span><strong>${escapeHtml(formatGuardrailValue(key, control))}</strong></div>
            <div class="guardrail-value"><span>treatment</span><strong>${escapeHtml(formatGuardrailValue(key, treatment))}</strong></div>
          </div>
          <p class="guardrail-delta">${escapeHtml(signedPct(delta))} versus control · ${harmful ? "needs review before scaling" : "no directional concern in this sample"}</p>
        </article>
      `;
    }).join("");
  }

  function renderSegments(payload) {
    const groups = {};
    (payload.segments || []).forEach((row) => {
      groups[row.segment] ||= {};
      groups[row.segment][row.variant] = row;
    });
    const rows = Object.entries(groups).map(([segment, variants]) => {
      const control = Number(variants.control?.conversion_rate ?? 0);
      const treatment = Number(variants.treatment?.conversion_rate ?? 0);
      const delta = control ? treatment / control - 1 : 0;
      return `<tr><td class="segment-name">${escapeHtml(segment)}</td><td>${escapeHtml(pct(control))}</td><td>${escapeHtml(pct(treatment))}</td><td class="segment-delta ${delta >= 0 ? "positive" : "negative"}">${escapeHtml(signedPct(delta))}</td></tr>`;
    }).join("");
    return rows || `<tr><td colspan="4">No segment rows are available in this payload.</td></tr>`;
  }

  function renderTrend(payload) {
    const rows = payload.daily_trend || [];
    const dates = [...new Set(rows.map((row) => row.snapshot_date))];
    const values = rows.map((row) => Number(row.cumulative_revenue) || 0);
    const max = Math.max(...values, 1);
    const x = (index) => dates.length < 2 ? 25 : 25 + (index / (dates.length - 1)) * 570;
    const y = (value) => 193 - (value / max) * 168;
    const polyline = (variant, color) => {
      const points = dates.map((date, index) => {
        const row = rows.find((candidate) => candidate.snapshot_date === date && candidate.variant === variant);
        return `${x(index)},${y(Number(row?.cumulative_revenue) || 0)}`;
      }).join(" ");
      return `<polyline points="${points}" fill="none" stroke="${color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />`;
    };
    const lastDate = dates.at(-1) || "—";
    return `
      <svg viewBox="0 0 620 220" role="img" aria-label="Cumulative revenue over the fourteen-day sample trend">
        <line x1="25" y1="25" x2="595" y2="25" stroke="#d7d2c4" stroke-width="1" />
        <line x1="25" y1="109" x2="595" y2="109" stroke="#d7d2c4" stroke-width="1" stroke-dasharray="3 4" />
        <line x1="25" y1="193" x2="595" y2="193" stroke="#d7d2c4" stroke-width="1" />
        <text x="25" y="17" fill="#70756e" font-size="9">${escapeHtml(money(max))}</text>
        <text x="25" y="105" fill="#70756e" font-size="9">${escapeHtml(money(max / 2))}</text>
        <text x="25" y="216" fill="#70756e" font-size="9">$0</text>
        ${polyline("control", "#101416")}
        ${polyline("treatment", "#71951e")}
      </svg>
      <div class="trend-axis"><span>${escapeHtml(dates[0] || "—")}</span><span>last observed ${escapeHtml(lastDate)}</span></div>
      <div class="chart-legend"><span class="legend-item"><span class="legend-swatch"></span>control</span><span class="legend-item"><span class="legend-swatch lime"></span>treatment</span></div>
    `;
  }

  function renderTraceability(payload) {
    const files = Object.entries(payload.source_manifest?.files || {});
    return `
      <div class="trace-panel">
        <h3>Lineage from source to screen</h3>
        <ol class="trace-list">
          ${(payload.lineage || []).map((item) => `<li><span class="trace-stage">${escapeHtml(item.stage)}</span><span class="trace-artifact">${escapeHtml(item.artifact)}<span class="trace-description">${escapeHtml(item.description)}</span></span></li>`).join("")}
        </ol>
      </div>
      <div class="trace-panel">
        <h3>Source manifest</h3>
        <div class="source-manifest">
          <div class="manifest-row"><span>seed</span><strong>${escapeHtml(number(payload.source_manifest?.seed))}</strong></div>
          <div class="manifest-row"><span>users requested</span><strong>${escapeHtml(number(payload.source_manifest?.n_users_requested))}</strong></div>
          ${files.map(([name, detail]) => `<div class="manifest-row"><span>${escapeHtml(name)}</span><strong>${escapeHtml(number(detail.rows))} rows</strong></div>`).join("")}
        </div>
      </div>
    `;
  }

  function renderMethodology(payload) {
    const primary = payload.methodology?.primary_metric || {};
    const adjustment = payload.methodology?.multiple_testing || {};
    const practical = payload.methodology?.practical_significance || {};
    return `
      <details class="methodology">
        <summary>Methodology, definitions, and limitations</summary>
        <div class="methodology-body">
          <div><h4>Metric definition</h4><p><strong>${escapeHtml(primary.name || "conversion_rate")}</strong> is measured at the ${escapeHtml(primary.grain || "assigned user")} grain. Numerator: ${escapeHtml(primary.numerator)}. Denominator: ${escapeHtml(primary.denominator)}.</p></div>
          <div><h4>Uncertainty</h4><p>${escapeHtml(payload.methodology?.uncertainty || "The interval is calculated from the user-level conversion rates.")}</p><h4>Adjustment</h4><p>${escapeHtml(adjustment.method || "Holm-Bonferroni")} is applied to the primary and secondary metric family. ${escapeHtml(adjustment.segments || "Segments remain exploratory.")}</p></div>
          <div><h4>Practical threshold</h4><p>The relative lift threshold is <strong>${escapeHtml(pct(practical.threshold || 0.01))}</strong>. Statistical significance alone is not enough to launch or stop.</p><h4>Limitations</h4><p>${(payload.limitations || []).map(escapeHtml).join(" ")}</p></div>
        </div>
      </details>
    `;
  }

  function renderValidator() {
    return `
      <section class="validator-panel" aria-labelledby="validator-title">
        <div class="panel-header"><div><h3 id="validator-title">Validate a CSV locally</h3><p>Schema checks are safe to run in-browser. No file is uploaded or analyzed here.</p></div><span class="panel-aside">optional</span></div>
        <div class="validator-body">
          <label class="file-drop" id="file-drop" for="csv-file"><strong>Drop a CSV or choose a file</strong><span>Validation stays on this device</span><input id="csv-file" type="file" accept=".csv,text/csv" /></label>
          <div class="schema-list"><p>Choose the expected contract:</p><select id="schema-select" aria-label="CSV schema"><option value="raw_experiment_assignments">raw_experiment_assignments.csv</option><option value="raw_events">raw_events.csv</option><option value="raw_orders">raw_orders.csv</option></select><p>Required headers: <code id="schema-headers"></code></p><div id="validation-result" class="validation-result" role="status">Waiting for a file.</div></div>
        </div>
      </section>
    `;
  }

  function renderWorkspace(payload) {
    const analysis = payload.analysis;
    const decision = decisionLabel(analysis.decision);
    const primaryMetric = payload.metrics?.conversion_rate || {};
    const quality = payload.quality.summary;
    const pValue = analysis.adjusted_p_value;
    const effectClass = analysis.practical_significance ? "positive" : "warning";
    return `
      <section class="decision-hero">
        <div><p class="eyebrow"><span class="eyebrow-index">03</span> ${escapeHtml(payload.ui?.status_label || "sample workspace")}</p><h1>${escapeHtml(payload.experiment.title)}<br /><span class="decision-word">${escapeHtml(decision)}</span></h1><p class="decision-copy">${escapeHtml(decisionDescription(analysis.decision))} ${escapeHtml(payload.ui?.takeaway || "")}</p></div>
        <div class="decision-meta"><div class="hypothesis-card"><span class="label">hypothesis</span><p>${escapeHtml(payload.experiment.hypothesis)}</p></div><div class="source-line"><span>${escapeHtml(payload.experiment.owner)}</span><span>${escapeHtml(payload.experiment.sample_profile)} profile</span></div></div>
      </section>
      <section class="decision-banner" data-decision="${escapeHtml(analysis.decision)}" aria-labelledby="decision-title"><div><span class="banner-label">recommendation</span><h2 id="decision-title">${escapeHtml(decision)}${analysis.decision === "investigate" ? " before acting" : " with the evidence"}</h2><p class="banner-reason">${escapeHtml(analysis.rationale?.[0] || decisionDescription(analysis.decision))}</p></div><div class="banner-score"><strong>${escapeHtml(pct(analysis.relative_lift))}</strong><span>primary lift · ${escapeHtml(quality)} quality</span></div></section>

      <section class="content-section" aria-labelledby="metric-title"><div class="section-kicker"><div><p class="eyebrow"><span class="eyebrow-index">04</span> the primary readout</p><h2 id="metric-title">What changed?</h2></div><p>Start with the assigned-user denominator, then follow the effect into uncertainty and practical significance.</p></div>
        <div class="metrics-layout"><article class="paper-panel metric-card"><div class="metric-card-header"><div><h3>Purchase conversion rate</h3><p class="metric-definition">${escapeHtml(primaryMetric.numerator || "Users with at least one post-assignment purchase event")} / ${escapeHtml(primaryMetric.denominator || "canonically assigned users")}</p></div><span class="metric-unit">${escapeHtml(primaryMetric.grain || "assigned_user")} grain</span></div><div class="effect-chart">${renderEffectChart(analysis)}<div class="effect-axis"><span>${escapeHtml(signedPct(analysis.ci_lower, 1))}</span><span>95% interval · treatment − control</span><span>${escapeHtml(signedPct(analysis.ci_upper, 1))}</span></div><div class="chart-legend"><span class="legend-item"><span class="legend-swatch lime"></span>point estimate + interval</span><span class="legend-item"><span class="legend-swatch"></span>zero effect</span></div></div><table class="comparison-table"><thead><tr><th>metric</th><th>control</th><th>treatment</th></tr></thead><tbody>${renderComparison(analysis)}</tbody></table></article><div class="evidence-stack"><article class="evidence-card"><span class="evidence-card-label">relative lift</span><strong class="evidence-card-value ${effectClass}">${escapeHtml(signedPct(analysis.relative_lift, 2))}</strong><p class="evidence-card-note">Treatment versus control.</p></article><article class="evidence-card"><span class="evidence-card-label">adjusted p-value</span><strong class="evidence-card-value ${pValue < 0.05 ? "positive" : "warning"}">${escapeHtml(pValue < 0.001 ? "< 0.001" : pValue.toFixed(3))}</strong><p class="evidence-card-note">${escapeHtml(analysis.multiple_testing_method)} across 2 confirmatory metrics.</p></article><article class="evidence-card"><span class="evidence-card-label">practical gate</span><strong class="evidence-card-value ${analysis.practical_significance ? "positive" : "warning"}">${analysis.practical_significance ? "cleared" : "not cleared"}</strong><p class="evidence-card-note">Minimum relative change: ${escapeHtml(pct(analysis.practical_threshold))}.</p></article></div></div>
      </section>

      <section class="content-section" aria-labelledby="quality-title"><div class="section-kicker"><div><p class="eyebrow"><span class="eyebrow-index">05</span> trust the denominator</p><h2 id="quality-title">Can we trust it?</h2></div><p>Critical failures block the product call. Warnings stay visible so the operator can decide what to investigate next.</p></div><article class="paper-panel quality-panel">${renderQuality(payload.quality)}</article></section>

      <section class="content-section" aria-labelledby="guardrail-title"><div class="section-kicker"><div><p class="eyebrow"><span class="eyebrow-index">06</span> what could break?</p><h2 id="guardrail-title">Guardrails</h2></div><p>Conversion is not the only outcome. Treatment should not quietly reduce engagement or increase customer-operations load.</p></div><div class="guardrail-grid">${renderGuardrails(payload)}</div></section>

      <section class="content-section" aria-labelledby="context-title"><div class="section-kicker"><div><p class="eyebrow"><span class="eyebrow-index">07</span> context, not camouflage</p><h2 id="context-title">Segments and trend</h2></div><p>These views explain the shape of the result. They are not permission to cherry-pick a segment.</p></div><div class="detail-grid"><article class="paper-panel trend-panel"><div class="panel-header"><div><h3>Cumulative revenue by day</h3><p>Positive revenue only · post-assignment window</p></div><span class="panel-aside">14 days</span></div><div class="trend-chart">${renderTrend(payload)}</div></article><article class="paper-panel segment-panel"><div class="panel-header"><div><h3>Conversion by segment</h3><p>Exploratory cuts by user segment</p></div><span class="panel-aside">3 segments</span></div><table class="segment-table"><thead><tr><th>segment</th><th>control</th><th>treatment</th><th>delta</th></tr></thead><tbody>${renderSegments(payload)}</tbody></table></article></div></section>

      <section class="content-section" aria-labelledby="trace-title"><div class="section-kicker"><div><p class="eyebrow"><span class="eyebrow-index">08</span> trace it back</p><h2 id="trace-title">Evidence map</h2></div><p>Every panel on this page is a view over the generated artifact contract below.</p></div><div class="traceability-layout">${renderTraceability(payload)}</div>${renderMethodology(payload)}${renderValidator()}</section>
    `;
  }

  function parseCsvHeader(line) {
    const values = [];
    let current = "";
    let quoted = false;
    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      if (char === '"' && line[index + 1] === '"') { current += '"'; index += 1; continue; }
      if (char === '"') { quoted = !quoted; continue; }
      if (char === "," && !quoted) { values.push(current.trim()); current = ""; continue; }
      current += char;
    }
    values.push(current.trim());
    return values.filter(Boolean);
  }

  function bindValidator() {
    const input = $("#csv-file");
    const select = $("#schema-select");
    const headers = $("#schema-headers");
    const result = $("#validation-result");
    const drop = $("#file-drop");
    const updateSchema = () => { headers.textContent = schemas[select.value].join(", "); };
    const validate = async (file) => {
      if (!file) return;
      result.classList.remove("error");
      result.innerHTML = "Reading the header locally…";
      try {
        const text = await file.text();
        const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
        const actual = lines.length ? parseCsvHeader(lines[0]) : [];
        const required = schemas[select.value];
        const missing = required.filter((field) => !actual.includes(field));
        if (!lines.length || missing.length) {
          result.classList.add("error");
          result.innerHTML = `<strong>Not ready for analysis.</strong> Missing ${escapeHtml(missing.length ? missing.join(", ") : "a header row")}.`;
          return;
        }
        result.innerHTML = `<strong>Schema looks valid.</strong> ${escapeHtml(file.name)} has ${escapeHtml(number(lines.length - 1))} data rows and all required headers.`;
      } catch (error) {
        result.classList.add("error");
        result.innerHTML = `<strong>Could not read this file.</strong> ${escapeHtml(error.message)}`;
      }
    };
    updateSchema();
    select.addEventListener("change", () => { updateSchema(); if (input.files[0]) validate(input.files[0]); });
    input.addEventListener("change", () => validate(input.files[0]));
    ["dragenter", "dragover"].forEach((eventName) => drop.addEventListener(eventName, (event) => { event.preventDefault(); drop.classList.add("dragover"); }));
    ["dragleave", "drop"].forEach((eventName) => drop.addEventListener(eventName, (event) => { event.preventDefault(); drop.classList.remove("dragover"); }));
    drop.addEventListener("drop", (event) => validate(event.dataTransfer.files[0]));
  }

  async function openWorkspace(id, push = true) {
    const item = state.catalog.experiments.find((candidate) => candidate.id === id);
    if (!item) return renderLanding();
    showView("loading");
    try {
      state.payload = await fetchJson(`data/${item.path}`);
      $("#workspace-content").innerHTML = renderWorkspace(state.payload);
      renderWorkspaceOptions(item.id);
      if (push) history.pushState({ experiment: item.id }, "", `?experiment=${encodeURIComponent(item.id)}`);
      showView("workspace");
      bindValidator();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      $("#error-message").textContent = error.message;
      showView("error");
    }
  }

  async function boot() {
    showView("loading");
    try {
      state.catalog = await fetchJson("data/catalog.json");
      if (!Array.isArray(state.catalog.experiments)) throw new Error("The artifact catalog is empty or malformed.");
      $("#back-button").onclick = () => { history.pushState({}, "", window.location.pathname); renderLanding(); window.scrollTo({ top: 0, behavior: "smooth" }); };
      $("#brand-home").onclick = (event) => { event.preventDefault(); history.pushState({}, "", window.location.pathname); renderLanding(); window.scrollTo({ top: 0, behavior: "smooth" }); };
      $("#retry-button").onclick = boot;
      renderLanding();
      const requested = new URLSearchParams(window.location.search).get("experiment");
      if (requested && state.catalog.experiments.some((item) => item.id === requested)) await openWorkspace(requested, false);
    } catch (error) {
      $("#error-message").textContent = error.message;
      showView("error");
    }
  }

  window.addEventListener("popstate", () => {
    const requested = new URLSearchParams(window.location.search).get("experiment");
    if (requested && state.catalog) openWorkspace(requested, false);
    else if (state.catalog) renderLanding();
  });

  boot();
})();
