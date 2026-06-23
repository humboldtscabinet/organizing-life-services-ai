from app.services import gbp_service


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "multiDailyMetricTimeSeries": [
                {
                    "dailyMetricTimeSeries": [
                        {
                            "dailyMetric": "WEBSITE_CLICKS",
                            "timeSeries": {
                                "datedValues": [
                                    {
                                        "date": {"year": 2026, "month": 6, "day": 20},
                                        "value": "4",
                                    }
                                ]
                            },
                        },
                        {
                            "dailyMetric": "CALL_CLICKS",
                            "timeSeries": {
                                "datedValues": [
                                    {
                                        "date": {"year": 2026, "month": 6, "day": 20},
                                        "value": "2",
                                    }
                                ]
                            },
                        },
                    ]
                }
            ]
        }


class _FakeDb:
    def __init__(self):
        self.added = []
        self.commit_count = 0

    def add(self, record):
        self.added.append(record)

    def commit(self):
        self.commit_count += 1


def test_pull_gbp_data_uses_get_query_params_and_empty_body(monkeypatch):
    calls = []

    def fake_get(url, headers, params, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }
        )
        return _FakeResponse()

    monkeypatch.setattr(gbp_service, "_auth_headers", lambda: {"Authorization": "Bearer test"})
    monkeypatch.setattr(gbp_service.httpx, "get", fake_get)

    db = _FakeDb()
    result = gbp_service.pull_gbp_data(db=db, location_id="locations/123", days_back=1)

    assert result["status"] == "success"
    assert result["rows_inserted"] == 2
    assert db.commit_count == 2
    assert len(db.added) == 3  # two GBPInsight rows plus one WorkflowLog

    call = calls[0]
    assert call["url"].endswith("/locations/123:fetchMultiDailyMetricsTimeSeries")
    assert call["headers"] == {"Authorization": "Bearer test"}
    assert call["timeout"] == 60

    params = call["params"]
    metric_params = [value for key, value in params if key == "dailyMetrics"]
    assert metric_params == gbp_service.DAILY_METRICS
    assert any(key == "dailyRange.start_date.year" for key, _value in params)
    assert any(key == "dailyRange.end_date.day" for key, _value in params)
