"""Small, dependency-free helpers for orbital element age summaries."""

import math


def add_epoch_age_summary(payload):
    """Fill youngest and oldest epoch ages from per-record freshness data."""
    freshness = payload.get("tle_freshness")
    if not isinstance(freshness, dict):
        return payload

    records = freshness.get("records")
    ages = []

    if isinstance(records, list):
        for record in records:
            if not isinstance(record, dict):
                continue

            age = record.get("age_hours")
            if (
                isinstance(age, (int, float))
                and not isinstance(age, bool)
                and math.isfinite(age)
            ):
                ages.append(float(age))

    freshness["youngest_age_hours"] = min(ages) if ages else None
    freshness["oldest_age_hours"] = max(ages) if ages else None
    return payload
