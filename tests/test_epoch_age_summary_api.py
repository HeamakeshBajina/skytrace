from skytrace.epoch_age import add_epoch_age_summary


def test_epoch_age_summary_uses_record_minimum_and_maximum():
    payload = {
        "tle_freshness": {
            "records": [
                {"age_hours": 16.3, "status": "fresh"},
                {"age_hours": 42.7, "status": "stale"},
                {"age_hours": 8.2, "status": "fresh"},
            ]
        }
    }

    result = add_epoch_age_summary(payload)

    assert result["tle_freshness"]["youngest_age_hours"] == 8.2
    assert result["tle_freshness"]["oldest_age_hours"] == 42.7


def test_epoch_age_summary_ignores_invalid_values():
    payload = {
        "tle_freshness": {
            "records": [
                {"age_hours": 12.5},
                {"age_hours": None},
                {"age_hours": "invalid"},
                {"age_hours": float("nan")},
                {"age_hours": float("inf")},
                None,
            ]
        }
    }

    result = add_epoch_age_summary(payload)

    assert result["tle_freshness"]["youngest_age_hours"] == 12.5
    assert result["tle_freshness"]["oldest_age_hours"] == 12.5


def test_epoch_age_summary_returns_null_when_no_valid_ages_exist():
    payload = {"tle_freshness": {"records": [{"age_hours": None}]}}

    result = add_epoch_age_summary(payload)

    assert result["tle_freshness"]["youngest_age_hours"] is None
    assert result["tle_freshness"]["oldest_age_hours"] is None
