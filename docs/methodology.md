# Methodology

## Decision states

The product maps analysis evidence to four operator-facing states:

| State | Gate |
|---|---|
| `launch` | No critical quality failures; adjusted primary evidence is significant and positive; relative lift clears the practical threshold. |
| `stop` | No critical quality failures; adjusted primary evidence is significant and negative; practical harm clears the threshold. |
| `continue` | No critical quality failure, but evidence or practical effect is not strong enough for launch/stop. |
| `investigate` | At least one critical quality check fails. The observed effect is not safe to use as a product decision. |

The existing `recommendation` field (`launch`, `hold`, `iterate`) is preserved for compatibility with the CLI and Markdown reports. The browser uses the more explicit `decision` field.

## Primary metric

`conversion_rate` is measured at the assigned-user grain:

- numerator: users with at least one post-assignment purchase event;
- denominator: canonically assigned users, keeping the first assignment by assignment timestamp and ID;
- test: two-proportion z-test;
- uncertainty: 95% normal-approximation confidence interval for treatment minus control.

The warehouse excludes non-positive order revenue from `revenue_per_user` and uses the same post-assignment window for events, sessions, orders, and support tickets.

## Multiple testing

The primary conversion metric and revenue-per-user secondary metric form the confirmatory family. Their p-values are adjusted with Holm-Bonferroni before the browser upgrades a result to `launch` or `stop`. Segment cuts are visible for diagnosis but remain exploratory and cannot upgrade the decision.

## Practical significance

The experiment registry sets a minimum relative lift of 1%. A small, statistically detectable movement is not automatically a launch or stop call. The browser shows the observed relative lift and the threshold side by side.

## Guardrails and quality

Sessions per user, average session duration, support tickets per user, and high-priority ticket burden provide operating context. Assignment duplicates, multiple variants, missing timestamps, events before assignment, null events, negative revenue, missing mart rows, and session-ratio degradation are surfaced as explicit checks. Critical failures map to `investigate`.
