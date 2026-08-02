"""Generate deterministic source data for a product experimentation platform."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_NAME = "checkout_progress_indicator"
CONTROL = "control"
TREATMENT = "treatment"


@dataclass(frozen=True)
class DemoDataManifest:
    """Summary of generated source files."""

    files: list[Path]
    n_users: int
    experiment_name: str
    seed: int


def _choice(rng: np.random.Generator, values: list[str], size: int, p: list[float] | None = None) -> np.ndarray:
    return rng.choice(values, size=size, p=p)


def _timestamp_series(start: str, minutes: np.ndarray) -> pd.Series:
    base = pd.Timestamp(start)
    return pd.Series(base + pd.to_timedelta(minutes, unit="m"))


def generate_demo_data(
    output_dir: str | Path,
    seed: int = 42,
    n_users: int = 5000,
    experiment_name: str = EXPERIMENT_NAME,
    quality_profile: str = "flawed",
    treatment_lift: float | None = None,
) -> DemoDataManifest:
    """Generate raw source CSVs for an end-to-end experimentation workflow.

    The data is intentionally rich enough to support warehouse modeling:
    assignments, events, sessions, orders, feature exposures, support tickets,
    and daily user snapshots. It also includes realistic data quality issues
    so the platform can demonstrate audit behavior.
    """

    if quality_profile not in {"flawed", "clean"}:
        raise ValueError("quality_profile must be 'flawed' or 'clean'")

    rng = np.random.default_rng(seed)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    user_ids = np.arange(1, n_users + 1)
    segments = _choice(rng, ["new", "returning", "power"], n_users, [0.34, 0.46, 0.20])
    devices = _choice(rng, ["ios", "android", "web"], n_users, [0.36, 0.34, 0.30])
    regions = _choice(rng, ["west", "south", "midwest", "northeast"], n_users, [0.33, 0.25, 0.20, 0.22])
    acquisition_channels = _choice(
        rng, ["paid_search", "organic", "partner", "lifecycle"], n_users, [0.28, 0.36, 0.14, 0.22]
    )
    signup_minutes = rng.integers(0, 70 * 24 * 60, size=n_users)

    users = pd.DataFrame(
        {
            "user_id": user_ids,
            "signup_date": _timestamp_series("2025-12-15", signup_minutes).dt.date.astype(str),
            "segment": segments,
            "device": devices,
            "region": regions,
            "acquisition_channel": acquisition_channels,
        }
    )

    variants = _choice(rng, [CONTROL, TREATMENT], n_users, [0.501, 0.499])
    assigned_minutes = rng.integers(0, 14 * 24 * 60, size=n_users)
    assignments = pd.DataFrame(
        {
            "assignment_id": np.arange(1, n_users + 1),
            "experiment_name": experiment_name,
            "user_id": user_ids,
            "variant": variants,
            "assigned_at": _timestamp_series("2026-03-01", assigned_minutes).dt.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    if quality_profile == "flawed":
        duplicate_count = max(8, n_users // 160)
        duplicates = assignments.sample(duplicate_count, random_state=seed).copy()
        duplicates["assignment_id"] = np.arange(n_users + 1, n_users + 1 + duplicate_count)
        switch_count = max(2, duplicate_count // 5)
        switched = duplicates.index[:switch_count]
        duplicates.loc[switched, "variant"] = np.where(
            duplicates.loc[switched, "variant"] == CONTROL, TREATMENT, CONTROL
        )
        assignments = pd.concat([assignments, duplicates], ignore_index=True)

    canonical_assignments = assignments.sort_values(["assigned_at", "assignment_id"]).drop_duplicates(
        ["experiment_name", "user_id"]
    )
    assignment_lookup = canonical_assignments.set_index("user_id")

    session_rows: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    order_rows: list[dict[str, object]] = []
    exposure_rows: list[dict[str, object]] = []
    ticket_rows: list[dict[str, object]] = []
    snapshot_rows: list[dict[str, object]] = []

    session_id = 1
    event_id = 1
    order_id = 1
    exposure_id = 1
    ticket_id = 1
    event_names = ["view_home", "search", "view_product", "add_to_cart", "checkout_start", "purchase"]

    segment_session_lambda = {"new": 2.1, "returning": 3.2, "power": 6.3}
    segment_base_conversion = {"new": 0.038, "returning": 0.061, "power": 0.103}
    segment_ticket_prob = {"new": 0.035, "returning": 0.027, "power": 0.018}

    for user_id in user_ids:
        user = users.loc[users["user_id"] == user_id].iloc[0]
        assignment = assignment_lookup.loc[user_id]
        variant = str(assignment["variant"])
        segment = str(user["segment"])
        assigned_at = pd.Timestamp(assignment["assigned_at"])

        n_sessions = int(rng.poisson(segment_session_lambda[segment])) + 1
        conversion_prob = segment_base_conversion[segment] + (
            (0.014 if treatment_lift is None else treatment_lift) if variant == TREATMENT else 0.0
        )
        checkout_prob = min(0.55, conversion_prob * 4.8)
        cumulative_events = 0
        cumulative_sessions = 0
        cumulative_revenue = 0.0

        exposure_rows.append(
            {
                "exposure_id": exposure_id,
                "experiment_name": experiment_name,
                "user_id": user_id,
                "variant": variant,
                "surface": "checkout",
                "exposed_at": assigned_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        exposure_id += 1

        for session_number in range(n_sessions):
            started_at = assigned_at + pd.to_timedelta(int(rng.integers(0, 14 * 24 * 60)), unit="m")
            duration_seconds = int(max(30, rng.normal(430 if segment == "power" else 300, 110)))
            session_rows.append(
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": duration_seconds,
                    "device": user["device"],
                }
            )

            session_events = ["view_home"]
            if rng.random() < 0.62:
                session_events.append("search")
            if rng.random() < 0.74:
                session_events.append("view_product")
            if rng.random() < checkout_prob:
                session_events.extend(["add_to_cart", "checkout_start"])
            made_purchase = rng.random() < conversion_prob
            if made_purchase:
                session_events.append("purchase")

            for offset, event_name in enumerate(session_events):
                event_rows.append(
                    {
                        "event_id": event_id,
                        "session_id": session_id,
                        "user_id": user_id,
                        "event_name": event_name,
                        "event_at": (started_at + pd.to_timedelta(offset * 43, unit="s")).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "source": "product",
                    }
                )
                event_id += 1
                cumulative_events += 1

            if made_purchase:
                revenue = round(float(rng.gamma(2.4, 24.0)), 2)
                order_rows.append(
                    {
                        "order_id": order_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "order_at": (started_at + pd.to_timedelta(5, unit="m")).strftime("%Y-%m-%d %H:%M:%S"),
                        "revenue": revenue,
                        "currency": "USD",
                    }
                )
                order_id += 1
                cumulative_revenue += revenue

            cumulative_sessions += 1
            session_id += 1

        if rng.random() < segment_ticket_prob[segment]:
            priority = str(_choice(rng, ["low", "medium", "high", "urgent"], 1, [0.35, 0.36, 0.20, 0.09])[0])
            ticket_rows.append(
                {
                    "ticket_id": ticket_id,
                    "user_id": user_id,
                    "created_at": (assigned_at + pd.to_timedelta(int(rng.integers(0, 14 * 24 * 60)), unit="m")).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "category": str(_choice(rng, ["billing", "checkout", "account", "bug"], 1)[0]),
                    "priority": priority,
                    "first_response_minutes": int(max(5, rng.normal(90 if priority in {"high", "urgent"} else 240, 45))),
                }
            )
            ticket_id += 1

        for day in range(14):
            snapshot_date = (assigned_at.normalize() + pd.to_timedelta(day, unit="D")).date().isoformat()
            snapshot_rows.append(
                {
                    "snapshot_date": snapshot_date,
                    "user_id": user_id,
                    "experiment_name": experiment_name,
                    "variant": variant,
                    "segment": segment,
                    "cumulative_sessions": cumulative_sessions if day == 13 else int(cumulative_sessions * (day + 1) / 14),
                    "cumulative_events": cumulative_events if day == 13 else int(cumulative_events * (day + 1) / 14),
                    "cumulative_revenue": round(cumulative_revenue * (day + 1) / 14, 2),
                }
            )

    sessions = pd.DataFrame(session_rows)
    events = pd.DataFrame(event_rows)
    orders = pd.DataFrame(order_rows)
    exposures = pd.DataFrame(exposure_rows)
    tickets = pd.DataFrame(ticket_rows)
    snapshots = pd.DataFrame(snapshot_rows)

    if quality_profile == "flawed" and not events.empty:
        null_count = max(4, len(events) // 900)
        null_indices = events.sample(null_count, random_state=seed + 10).index
        events.loc[null_indices, "event_name"] = None
        early_indices = events.sample(max(3, len(events) // 1100), random_state=seed + 11).index
        events.loc[early_indices, "event_at"] = "2026-02-20 00:00:00"

    if quality_profile == "flawed" and not orders.empty:
        negative_indices = orders.sample(max(2, len(orders) // 150), random_state=seed + 12).index
        orders.loc[negative_indices, "revenue"] = -10.00

    if tickets.empty:
        tickets = pd.DataFrame(
            [
                {
                    "ticket_id": 1,
                    "user_id": int(user_ids[0]),
                    "created_at": "2026-03-03 12:00:00",
                    "category": "checkout",
                    "priority": "urgent",
                    "first_response_minutes": 155,
                }
            ]
        )
    elif "urgent" not in set(tickets["priority"]):
        tickets.loc[tickets.index[0], "priority"] = "urgent"

    outputs = {
        "raw_users.csv": users,
        "raw_experiment_assignments.csv": assignments,
        "raw_events.csv": events,
        "raw_sessions.csv": sessions,
        "raw_orders.csv": orders,
        "raw_feature_exposures.csv": exposures,
        "raw_support_tickets.csv": tickets,
        "raw_user_daily_snapshots.csv": snapshots,
    }

    files: list[Path] = []
    for filename, frame in outputs.items():
        path = output_path / filename
        frame.to_csv(path, index=False)
        files.append(path)

    return DemoDataManifest(files=files, n_users=n_users, experiment_name=experiment_name, seed=seed)
